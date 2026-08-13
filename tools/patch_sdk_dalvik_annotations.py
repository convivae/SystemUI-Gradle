#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch android-SysUISdk jars with the missing dalvik.annotation.optimization
classes from AOSP core-libart, so javac can resolve @NeverCompile and siblings
on the compileSdk bootclasspath.

Background (docs/architecture/2026-08-13-nevercompile-classpath-options.md):
    SystemUI sources import `dalvik.annotation.optimization.NeverCompile` (and
    could later adopt NeverInline / DeadReferenceSafe / ReachabilitySensitive).
    The annotation is @Retention(CLASS), a compile-time-only no-op. Our
    SysUISdk android.jar / core-for-system-modules.jar ship only the
    CriticalNative + FastNative members of that package (public-SDK slice).
    Because the package already exists on the bootclasspath, javac's
    bootclasspath-first package resolution shadows the same classes that
    `compileOnly(android_module_lib_stubs_current.jar)` provides on the regular
    compile classpath → "cannot find symbol NeverCompile".

    Rule F (AGENTS.md §2.4 point 1) explicitly sanctions patching SysUISdk
    android.jar with AOSP framework.jar / core-libart classes. This tool
    injects ONLY the dalvik.annotation.optimization.* classes that are present
    in the AOSP core-libart javac jar but absent from the target SDK jar — no
    other packages, no overwrites of existing entries.

Idempotent: re-running reports "already patched" and mutates nothing. A
`<target>.orig` backup is created before the first mutation of each target
(matching the existing android.jar.orig precedent); an existing `.orig` is
never overwritten so the pristine pre-mutation state is preserved.

User authorization: 2026-08-13 ("同意a: Patch SysUISdk") — scoped to exactly
the dalvik.annotation.optimization classes. Any broader SDK change is
forbidden; halt and escalate.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# --- Configuration ---------------------------------------------------------

# AOSP core-libart javac jar (tier ② AOSP artifact, no resources).
# Prefer a `javac/` (never `turbine`) variant. Env override: CORE_LIBART_JAR.
DEFAULT_SOURCE_JAR = (
    "/home/conv/myspace/aosp/out/soong/.intermediates/libcore/"
    "core-libart/android_common_apex31/javac/core-libart.jar"
)

# Package whose classes are candidates for injection. Nothing outside this
# package is ever injected — this is the scope boundary of the user approval.
PACKAGE = "dalvik/annotation/optimization"

# SDK jars to patch (resolved under the SysUISdk platform dir).
TARGET_JARS = ("android.jar", "core-for-system-modules.jar")


# --- Helpers ---------------------------------------------------------------

def list_package_classes(jar_path: Path, package: str = PACKAGE) -> set:
    """Return the set of `Class.class` entry names under `package` in the jar.

    Entries are stored with forward slashes; the package dir has a trailing
    slash. Only `.class` files are returned (the bare directory entry is
    ignored).
    """
    prefix = package.rstrip("/") + "/"
    classes: set[str] = set()
    with zipfile.ZipFile(jar_path, "r") as archive:
        for name in archive.namelist():
            if name.startswith(prefix) and name.endswith(".class"):
                classes.add(name)
    return classes


def _jar_tool() -> str:
    jar = shutil.which("jar")
    if not jar:
        raise RuntimeError("`jar` (JDK) not found on PATH")
    return jar


def backup_if_needed(target: Path) -> str | None:
    """Create `<target>.orig` if it does not exist; return the backup path or
    None if a backup already existed (preserving the pristine pre-mutation
    state). Never overwrites an existing `.orig`.
    """
    orig = target.with_name(target.name + ".orig")
    if orig.exists():
        return None
    shutil.copy2(target, orig)
    return str(orig)


