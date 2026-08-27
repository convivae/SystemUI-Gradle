#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/package_misc_jars.py — task 064 frozen misc-JAR map.

Covers:
  1. frozen mapping completeness (12 entries, names, modules, destinations)
  2. relpath/destination shape discipline (never absolute, always libs/)
  3. sha256 field format
  4. resolve_source joins under soong intermediates
  5. generate(): byte copy + MATCH/DIFF verdicts + drift warning
  6. verify_only(): MATCH / DIFF / MISSING against the output root
  7. CLI selection rules (--all vs single, --verify-only conflicts)
  8. aosp_paths integration (single AOSP root source)
"""

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# The script under test imports aosp_paths; make tools/ importable no matter
# where the test runner is invoked from.
_TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import aosp_paths

_SCRIPT = _TOOLS_DIR / "package_misc_jars.py"
_spec = importlib.util.spec_from_file_location("package_misc_jars", _SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)

EXPECTED_ENTRIES = {
    "framework": ("framework", "libs/framework.jar"),
    "framework-statsd": ("framework-statsd.impl", "libs/framework-statsd.jar"),
    "android.car": ("android.car", "libs/android.car.jar"),
    "android_module_lib_stubs_current": (
        "android_module_lib_stubs_current",
        "libs/android_module_lib_stubs_current.jar",
    ),
    "SystemUI-proto": ("SystemUI-proto", "libs/SystemUI-proto.jar"),
    "SystemUI-statsd": ("SystemUI-statsd", "libs/SystemUI-statsd.jar"),
    "SystemUI-tags": ("SystemUI-tags", "libs/SystemUI-tags.jar"),
    "contextualeducationlib": (
        "contextualeducationlib",
        "libs/contextualeducationlib.jar",
    ),
    "msdl": ("msdl", "libs/msdl.jar"),
    "PlatformMotionTestingComposeValues": (
        "PlatformMotionTestingComposeValues",
        "libs/PlatformMotionTestingComposeValues.jar",
    ),
    "keepanno-annotations": (
        "keepanno-annotations",
        "libs/keepanno-annotations.jar",
    ),
    "tracinglib-platform": (
        "tracinglib-platform",
        "libs/prebuilts/tracinglib-platform.jar",
    ),
}


class TestFrozenMapping(unittest.TestCase):
    def test_mapping_covers_exactly_the_twelve_gap_artifacts(self):
        self.assertEqual(set(module.CONFIGS), set(EXPECTED_ENTRIES))
        self.assertEqual(len(module.CONFIGS), 12)

    def test_entries_carry_module_and_destination(self):
        for name, (soong_module, destination) in EXPECTED_ENTRIES.items():
            with self.subTest(entry=name):
                self.assertEqual(module.CONFIGS[name]["module"], soong_module)
                self.assertEqual(
                    module.CONFIGS[name]["destination"], destination
                )

    def test_relpaths_are_relative_and_under_expected_roots(self):
        for name, entry in module.CONFIGS.items():
            with self.subTest(entry=name):
                relpath = Path(entry["relpath"])
                self.assertFalse(relpath.is_absolute())
                # Frozen intermediates paths are never absolute and contain
                # the owning module directory before the variant segments.
                self.assertIn(entry["module"], entry["relpath"])
                self.assertTrue(
                    any(part in entry["relpath"].split("/")
                        for part in ("javac", "kotlin", "turbine-combined",
                                     "combined"))
                )

    def test_destinations_live_under_libs(self):
        for name, entry in module.CONFIGS.items():
            with self.subTest(entry=name):
                destination = Path(entry["destination"])
                self.assertEqual(destination.parts[0], "libs")
                self.assertTrue(destination.name.endswith(".jar"))

    def test_sha_fields_are_lowercase_hex_fingerprints(self):
        for name, entry in module.CONFIGS.items():
            with self.subTest(entry=name):
                for field in ("source_sha256", "baseline_sha256"):
                    self.assertRegex(
                        entry[field], r"^[0-9a-f]{64}$"
                    )

    def test_no_entry_is_frozen_as_diff(self):
        # Task 065 (user-approved replacement): framework-statsd and
        # android.car were replaced with the script-regenerated Soong outputs
        # on 2026-08-26, and their baselines re-frozen to the sources. Every
        # frozen source fingerprint must now equal its baseline fingerprint —
        # a mismatch means someone introduced a new hand-copied jar.
        diff = {
            name
            for name, entry in module.CONFIGS.items()
            if entry["source_sha256"] != entry["baseline_sha256"]
        }
        self.assertEqual(diff, set())

    def test_replaced_jars_are_the_frozen_soong_sources(self):
        # Pins the task 065 replacement hashes (re-frozen at AOSP-17 in Task
        # 071; framework-statsd also moved to the apex31 variant) so an
        # accidental revert to a hand copy is caught by CI.
        self.assertEqual(
            module.CONFIGS["framework-statsd"]["baseline_sha256"],
            "5d3d05e78367d0a4f101769cf84688b44fb0734218e2ddc05a005677939eacdd",
        )
        self.assertEqual(
            module.CONFIGS["framework-statsd"]["relpath"],
            "packages/modules/StatsD/framework/framework-statsd.impl/"
            "android_common_apex31/javac/framework-statsd.jar",
        )
        self.assertEqual(
            module.CONFIGS["android.car"]["baseline_sha256"],
            "ea64c4c5aaa871af13d5e89b2a39c26620d581878353b673736d3db4abb950f7",
        )

    def test_keepanno_shares_the_sysuisdk_frozen_input(self):
        # build_sysuisdk.py AOSP_INPUT_RELPATHS["keepanno_jar"] is the same
        # artifact; both mappings must stay in sync.
        relpath = module.CONFIGS["keepanno-annotations"]["relpath"]
        self.assertEqual(
            relpath,
            "prebuilts/r8/keepanno-annotations/android_common/combined/"
            "keepanno-annotations.jar",
        )

    def test_framework_shares_the_sysuisdk_frozen_input(self):
        relpath = module.CONFIGS["framework"]["relpath"]
        self.assertEqual(
            relpath,
            "frameworks/base/framework/android_common/turbine-combined/"
            "framework.jar",
        )


class TestResolveAndGenerate(unittest.TestCase):
    def test_resolve_source_joins_under_soong_intermediates(self):
        resolved = module.resolve_source(
            "framework", Path("/opt/aosp/out/soong/.intermediates")
        )
        self.assertEqual(
            resolved,
            Path("/opt/aosp/out/soong/.intermediates")
            / module.CONFIGS["framework"]["relpath"],
        )

    def _fake_entry(self, root, name, payload=b"jar-bytes"):
        source = root / "intermediates" / module.CONFIGS[name]["relpath"]
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(payload)
        return source, hashlib.sha256(payload).hexdigest()

    def test_generate_copies_bytes_and_reports_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, digest = self._fake_entry(root, "framework")
            entry = dict(module.CONFIGS["framework"])
            entry["source_sha256"] = digest
            entry["baseline_sha256"] = digest
            with mock.patch.dict(module.CONFIGS, {"framework": entry}):
                verdict = module.generate(
                    "framework",
                    root / "intermediates",
                    root / "out-root",
                )
            self.assertEqual(verdict, "MATCH")
            generated = root / "out-root" / "libs" / "framework.jar"
            self.assertEqual(generated.read_bytes(), b"jar-bytes")
            self.assertEqual(source.read_bytes(), b"jar-bytes")

    def test_generate_reports_diff_without_failing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, digest = self._fake_entry(root, "android.car")
            entry = dict(module.CONFIGS["android.car"])
            entry["source_sha256"] = digest
            entry["baseline_sha256"] = "0" * 64
            with mock.patch.dict(module.CONFIGS, {"android.car": entry}):
                verdict = module.generate(
                    "android.car", root / "intermediates", root / "out-root"
                )
            self.assertEqual(verdict, "DIFF")

    def test_generate_warns_on_source_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fake_entry(root, "msdl")
            entry = dict(module.CONFIGS["msdl"])
            # Tree drifted since the mapping was frozen (stale source sha),
            # but the current artifact still matches the baseline.
            entry["source_sha256"] = "f" * 64
            entry["baseline_sha256"] = hashlib.sha256(b"jar-bytes").hexdigest()
            with mock.patch.dict(module.CONFIGS, {"msdl": entry}):
                with mock.patch("builtins.print") as printed:
                    verdict = module.generate(
                        "msdl", root / "intermediates", root / "out-root"
                    )
            self.assertEqual(verdict, "MATCH")
            self.assertTrue(
                any("drifted" in str(call.args[0]) for call in printed.call_args_list)
            )

    def test_generate_missing_source_is_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                module.generate(
                    "msdl", root / "intermediates", root / "out-root"
                )


class TestVerifyOnly(unittest.TestCase):
    def test_verify_only_match_diff_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = root / "libs" / "framework.jar"
            good.parent.mkdir(parents=True)
            good.write_bytes(b"good")
            entry = dict(module.CONFIGS["framework"])
            entry["baseline_sha256"] = hashlib.sha256(b"good").hexdigest()
            bad = root / "libs" / "msdl.jar"
            bad.write_bytes(b"bad")
            with mock.patch.dict(
                module.CONFIGS, {"framework": entry, "msdl": module.CONFIGS["msdl"]}
            ):
                with mock.patch("builtins.print"):
                    overall = module.verify_only(root)
            self.assertEqual(overall, "DIFF")  # msdl DIFF + others MISSING

    def test_verify_only_all_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            patched = {}
            for name in module.CONFIGS:
                destination = root / module.CONFIGS[name]["destination"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                payload = f"payload-{name}".encode()
                destination.write_bytes(payload)
                entry = dict(module.CONFIGS[name])
                entry["baseline_sha256"] = hashlib.sha256(payload).hexdigest()
                patched[name] = entry
            with mock.patch.dict(module.CONFIGS, patched):
                with mock.patch("builtins.print"):
                    overall = module.verify_only(root)
            self.assertEqual(overall, "MATCH")


class TestMainCli(unittest.TestCase):
    def test_require_match_fails_on_diff(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, digest = self._fake(root, "msdl")
            entry = dict(module.CONFIGS["msdl"])
            entry["source_sha256"] = digest
            entry["baseline_sha256"] = "0" * 64
            with mock.patch.dict(module.CONFIGS, {"msdl": entry}):
                rc = module.main(
                    ["msdl", "--aosp-root", str(root),
                     "--output-root", str(root / "out"), "--require-match"]
                )
            self.assertEqual(rc, 1)

    def test_require_match_passes_on_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, digest = self._fake(root, "msdl")
            entry = dict(module.CONFIGS["msdl"])
            entry["source_sha256"] = digest
            entry["baseline_sha256"] = digest
            with mock.patch.dict(module.CONFIGS, {"msdl": entry}):
                rc = module.main(
                    ["msdl", "--aosp-root", str(root),
                     "--output-root", str(root / "out"), "--require-match"]
                )
            self.assertEqual(rc, 0)

    def test_aosp_root_routes_through_aosp_paths(self):
        # The --aosp-root value is delegated to aosp_paths.soong_intermediates.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, digest = self._fake(root, "msdl")
            entry = dict(module.CONFIGS["msdl"])
            entry["source_sha256"] = digest
            entry["baseline_sha256"] = digest
            with mock.patch.dict(module.CONFIGS, {"msdl": entry}):
                with mock.patch.object(
                    module, "soong_intermediates",
                    side_effect=aosp_paths.soong_intermediates,
                ) as resolved:
                    rc = module.main(
                        ["msdl", "--aosp-root", str(root),
                         "--output-root", str(root / "out")]
                    )
            self.assertEqual(rc, 0)
            resolved.assert_called_once_with(root)

    def test_verify_only_rejects_generation_flags(self):
        with self.assertRaises(SystemExit):
            module.main(["--verify-only", "--all"])

    def test_selection_is_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            module.main(["msdl", "--all"])

    def test_no_selection_is_an_error(self):
        with self.assertRaises(SystemExit):
            module.main([])

    @staticmethod
    def _fake(root, name):
        source = root / "out/soong/.intermediates" / module.CONFIGS[name]["relpath"]
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"payload")
        return source, hashlib.sha256(b"payload").hexdigest()


class TestAospPathsIntegration(unittest.TestCase):
    def test_verify_only_default_output_root_is_repo_root(self):
        self.assertEqual(module.REPO_ROOT, _TOOLS_DIR.parent)

    def test_script_uses_shared_aosp_root_module(self):
        # package_misc_jars must not keep its own hardcoded root.
        self.assertEqual(
            module.soong_intermediates.__module__, "aosp_paths"
        )


if __name__ == "__main__":
    unittest.main()
