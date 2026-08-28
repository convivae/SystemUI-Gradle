#!/usr/bin/env python3
"""Package the fifteen frozen misc JARs from AOSP Soong artifacts.

Task 064 (regeneration gap closure): every ``libs/`` JAR that was
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

Task 072 (C4 wiring, 2026-08-28): +3 surfaceeffects Kotlin JARs from
frameworks/libs/systemui/surfaceeffects (17 SystemUI-core bp static_libs
SurfaceEffectsComposeLib; SystemUI-17 sources import all three namespaces
com.android.systemui.surfaceeffects.{core,compose,view}.*). Each jar carries
only its own namespace's classes (verified disjoint); frozen at first
generation, source == baseline.

Usage::

    python3 tools/package_misc_jars.py --all            # regenerate all 15
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
#                 frozen; a mismatch warns about tree drift
#   baseline_sha256 fingerprint of the current libs/ jar (MATCH target)
#
# AOSP-17 (Task 071, 2026-08-27 re-freeze): all twelve mappings re-frozen
# against the android-17.0.0_r1 build; baseline = frozen source (the
# task-065 "script output wins" state). Drift vs the 16-era fingerprints:
# framework-statsd moved to the android_common_apex31 variant; SystemUI-tags
# and keepanno-annotations are byte-identical across vintages; the rest
# drifted in place (byte-level, same owning paths).
#
# Task 072 (C4 wiring, 2026-08-28): +3 surfaceeffects Kotlin jars. bp has
# no resource_dirs and the source trees carry no res directories → tier②
# JAR (rule F: frameworks/libs/systemui is not SystemUI-owned code).
CONFIGS: dict[str, dict] = {
    "framework": {
        "module": "framework",
        "relpath": "frameworks/base/framework/android_common/"
                   "turbine-combined/framework.jar",
        "destination": "libs/framework.jar",
        "source_sha256":
            "a2ff898903296097fa12951e786f8620cb213113a0325add81b9e0bb7ff9009d",
        "baseline_sha256":
            "a2ff898903296097fa12951e786f8620cb213113a0325add81b9e0bb7ff9009d",
    },
    "framework-statsd": {
        # 2026-08-26 (task 065, user-approved): baseline is the impl javac
        # jar (real classes). AOSP-17 (Task 071): the impl javac output moved
        # from the android_common_apex30 to the android_common_apex31 variant.
        "module": "framework-statsd.impl",
        "relpath": "packages/modules/StatsD/framework/framework-statsd.impl/"
                   "android_common_apex31/javac/framework-statsd.jar",
        "destination": "libs/framework-statsd.jar",
        "source_sha256":
            "5d3d05e78367d0a4f101769cf84688b44fb0734218e2ddc05a005677939eacdd",
        "baseline_sha256":
            "5d3d05e78367d0a4f101769cf84688b44fb0734218e2ddc05a005677939eacdd",
    },
    "android.car": {
        # 2026-08-26 (task 065, user-approved): baseline is the frozen
        # turbine-combined closure (stub classes incl. the static dep
        # closure). compileOnly wiring — stubs are fine. Re-frozen at 17.
        "module": "android.car",
        "relpath": "packages/services/Car/car-lib/android.car/android_common/"
                   "turbine-combined/android.car.jar",
        "destination": "libs/android.car.jar",
        "source_sha256":
            "ea64c4c5aaa871af13d5e89b2a39c26620d581878353b673736d3db4abb950f7",
        "baseline_sha256":
            "ea64c4c5aaa871af13d5e89b2a39c26620d581878353b673736d3db4abb950f7",
    },
    "android_module_lib_stubs_current": {
        "module": "android_module_lib_stubs_current",
        "relpath": "frameworks/base/api/android_module_lib_stubs_current/"
                   "android_common/turbine-combined/"
                   "android_module_lib_stubs_current.jar",
        "destination": "libs/android_module_lib_stubs_current.jar",
        "source_sha256":
            "95b9cec09dde7279a3f7c03d3d877c2e526318492a7c99e11990ecf41f0eb5e2",
        "baseline_sha256":
            "95b9cec09dde7279a3f7c03d3d877c2e526318492a7c99e11990ecf41f0eb5e2",
    },
    "SystemUI-proto": {
        "module": "SystemUI-proto",
        "relpath": "frameworks/base/packages/SystemUI/SystemUI-proto/"
                   "android_common/javac/SystemUI-proto.jar",
        "destination": "libs/SystemUI-proto.jar",
        "source_sha256":
            "159b2da75a80cfa19bce99d7aef01b6a1f4bf02cec4aa1ac328718082c43ee9a",
        "baseline_sha256":
            "159b2da75a80cfa19bce99d7aef01b6a1f4bf02cec4aa1ac328718082c43ee9a",
    },
    "SystemUI-statsd": {
        "module": "SystemUI-statsd",
        "relpath": "frameworks/base/packages/SystemUI/shared/SystemUI-statsd/"
                   "android_common/javac/SystemUI-statsd.jar",
        "destination": "libs/SystemUI-statsd.jar",
        "source_sha256":
            "f0ac4c6f0371d969549e0675c19b7a3db31b644f12e9e5b512413dfca5dc75c1",
        "baseline_sha256":
            "f0ac4c6f0371d969549e0675c19b7a3db31b644f12e9e5b512413dfca5dc75c1",
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
            "ebfae7a06640bfc2efef3c30843260f849ee6797ce0e7bc28255bf925764e0e5",
        "baseline_sha256":
            "ebfae7a06640bfc2efef3c30843260f849ee6797ce0e7bc28255bf925764e0e5",
    },
    "msdl": {
        "module": "msdl",
        "relpath": "frameworks/libs/systemui/msdllib/msdl/android_common/"
                   "kotlin/msdl.jar",
        "destination": "libs/msdl.jar",
        "source_sha256":
            "9687cf1bb9e930e2561c90037d07813074d38bf3ecfec3f0d69bd4e8d53a7ffe",
        "baseline_sha256":
            "9687cf1bb9e930e2561c90037d07813074d38bf3ecfec3f0d69bd4e8d53a7ffe",
    },
    "PlatformMotionTestingComposeValues": {
        "module": "PlatformMotionTestingComposeValues",
        "relpath": "platform_testing/libraries/motion/compose/values/"
                   "PlatformMotionTestingComposeValues/android_common/kotlin/"
                   "PlatformMotionTestingComposeValues.jar",
        "destination": "libs/PlatformMotionTestingComposeValues.jar",
        "source_sha256":
            "eedef559b852823db211006a77d090423240f5dcefbd87a70965eb8f0d1b29dd",
        "baseline_sha256":
            "eedef559b852823db211006a77d090423240f5dcefbd87a70965eb8f0d1b29dd",
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
        # separate clean_prebuilts.py step. Re-frozen at 17 (byte drift,
        # same owning path).
        "module": "tracinglib-platform",
        "relpath": "frameworks/libs/systemui/tracinglib/core/"
                   "tracinglib-platform/android_common/kotlin/"
                   "tracinglib-platform.jar",
        "destination": "libs/prebuilts/tracinglib-platform.jar",
        "source_sha256":
            "aa5077c38e9991970ca2230df7709e8d36fa8c36c79abc9b015668e8f72f6dcd",
        "baseline_sha256":
            "aa5077c38e9991970ca2230df7709e8d36fa8c36c79abc9b015668e8f72f6dcd",
    },
    # ↓↓↓ Task 072 (C4 wiring): surfaceeffects 三库 Kotlin 实现产物
    # （SurfaceEffectsCoreLib / SurfaceEffectsComposeLib / SurfaceEffectsViewLib）。
    # frameworks/libs/systemui/surfaceeffects/{core,compose,view}（规则 F tier② jar：
    # bp 无 resource_dirs、源树无 res）；17 SystemUI-core bp static_libs 含
    # SurfaceEffectsComposeLib，SystemUI-17 源码 import 三个 namespace
    # com.android.systemui.surfaceeffects.{core,compose,view}.*（AuthRippleView /
    # AuthRippleScrim / WiredChargingRippleController 等）。三 jar 各只含自有
    # namespace 类（互不相交，已验证）；取 Kotlin 实现产物（非 kotlin_headers）。
    "SurfaceEffectsCoreLib": {
        "module": "SurfaceEffectsCoreLib",
        "relpath": "frameworks/libs/systemui/surfaceeffects/core/"
                   "SurfaceEffectsCoreLib/android_common/kotlin/"
                   "SurfaceEffectsCoreLib.jar",
        "destination": "libs/SurfaceEffectsCoreLib.jar",
        "source_sha256":
            "c1ba44f192688687255bacc7bd96c1ef9dcc61aa9667da37e8d5ae3fa8974c35",
        "baseline_sha256":
            "c1ba44f192688687255bacc7bd96c1ef9dcc61aa9667da37e8d5ae3fa8974c35",
    },
    "SurfaceEffectsComposeLib": {
        "module": "SurfaceEffectsComposeLib",
        "relpath": "frameworks/libs/systemui/surfaceeffects/compose/"
                   "SurfaceEffectsComposeLib/android_common/kotlin/"
                   "SurfaceEffectsComposeLib.jar",
        "destination": "libs/SurfaceEffectsComposeLib.jar",
        "source_sha256":
            "8be1de742326d052b689250c008fd5f12de0d513a9f5c259eeb6cda109814658",
        "baseline_sha256":
            "8be1de742326d052b689250c008fd5f12de0d513a9f5c259eeb6cda109814658",
    },
    "SurfaceEffectsViewLib": {
        "module": "SurfaceEffectsViewLib",
        "relpath": "frameworks/libs/systemui/surfaceeffects/view/"
                   "SurfaceEffectsViewLib/android_common/kotlin/"
                   "SurfaceEffectsViewLib.jar",
        "destination": "libs/SurfaceEffectsViewLib.jar",
        "source_sha256":
            "dff01e0b86351ed5a88e85e56eb136c92da2b71c16a5ea4dcd7e0dd13a02e987",
        "baseline_sha256":
            "dff01e0b86351ed5a88e85e56eb136c92da2b71c16a5ea4dcd7e0dd13a02e987",
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
