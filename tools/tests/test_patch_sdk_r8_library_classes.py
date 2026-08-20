#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/patch_sdk_r8_library_classes.py (Task 041).

All tests use fixture jars under tempfile directories — the real SysUISdk and
the real AOSP source artifacts are never touched. Covers: the exact 35-entry
approved inventory, group counts, Task 042 boundary (AssumeTrueForR8 absent),
source-entry existence, mutation safety (idempotency, collision rejection,
backup scoping, determinism, unrelated-entry preservation), and error paths.
"""
import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "patch_sdk_r8_library_classes.py"
_spec = importlib.util.spec_from_file_location("patch_sdk_r8_library_classes", _SCRIPT)
module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = module  # dataclass needs the module registered
_spec.loader.exec_module(module)

ClassSlice = module.ClassSlice

# --- approved entry declarations (mirror of the plan's exact slices) -------

IO_UTILS = (
    "libcore/io/IoUtils.class",
    "libcore/io/IoUtils$FileReader.class",
)
NATIVE_ALLOCATION = (
    "libcore/util/NativeAllocationRegistry.class",
    "libcore/util/NativeAllocationRegistry$CleanerRunner.class",
    "libcore/util/NativeAllocationRegistry$CleanerThunk.class",
    "libcore/util/NativeAllocationRegistry$Metrics.class",
)
DDMC = (
    "org/apache/harmony/dalvik/ddmc/Chunk.class",
    "org/apache/harmony/dalvik/ddmc/ChunkHandler.class",
    "org/apache/harmony/dalvik/ddmc/DdmServer.class",
    "org/apache/harmony/dalvik/ddmc/DdmVmInternal.class",
)
UNSUPPORTED = (
    "android/compat/annotation/UnsupportedAppUsage.class",
    "android/compat/annotation/UnsupportedAppUsage$Container.class",
)
ACONFIG = ("com/android/aconfig/annotations/AconfigFlagAccessor.class",)
KEEPANNO = tuple(
    f"com/android/tools/r8/keepanno/annotations/{n}.class" for n in (
        "AnnotationPattern", "CheckOptimizedOut", "CheckRemoved",
        "ClassAccessFlags", "ClassNamePattern", "FieldAccessFlags",
        "InstanceOfPattern", "KeepBinding", "KeepCondition", "KeepConstraint",
        "KeepEdge", "KeepForApi", "KeepItemKind", "KeepOption", "KeepTarget",
        "MemberAccessFlags", "MethodAccessFlags", "StringPattern",
        "TypePattern", "UsedByNative", "UsedByReflection", "UsesReflection"))

APPROVED_35 = sorted(IO_UTILS + NATIVE_ALLOCATION + DDMC + UNSUPPORTED + ACONFIG
                     + KEEPANNO)
assert len(APPROVED_35) == 35


def _payload(entry: str) -> bytes:
    """Deterministic distinct fake class bytes for a fixture entry."""
    return b"\xCA\xFE\xBA\xBE" + entry.encode("utf-8")


def _make_jar(path: Path, entries) -> None:
    """Create a jar with the given entries ({name: bytes} or iterable of names
    populated with _payload)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(entries, dict):
        entries = {e: _payload(e) for e in entries}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


class _SourceFixtures:
    """Provisions the four source jars with all approved entries (fake bytes)
    plus unrelated out-of-scope entries."""

    def __init__(self, root: Path) -> None:
        self.core = root / "core-libart.jar"
        _make_jar(self.core, list(IO_UTILS + NATIVE_ALLOCATION + DDMC) + [
            # unrelated core-libart content that must never be injected
            "dalvik/annotation/optimization/NeverCompile.class",
            "java/lang/X.class",
            "META-INF/MANIFEST.MF",
        ])
        self.unsupported = root / "unsupportedappusage.jar"
        _make_jar(self.unsupported, list(UNSUPPORTED) + [
            "java/lang/Y.class",  # unrelated
        ])
        self.aconfig = root / "aconfig-annotations-lib.jar"
        _make_jar(self.aconfig, list(ACONFIG) + [
            # sibling classes in the same source package, deliberately NOT
            # approved (AssumeTrueForR8 is Task 042)
            "com/android/aconfig/annotations/AssumeTrueForR8.class",
            "com/android/aconfig/annotations/AssumeFalseForR8.class",
            "com/android/aconfig/annotations/VisibleForTesting.class",
            "com/android/aconfig/annotations/VisibleForTesting$Visibility.class",
        ])
        self.keepanno = root / "keepanno-annotations.jar"
        _make_jar(self.keepanno, list(KEEPANNO) + [
            # out-of-package sibling + jar-level metadata, never injected
            "com/android/tools/r8/other/Foo.class",
            "META-INF/MANIFEST.MF",
            "r8-version.properties",
        ])

    def slices(self):
        return module.task041_slices(self.core, self.unsupported,
                                     self.aconfig, self.keepanno)