def update_jar(target: Path, staged_dir: Path, entries: list[str]) -> None:
    """`jar uf` the staged class entries into the target jar in place.

    `jar uf` preserves every existing entry byte-for-byte and only adds the
    listed entries. `entries` are archive-relative paths
    (e.g. `dalvik/annotation/optimization/NeverCompile.class`) that already
    exist under `staged_dir`. We run with cwd=staged_dir and pass the entries
    as relative paths: `jar`'s `-C` flag applies to only a single following
    file, so cwd-relative invocation is the robust form for multiple files.
    """
    if not entries:
        return
    cmd = [_jar_tool(), "uf", str(target)]
    cmd.extend(entries)
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(staged_dir))
    if proc.returncode != 0:
        raise RuntimeError(
            f"jar uf failed (rc={proc.returncode}):\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )


def patch_target(
    target: Path,
    source_jar: Path,
    package: str = PACKAGE,
    create_backup: bool = True,
) -> dict:
    """Patch one target jar with the optimization classes missing from it.

    Returns a dict:
      injected:    list of class entry names added (sorted)
      already:     list of class entry names already present (sorted)
      backup:      backup path created, or None
      source_jar:  the source jar path used
    Idempotent: if nothing is missing, no mutation occurs and `injected` is [].
    Never overwrites an existing class entry — only absent ones are injected.
    """
    if not target.is_file():
        raise FileNotFoundError(f"target jar not found: {target}")
    if not source_jar.is_file():
        raise FileNotFoundError(f"source jar not found: {source_jar}")

    src_classes = list_package_classes(source_jar, package)
    tgt_classes = list_package_classes(target, package)
    if not src_classes:
        raise RuntimeError(
            f"source jar has no classes under {package}/: {source_jar}"
        )

    missing = sorted(src_classes - tgt_classes)
    already = sorted(src_classes & tgt_classes)

    result = {
        "injected": missing,
        "already": already,
        "backup": None,
        "source_jar": str(source_jar),
    }
    if not missing:
        return result  # already patched — no-op

    if create_backup:
        result["backup"] = backup_if_needed(target)

    # Stage the missing .class files preserving their archive-relative path.
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        with zipfile.ZipFile(source_jar, "r") as src:
            for entry in missing:
                rel = entry  # e.g. dalvik/annotation/optimization/NeverCompile.class
                out = stage / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                with src.open(entry) as fh, open(out, "wb") as out_fh:
                    out_fh.write(fh.read())
        update_jar(target, stage, missing)

    return result


def _resolve_sdk_dir() -> Path:
    sdk_root = (
        os.environ.get("ANDROID_HOME")
        or os.environ.get("ANDROID_SDK_ROOT")
        or "/home/conv/Android/Sdk"
    )
    return Path(sdk_root) / "platforms" / "android-SysUISdk"


def main() -> int:
    source_jar = Path(os.environ.get("CORE_LIBART_JAR", DEFAULT_SOURCE_JAR))
    sdk_dir = _resolve_sdk_dir()
    if not sdk_dir.is_dir():
        print(f"ERROR: SysUISdk platform dir not found: {sdk_dir}", file=sys.stderr)
        return 1
    if not source_jar.is_file():
        print(f"ERROR: source jar not found: {source_jar}", file=sys.stderr)
        return 1

    print(f"SysUISdk:  {sdk_dir}")
    print(f"Source:    {source_jar}")
    print(f"Package:   {PACKAGE}/")
    print("")

    rc = 0
    for name in TARGET_JARS:
        target = sdk_dir / name
        print(f"== {name} ==")
        try:
            res = patch_target(target, source_jar)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}", file=sys.stderr)
            rc = 1
            continue
        if res["backup"]:
            print(f"  backup:   {res['backup']}")
        if res["injected"]:
            print(f"  injected: {len(res['injected'])}")
            for cls in res["injected"]:
                print(f"    + {cls}")
        else:
            print("  already patched (no-op)")
        print(f"  present:  {len(res['already'])}")
        print("")

    return rc


if __name__ == "__main__":
    sys.exit(main())
