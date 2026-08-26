#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract tests for the narrow R8 adapter (app/proguard_gradle.flags).

Pins the cumulative user-approved rule set, one decision per rule:

- Task 044 (2026-08-21): exact single-FQN
  ``-dontwarn com.android.aconfig.annotations.AssumeTrueForR8``
  (docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md);
- task 060 (2026-08-25): same-family
  ``-dontwarn com.android.aconfig.annotations.AssumeFalseForR8``
  plus ``-dontobfuscate`` aligning R8 with Soong's never-obfuscated
  SystemUI build contract (dex.go:545);
- task 061 (2026-08-26): three exact-FQN ``-keep`` rules blocking R8
  horizontal class merging of identity-distinct CoreStartables
  (DumpManager registers by class name).

Still forbidden: wildcards/``**``, ``-assumevalues``,
``-assumenosideeffects``, and any ``-keep`` beyond the three approved
exact classes. The adapter is wired exactly once into the minified
``release`` build type of ``app/build.gradle.kts`` and never into
``debug``; the byte-exact AOSP-owned ``app/*.flags`` rule files carry
no active rule mentioning the annotation.
"""

import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
APP_DIR = _REPO / "app"
ADAPTER = APP_DIR / "proguard_gradle.flags"
BUILD_GRADLE = APP_DIR / "build.gradle.kts"

FQN = "com.android.aconfig.annotations.AssumeTrueForR8"
FQN_FALSE = "com.android.aconfig.annotations.AssumeFalseForR8"

# Cumulative user-approved active rules, in file order (one decision each:
# Task 044, task 060, task 061 — see module docstring for provenance).
APPROVED_RULES = [
    f"-dontwarn {FQN}",
    f"-dontwarn {FQN_FALSE}",
    "-dontobfuscate",
    "-keep class com.android.systemui.CoreStartable$Nop { *; }",
    "-keep class com.android.systemui.NoOpCoreStartable { *; }",
    "-keep class com.android.systemui.flags.FeatureFlagsReleaseStartable { *; }",
]
APPROVED_KEEP_RULES = {
    line for line in APPROVED_RULES if line.startswith("-keep ")
}

# Stable ordering markers in app/build.gradle.kts (audited 2026-08-21):
# buildTypes { debug { ... } release { ... } } followed by the AOSP bp comment.
DEBUG_MARKER = "debug {"
RELEASE_MARKER = "release {"
END_MARKER = "// AOSP bp: dxflags"


def _active_lines(text):
    """ProGuard-config lines with comments and blanks removed."""
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def _build_type_segments(text):
    """Split build.gradle.kts text into (debug, release) segment strings."""
    debug_idx = text.find(DEBUG_MARKER)
    release_idx = text.find(RELEASE_MARKER)
    end_idx = text.find(END_MARKER)
    if debug_idx < 0:
        raise AssertionError(f"marker not found: {DEBUG_MARKER!r}")
    if release_idx < 0:
        raise AssertionError(f"marker not found: {RELEASE_MARKER!r}")
    if end_idx < 0:
        raise AssertionError(f"marker not found: {END_MARKER!r}")
    if not debug_idx < release_idx < end_idx:
        raise AssertionError(
            "unexpected marker order in app/build.gradle.kts: "
            f"debug={debug_idx} release={release_idx} end={end_idx}"
        )
    return text[debug_idx:release_idx], text[release_idx:end_idx]


class TestAdapterFile(unittest.TestCase):
    def test_adapter_file_exists(self):
        self.assertTrue(ADAPTER.is_file(), f"missing adapter file: {ADAPTER}")

    def test_adapter_has_exactly_the_approved_rules(self):
        self.assertTrue(ADAPTER.is_file(), f"missing adapter file: {ADAPTER}")
        active = _active_lines(ADAPTER.read_text())
        self.assertEqual(active, APPROVED_RULES, active)

    def test_adapter_has_no_wildcard_or_assume_rules(self):
        self.assertTrue(ADAPTER.is_file(), f"missing adapter file: {ADAPTER}")
        for line in _active_lines(ADAPTER.read_text()):
            self.assertNotIn("**", line)
            self.assertFalse(line.startswith("-assumevalues"), line)
            self.assertFalse(line.startswith("-assumenosideeffects"), line)
            if line.startswith("-keep"):
                self.assertIn(line, APPROVED_KEEP_RULES, line)


class TestGradleWiring(unittest.TestCase):
    def setUp(self):
        text = BUILD_GRADLE.read_text()
        self.debug_seg, self.release_seg = _build_type_segments(text)

    def test_debug_does_not_reference_adapter(self):
        self.assertNotIn("proguard_gradle.flags", self.debug_seg)

    def test_release_references_adapter_exactly_once(self):
        self.assertEqual(self.release_seg.count('"proguard_gradle.flags"'), 1)


class TestAospRuleFilesUntouched(unittest.TestCase):
    def test_other_app_flags_have_no_active_annotation_rule(self):
        others = sorted(
            p for p in APP_DIR.glob("*.flags") if p != ADAPTER
        )
        self.assertTrue(others, "expected existing app/*.flags rule files")
        for path in others:
            for line in _active_lines(path.read_text()):
                self.assertNotIn(
                    FQN,
                    line,
                    f"{path.name} carries an active rule mentioning {FQN}",
                )


if __name__ == "__main__":
    unittest.main()