# --- inventory tests -------------------------------------------------------

class TestTask041Slices(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fx = _SourceFixtures(Path(self.tmp.name))

    def test_exactly_35_unique_entries(self):
        slices = self.fx.slices()
        entries = [e for s in slices for e in s.entries]
        self.assertEqual(len(entries), 35)
        self.assertEqual(len(set(entries)), 35)
        self.assertEqual(sorted(entries), APPROVED_35)

    def test_assume_true_for_r8_absent(self):
        slices = self.fx.slices()
        entries = [e for s in slices for e in s.entries]
        self.assertNotIn(
            "com/android/aconfig/annotations/AssumeTrueForR8.class", entries)

    def test_group_counts(self):
        slices = self.fx.slices()
        counts = [len(s.entries) for s in slices]
        self.assertEqual(counts, [2, 4, 4, 2, 1, 22])

    def test_each_declared_entry_exists_in_its_assigned_source(self):
        for sl in self.fx.slices():
            with zipfile.ZipFile(sl.source_jar) as zf:
                names = set(zf.namelist())
            for e in sl.entries:
                self.assertIn(e, names, f"{e} not in {sl.source_jar}")

    def test_keepanno_slice_is_exactly_the_approved_22(self):
        keep = [s for s in self.fx.slices() if s.label.startswith("keepanno")][0]
        self.assertEqual(sorted(keep.entries), sorted(KEEPANNO))

    def test_slice_fields(self):
        sl = self.fx.slices()[0]
        self.assertIsInstance(sl, ClassSlice)
        self.assertEqual(sl.label, "core-libart IoUtils")
        self.assertEqual(sl.source_jar, self.fx.core)


# --- mutation-safety tests -------------------------------------------------

class TestPatchTarget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fx = _SourceFixtures(self.root)
        self.slices = self.fx.slices()
        # a realistic target: unrelated platform entries + manifest, no
        # approved entries yet
        self.target = self.root / "android.jar"
        _make_jar(self.target, {
            "android/A.class": b"\xCA\xFE\xBA\xBEbaseA",
            "java/lang/String.class": b"\xCA\xFE\xBA\xBEstr",
            "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\n",
        })
        self.pre_bytes = self.target.read_bytes()

    # 1. missing all 35 -> exactly 35 source-identical bytes injected
    def test_injects_35_source_identical_entries(self):
        res = module.patch_target(self.target, self.slices)
        self.assertEqual(res["injected"], APPROVED_35)
        with zipfile.ZipFile(self.target) as zf:
            for entry in APPROVED_35:
                self.assertEqual(zf.read(entry), _payload(entry))
            # nothing beyond the 35 + original entries
            names = {n for n in zf.namelist() if not n.endswith("/")}
        self.assertEqual(names, set(APPROVED_35) | {
            "android/A.class", "java/lang/String.class",
            "META-INF/MANIFEST.MF"})

    # 2. already source-identical -> reported in already, not rewritten
    def test_already_identical_entries_reported_not_rewritten(self):
        # pre-populate 3 approved entries with identical source bytes
        pre = {e: _payload(e) for e in (IO_UTILS[0], UNSUPPORTED[0], ACONFIG[0])}
        with zipfile.ZipFile(self.target, "a") as zf:
            for e, data in pre.items():
                zf.writestr(e, data)
        res = module.patch_target(self.target, self.slices)
        self.assertEqual(
            res["already"], sorted((IO_UTILS[0], UNSUPPORTED[0], ACONFIG[0])))
        self.assertEqual(len(res["injected"]), 32)
        with zipfile.ZipFile(self.target) as zf:
            for e, data in pre.items():
                self.assertEqual(zf.read(e), data)

    def test_fully_patched_target_is_noop_without_backup(self):
        # target already has all 35 with identical bytes
        _make_jar(self.target, {
            "android/A.class": b"\xCA\xFE\xBA\xBEbaseA",
            **{e: _payload(e) for e in APPROVED_35},
        })
        before = self.target.read_bytes()
        res = module.patch_target(self.target, self.slices)
        self.assertEqual(res["injected"], [])
        self.assertEqual(res["already"], APPROVED_35)
        self.assertIsNone(res["backup"])
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(
            self.target.with_name("android.jar.bak-prer8lib").exists())

    # 3. same path with different bytes -> RuntimeError containing 'collision'
    def test_collision_with_different_bytes_raises(self):
        with zipfile.ZipFile(self.target, "a") as zf:
            zf.writestr(IO_UTILS[0], b"\xCA\xFE\xBA\xBETAMPERED")
        with self.assertRaises(RuntimeError) as ctx:
            module.patch_target(self.target, self.slices)
        self.assertIn("collision", str(ctx.exception))
        # target untouched, no backup created
        with zipfile.ZipFile(self.target) as zf:
            self.assertEqual(zf.read(IO_UTILS[0]), b"\xCA\xFE\xBA\xBETAMPERED")
        self.assertFalse(
            self.target.with_name("android.jar.bak-prer8lib").exists())

    # 4. undeclared source classes are never injected
    def test_undeclared_source_classes_never_injected(self):
        res = module.patch_target(self.target, self.slices)
        injected_set = set(res["injected"])
        self.assertEqual(injected_set, set(APPROVED_35))
        with zipfile.ZipFile(self.target) as zf:
            names = set(zf.namelist())
        for undeclared in (
            "dalvik/annotation/optimization/NeverCompile.class",
            "java/lang/X.class",
            "java/lang/Y.class",
            "com/android/aconfig/annotations/AssumeTrueForR8.class",
            "com/android/aconfig/annotations/AssumeFalseForR8.class",
            "com/android/aconfig/annotations/VisibleForTesting.class",
            "com/android/tools/r8/other/Foo.class",
            "r8-version.properties",
        ):
            self.assertNotIn(undeclared, names)

    # 5. duplicate class paths across slices rejected before mutation
    def test_duplicate_entries_across_slices_rejected(self):
        bad_slices = self.slices + (
            ClassSlice("dup", self.fx.core, (IO_UTILS[0],)),)
        with self.assertRaises(RuntimeError) as ctx:
            module.patch_target(self.target, bad_slices)
        self.assertIn("duplicate", str(ctx.exception))
        self.assertEqual(self.target.read_bytes(), self.pre_bytes)
        self.assertFalse(
            self.target.with_name("android.jar.bak-prer8lib").exists())

    # 6. missing declared source entry rejected before mutation
    def test_missing_declared_source_entry_rejected(self):
        bad_slices = (
            ClassSlice("bad", self.fx.core,
                       ("libcore/io/DoesNotExist.class",)),)
        with self.assertRaises(RuntimeError) as ctx:
            module.patch_target(self.target, bad_slices)
        self.assertIn("libcore/io/DoesNotExist.class", str(ctx.exception))
        self.assertEqual(self.target.read_bytes(), self.pre_bytes)
        self.assertFalse(
            self.target.with_name("android.jar.bak-prer8lib").exists())

    # 7. first mutation creates .bak-prer8lib preserving pre-mutation bytes
    def test_backup_created_on_first_mutation(self):
        module.patch_target(self.target, self.slices)
        bak = self.target.with_name("android.jar.bak-prer8lib")
        self.assertTrue(bak.exists())
        self.assertEqual(bak.read_bytes(), self.pre_bytes)

    # 8. an existing backup is never overwritten
    def test_existing_backup_not_overwritten(self):
        bak = self.target.with_name("android.jar.bak-prer8lib")
        pristine = b"PRISTINE-PRE-S3B"
        bak.write_bytes(pristine)
        res = module.patch_target(self.target, self.slices)
        self.assertIsNone(res["backup"])
        self.assertEqual(bak.read_bytes(), pristine)

    # 9. second run is a byte-for-byte no-op with no new backup
    def test_second_run_is_byte_for_byte_noop(self):
        module.patch_target(self.target, self.slices)
        after_first = self.target.read_bytes()
        res = module.patch_target(self.target, self.slices)
        self.assertEqual(res["injected"], [])
        self.assertEqual(res["already"], APPROVED_35)
        self.assertIsNone(res["backup"])
        self.assertEqual(self.target.read_bytes(), after_first)

    # 10. two independent identical inputs produce byte-identical outputs
    def test_deterministic_output(self):
        target2 = self.root / "android-2.jar"
        target2.write_bytes(self.pre_bytes)
        module.patch_target(self.target, self.slices)
        module.patch_target(target2, self.slices)
        self.assertEqual(self.target.read_bytes(), target2.read_bytes())

    # 11. unrelated target entries and metadata remain present
    def test_unrelated_entries_and_metadata_preserved(self):
        # rebuild target with dated ZipInfo metadata for an unrelated entry
        # (even second: DOS zip timestamps have 2-second granularity)
        dated = zipfile.ZipInfo("java/util/Date.class", (2020, 1, 2, 3, 4, 6))
        dated.external_attr = 0o644 << 16
        with zipfile.ZipFile(self.target, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("android/A.class", b"\xCA\xFE\xBA\xBEbaseA")
            zf.writestr(dated, b"\xCA\xFE\xBA\xBEdated")
            zf.writestr("META-INF/MANIFEST.MF", b"Manifest-Version: 1.0\n")
        module.patch_target(self.target, self.slices)
        with zipfile.ZipFile(self.target) as zf:
            infos = {i.filename: i for i in zf.infolist()}
            self.assertEqual(zf.read("android/A.class"), b"\xCA\xFE\xBA\xBEbaseA")
            self.assertEqual(zf.read("java/util/Date.class"),
                             b"\xCA\xFE\xBA\xBEdated")
            self.assertEqual(zf.read("META-INF/MANIFEST.MF"),
                             b"Manifest-Version: 1.0\n")
            # metadata preserved on the unrelated entry
            self.assertEqual(infos["java/util/Date.class"].date_time,
                             (2020, 1, 2, 3, 4, 6))
            self.assertEqual(
                infos["java/util/Date.class"].external_attr,
                0o644 << 16)

    # 12. missing target/source files raise FileNotFoundError
    def test_missing_target_raises(self):
        with self.assertRaises(FileNotFoundError):
            module.patch_target(self.root / "nope.jar", self.slices)

    def test_missing_source_raises(self):
        bad_slices = (
            ClassSlice("bad", self.root / "missing-source.jar", IO_UTILS),)
        with self.assertRaises(FileNotFoundError):
            module.patch_target(self.target, bad_slices)


# --- validate_target (read-only) tests --------------------------------------

class TestValidateTarget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fx = _SourceFixtures(self.root)
        self.slices = self.fx.slices()
        self.target = self.root / "core-for-system-modules.jar"
        _make_jar(self.target, {
            "java/lang/X.class": b"\xCA\xFE\xBA\xBEcoreX",
            "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\n",
        })

    def test_read_only_reports_missing(self):
        res = module.validate_target(self.target, self.slices)
        self.assertEqual(res["missing"], APPROVED_35)
        self.assertEqual(res["already"], [])
        self.assertEqual(set(res["source_by_entry"]), set(APPROVED_35))
        for entry in APPROVED_35:
            self.assertEqual(res["source_by_entry"][entry], _payload(entry))
        # target unchanged
        with zipfile.ZipFile(self.target) as zf:
            self.assertEqual(
                set(n for n in zf.namelist() if not n.endswith("/")),
                {"java/lang/X.class", "META-INF/MANIFEST.MF"})

    def test_reports_already_for_identical_entries(self):
        with zipfile.ZipFile(self.target, "a") as zf:
            zf.writestr(DDMC[0], _payload(DDMC[0]))
        res = module.validate_target(self.target, self.slices)
        self.assertEqual(res["already"], [DDMC[0]])
        self.assertEqual(len(res["missing"]), 34)

    def test_collision_raises_in_validate(self):
        with zipfile.ZipFile(self.target, "a") as zf:
            zf.writestr(DDMC[0], b"\xCA\xFE\xBA\xBETAMPERED")
        with self.assertRaises(RuntimeError) as ctx:
            module.validate_target(self.target, self.slices)
        self.assertIn("collision", str(ctx.exception))

    def test_missing_target_raises(self):
        with self.assertRaises(FileNotFoundError):
            module.validate_target(self.root / "nope.jar", self.slices)


if __name__ == "__main__":
    unittest.main(verbosity=2)
