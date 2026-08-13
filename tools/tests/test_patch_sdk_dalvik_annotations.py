#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/patch_sdk_dalvik_annotations.py.

Tests use fixture jars under tempfile directories — the real SysUISdk is never
touched. Covers: correct class set, idempotency, no-overwrite of existing
entries, backup creation, and package-scope boundary.
"""
import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "patch_sdk_dalvik_annotations.py"
_spec = importlib.util.spec_from_file_location("patch_sdk_dalvik_annotations", _SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)

PKG = module.PACKAGE  # dalvik/annotation/optimization

# The 6 upstream classes in core-libart's optimization package.
ALL_SIX = [
    "CriticalNative",
    "DeadReferenceSafe",
    "FastNative",
    "NeverCompile",
    "NeverInline",
    "ReachabilitySensitive",
]


def _entry(name: str) -> str:
    return f"{PKG}/{name}.class"


def _make_jar(path: Path, classes: list[str], payload: bytes = b"class-bytes") -> None:
    """Create a jar containing the given class entries under PKG."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        # include the bare directory entry like real jars do
        archive.writestr(f"{PKG}/", b"")
        for name in classes:
            archive.writestr(_entry(name), payload)


class TestListPackageClasses(unittest.TestCase):
    def test_lists_only_class_files_under_package(self):
        with tempfile.TemporaryDirectory() as d:
            jar = Path(d) / "src.jar"
            _make_jar(jar, ALL_SIX)
            # also add an unrelated class to ensure it is excluded
            with zipfile.ZipFile(jar, "a") as archive:
                archive.writestr("java/lang/String.class", b"x")
            classes = module.list_package_classes(jar)
            self.assertEqual(classes, {_entry(n) for n in ALL_SIX})

    def test_ignores_bare_directory_entry(self):
        with tempfile.TemporaryDirectory() as d:
            jar = Path(d) / "src.jar"
            _make_jar(jar, ["NeverCompile"])
            classes = module.list_package_classes(jar)
            self.assertEqual(classes, {_entry("NeverCompile")})


