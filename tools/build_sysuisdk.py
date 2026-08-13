#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproducible SysUISdk build pipeline (S0–S4 build + S5 verify, staging-only).

Rebuilds the SysUISdk platform into a STAGING directory from tracked artifacts
and verifies inventory-level equivalence with the live SDK. The live SDK at
``~/Android/Sdk/platforms/android-SysUISdk`` is NEVER written to, renamed, or
deleted by the build/verify path — this orchestrator hard-fails if ``--target``
resolves to it. The only sanctioned live mutation is ``--apply`` (user
pre-approval 2026-08-13), which syncs a staging result onto the live SDK with
timestamped backups of every overwritten file.

Stages (see docs/architecture/2026-08-13-sysuisdk-reproducible-build.md):
  S0  copy the base platform (android-37.0) to --target, rewrite package.xml
      for the staging name, copy build.prop / data / optional verbatim.
  S1  copy libs/android-merged.jar wholesale as android.jar (the 2026-07-22
      merge product; strict superset of live-minus-4-dalvik; carries the stale
      May-27 resources.arsc + res/). MANIFEST.MF pinned to audited live bytes.
  S2  framework.aidl hidden-iface/parcelable patch (reuses tools/install_sdk.py).
  S3  dalvik.annotation.optimization patch into both jars (reuses
      tools/patch_sdk_dalvik_annotations.py; source: AOSP core-libart javac jar).
  S4  overlay the current AOSP framework-res.apk resources.arsc + res/** onto
      android.jar, replacing S1's stale May-27 snapshot — fixes androidprv:
      private-resource linking (AGENTS.md §2.4 point 2). Opt-in via --stages;
      deterministic, idempotent, .bak-preres backup on first mutation.
  S5  --verify: compare staging vs live (entry inventories names+CRC for the two
      jars, byte-equality for framework.aidl, presence/shape for package.xml /
      build.prop / data / optional). Prints a per-file PASS/DIFF report and
      exits non-zero on any DIFF. ``--expect-s4-delta`` allows an android.jar
      resource delta after a build with s4 (non-resource entries stay strict);
      without it the strict 7/7 check (pre-S4 reproduction) is unchanged.

Authority: redline-gated (user pre-approval 2026-08-13); --apply is the only
live-mutation path.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
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
DEFAULT_FRAMEWORK_RES_APK = _REPO_ROOT / "libs" / "framework-res.apk"

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

ALL_STAGES = ("s0", "s1", "s2", "s3", "s4")


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


# --- S4: framework-res resource overlay ------------------------------------

RESOURCE_ENTRY_NAME = "resources.arsc"


def _is_resource_entry(name: str) -> bool:
    """An entry S4 owns: the flattened resource table or any res/ file."""
    return name == RESOURCE_ENTRY_NAME or name.startswith("res/")


def _copy_zipinfo(out: zipfile.ZipFile, info: zipfile.ZipInfo, data: bytes) -> None:
    """Write ``data`` under a fresh ZipInfo cloned from ``info`` so the entry's
    stored CRC (computed over uncompressed bytes) matches the source exactly,
    independent of jar-level compression/ordering. Same pattern as S1/S3."""
    new_info = zipfile.ZipInfo(info.filename, info.date_time)
    new_info.compress_type = info.compress_type
    new_info.external_attr = info.external_attr
    new_info.create_system = info.create_system
    out.writestr(new_info, data)


def _overlay_framework_res(android_jar: Path, framework_res_apk: Path) -> dict:
    """Strip ``resources.arsc`` + ``res/**`` from ``android_jar`` then add the
    same entries from ``framework_res_apk``.

    Non-resource entries (classes, ``META-INF/MANIFEST.MF``, …) are preserved
    from ``android_jar`` with their original CRCs. The apk's non-resource
    entries (``AndroidManifest.xml``, ``META-INF/*``, ``assets/``) are NOT
    carried over — only resources are overlaid. Idempotent: a second run strips
    the just-overlaid resources and re-adds them, yielding the same bytes.
    Returns counts: {stripped_res, stripped_arsc, added_res, added_arsc, kept}.
    """
    with zipfile.ZipFile(android_jar, "r") as az:
        all_infos = [i for i in az.infolist() if not i.is_dir()]
        kept_infos = [i for i in all_infos if not _is_resource_entry(i.filename)]
        kept_data = {i.filename: az.read(i.filename) for i in kept_infos}
        stripped_res = sum(1 for i in all_infos if i.filename.startswith("res/"))
        stripped_arsc = sum(
            1 for i in all_infos if i.filename == RESOURCE_ENTRY_NAME)
    with zipfile.ZipFile(framework_res_apk, "r") as fz:
        res_infos = [i for i in fz.infolist()
                     if not i.is_dir() and _is_resource_entry(i.filename)]
        res_data = {i.filename: fz.read(i.filename) for i in res_infos}
    added_res = sum(1 for i in res_infos if i.filename.startswith("res/"))
    added_arsc = sum(1 for i in res_infos if i.filename == RESOURCE_ENTRY_NAME)

    tmp = android_jar.with_suffix(".jar.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for info in kept_infos:
            _copy_zipinfo(out, info, kept_data[info.filename])
        for info in res_infos:
            _copy_zipinfo(out, info, res_data[info.filename])
    os.replace(tmp, android_jar)
    return {
        "stripped_res": stripped_res,
        "stripped_arsc": stripped_arsc,
        "added_res": added_res,
        "added_arsc": added_arsc,
        "kept": len(kept_infos),
    }


def stage_s4(target: Path, framework_res_apk: Path) -> None:
    """Overlay AOSP ``framework-res.apk`` resources onto staging ``android.jar``.

    Replaces the stale May-27 ``resources.arsc`` + ``res/**`` snapshot carried
    by ``libs/android-merged.jar`` (S1) with the current AOSP
    ``framework-res.apk`` resources — resolving the ``androidprv:`` private-
    resource linking errors (AGENTS.md §2.4 point 2). Preserves all non-resource
    entries (incl. the pinned ``META-INF/MANIFEST.MF``). Creates
    ``android.jar.bak-preres`` on first mutation.
    """
    _ensure_file(framework_res_apk, "framework-res.apk (S4 source)")
    android = target / "android.jar"
    _ensure_file(android, "staging android.jar")
    backup = _backup_if_needed(android, ".bak-preres")
    if backup:
        print(f"S4: backup {backup}")
    res = _overlay_framework_res(android, framework_res_apk)
    print(f"S4: stripped {res['stripped_res']} res/ + {res['stripped_arsc']} "
          f"resources.arsc from android.jar; added {res['added_res']} res/ + "
          f"{res['added_arsc']} resources.arsc from framework-res.apk; kept "
          f"{res['kept']} non-resource entries")


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


def _cmp_jar_split_resource(label: str, staging_jar: Path, live_jar: Path) -> tuple:
    """Compare android.jar with the expected S4 resource delta.

    Non-resource entries (everything except ``resources.arsc`` and ``res/**``)
    must match the live SDK strictly (names + CRC). Resource entries are
    reported as a delta and do NOT gate the result — S4 intentionally replaces
    the stale merged-jar resources with the current AOSP framework-res.
    Returns (status, detail) where status is PASS only if non-resource matches.
    """
    s = _jar_inventory(staging_jar)
    l = _jar_inventory(live_jar)
    s_nr = {k: v for k, v in s.items() if not _is_resource_entry(k)}
    l_nr = {k: v for k, v in l.items() if not _is_resource_entry(k)}
    missing = sorted(set(l_nr) - set(s_nr))
    extra = sorted(set(s_nr) - set(l_nr))
    crc_diff = sorted(n for n in (set(s_nr) & set(l_nr)) if s_nr[n] != l_nr[n])
    ok = not (missing or extra or crc_diff)
    status = "PASS" if ok else "DIFF"
    print(f"S5: {label}: {status} (non-resource strict; S4 resource delta allowed)  "
          f"(staging_nr={len(s_nr)} live_nr={len(l_nr)} missing={len(missing)} "
          f"extra={len(extra)} crc_diff={len(crc_diff)})")
    s_r = {k: v for k, v in s.items() if _is_resource_entry(k)}
    l_r = {k: v for k, v in l.items() if _is_resource_entry(k)}
    r_missing = len(set(l_r) - set(s_r))
    r_extra = len(set(s_r) - set(l_r))
    r_crc = sum(1 for n in (set(s_r) & set(l_r)) if s_r[n] != l_r[n])
    print(f"     resource delta (resources.arsc + res/**): "
          f"staging={len(s_r)} live={len(l_r)} missing={r_missing} "
          f"extra={r_extra} crc_diff={r_crc})")
    if missing:
        print(f"     missing-in-staging (non-res) sample: {missing[:6]}")
    if extra:
        print(f"     extra-in-staging (non-res) sample: {extra[:6]}")
    if crc_diff:
        print(f"     crc-diff (non-res) sample: {crc_diff[:6]}")
    return status, {"non_resource_ok": ok, "missing": len(missing),
                    "extra": len(extra), "crc_diff": len(crc_diff)}


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


def stage_verify(target: Path, live: Path, expect_s4_delta: bool = False) -> int:
    _ensure_dir(target, "staging target")
    _ensure_dir(live, "live SDK")
    mode = (" (--expect-s4-delta: android.jar resource delta allowed)"
            if expect_s4_delta else "")
    print(f"S5: verifying staging {target} vs live {live}{mode}")
    results = []
    if expect_s4_delta:
        results.append(_cmp_jar_split_resource("android.jar",
                                               target / "android.jar",
                                               live / "android.jar"))
    else:
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
        if expect_s4_delta:
            print("S5: ALL PASS (non-resource strict) — android.jar resource "
                  "delta is the expected S4 overlay; staging is otherwise "
                  "equivalent to live.")
        else:
            print("S5: ALL PASS — staging is inventory-equivalent to the live SDK.")
        return 0
    failed = [name for name, (s, _) in zip(
        ["android.jar", "core-for-system-modules.jar", "framework.aidl",
         "build.prop", "package.xml", "data/", "optional/"], results) if s != "PASS"]
    print(f"S5: DIFF in {len(failed)} file(s): {', '.join(failed)}")
    return 1


# --- apply: sync staging onto the live SDK (pre-approved) ------------------

# The artifact files the pipeline patches and that --apply syncs onto live.
# Identity-bearing files (package.xml, source.properties, sdk.properties) are
# NOT touched — staging carries the staging name, the live SDK carries the real
# SysUISdk identity.
APPLY_FILES = ("android.jar", "core-for-system-modules.jar", "framework.aidl")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def apply_to_live(source: Path) -> int:
    """Sync staging artifacts onto the live SDK (user pre-approval 2026-08-13).

    Copies each of ``APPLY_FILES`` from the staging ``source`` to the live SDK,
    creating a timestamped backup (``<name>.bak-<ts>``) of every live file that
    actually differs. Identical files are skipped (no backup, no overwrite).
    This is the ONLY sanctioned live-SDK mutation path; it is deliberately
    separate from the staging build/verify path (which hard-fails on the live
    SDK via ``_live_guard``).
    """
    _ensure_dir(source, "staging source")
    live = _resolve(LIVE_SDK_DIR)
    _ensure_dir(live, "live SDK")
    _live_guard(source)  # refuse if --source is/inside the live SDK
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"apply: source={source} live={live} ts={ts}")
    applied: list[str] = []
    skipped: list[str] = []
    for name in APPLY_FILES:
        s = source / name
        l = live / name
        _ensure_file(s, f"staging {name}")
        _ensure_file(l, f"live {name}")
        if _sha256(s) == _sha256(l):
            skipped.append(name)
            print(f"apply: {name}: identical (skip)")
            continue
        bak = l.with_name(f"{name}.bak-{ts}")
        shutil.copy2(l, bak)
        print(f"apply: {name}: backup {bak}")
        shutil.copy2(s, l)
        applied.append(name)
        print(f"apply: {name}: synced")
    print(f"apply: done — synced {len(applied)} "
          f"({', '.join(applied) or 'none'}), skipped {len(skipped)} identical")
    return 0


# --- main ------------------------------------------------------------------

def _run_stages(stages: list[str], base: Path, target: Path,
                merged_jar: Path, core_libart_jar: Path,
                framework_res_apk: Path, clean: bool) -> None:
    if "s0" in stages:
        stage_s0(base, target, clean)
    if "s1" in stages:
        stage_s1(target, merged_jar)
    if "s2" in stages:
        stage_s2(target)
    if "s3" in stages:
        stage_s3(target, core_libart_jar)
    if "s4" in stages:
        stage_s4(target, framework_res_apk)


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
    ap.add_argument("--framework-res-apk", default=str(DEFAULT_FRAMEWORK_RES_APK),
                    help="S4 framework-res.apk source (default libs/framework-res.apk)")
    ap.add_argument("--clean", action="store_true",
                    help="remove the staging target before S0 (S0 only)")
    ap.add_argument("--stages", default="s0,s1,s2,s3",
                    help="comma-separated stages to run (default s0,s1,s2,s3; "
                         "append s4 for the framework-res overlay)")
    ap.add_argument("--verify", action="store_true",
                    help="run S5 verify against the live SDK and exit")
    ap.add_argument("--expect-s4-delta", action="store_true",
                    help="with --verify: allow android.jar resource delta from S4 "
                         "(non-resource entries stay strict); use after a build with s4")
    ap.add_argument("--apply", action="store_true",
                    help="sync staging artifacts onto the live SDK (pre-approved "
                         "2026-08-13); --source selects the staging dir")
    ap.add_argument("--source", default=str(DEFAULT_TARGET),
                    help=f"staging source dir for --apply (default {DEFAULT_TARGET})")
    args = ap.parse_args()

    target = Path(args.target)

    if args.apply:
        _live_guard(_resolve(Path(args.source)))
        return apply_to_live(_resolve(Path(args.source)))

    _live_guard(target)

    if args.verify:
        return stage_verify(_resolve(target), _resolve(LIVE_SDK_DIR),
                            expect_s4_delta=args.expect_s4_delta)

    stages = [s.strip().lower() for s in args.stages.split(",") if s.strip()]
    for s in stages:
        if s not in ALL_STAGES:
            sys.exit(f"ERROR: unknown stage {s!r}; choose from {ALL_STAGES}")
    _run_stages(stages, _resolve(Path(args.base)), _resolve(target),
                _resolve(Path(args.merged_jar)),
                _resolve(Path(args.core_libart_jar)),
                _resolve(Path(args.framework_res_apk)), args.clean)
    print("")
    print("Done. Run with --verify to compare staging against the live SDK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
