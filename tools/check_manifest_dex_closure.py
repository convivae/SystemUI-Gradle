#!/usr/bin/env python3
"""Task 050 — packaged-manifest-to-DEX closure gate.

Asserts that every class referenced by the PACKAGED APK manifest (component
android:name attributes for activity/service/receiver/provider/activity-alias,
the application android:name / android:backupAgent, and activity-alias
android:targetActivity) exists as a defined class in the APK's DEX files.

The manifest is read from the packaged APK itself (via `aapt2 dump xmltree`),
so AGP's package-relative-name expansion is exercised exactly as the platform
PackageManager would see it at runtime.

Usage:
    python3 tools/check_manifest_dex_closure.py --apk app/build/outputs/apk/debug/app-debug.apk

Exit 0 = PASS (all manifest entry classes defined in DEX).
Exit 1 = FAIL (at least one missing class).
Exit 2 = tool error.
"""

import argparse
import re
import struct
import subprocess
import sys
import zipfile


MANIFEST_COMPONENT_TAGS = {
    "activity", "service", "receiver", "provider", "activity-alias",
}
MANIFEST_ATTRS = {
    "name",
    "backupAgent",
    "targetActivity",
}
# Manifest attributes that reference classes but must NOT be treated as
# component-name expansion candidates; they are always absolute already or
# non-class values, and are excluded from the closure set.
NON_CLASS_ATTRS = set()


def dex_defined_classes(dex_bytes):
    """Return the set of type descriptors defined by one DEX file.

    Minimal reader: header -> string_ids -> type_ids -> class_defs.
    class_def_off points at fixed-size (32-bit field) records, so no uleb128
    decoding is needed for this purpose.
    """
    if dex_bytes[0:4] != b"dex\n":
        raise ValueError("not a DEX file")
    string_ids_size, string_ids_off = struct.unpack_from(
        "<II", dex_bytes, 0x38)
    type_ids_size, type_ids_off = struct.unpack_from(
        "<II", dex_bytes, 0x40)
    class_defs_size, class_defs_off = struct.unpack_from(
        "<II", dex_bytes, 0x60)

    # MUTF-8 strings are NUL-terminated; class names are ASCII-safe here.
    def read_string(idx):
        off = struct.unpack_from("<I", dex_bytes, string_ids_off + 4 * idx)[0]
        # skip uleb128 utf16 length
        i = off
        while dex_bytes[i] & 0x80:
            i += 1
        i += 1
        end = dex_bytes.index(b"\x00", i)
        return dex_bytes[i:end].decode("utf-8", errors="replace")

    def type_descriptor(idx):
        str_idx = struct.unpack_from("<I", dex_bytes, type_ids_off + 4 * idx)[0]
        return read_string(str_idx)

    classes = set()
    for i in range(class_defs_size):
        rec = class_defs_off + 32 * i
        type_idx = struct.unpack_from("<I", dex_bytes, rec)[0]
        classes.add(type_descriptor(type_idx))
    del string_ids_size, type_ids_size
    return classes


def descriptor_to_name(descriptor):
    # Lcom/android/systemui/Foo; -> com.android.systemui.Foo
    return descriptor[1:-1].replace("/", ".")


def manifest_entry_classes(apk_path, aapt2):
    """Extract (tag, class_name) pairs from the packaged binary manifest."""
    proc = subprocess.run(
        [aapt2, "dump", "xmltree", "--file", "AndroidManifest.xml", apk_path],
        capture_output=True, text=True, check=True)
    entries = []
    package = None
    # Example lines:
    #   A: package="com.android.systemui" (Raw: "com.android.systemui")
    #   E: activity (line=123)
    #     A: http://schemas.android.com/apk/res/android:name(0x01010003)="..." (Raw: "...")
    tag_re = re.compile(r"^\s*E: (\S[-\w]*) \(line=\d+\)")
    attr_re = re.compile(
        r"^\s*A: (?:http://schemas\.android\.com/apk/res/android:)?(\S+?)\(0x[0-9a-f]+\)=(.*)$")
    current_tag = None
    for line in proc.stdout.splitlines():
        m = tag_re.match(line)
        if m:
            current_tag = m.group(1)
            continue
        if current_tag == "manifest":
            mm = re.match(r'^\s*A: package="([^"]+)"', line)
            if mm:
                package = mm.group(1)
            continue
        m = attr_re.match(line)
        if not m:
            continue
        attr, value = m.group(1), m.group(2).strip()
        if current_tag is None or attr not in MANIFEST_ATTRS:
            continue
        if attr in NON_CLASS_ATTRS:
            continue
        if current_tag not in MANIFEST_COMPONENT_TAGS and current_tag != "application":
            continue
        # String values look like "..." or "..." (Raw: "...")
        mm = re.match(r'^"([^"]+)"', value)
        if not mm:
            continue
        name = mm.group(1)
        if name.startswith(".") and package:
            name = package + name
        elif (not name.startswith(".") and current_tag in MANIFEST_COMPONENT_TAGS
              and attr == "name" and "." not in name.split("$")[0]):
            # Bare class name relative to package (rare); expand.
            name = package + "." + name
        entries.append((current_tag, attr, name))
    return package, entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk", required=True)
    ap.add_argument("--aapt2", default="/home/conv/Android/Sdk/build-tools/37.0.0/aapt2")
    args = ap.parse_args()

    with zipfile.ZipFile(args.apk) as zf:
        dex_names = sorted(
            n for n in zf.namelist()
            if re.fullmatch(r"classes\d*\.dex", n))
        defined = set()
        for n in dex_names:
            defined |= dex_defined_classes(zf.read(n))

    package, entries = manifest_entry_classes(args.apk, args.aapt2)
    if package is None:
        print("ERROR: could not read manifest package", file=sys.stderr)
        return 2

    print(f"APK={args.apk}")
    print(f"PACKAGE={package}")
    print(f"DEX_FILES={len(dex_names)}")
    print(f"DEFINED_CLASSES={len(defined)}")

    present, missing, aliases = [], [], []
    seen = set()
    for tag, attr, name in entries:
        key = (tag, attr, name)
        if key in seen:
            continue
        seen.add(key)
        # An activity-alias android:name is a manifest alias handle, not a
        # DEX class; PackageManager resolves the alias to its targetActivity
        # class, which IS checked below. Do not require an alias class.
        if tag == "activity-alias" and attr == "name":
            aliases.append(key)
            continue
        if ("L" + name.replace(".", "/") + ";") in defined:
            present.append(key)
        else:
            missing.append(key)

    print(f"MANIFEST_ENTRY_CLASSES={len(seen)} "
          f"(present={len(present)} alias={len(aliases)} missing={len(missing)})")
    for tag, attr, name in aliases:
        print(f"ALIAS {tag} {attr} {name} (handle only; targetActivity checked)")
    for tag, attr, name in missing:
        print(f"MISSING {tag} {attr} {name}")
    if missing:
        print("RESULT=FAIL")
        return 1
    print("RESULT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
