#!/usr/bin/env python3
"""Package the twelve hand-copied misc JARs from frozen AOSP Soong artifacts.

Task 064 (regeneration gap closure): every remaining ``libs/`` JAR that was
hand-copied in 2026-07 without a script is mapped here to its owning Soong
intermediate, following the frozen-input discipline of ``build_sysuisdk.py``:
exact relative paths, no globbing, no newest-file fallback. Extraction is a
byte-identical copy; AOSP tree drift is detected via the frozen
``source_sha256`` fingerprint of the day this mapping was frozen.

Each entry also freezes ``baseline_sha256`` — the fingerprint of the jar that
lives in ``libs/`` today. After generating into an output root, the result is
compared against the baseline and reported as MATCH/DIFF. DIFF is *not* a
failure: the 2026-07 hand copies predate later AOSP syncs, and the report is
the decision input for Phase C ("script output wins" vs "baseline wins").

Two entries were historically DIFF and were replaced with the script
output on 2026-08-26 following explicit user approval ("script output wins
over hand-copied jars"); their baselines are now the frozen Soong sources
themselves, so ``--verify-only`` reports MATCH across the board. See
``docs/architecture/2026-08-26-regeneration-gap-closure.md`` §4:

* ``framework-statsd`` — no byte-exact Soong source of the 2026-07 hand copy
  exists in the current build; the frozen source is the closest superset
  (impl javac, real classes).
* ``android.car`` — the module only produces turbine output in this build;
  the frozen source is the turbine-combined closure (stub bodies, fine for
  the compileOnly wiring).

Usage::

    python3 tools/package_misc_jars.py --all            # regenerate all 12
    python3 tools/package_misc_jars.py framework        # regenerate one
    python3 tools/package_misc_jars.py --all --verify-only   # libs/ vs frozen baselines
    python3 tools/package_misc_jars.py --all --require-match  # exit 1 on any DIFF

Generated files land under ``--output-root`` (default: repository root, i.e.
real ``libs/`` paths). ``--verify-only`` never reads the AOSP tree and never
writes anything.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

from aosp_paths import soong_intermediates

REPO_ROOT = Path(__file__).resolve().parents[1]

# name -> frozen mapping. Fields:
#   module        owning Soong module name (for humans and drift archaeology)
#   relpath       path under out/soong/.intermediates (never absolute)
#   destination   path under the output root (mirrors the real libs/ layout)
#   source_sha256 fingerprint of the AOSP artifact when this mapping was
#                 frozen (2026-08-26); a mismatch warns about tree drift
#   baseline_sha256 fingerprint of the current libs/ jar (MATCH target)
CONFIGS: dict[str, dict] = {
    "framework": {
        "module": "framework",
        "relpath": "frameworks/base/framework/android_common/"
                   "turbine-combined/framework.jar",
        "destination": "libs/framework.jar",
        "source_sha256":
            "0fe39d800f34f6c7b17e5c936571bc29367e1329c8af9c6ab47e894beb05be26",
        "baseline_sha256":
            "0fe39d800f34f6c7b17e5c936571bc29367e1329c8af9c6ab47e894beb05be26",
    },
    "framework-statsd": {
        # Replaced 2026-08-26 (task 065, user-approved): the 2026-07 hand
        # copy (39 API-stub classes) had no byte-exact Soong source in the
        # current build. Baseline is now the frozen source itself: the impl
        # javac jar (70 entries, real classes, class-name superset of the
        # old hand copy).
        "module": "framework-statsd.impl",
        "relpath": "packages/modules/StatsD/framework/framework-statsd.impl/"
                   "android_common_apex30/javac/framework-statsd.jar",
        "destination": "libs/framework-statsd.jar",
        "source_sha256":
            "058f30a1a7ef191b1c4ecef3658b215d996d657f6d0a2591956eb6e3e5aba352",
        "baseline_sha256":
            "058f30a1a7ef191b1c4ecef3658b215d996d657f6d0a2591956eb6e3e5aba352",
    },
    "android.car": {
        # Replaced 2026-08-26 (task 065, user-approved): the 2026-07 hand copy
        # (678 stored stubs) came from a July-era tree state and carried 14
        # classes that no longer exist upstream. Baseline is now the frozen
        # turbine-combined closure (1219 stub classes incl. the static dep
        # closure). compileOnly wiring — stubs are fine.
        "module": "android.car",
        "relpath": "packages/services/Car/car-lib/android.car/android_common/"
                   "turbine-combined/android.car.jar",
        "destination": "libs/android.car.jar",
        "source_sha256":
            "89f04e0a30bf8889ab2198516d9ecf362e90559e3bc7dbad8863b1c6263919c0",
        "baseline_sha256":
            "89f04e0a30bf8889ab2198516d9ecf362e90559e3bc7dbad8863b1c6263919c0",
    },
    "android_module_lib_stubs_current": {
        "module": "android_module_lib_stubs_current",
        "relpath": "frameworks/base/api/android_module_lib_stubs_current/"
                   "android_common/turbine-combined/"
                   "android_module_lib_stubs_current.jar",
        "destination": "libs/android_module_lib_stubs_current.jar",
        "source_sha256":
            "af3fc1f18a9cbedebf01900deb9721e9339ab2fb51c3b42d3c8d052a223d13d7",
        "baseline_sha256":
            "af3fc1f18a9cbedebf01900deb9721e9339ab2fb51c3b42d3c8d052a223d13d7",
    },
    "SystemUI-proto": {
        "module": "SystemUI-proto",
        "relpath": "frameworks/base/packages/SystemUI/SystemUI-proto/"
                   "android_common/javac/SystemUI-proto.jar",
        "destination": "libs/SystemUI-proto.jar",
        "source_sha256":
            "8f24c6b2544aa86227a311d68946329e3afa2569e60eca3eecda0d0cc91a6ea3",
        "baseline_sha256":
            "8f24c6b2544aa86227a311d68946329e3afa2569e60eca3eecda0d0cc91a6ea3",
    },
    "SystemUI-statsd": {
        "module": "SystemUI-statsd",
        "relpath": "frameworks/base/packages/SystemUI/shared/SystemUI-statsd/"
                   "android_common/javac/SystemUI-statsd.jar",
        "destination": "libs/SystemUI-statsd.jar",
        "source_sha256":
            "3e96c65367070d15f2fa568de2cf4fba64626e87075e7e8fd2af7165518072bf",
        "baseline_sha256":
            "3e96c65367070d15f2fa568de2cf4fba64626e87075e7e8fd2af7165518072bf",
    },
    "SystemUI-tags": {
        "module": "SystemUI-tags",
        "relpath": "frameworks/base/packages/SystemUI/SystemUI-tags/"
                   "android_common/javac/SystemUI-tags.jar",
        "destination": "libs/SystemUI-tags.jar",
        "source_sha256":
            "441b05edc1fd304b879ee83097ad05f1c7d5f5b59f5431832ce44720792387aa",
        "baseline_sha256":
            "441b05edc1fd304b879ee83097ad05f1c7d5f5b59f5431832ce44720792387aa",
    },
    "contextualeducationlib": {
        "module": "contextualeducationlib",
        "relpath": "frameworks/libs/systemui/contextualeducationlib/"
                   "contextualeducationlib/android_common/kotlin/"
                   "contextualeducationlib.jar",
        "destination": "libs/contextualeducationlib.jar",
        "source_sha256":
            "21827c3c18dd1f8087eaac1bbecaa339fcb9679818a7d10dff169b6b1bc61385",
        "baseline_sha256":
            "21827c3c18dd1f8087eaac1bbecaa339fcb9679818a7d10dff169b6b1bc61385",
    },
    "msdl": {
        "module": "msdl",
        "relpath": "frameworks/libs/systemui/msdllib/msdl/android_common/"
                   "kotlin/msdl.jar",
        "destination": "libs/msdl.jar",
        "source_sha256":
            "ecbdfe63b8c65ea094110931d93e600d69880d56362928b3ad6ce6c36872468e",
        "baseline_sha256":
            "ecbdfe63b8c65ea094110931d93e600d69880d56362928b3ad6ce6c36872468e",
    },
    "PlatformMotionTestingComposeValues": {
        "module": "PlatformMotionTestingComposeValues",
        "relpath": "platform_testing/libraries/motion/compose/values/"
                   "PlatformMotionTestingComposeValues/android_common/kotlin/"
                   "PlatformMotionTestingComposeValues.jar",
        "destination": "libs/PlatformMotionTestingComposeValues.jar",
        "source_sha256":
            "beb021cfba4d335a05b77ccbaf18a7f935154f04bd1196531d78e4edaafba59e",
        "baseline_sha256":
            "beb021cfba4d335a05b77ccbaf18a7f935154f04bd1196531d78e4edaafba59e",
    },
    "keepanno-annotations": {
        # Same frozen input as build_sysuisdk.py AOSP_INPUT_RELPATHS
        # ["keepanno_jar"]; independently compileOnly-wired by SystemUI-core.
        "module": "keepanno-annotations",
        "relpath": "prebuilts/r8/keepanno-annotations/android_common/combined/"
                   "keepanno-annotations.jar",
        "destination": "libs/keepanno-annotations.jar",
        "source_sha256":
            "056412aa7731b573f06940c792db082859ad49e464be08f464a4bba52fd856c5",
        "baseline_sha256":
            "056412aa7731b573f06940c792db082859ad49e464be08f464a4bba52fd856c5",
    },
    "tracinglib-platform": {
        # Extracted raw; conflict cleaning (if ever needed again) is the
        # separate clean_prebuilts.py step. The current on-disk baseline is
        # byte-identical to the raw kotlin artifact, so no cleaning applies.
        "module": "tracinglib-platform",
        "relpath": "frameworks/libs/systemui/tracinglib/core/"
                   "tracinglib-platform/android_common/kotlin/"
                   "tracinglib-platform.jar",
        "destination": "libs/prebuilts/tracinglib-platform.jar",
        "source_sha256":
            "90ec3be83e8af0bc9167046533be67b43fff69f0bb09ca747e7b82ddb83409d4",
        "baseline_sha256":
            "90ec3be83e8af0bc9167046533be67b43fff69f0bb09ca747e7b82ddb83409d4",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_source(name: str, intermediates: Path) -> Path:
    """Resolve the frozen Soong artifact for ``name`` or fail loudly."""
    return intermediates / CONFIGS[name]["relpath"]


def generate(name: str, intermediates: Path, output_root: Path) -> str:
    """Copy the frozen source byte-identically; return MATCH or DIFF.

    MATCH/DIFF compares the generated bytes against the frozen baseline
    fingerprint (the jar currently in libs/). A source-fingerprint mismatch
    (AOSP tree drift since the mapping was frozen) is printed as a warning
    but never blocks generation.
    """
    source = resolve_source(name, intermediates)
    if not source.is_file():
        raise FileNotFoundError(f"missing frozen AOSP artifact for {name}: {source}")
    actual_source_sha = _sha256(source)
    if actual_source_sha != CONFIGS[name]["source_sha256"]:
        print(f"warning: {name}: AOSP source drifted from the frozen mapping "
              f"(expected {CONFIGS[name]['source_sha256'][:16]}…, "
              f"got {actual_source_sha[:16]}…); regenerating from the current "
              f"tree state")
    destination = output_root / CONFIGS[name]["destination"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(destination)
    verdict = "MATCH" if actual_source_sha == CONFIGS[name]["baseline_sha256"] else "DIFF"
    print(f"{name}: {source} -> {destination} [{verdict}]")
    return verdict


def verify_only(output_root: Path) -> str:
    """Compare on-disk libs/ jars against the frozen baselines (no AOSP read)."""
    verdicts = []
    for name in sorted(CONFIGS):
        path = output_root / CONFIGS[name]["destination"]
        if not path.is_file():
            print(f"{name}: MISSING (no {path})")
            verdicts.append("MISSING")
            continue
        verdict = (
            "MATCH" if _sha256(path) == CONFIGS[name]["baseline_sha256"]
            else "DIFF"
        )
        print(f"{name}: {path} [{verdict}]")
        verdicts.append(verdict)
    return "DIFF" if {"DIFF", "MISSING"} & set(verdicts) else "MATCH"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "artifact",
        nargs="?",
        choices=sorted(CONFIGS),
        help="single artifact to generate",
    )
    parser.add_argument("--all", action="store_true",
                        help="generate every configured artifact")
    parser.add_argument("--aosp-root", type=Path, default=None,
                        help="AOSP tree root (default: tools/aosp_paths.py "
                             "resolution, overridable via AOSP_ROOT env)")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT,
                        help="root under which libs/ destinations are written "
                             "(default: repository root)")
    parser.add_argument("--verify-only", action="store_true",
                        help="only compare existing libs/ jars against the "
                             "frozen baselines; no AOSP read, no writes")
    parser.add_argument("--require-match", action="store_true",
                        help="exit 1 if any generated artifact differs from "
                             "its frozen baseline (Phase C gating aid)")
    args = parser.parse_args(argv)

    if args.verify_only:
        if args.all or args.artifact:
            parser.error("--verify-only cannot be combined with generation")
        overall = verify_only(args.output_root)
        return 0 if (overall == "MATCH" or not args.require_match) else 1

    selected = int(bool(args.all)) + int(bool(args.artifact))
    if selected != 1:
        parser.error("pass exactly one of: a single artifact, --all")
    names = sorted(CONFIGS) if args.all else [args.artifact]
    intermediates = soong_intermediates(args.aosp_root)
    verdicts = [generate(name, intermediates, args.output_root) for name in names]
    if args.require_match and "DIFF" in verdicts:
        print("--require-match: refusing to accept DIFF artifact(s); "
              "see the task 064 report for the drift analysis",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
