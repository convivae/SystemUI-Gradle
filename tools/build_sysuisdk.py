#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproducible SysUISdk build pipeline (S0–S3 + S5 verify, staging-only).

Rebuilds the SysUISdk platform into a STAGING directory from tracked artifacts
and verifies inventory-level equivalence with the live SDK. The live SDK at
``~/Android/Sdk/platforms/android-SysUISdk`` is NEVER written to, renamed, or
deleted — this orchestrator hard-fails if the target resolves to it.

Stages (see docs/architecture/2026-08-13-sysuisdk-reproducible-build.md):
  S0  copy the base platform (android-37.0) to --target, rewrite package.xml
      for the staging name, copy build.prop / data / optional verbatim.
  S1  deterministic framework.jar merge into android.jar (framework is master;
      android.jar fills the gaps; MANIFEST.MF pinned to the audited live bytes).
      Source: libs/framework.jar (tracked).
  S2  framework.aidl hidden-iface/parcelable patch (reuses tools/install_sdk.py).
  S3  dalvik.annotation.optimization patch into both jars (reuses
      tools/patch_sdk_dalvik_annotations.py; source: AOSP core-libart javac jar).
  S5  --verify: compare staging vs live (entry inventories names+CRC for the two
      jars, byte-equality for framework.aidl, presence/shape for package.xml /
      build.prop / data / optional). Prints a per-file PASS/DIFF report and
      exits non-zero on any DIFF.

Authority: redline-gated (user pre-approval 2026-08-13, staging-only).
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# Make sibling tool modules importable when run as a script.
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import install_sdk  # noqa: E402
import patch_sdk_dalvik_annotations as _dalvik  # noqa: E402

# --- Configuration ---------------------------------------------------------

LIVE_SDK_DIR = Path("/home/conv/Android/Sdk/platforms/android-SysUISdk")
DEFAULT_BASE_PLATFORM = Path("/home/conv/Android/Sdk/platforms/android-37.0")
DEFAULT_TARGET = (
    Path.home() / "Android" / "Sdk" / "platforms" / "android-SysUISdk-staging"
)
_REPO_ROOT = _TOOLS_DIR.parent
DEFAULT_MERGED_JAR = _REPO_ROOT / "libs" / "android-merged.jar"
DEFAULT_CORE_LIBART_JAR = Path(
    "/home/conv/myspace/aosp/out/soong/.intermediates/libcore/"
    "core-libart/android_common_apex31/javac/core-libart.jar"
)

STAGING_DIR_NAME = "android-SysUISdk-staging"
STAGING_PKG_PATH = "platforms;android-SysUISdk-staging"
STAGING_API_LEVEL = "37"
STAGING_CODENAME = "SysUISdk"
STAGING_DISPLAY_NAME = "Android SDK Platform SysUISdk 37 (staging)"

# Audited live android.jar MANIFEST.MF bytes (produced by JDK `jar cf` on
# 2026-07-22; see docs/issues/2026-08-13-sysuisdk-reproducible-build.md §2.5).
# CRLF line endings, terminated by a blank CRLF line.
ANDROID_MANIFEST_BYTES = (
    b"Manifest-Version: 1.0\r\n"
    b"Created-By: 25.0.2 (Oracle Corporation)\r\n"
    b"\r\n"
)

# Files/dirs in the base platform that are pristine backups created by prior
# tool runs (or leftover scratch). S0 skips them so each stage creates its own
# backup of the freshly-copied base, matching the live SDK's backup pattern.
_BASE_SKIP_SUFFIXES = (".orig", ".bak-preaidl")

ALL_STAGES = ("s0", "s1", "s2", "s3")


# --- Helpers ---------------------------------------------------------------

def _resolve(p: Path) -> Path:
    return Path(p).expanduser().resolve()


