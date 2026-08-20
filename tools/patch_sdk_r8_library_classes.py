#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exact-entry SysUISdk R8 library-class patcher (Task 041).

Injects exactly the 35 user-approved class entries (docs/issues/
2026-08-21-r8-platform-build-classpath-closure.md, user approval 2026-08-21)
from four real AOSP/tracked source artifacts into a target SDK jar, so AGP
R8 can resolve them as library classes (AGP 9.3.1 exposes only the compileSdk
bootclasspath as R8 library input — see docs/architecture/
2026-08-20-r8-platform-classpath-bridge.md).

Design guarantees:

* Exact allowlist only: the six immutable slices below total exactly
  ``2 + 4 + 4 + 2 + 1 + 22 = 35`` entries; nothing else is ever injected and
  no source package is expanded at runtime.
* Task 042 boundary: ``com/android/aconfig/annotations/AssumeTrueForR8.class``
  is deliberately NOT declared here (reserved for Task 042).
* Source provenance: every injected entry is byte-for-byte identical to its
  approved source artifact entry.
* Collision rejection: if the target already contains a declared entry with
  bytes differing from the source, a ``RuntimeError`` is raised and the
  target is left untouched (a mismatch is a REDLINE, not a repair).
* Deterministic: existing entries are rewritten in their original order with
  their original ``ZipInfo`` metadata; missing entries are appended sorted by
  archive path using the source entry's ``ZipInfo``. Identical inputs produce
  byte-identical outputs.
* Idempotent: a second run injects nothing, creates no new backup, and does
  not rewrite the file.
* Scoped backup: the first mutation creates ``<target>.bak-prer8lib``
  preserving the pre-mutation bytes; an existing backup is never overwritten.
* Validation before mutation: duplicate entries across slices, missing
  declared source entries, and target collisions are all rejected before any
  backup or temporary file is created.
* No CLI / no live-SDK path: this module is a library consumed by
  ``tools/build_sysuisdk.py`` stage S3b; live SDK mutation remains exclusively
  the guarded ``build_sysuisdk.py --apply`` path.
