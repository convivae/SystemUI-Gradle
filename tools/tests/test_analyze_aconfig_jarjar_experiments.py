#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tests for tools/analyze_aconfig_jarjar_experiments.py (Task 079).

All fixtures are synthetic and in-memory (tempdirs): no AOSP checkout, SDK,
APK, or Gradle build is needed. The tests pin the semantics the driver must
not regress:

* RSP shell tokenization (duplicates preserved as separate rows, unique
  paths reported separately, jar/srcjar composition counts);
* classfile constant-pool reference/definition inspection (never infer
  success from the file name when archive contents are inspectable);
* the E3 ownership precondition (any 725-rule source defined in an artifact
  disqualifies that artifact from transformation -> E3=FAIL);
* AAR scratch invariants (non-code entries byte-identical, class entry-name
  sets equal, source refs gone / target refs present / target defs zero);
* E4 positive/negative result interpretation (a negative control that
  exits 0 is E4_NEGATIVE=FAIL, not success).
"""

import importlib.util
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "analyze_aconfig_jarjar_experiments.py"
_spec = importlib.util.spec_from_file_location("analyze_aconfig_jarjar_experiments", _SCRIPT)
ax = importlib.util.module_from_spec(_spec)
sys.modules["analyze_aconfig_jarjar_experiments"] = ax
_spec.loader.exec_module(ax)


# ---------------------------------------------------------------------------
# Synthetic classfile builder (valid enough for the constant-pool scanner)
# ---------------------------------------------------------------------------


def build_classfile(this_class: str, refs: list[str]) -> bytes:
    """Build a structurally minimal JVM classfile (v52.0).

    ``this_class`` is the class being defined; every descriptor in ``refs``
    is placed in the constant pool as a CONSTANT_Class entry (i.e. a type
    reference). The scanner under test must see exactly: one definition of
    ``this_class`` and one reference per ``refs`` entry.
    """
    pool: list[bytes] = []  # index 0 unused

    def utf8(s: str) -> int:
        data = s.encode("utf-8")
        pool.append(struct.pack(">BH", 1, len(data)) + data)
        return len(pool)

    def klass(desc: str) -> int:
        name_idx = utf8(desc)
        pool.append(struct.pack(">BH", 7, name_idx))
        return len(pool)

    this_idx = klass(this_class)
    ref_idxs = [klass(r) for r in refs]
    # A no-op method: access_flags=0, name=<init>, descriptor=()V, attrs=0.
    init_name = utf8("<init>")
    init_desc = utf8("()V")
    out = bytearray()
    out += struct.pack(">IHH", 0xCAFEBABE, 0, 52)
    out += struct.pack(">H", len(pool) + 1)
    for entry in pool:
        out += entry
    # access_flags=ACC_PUBLIC|ACC_SUPER, this_class, super_class=0 (scanner ignores)
    out += struct.pack(">HHH", 0x0001 + 0x0020, this_idx, 0)
    # interfaces/fields/methods/attributes counts
    out += struct.pack(">H", 0)  # interfaces_count
    out += struct.pack(">H", 0)  # fields_count
    out += struct.pack(">H", 1)  # methods_count
    out += struct.pack(">HHHH", 0x0001, init_name, init_desc, 0)
    out += struct.pack(">H", 0)  # class attributes_count
    return bytes(out)


def fqcn_to_desc(name: str) -> str:
    return "L" + name.replace(".", "/") + ";"


SRC = "android.app.Flags"
SRC2 = "android.os.Flags"
TGT = "com.android.internal.hidden_from_bootclasspath.android.app.Flags"
TGT2 = "com.android.internal.hidden_from_bootclasspath.android.os.Flags"


def make_jar(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


class TestRspTokenization(unittest.TestCase):
    def test_tokens_preserve_order_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            rsp = Path(tmp) / "list.rsp"
            rsp.write_text("a.jar 'b c.jar' a.jar\n")
            rows, unique = ax.tokenize_rsp(rsp)
        self.assertEqual(rows, ["a.jar", "b c.jar", "a.jar"])
        self.assertEqual(unique, 2)

    def test_composition_counts(self):
        rows = ["x/y.jar", "x/a.jar", "x/b.srcjar"]
        jars, srcjars = ax.composition_counts(rows)
        self.assertEqual((jars, srcjars), (2, 1))

    def test_empty_rsp_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            rsp = Path(tmp) / "empty.rsp"
            rsp.write_text("   \n")
            with self.assertRaises(ax.RspError):
                ax.tokenize_rsp(rsp)


class TestClassInspection(unittest.TestCase):
    def test_definitions_and_references_are_read_from_the_pool(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = Path(tmp) / "a.jar"
            make_jar(
                jar,
                {
                    "com/example/A.class": build_classfile(
                        "Lcom/example/A;", [fqcn_to_desc(SRC), fqcn_to_desc(TGT)]
                    ),
                },
            )
            info = ax.inspect_archive(jar)
        self.assertEqual(info.class_entry_names, {"com/example/A.class"})
        self.assertIn("Lcom/example/A;", info.definitions)
        self.assertIn(fqcn_to_desc(SRC), info.references)
        self.assertIn(fqcn_to_desc(TGT), info.references)

    def test_nested_jar_containers_are_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            inner = Path(tmp) / "inner.jar"
            make_jar(
                inner,
                {"com/example/B.class": build_classfile("Lcom/example/B;", [fqcn_to_desc(SRC)])},
            )
            outer = Path(tmp) / "outer.aar"
            make_jar(outer, {"classes.jar": inner.read_bytes(), "res/values.xml": b"<x/>"})
            info = ax.inspect_archive(outer)
        self.assertIn(fqcn_to_desc(SRC), info.references)
        self.assertIn("Lcom/example/B;", info.definitions)
        self.assertIn("res/values.xml", info.non_code_entries)

    def test_filename_alone_is_never_success_evidence(self):
        # A jar whose name says "repackaged" but whose pool still references
        # the source name must be reported as still-referencing.
        with tempfile.TemporaryDirectory() as tmp:
            jar = Path(tmp) / "repackaged-jarjar.jar"
            make_jar(
                jar,
                {"A.class": build_classfile("LA;", [fqcn_to_desc(SRC)])},
            )
            info = ax.inspect_archive(jar)
        self.assertIn(fqcn_to_desc(SRC), info.references)
        self.assertFalse(ax.is_source_free(info, [SRC]))


class TestE3Preconditions(unittest.TestCase):
    def test_source_definition_disqualifies_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = Path(tmp) / "project.jar"
            make_jar(
                jar,
                {"A.class": build_classfile("LA;", [fqcn_to_desc(SRC2)])},
                # B *defines* the source name: ownership violation.
            )
            # define SRC via a classfile whose this_class is the source name
            with zipfile.ZipFile(jar, "a") as zf:
                zf.writestr(
                    "android/app/Flags.class",
                    build_classfile(fqcn_to_desc(SRC), []),
                )
            info = ax.inspect_archive(jar)
        verdict = ax.check_e3_precondition(info, [(SRC, TGT), (SRC2, TGT2)])
        self.assertFalse(verdict.ok)
        self.assertIn(fqcn_to_desc(SRC), verdict.defined_sources)

    def test_clean_artifact_passes_precondition(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = Path(tmp) / "project.jar"
            make_jar(
                jar,
                {"A.class": build_classfile("LA;", [fqcn_to_desc(SRC), fqcn_to_desc(SRC2)])},
            )
            info = ax.inspect_archive(jar)
        verdict = ax.check_e3_precondition(info, [(SRC, TGT), (SRC2, TGT2)])
        self.assertTrue(verdict.ok)
        self.assertEqual(verdict.defined_sources, set())

    def test_no_matching_references_is_noop_not_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = Path(tmp) / "noop.jar"
            make_jar(jar, {"A.class": build_classfile("LA;", ["Lother/C;"])})
            info = ax.inspect_archive(jar)
        self.assertTrue(ax.matching_source_refs(info, [(SRC, TGT)]) == set())


class TestE2AarInvariants(unittest.TestCase):
    def _current_aar(self, tmp) -> Path:
        tmp = Path(tmp)
        aar = tmp / "lib.aar"
        make_jar(
            aar,
            {
                "classes.jar": self._inner(
                    {"A.class": build_classfile("LA;", [fqcn_to_desc(SRC)])}
                ),
                "res/values.xml": b"<resources/>",
                "AndroidManifest.xml": b"<manifest/>",
            },
        )
        return aar

    def _inner(self, entries: dict[str, bytes]) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "inner.jar"
            make_jar(p, entries)
            return p.read_bytes()

    def test_scratch_replacement_invariants(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = self._current_aar(tmp)
            scratch = Path(tmp) / "scratch.aar"
            with tempfile.TemporaryDirectory() as t2:
                repackaged = Path(t2) / "repackaged.jar"
                make_jar(
                    repackaged,
                    {"A.class": build_classfile("LA;", [fqcn_to_desc(TGT)])},
                )
                make_jar(
                    scratch,
                    {
                        "classes.jar": repackaged.read_bytes(),
                        "res/values.xml": b"<resources/>",
                        "AndroidManifest.xml": b"<manifest/>",
                    },
                )
            result = ax.compare_aar(current, scratch, [(SRC, TGT)])
        self.assertTrue(result.non_code_identical)
        self.assertTrue(result.class_names_equal)
        self.assertTrue(result.source_refs_gone)
        self.assertTrue(result.target_refs_present)
        self.assertEqual(result.target_definitions, 0)

    def test_class_set_drift_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = self._current_aar(tmp)
            scratch = Path(tmp) / "scratch.aar"
            with tempfile.TemporaryDirectory() as t2:
                repackaged = Path(t2) / "repackaged.jar"
                make_jar(
                    repackaged,
                    {
                        "A.class": build_classfile("LA;", [fqcn_to_desc(TGT)]),
                        "Extra.class": build_classfile("LExtra;", []),
                    },
                )
                make_jar(
                    scratch,
                    {
                        "classes.jar": repackaged.read_bytes(),
                        "res/values.xml": b"<resources/>",
                        "AndroidManifest.xml": b"<manifest/>",
                    },
                )
            result = ax.compare_aar(current, scratch, [(SRC, TGT)])
        self.assertFalse(result.class_names_equal)

    def test_non_code_drift_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = self._current_aar(tmp)
            scratch = Path(tmp) / "scratch.aar"
            with tempfile.TemporaryDirectory() as t2:
                repackaged = Path(t2) / "repackaged.jar"
                make_jar(
                    repackaged,
                    {"A.class": build_classfile("LA;", [fqcn_to_desc(TGT)])},
                )
                make_jar(
                    scratch,
                    {
                        "classes.jar": repackaged.read_bytes(),
                        "res/values.xml": b"<changed/>",
                        "AndroidManifest.xml": b"<manifest/>",
                    },
                )
            result = ax.compare_aar(current, scratch, [(SRC, TGT)])
        self.assertFalse(result.non_code_identical)


class TestE4Interpretation(unittest.TestCase):
    def test_positive_pass(self):
        ev = ax.interpret_e4_positive(
            exit_code=0,
            stderr="",
            output_refs_all_targets=True,
            output_target_defs=0,
        )
        self.assertTrue(ev.passed)

    def test_positive_missing_class_is_fail(self):
        ev = ax.interpret_e4_positive(
            exit_code=0,
            stderr="Missing class com.android.internal.hidden_from_bootclasspath.android.app.Flags",
            output_refs_all_targets=True,
            output_target_defs=0,
        )
        self.assertFalse(ev.passed)

    def test_positive_output_lost_target_ref_is_fail(self):
        ev = ax.interpret_e4_positive(
            exit_code=0, stderr="", output_refs_all_targets=False, output_target_defs=0
        )
        self.assertFalse(ev.passed)

    def test_negative_control_must_fail(self):
        ev = ax.interpret_e4_negative(
            exit_code=1,
            stderr="Missing class android... hidden_from_bootclasspath.android.app.Flags (referenced from: probe)",
            all_targets_in_diagnostics=True,
        )
        self.assertTrue(ev.passed)

    def test_negative_control_exiting_zero_is_fail(self):
        ev = ax.interpret_e4_negative(
            exit_code=0, stderr="", all_targets_in_diagnostics=False
        )
        self.assertFalse(ev.passed)

    def test_negative_missing_some_targets_is_fail(self):
        ev = ax.interpret_e4_negative(
            exit_code=1,
            stderr="Missing class ...hidden_from_bootclasspath.android.app.Flags",
            all_targets_in_diagnostics=False,
        )
        self.assertFalse(ev.passed)


class TestSummaryKeys(unittest.TestCase):
    def test_summary_keys_are_stable_and_ordered(self):
        summary = ax.build_summary(
            rules=725,
            rsp_inputs=464,
            rsp_classified=464,
            rsp_unknown=0,
            rsp_jars=463,
            rsp_srcjars=1,
            gradle_modules=17,
            gradle_modules_classified=17,
            e1="PASS",
            e2="PASS",
            e3="PASS",
            e4_positive="PASS",
            e4_negative="PASS",
            candidate="PASS",
            experiments_complete="PASS",
        )
        lines = summary.strip().splitlines()
        self.assertEqual(
            lines,
            [
                "RULES=725",
                "RSP_INPUTS=464",
                "RSP_CLASSIFIED=464",
                "RSP_UNKNOWN=0",
                "RSP_JARS=463",
                "RSP_SRCJARS=1",
                "GRADLE_MODULES=17",
                "GRADLE_MODULES_CLASSIFIED=17",
                "E1=PASS",
                "E2=PASS",
                "E3=PASS",
                "E4_POSITIVE=PASS",
                "E4_NEGATIVE=PASS",
                "CANDIDATE=PASS",
                "EXPERIMENTS_COMPLETE=PASS",
            ],
        )


if __name__ == "__main__":
    unittest.main()