def _live_guard(target: Path) -> None:
    """Hard-fail if target is the live SDK or inside it."""
    tgt = _resolve(target)
    live = _resolve(LIVE_SDK_DIR)
    try:
        tgt.relative_to(live)
        inside = True
    except ValueError:
        inside = tgt == live
    if inside:
        sys.exit(
            f"REFUSING to operate: --target {tgt} is the live SDK "
            f"({live}). The live SDK must never be written to."
        )


def _jar_inventory(jar_path: Path) -> dict:
    """Return {entry_name: CRC32} for non-directory entries in the jar."""
    inv: dict[str, int] = {}
    with zipfile.ZipFile(jar_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            inv[info.filename] = info.CRC
    return inv


def _ensure_file(path: Path, label: str) -> None:
    if not path.is_file():
        sys.exit(f"ERROR: {label} not found: {path}")


def _ensure_dir(path: Path, label: str) -> None:
    if not path.is_dir():
        sys.exit(f"ERROR: {label} not found: {path}")


def _backup_if_needed(target: Path, suffix: str) -> str | None:
    """Create ``<target><suffix>`` from target if it does not exist; return the
    backup path, or None if a backup already existed. Never overwrites."""
    bak = target.with_name(target.name + suffix)
    if bak.exists():
        return None
    shutil.copy2(target, bak)
    return str(bak)


# --- S0: base platform copy + package.xml rewrite ---------------------------

def _rewrite_package_xml(pkg_xml: Path) -> None:
    """Rewrite the base platform's package.xml for the staging name.

    Mirrors the audited base→live delta (localPackage path, api-level, codename,
    display-name) but uses the staging name so the staging dir is a valid,
    self-describing SDK platform. See architecture doc §2.6.
    """
    text = pkg_xml.read_text(encoding="utf-8")
    repl = [
        ('path="platforms;android-37.0"', f'path="{STAGING_PKG_PATH}"'),
        ("<api-level>37.0</api-level>", f"<api-level>{STAGING_API_LEVEL}</api-level>"),
        ("<codename></codename>", f"<codename>{STAGING_CODENAME}</codename>"),
        ("<display-name>Android SDK Platform 37.0</display-name>",
         f"<display-name>{STAGING_DISPLAY_NAME}</display-name>"),
    ]
    for old, new in repl:
        if old not in text:
            sys.exit(
                f"ERROR: package.xml rewrite failed — expected substring not "
                f"found: {old!r}. Base platform layout may have changed."
            )
        text = text.replace(old, new, 1)
    pkg_xml.write_text(text, encoding="utf-8")


def stage_s0(base: Path, target: Path, clean: bool) -> None:
    _ensure_dir(base, "base platform")
    if target.exists():
        if not clean:
            print(f"S0: --clean not given; keeping existing staging dir {target}")
            return
        print(f"S0: --clean; removing existing {target}")
        shutil.rmtree(target)

    print(f"S0: copying base platform {base} -> {target}")
    skipped: list[str] = []
    for entry in os.listdir(base):
        if any(entry.endswith(s) for s in _BASE_SKIP_SUFFIXES):
            skipped.append(entry)
            continue
        src = base / entry
        dst = target / entry
        if src.is_dir():
            # data/, optional/, templates/, skins/ — full recursive copy.
            shutil.copytree(src, dst, copy_function=shutil.copy2, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    if skipped:
        print(f"S0: skipped base backups ({', '.join(sorted(skipped))}); "
              f"each stage creates its own on first mutation")

    pkg_xml = target / "package.xml"
    if not pkg_xml.is_file():
        sys.exit(f"ERROR: copied platform missing package.xml: {pkg_xml}")
    _rewrite_package_xml(pkg_xml)
    print(f"S0: rewrote {pkg_xml.name} -> path={STAGING_PKG_PATH}, "
          f"api-level={STAGING_API_LEVEL}, codename={STAGING_CODENAME}")


# --- S1: deterministic framework.jar merge ---------------------------------

def _copy_merged_master(
    android_jar: Path, merged_jar: Path, manifest_bytes: bytes
) -> dict:
    """Copy ``android-merged.jar`` wholesale as ``android.jar``, pinning
    MANIFEST.MF.

    Semantics (audited 2026-08-13, see architecture doc §2.4): ``android-merged.jar``
    is the complete 2026-07-22 merge product (``framework.jar`` ∪ base
    ``android.jar`` ∪ 1266 device-framework inner classes) and is a strict
    superset of the live ``android.jar`` minus the 4 S3 dalvik classes (0 CRC
    diffs on the 38892-entry intersection; ``merged - live = 0``; ``live -
    merged = 4`` = exactly the S3 dalvik set). It already carries
    ``resources.arsc`` + ``res/`` (8451 entries, matching live), so the base jar
    is not consulted for gaps. S1 therefore = copy merged verbatim (MANIFEST.MF
    pinned for JDK-determinism); S3 then adds the 4 dalvik classes → live.

    Implemented with stdlib ``zipfile`` so per-entry CRCs match the source
    exactly (CRC is over uncompressed bytes), independent of jar-level
    compression/ordering. Directory entries are dropped (consistent with
    ``_jar_inventory`` / ``_rewrite_manifest_entry``; the live SDK's
    inventory-level verify also ignores directories).

    Returns a dict: {merged, manifest}.
    """
    with zipfile.ZipFile(merged_jar, "r") as mz:
        m_infos = [i for i in mz.infolist() if not i.is_dir()]
    tmp = android_jar.with_suffix(".jar.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out, \
            zipfile.ZipFile(merged_jar, "r") as mz:
        for info in m_infos:
            data = manifest_bytes if info.filename == "META-INF/MANIFEST.MF" \
                else mz.read(info.filename)
            new_info = zipfile.ZipInfo(info.filename, info.date_time)
            new_info.compress_type = info.compress_type
            new_info.external_attr = info.external_attr
            new_info.create_system = info.create_system
            out.writestr(new_info, data)
    os.replace(tmp, android_jar)
    return {"merged": len(m_infos), "manifest": "META-INF/MANIFEST.MF"}


def stage_s1(target: Path, merged_jar: Path) -> None:
    _ensure_file(merged_jar, "android-merged.jar (S1 source)")
    android = target / "android.jar"
    _ensure_file(android, "staging android.jar")
    backup = _backup_if_needed(android, ".orig")
    if backup:
        print(f"S1: backup {backup}")
    res = _copy_merged_master(android, merged_jar, ANDROID_MANIFEST_BYTES)
    print(f"S1: copied android-merged.jar wholesale ({res['merged']} entries) "
          f"as android.jar; MANIFEST.MF pinned to audited live bytes")


# --- S2: framework.aidl patch ---------------------------------------------

def stage_s2(target: Path) -> None:
    aidl = target / "framework.aidl"
    _ensure_file(aidl, "staging framework.aidl")
    backup = _backup_if_needed(aidl, ".bak-preaidl")
    if backup:
        print(f"S2: backup {backup}")
    res = install_sdk.patch_framework_aidl(aidl)
    for decl in res["already"]:
        print(f"S2:   already present: {decl}")
    for decl in res["appended"]:
        print(f"S2:   appended:       {decl}")
    print(f"S2: framework.aidl patched ({len(res['appended'])} appended, "
          f"{len(res['already'])} already present)")


# --- S3: dalvik annotation patch ------------------------------------------

def _rewrite_manifest_entry(jar: Path, manifest_bytes: bytes) -> None:
    """Re-zip the jar with every entry unchanged except META-INF/MANIFEST.MF,
    which is set to ``manifest_bytes``. Guarantees the manifest CRC matches the
    audited live value regardless of the ``jar uf`` tool version used by S3.
    Per-entry CRCs of all other entries are preserved (CRC is over uncompressed
    bytes). Idempotent.
    """
    tmp = jar.with_suffix(".jar.tmp")
    with zipfile.ZipFile(jar, "r") as src, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for info in src.infolist():
            if info.is_dir():
                continue
            data = manifest_bytes if info.filename == "META-INF/MANIFEST.MF" \
                else src.read(info.filename)
            new_info = zipfile.ZipInfo(info.filename, info.date_time)
            new_info.compress_type = info.compress_type
            new_info.external_attr = info.external_attr
            new_info.create_system = info.create_system
            out.writestr(new_info, data)
    os.replace(tmp, jar)


def stage_s3(target: Path, core_libart_jar: Path) -> None:
    _ensure_file(core_libart_jar, "core-libart javac jar (S3 source)")
    for name in _dalvik.TARGET_JARS:
        jar = target / name
        _ensure_file(jar, f"staging {name}")
        res = _dalvik.patch_target(jar, core_libart_jar, create_backup=True)
        if res["backup"]:
            print(f"S3: {name}: backup {res['backup']}")
        if res["injected"]:
            print(f"S3: {name}: injected {len(res['injected'])} classes")
            for cls in res["injected"]:
                print(f"S3:    + {cls}")
        else:
            print(f"S3: {name}: already patched (no-op)")
    # Defensive: pin android.jar manifest to the audited live bytes after the
    # `jar uf` invocation (core-for-system-modules.jar keeps its soong_zip
    # manifest, which S3 preserves; only android.jar was repackaged by S1).
    _rewrite_manifest_entry(target / "android.jar", ANDROID_MANIFEST_BYTES)
    print("S3: normalized android.jar MANIFEST.MF to audited live bytes")


# --- S5: verify ------------------------------------------------------------

def _cmp_jar_inventory(label: str, staging_jar: Path, live_jar: Path) -> tuple:
    s = _jar_inventory(staging_jar)
    l = _jar_inventory(live_jar)
    missing = sorted(set(l) - set(s))           # in live, not in staging
    extra = sorted(set(s) - set(l))             # in staging, not in live
    common = set(s) & set(l)
    crc_diff = sorted(n for n in common if s[n] != l[n])
    ok = not (missing or extra or crc_diff)
    status = "PASS" if ok else "DIFF"
    print(f"S5: {label}: {status}  "
          f"(staging={len(s)} live={len(l)} missing={len(missing)} "
          f"extra={len(extra)} crc_diff={len(crc_diff)})")
    if missing:
        print(f"     missing-in-staging sample: {missing[:6]}")
    if extra:
        print(f"     extra-in-staging sample: {extra[:6]}")
    if crc_diff:
        print(f"     crc-diff sample: {crc_diff[:6]}")
    return status, {"missing": len(missing), "extra": len(extra),
                    "crc_diff": len(crc_diff)}


def _cmp_bytes(label: str, staging: Path, live: Path) -> tuple:
    sb = staging.read_bytes()
    lb = live.read_bytes()
    ok = sb == lb
    status = "PASS" if ok else "DIFF"
    print(f"S5: {label}: {status}  (staging={len(sb)}B live={len(lb)}B)")
    return status, {"staging_bytes": len(sb), "live_bytes": len(lb)}


def _cmp_tree_names(label: str, staging: Path, live: Path) -> tuple:
    def rel_files(root: Path) -> set:
        return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    s = rel_files(staging)
    l = rel_files(live)
    missing = sorted(set(l) - set(s))
    extra = sorted(set(s) - set(l))
    ok = not (missing or extra)
    status = "PASS" if ok else "DIFF"
    print(f"S5: {label}/: {status}  (staging={len(s)} live={len(l)} "
          f"missing={len(missing)} extra={len(extra)})")
    if missing:
        print(f"     missing sample: {missing[:6]}")
    if extra:
        print(f"     extra sample: {extra[:6]}")
    return status, {"missing": len(missing), "extra": len(extra)}


def _check_package_xml_shape(label: str, pkg_xml: Path) -> tuple:
    ok = pkg_xml.is_file()
    detail = {"present": ok}
    if ok:
        text = pkg_xml.read_text(encoding="utf-8")
        import re
        m = re.search(r'localPackage path="([^"]+)"', text)
        api = re.search(r"<api-level>([^<]*)</api-level>", text)
        code = re.search(r"<codename>([^<]*)</codename>", text)
        detail.update(path=m.group(1) if m else None,
                      api_level=api.group(1) if api else None,
                      codename=code.group(1) if code else None)
        ok = bool(m and api and code)
    status = "PASS" if ok else "DIFF"
    print(f"S5: {label}: {status}  (path={detail.get('path')} "
          f"api-level={detail.get('api_level')} codename={detail.get('codename')})")
    return status, detail


def stage_verify(target: Path, live: Path) -> int:
    _ensure_dir(target, "staging target")
    _ensure_dir(live, "live SDK")
    print(f"S5: verifying staging {target} vs live {live}")
    results = []
    results.append(_cmp_jar_inventory("android.jar",
                                       target / "android.jar", live / "android.jar"))
    results.append(_cmp_jar_inventory("core-for-system-modules.jar",
                                       target / "core-for-system-modules.jar",
                                       live / "core-for-system-modules.jar"))
    results.append(_cmp_bytes("framework.aidl",
                               target / "framework.aidl", live / "framework.aidl"))
    results.append(_cmp_bytes("build.prop",
                               target / "build.prop", live / "build.prop"))
    results.append(_check_package_xml_shape("package.xml",
                                             target / "package.xml"))
    results.append(_cmp_tree_names("data", target / "data", live / "data"))
    results.append(_cmp_tree_names("optional", target / "optional",
                                    live / "optional"))
    statuses = [s for s, _ in results]
    print("")
    if all(s == "PASS" for s in statuses):
        print("S5: ALL PASS — staging is inventory-equivalent to the live SDK.")
        return 0
    failed = [name for name, (s, _) in zip(
        ["android.jar", "core-for-system-modules.jar", "framework.aidl",
         "build.prop", "package.xml", "data/", "optional/"], results) if s != "PASS"]
    print(f"S5: DIFF in {len(failed)} file(s): {', '.join(failed)}")
    return 1


# --- main ------------------------------------------------------------------

def _run_stages(stages: list[str], base: Path, target: Path,
                merged_jar: Path, core_libart_jar: Path, clean: bool) -> None:
    if "s0" in stages:
        stage_s0(base, target, clean)
    if "s1" in stages:
        stage_s1(target, merged_jar)
    if "s2" in stages:
        stage_s2(target)
    if "s3" in stages:
        stage_s3(target, core_libart_jar)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", default=str(DEFAULT_TARGET),
                    help=f"staging platform dir (default {DEFAULT_TARGET})")
    ap.add_argument("--base", default=str(DEFAULT_BASE_PLATFORM),
                    help="base stock platform to copy in S0")
    ap.add_argument("--merged-jar", default=str(DEFAULT_MERGED_JAR),
                    help="S1 android-merged.jar source (default libs/android-merged.jar)")
    ap.add_argument("--core-libart-jar", default=str(DEFAULT_CORE_LIBART_JAR),
                    help="S3 core-libart javac jar source")
    ap.add_argument("--clean", action="store_true",
                    help="remove the staging target before S0 (S0 only)")
    ap.add_argument("--stages", default="s0,s1,s2,s3",
                    help="comma-separated stages to run (default s0,s1,s2,s3)")
    ap.add_argument("--verify", action="store_true",
                    help="run S5 verify against the live SDK and exit")
    args = ap.parse_args()

    target = Path(args.target)
    _live_guard(target)

    if args.verify:
        return stage_verify(_resolve(target), _resolve(LIVE_SDK_DIR))

    stages = [s.strip().lower() for s in args.stages.split(",") if s.strip()]
    for s in stages:
        if s not in ALL_STAGES:
            sys.exit(f"ERROR: unknown stage {s!r}; choose from {ALL_STAGES}")
    _run_stages(stages, _resolve(Path(args.base)), _resolve(target),
                _resolve(Path(args.merged_jar)),
                _resolve(Path(args.core_libart_jar)), args.clean)
    print("")
    print("Done. Run with --verify to compare staging against the live SDK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