"""
from __future__ import annotations

import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

# --- Approved exact class slices (user approval 2026-08-21) -----------------
#
# Six closed slices from four source artifacts. The DDMS four-class package
# and the keepanno 22-class package are closed owner boundaries: no other
# classes from their source JARs are permitted.

IO_UTILS_ENTRIES = (
    "libcore/io/IoUtils.class",
    "libcore/io/IoUtils$FileReader.class",
)
NATIVE_ALLOCATION_REGISTRY_ENTRIES = (
    "libcore/util/NativeAllocationRegistry.class",
    "libcore/util/NativeAllocationRegistry$CleanerRunner.class",
    "libcore/util/NativeAllocationRegistry$CleanerThunk.class",
    "libcore/util/NativeAllocationRegistry$Metrics.class",
)
DDMC_ENTRIES = (
    "org/apache/harmony/dalvik/ddmc/Chunk.class",
    "org/apache/harmony/dalvik/ddmc/ChunkHandler.class",
    "org/apache/harmony/dalvik/ddmc/DdmServer.class",
    "org/apache/harmony/dalvik/ddmc/DdmVmInternal.class",
)
UNSUPPORTED_APP_USAGE_ENTRIES = (
    "android/compat/annotation/UnsupportedAppUsage.class",
    "android/compat/annotation/UnsupportedAppUsage$Container.class",
)
ACONFIG_FLAG_ACCESSOR_ENTRIES = (
    "com/android/aconfig/annotations/AconfigFlagAccessor.class",
)
KEEPANNO_ANNOTATION_ENTRIES = tuple(
    f"com/android/tools/r8/keepanno/annotations/{name}.class" for name in (
        "AnnotationPattern", "CheckOptimizedOut", "CheckRemoved",
        "ClassAccessFlags", "ClassNamePattern", "FieldAccessFlags",
        "InstanceOfPattern", "KeepBinding", "KeepCondition", "KeepConstraint",
        "KeepEdge", "KeepForApi", "KeepItemKind", "KeepOption", "KeepTarget",
        "MemberAccessFlags", "MethodAccessFlags", "StringPattern",
        "TypePattern", "UsedByNative", "UsedByReflection", "UsesReflection",
    ))

TOTAL_APPROVED_ENTRIES = (
    len(IO_UTILS_ENTRIES) + len(NATIVE_ALLOCATION_REGISTRY_ENTRIES)
    + len(DDMC_ENTRIES) + len(UNSUPPORTED_APP_USAGE_ENTRIES)
    + len(ACONFIG_FLAG_ACCESSOR_ENTRIES) + len(KEEPANNO_ANNOTATION_ENTRIES))
assert TOTAL_APPROVED_ENTRIES == 35, TOTAL_APPROVED_ENTRIES
assert ("com/android/aconfig/annotations/AssumeTrueForR8.class"
        not in IO_UTILS_ENTRIES + NATIVE_ALLOCATION_REGISTRY_ENTRIES
        + DDMC_ENTRIES + UNSUPPORTED_APP_USAGE_ENTRIES
        + ACONFIG_FLAG_ACCESSOR_ENTRIES + KEEPANNO_ANNOTATION_ENTRIES)

DEFAULT_BACKUP_SUFFIX = ".bak-prer8lib"


@dataclass(frozen=True)
class ClassSlice:
    """One approved (source jar, exact entry set) slice."""
    label: str
    source_jar: Path
    entries: tuple[str, ...]


def task041_slices(
    core_libart_jar: Path,
    unsupported_jar: Path,
    aconfig_jar: Path,
    keepanno_jar: Path,
) -> tuple[ClassSlice, ...]:
    """Build the six approved Task 041 slices from the four source jars."""
    core = Path(core_libart_jar)
    return (
        ClassSlice("core-libart IoUtils", core, IO_UTILS_ENTRIES),
        ClassSlice("core-libart NativeAllocationRegistry", core,
                   NATIVE_ALLOCATION_REGISTRY_ENTRIES),
        ClassSlice("core-libart ddmc", core, DDMC_ENTRIES),
        ClassSlice("unsupportedappusage", Path(unsupported_jar),
                   UNSUPPORTED_APP_USAGE_ENTRIES),
        ClassSlice("aconfig-annotations", Path(aconfig_jar),
                   ACONFIG_FLAG_ACCESSOR_ENTRIES),
        ClassSlice("keepanno-annotations", Path(keepanno_jar),
                   KEEPANNO_ANNOTATION_ENTRIES),
    )


# --- validation -------------------------------------------------------------

def _load_sources(
    slices: tuple[ClassSlice, ...]
) -> dict[str, tuple[Path, bytes]]:
    """Validate slices and load {entry: (source_jar, bytes)}.

    Raises before any mutation when: a source jar is missing
    (``FileNotFoundError``), a declared entry is absent from its assigned
    source jar (``RuntimeError``), or an entry is declared by more than one
    slice (``RuntimeError``).
    """
    seen: dict[str, tuple[Path, bytes]] = {}
    for sl in slices:
        jar = Path(sl.source_jar)
        if not jar.is_file():
            raise FileNotFoundError(f"source jar not found: {jar}")
        with zipfile.ZipFile(jar, "r") as zf:
            names = set(zf.namelist())
            for entry in sl.entries:
                if entry in seen:
                    raise RuntimeError(
                        f"duplicate class path declared across slices: "
                        f"{entry} (in {seen[entry][0]} and {jar})")
                if entry not in names:
                    raise RuntimeError(
                        f"declared source entry missing from {jar}: {entry}")
                seen[entry] = (jar, zf.read(entry))
    return seen


def validate_target(target: Path, slices: tuple[ClassSlice, ...]) -> dict:
    """Read-only validation of one target jar against the slices.

    Returns ``{"missing": [...], "already": [...], "source_by_entry": {...}}``
    (missing/already sorted). Raises ``FileNotFoundError`` for a missing
    target/source and ``RuntimeError`` for duplicates, missing declared source
    entries, or a target entry whose bytes collide with the approved source
    bytes. Never mutates anything.
    """
    target = Path(target)
    if not target.is_file():
        raise FileNotFoundError(f"target jar not found: {target}")
    source_map = _load_sources(slices)
    missing: list[str] = []
    already: list[str] = []
    with zipfile.ZipFile(target, "r") as zf:
        tgt_names = set(zf.namelist())
        for entry in sorted(source_map):
            if entry not in tgt_names:
                missing.append(entry)
            else:
                src_jar, src_bytes = source_map[entry]
                if zf.read(entry) != src_bytes:
                    raise RuntimeError(
                        f"collision: target {target} entry {entry} differs "
                        f"from approved source {src_jar}")
                already.append(entry)
    return {
        "missing": missing,
        "already": already,
        "source_by_entry": {e: source_map[e][1] for e in source_map},
    }


# --- patching ----------------------------------------------------------------

def _clone_zipinfo(info: zipfile.ZipInfo) -> zipfile.ZipInfo:
    """Clone the metadata-bearing fields of a ZipInfo for a deterministic
    rewrite (same pattern as build_sysuisdk S1/S3/S4)."""
    new_info = zipfile.ZipInfo(info.filename, info.date_time)
    new_info.compress_type = info.compress_type
    new_info.external_attr = info.external_attr
    new_info.create_system = info.create_system
    return new_info


def patch_target(
    target: Path,
    slices: tuple[ClassSlice, ...],
    backup_suffix: str = DEFAULT_BACKUP_SUFFIX,
) -> dict:
    """Patch one target jar with the exact approved entries missing from it.

    Revalidates everything (duplicates, source entries, collisions) before
    creating any backup or temporary file. Injects only missing entries —
    source-byte-identical, appended sorted by archive path with the source
    entry's ``ZipInfo``. Idempotent: nothing is done when nothing is missing.

    Returns ``{"injected": [...], "already": [...], "backup": str | None,
    "source_by_entry": {...}}``.
    """
    target = Path(target)
    report = validate_target(target, slices)
    missing = report["missing"]
    result = {
        "injected": list(missing),
        "already": report["already"],
        "backup": None,
        "source_by_entry": report["source_by_entry"],
    }
    if not missing:
        return result  # already patched — no-op, no backup

    # Scoped backup (never overwritten) — created only after validation.
    bak = target.with_name(target.name + backup_suffix)
    if not bak.exists():
        shutil.copy2(target, bak)
        result["backup"] = str(bak)

    # Source ZipInfos for the missing entries.
    missing_set = set(missing)
    src_infos: dict[str, zipfile.ZipInfo] = {}
    for sl in slices:
        jar = Path(sl.source_jar)
        with zipfile.ZipFile(jar, "r") as zf:
            for info in zf.infolist():
                if info.filename in missing_set:
                    src_infos[info.filename] = info

    # Deterministic rewrite: existing non-directory entries in original
    # order (original ZipInfo + bytes), then missing entries sorted by path
    # (source ZipInfo + source bytes). Atomic replace.
    tmp = target.with_name(target.name + ".tmp-r8lib")
    with zipfile.ZipFile(target, "r") as src, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for info in src.infolist():
            if info.is_dir():
                continue
            out.writestr(_clone_zipinfo(info), src.read(info.filename))
        for entry in sorted(missing):
            out.writestr(_clone_zipinfo(src_infos[entry]),
                         report["source_by_entry"][entry])
    os.replace(tmp, target)
    return result
