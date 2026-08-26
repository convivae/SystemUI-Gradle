#!/usr/bin/env python3
"""Deterministic clean-JAR packager for view_capture and motion_tool_lib.

Merges fixed owning-Soong *implementation* outputs (javac/kotlin — never
turbine, header, combined, or FAT jars) into two class-only repository JARs:

* ``libs/view_capture.jar`` — 56 classes under ``com/android/app/viewcapture/``
  from contributions 9 (javac) + 23 (kotlin) + 24 (view_capture_proto javac);
* ``libs/motion_tool_lib.jar`` — 65 classes under ``com/android/app/motiontool/``
  from contributions 8 (kotlin) + 57 (motion_tool_proto javac).

The packager is deterministic: entries are sorted by path, ZIP timestamps are
fixed, permissions are fixed, and non-class entries (manifests, directories)
are dropped. Any class outside the target's approved namespace, any duplicate
class (within or across inputs), and any missing/invalid/empty input is
rejected.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
VIEW_PREFIX = "com/android/app/viewcapture/"
MOTION_PREFIX = "com/android/app/motiontool/"

from aosp_paths import aosp_root

# Single AOSP root source (user rule 2026-08-25): tools/aosp_paths.py resolves
# the default, the AOSP_ROOT env override, and any explicit --aosp-root value.
DEFAULT_AOSP_ROOT = aosp_root()

REPO_ROOT = Path(__file__).resolve().parents[1]

# Fixed owning-Soong implementation inputs, relative to the AOSP root.
# Paths deliberately contain /javac/ or /kotlin/ implementation outputs only.
VIEW_INPUTS = (
    "out/soong/.intermediates/frameworks/libs/systemui/viewcapturelib/"
    "view_capture/android_common/javac/view_capture.jar",
    "out/soong/.intermediates/frameworks/libs/systemui/viewcapturelib/"
    "view_capture/android_common/kotlin/view_capture.jar",
    "out/soong/.intermediates/frameworks/libs/systemui/viewcapturelib/"
    "view_capture_proto/android_common/javac/view_capture_proto.jar",
)
MOTION_INPUTS = (
    "out/soong/.intermediates/frameworks/libs/systemui/motiontoollib/"
    "motion_tool_lib/android_common/kotlin/motion_tool_lib.jar",
    "out/soong/.intermediates/frameworks/libs/systemui/motiontoollib/"
    "motion_tool_proto/android_common/javac/motion_tool_proto.jar",
)

VIEW_OUTPUT = REPO_ROOT / "libs" / "view_capture.jar"
MOTION_OUTPUT = REPO_ROOT / "libs" / "motion_tool_lib.jar"


class PackagingError(Exception):
    """Raised for invalid inputs, namespace pollution, or duplicate classes."""


def _collect_classes(source: Path, label: str, approved_prefix: str) -> dict[str, bytes]:
    """Return ``{archive_name: payload}`` for approved class entries."""
    if not source.is_file():
        raise PackagingError(f"input jar missing: {label} ({source})")
    try:
        with zipfile.ZipFile(source) as archive:
            classes = _collect_classes_from(archive, label, source, approved_prefix)
    except zipfile.BadZipFile as error:
        raise PackagingError(f"input jar is not a valid ZIP: {label} ({source})") from error
    if not classes:
        raise PackagingError(f"input jar contains no classes: {label} ({source})")
    return classes


def _collect_classes_from(
    archive: zipfile.ZipFile, label: str, source: Path, approved_prefix: str
) -> dict[str, bytes]:
    """Return ``{archive_name: payload}`` for approved class entries."""
    classes: dict[str, bytes] = {}
    for name in archive.namelist():
        if not name.endswith(".class"):
            continue
        if not name.startswith(approved_prefix):
            raise PackagingError(
                f"class outside approved namespace {approved_prefix!r}: "
                f"{name} in {label} ({source})"
            )
        if name in classes:
            raise PackagingError(
                f"duplicate class {name} within input {label} ({source})"
            )
        classes[name] = archive.read(name)
    return classes


def package_target(
    inputs: tuple[Path, ...], output: Path, approved_prefix: str
) -> tuple[int, ...]:
    """Merge ``inputs`` into a deterministic class-only ``output`` JAR.

    Returns the per-input contributed class counts, in input order.
    """
    merged: dict[str, bytes] = {}
    counts: list[int] = []
    for index, source in enumerate(inputs):
        label = getattr(source, "name", str(source)) or f"input-{index}"
        classes = _collect_classes(source, label, approved_prefix)
        for name in classes:
            if name in merged:
                raise PackagingError(
                    f"duplicate class {name} across inputs "
                    f"(already contributed by an earlier input)"
                )
        merged.update(classes)
        counts.append(len(classes))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for name in sorted(merged):
            info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, merged[name])
    return tuple(counts)


def _resolve(root: Path, relative: str) -> Path:
    return root / relative


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="package both targets")
    parser.add_argument("--aosp-root", type=Path, default=DEFAULT_AOSP_ROOT)
    args = parser.parse_args(argv)
    if not args.all:
        parser.error("nothing to do; pass --all")

    targets = (
        ("view_capture", VIEW_INPUTS, VIEW_OUTPUT, VIEW_PREFIX),
        ("motion_tool_lib", MOTION_INPUTS, MOTION_OUTPUT, MOTION_PREFIX),
    )
    failed = False
    for name, relatives, output, prefix in targets:
        inputs = tuple(_resolve(args.aosp_root, relative) for relative in relatives)
        try:
            counts = package_target(inputs, output, prefix)
        except PackagingError as error:
            print(f"ERROR [{name}]: {error}", file=sys.stderr)
            failed = True
            continue
        detail = " + ".join(str(count) for count in counts)
        print(f"{name}: ({detail}) = {sum(counts)} classes -> {output}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