class TestPatchTarget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "core-libart.jar"
        _make_jar(self.source, ALL_SIX)

    def tearDown(self):
        self.tmp.cleanup()

    def test_injects_only_missing_four_classes(self):
        target = self.root / "android.jar"
        # target ships the public-SDK partial set (CriticalNative, FastNative)
        _make_jar(target, ["CriticalNative", "FastNative"])
        res = module.patch_target(target, self.source)
        injected_names = [
            e.split("/")[-1].removesuffix(".class") for e in res["injected"]
        ]
        self.assertEqual(
            set(injected_names),
            {"NeverCompile", "NeverInline", "DeadReferenceSafe",
             "ReachabilitySensitive"},
        )
        self.assertEqual(
            set(e.split("/")[-1].removesuffix(".class") for e in res["already"]),
            {"CriticalNative", "FastNative"},
        )
        # after patch, target has all 6
        after = module.list_package_classes(target)
        self.assertEqual(after, {_entry(n) for n in ALL_SIX})

    def test_idempotent_re_run_is_noop(self):
        target = self.root / "android.jar"
        _make_jar(target, ["CriticalNative", "FastNative"])
        first = module.patch_target(target, self.source)
        self.assertTrue(first["injected"])
        second = module.patch_target(target, self.source)
        self.assertEqual(second["injected"], [])
        self.assertEqual(
            set(e.split("/")[-1].removesuffix(".class") for e in second["already"]),
            set(ALL_SIX),
        )

    def test_does_not_overwrite_existing_entries(self):
        target = self.root / "android.jar"
        # target already has NeverCompile with a DISTINCT payload
        marker = b"TARGET-NeverCompile"
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr(f"{PKG}/", b"")
            archive.writestr(_entry("CriticalNative"), b"a")
            archive.writestr(_entry("FastNative"), b"b")
            archive.writestr(_entry("NeverCompile"), marker)
        res = module.patch_target(target, self.source)
        # NeverCompile must not be in injected (it already exists)
        injected_names = {
            e.split("/")[-1].removesuffix(".class") for e in res["injected"]
        }
        self.assertNotIn("NeverCompile", injected_names)
        self.assertIn("NeverCompile", {e.split("/")[-1].removesuffix(".class")
                                       for e in res["already"]})
        # the existing NeverCompile bytes are preserved (not overwritten)
        with zipfile.ZipFile(target, "r") as archive:
            self.assertEqual(archive.read(_entry("NeverCompile")), marker)

    def test_backup_created_on_first_mutation(self):
        target = self.root / "core-for-system-modules.jar"
        _make_jar(target, ["CriticalNative", "FastNative"])
        orig_bytes = target.read_bytes()
        res = module.patch_target(target, self.source)
        self.assertIsNotNone(res["backup"])
        backup = Path(res["backup"])
        self.assertTrue(backup.exists())
        self.assertEqual(backup.name, "core-for-system-modules.jar.orig")
        # backup preserves pre-mutation bytes
        self.assertEqual(backup.read_bytes(), orig_bytes)

    def test_existing_backup_is_not_overwritten(self):
        target = self.root / "android.jar"
        _make_jar(target, ["CriticalNative", "FastNative"])
        # pre-existing .orig from a prior SDK mutation (2026-07-22 precedent)
        orig = target.with_name("android.jar.orig")
        pristine = b"PRISTINE-PRE-MERGE"
        orig.write_bytes(pristine)
        res = module.patch_target(target, self.source)
        self.assertIsNone(res["backup"])  # did not create/overwrite
        # pristine backup untouched
        self.assertEqual(orig.read_bytes(), pristine)

    def test_no_mutation_when_already_complete(self):
        target = self.root / "android.jar"
        _make_jar(target, ALL_SIX)  # already has everything
        before = target.read_bytes()
        res = module.patch_target(target, self.source)
        self.assertEqual(res["injected"], [])
        self.assertIsNone(res["backup"])  # no backup needed (no mutation)
        # file untouched
        self.assertEqual(target.read_bytes(), before)

    def test_preserves_unrelated_entries(self):
        target = self.root / "android.jar"
        unrelated = b"java-lang-string"
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr(f"{PKG}/", b"")
            archive.writestr(_entry("CriticalNative"), b"a")
            archive.writestr(_entry("FastNative"), b"b")
            archive.writestr("java/lang/String.class", unrelated)
        module.patch_target(target, self.source)
        with zipfile.ZipFile(target, "r") as archive:
            self.assertEqual(archive.read("java/lang/String.class"), unrelated)

    def test_scope_boundary_only_optimization_package(self):
        """No class outside dalvik/annotation/optimization is ever injected,
        even if the source jar carries other packages."""
        source = self.root / "core-libart-extra.jar"
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr(f"{PKG}/", b"")
            for n in ALL_SIX:
                archive.writestr(_entry(n), b"x")
            # unrelated package that must NOT be injected
            archive.writestr("java/lang/Thread.class", b"secret")
            archive.writestr("dalvik/annotation/Signature.class", b"secret2")
        target = self.root / "android.jar"
        _make_jar(target, ["CriticalNative", "FastNative"])
        res = module.patch_target(target, source)
        # only optimization-package classes were injected
        for e in res["injected"]:
            self.assertTrue(e.startswith(f"{PKG}/"))
        # unrelated entries absent from target
        with zipfile.ZipFile(target, "r") as archive:
            names = set(archive.namelist())
        self.assertNotIn("java/lang/Thread.class", names)
        self.assertNotIn("dalvik/annotation/Signature.class", names)

    def test_error_when_source_has_no_optimization_classes(self):
        bad_source = self.root / "empty.jar"
        with zipfile.ZipFile(bad_source, "w") as archive:
            archive.writestr("java/lang/Object.class", b"x")
        target = self.root / "android.jar"
        _make_jar(target, ["CriticalNative", "FastNative"])
        with self.assertRaises(RuntimeError):
            module.patch_target(target, bad_source)

    def test_error_when_target_missing(self):
        target = self.root / "nope.jar"
        with self.assertRaises(FileNotFoundError):
            module.patch_target(target, self.source)


if __name__ == "__main__":
    unittest.main()
