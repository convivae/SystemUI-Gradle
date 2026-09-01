#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tested analysis primitives for the C5 pre-R8 JarJar experiments (Task 079).

The current checkpoint implements the reusable inspection and verdict API.
The ``run`` subcommand remains intentionally staged until E1–E4 orchestration
is added; invoking it does not claim that any experiment ran.

The completed driver will produce the bounded evidence inputs required to
adjudicate the pre-R8 JarJar implementation seam without changing project
behavior:

* E1: complete variant/ownership inventory of the 464 stock R8 input tokens
  (463 ``.jar`` + 1 ``.srcjar``) from ``withres/SystemUI.jar.rsp``;
* E2: scratch dry-run of affected AARs rebuilt from AOSP
  ``repackaged-jarjar`` intermediate outputs;
* E3: scratch JarJar dry-run over per-module local javac/Kotlin outputs;
* E4: standalone AGP 9.3.1 bundled-R8 positive/negative probe of SysUISdk
  hidden-name resolution.

All scratch artifacts live under an explicit scratch root (default
``/tmp/task079-c5-jarjar-e1-e4``); nothing outside that root is written. The
tool is stdlib-only and never infers success from a file name when archive
contents are inspectable.

The semantic API pinned by ``tools/tests/test_analyze_aconfig_jarjar_experiments.py``:
``tokenize_rsp``/``composition_counts`` (RSP tokenization),
``inspect_archive``/``is_source_free`` (constant-pool inspection),
``check_e3_precondition``/``matching_source_refs`` (E3 ownership),
``compare_aar`` (E2 invariants), ``interpret_e4_positive``/
``interpret_e4_negative`` (E4 controls), and ``build_summary`` (stable
machine-checkable output block). The run driver composes these primitives.
"""

from __future__ import annotations

import io
import shlex
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "RspError",
    "ArchiveInfo",
    "E3Verdict",
    "AarCompareResult",
    "E4Verdict",
    "tokenize_rsp",
    "composition_counts",
    "inspect_archive",
    "is_source_free",
    "check_e3_precondition",
    "matching_source_refs",
    "compare_aar",
    "interpret_e4_positive",
    "interpret_e4_negative",
    "build_summary",
]

_CLASS_SUFFIX = ".class"
_CODE_CONTAINERS = (".jar", ".srcjar", ".aar")


class RspError(Exception):
    """The RSP file cannot be tokenized (empty / unreadable)."""


# ---------------------------------------------------------------------------
# RSP tokenization
# ---------------------------------------------------------------------------


def tokenize_rsp(rsp_path: Path) -> tuple[list[str], int]:
    """Tokenize an RSP file with shell semantics, preserving order and duplicates.

    Returns ``(rows, unique_count)`` where ``rows`` keeps every shell token
    (duplicates as separate rows, original order) and ``unique_count`` is the
    number of distinct paths.
    """
    try:
        text = Path(rsp_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise RspError(f"cannot read RSP file {rsp_path}: {exc}") from exc
    rows = shlex.split(text)
    if not rows:
        raise RspError(f"RSP file contains no shell tokens: {rsp_path}")
    return rows, len(set(rows))


def composition_counts(rows: list[str]) -> tuple[int, int]:
    """Return ``(jar_count, srcjar_count)`` for a list of RSP token rows."""
    jars = sum(1 for r in rows if r.endswith(".jar"))
    srcjars = sum(1 for r in rows if r.endswith(".srcjar"))
    return jars, srcjars


# ---------------------------------------------------------------------------
# Classfile constant-pool inspection
# ---------------------------------------------------------------------------


@dataclass
class ArchiveInfo:
    """Definitions/references found in an archive (nested containers included).

    ``definitions``/``references`` hold JVM descriptors (``La/b/C;``);
    ``non_code_entries`` maps every non-code ZIP entry name to its exact
    bytes so byte-identity can be proven, not just name-set equality.
    """

    class_entry_names: set[str] = field(default_factory=set)
    definitions: set[str] = field(default_factory=set)
    references: set[str] = field(default_factory=set)
    non_code_entries: dict[str, bytes] = field(default_factory=dict)


def _scan_classfile(data: bytes) -> tuple[str, set[str]]:
    """Return ``(this_class_descriptor, referenced_descriptors)`` for one classfile.

    References are collected as JVM descriptors (``La/b/C;``) from two
    complementary places, because a classfile references types both ways:

    * every ``CONSTANT_Class`` entry (superclasses, interfaces, field types,
      exception tables...) whose Utf8 name is an internal name
      (``a/b/C``) is wrapped as ``La/b/C;``; names already in descriptor
      form (``L...;`` or array ``[...``) are taken verbatim -- an internal
      name can never legitimately start with ``L`` and end with ``;``, so
      accepting both forms is unambiguous;
    * descriptor-embedded class references inside every ``CONSTANT_Utf8``
      entry (method/field/signature descriptors), scanned for the
      ``L<internal-name>;`` pattern.

    Only descriptors are tracked, matching the descriptor semantics of the
    frozen DEX gate (``check_aconfig_jarjar_references.py``).
    """
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("not a JVM classfile (bad magic)")
    (count,) = struct.unpack_from(">H", data, 8)
    idx = 10
    consts: list[tuple[str, object] | None] = [None] * count
    i = 1
    while i < count:
        if idx >= len(data):
            raise ValueError("truncated constant pool")
        tag = data[idx]
        idx += 1
        if tag == 1:  # Utf8
            (n,) = struct.unpack_from(">H", data, idx)
            idx += 2
            consts[i] = ("u", data[idx : idx + n])
            idx += n
        elif tag == 7:  # Class
            (name_idx,) = struct.unpack_from(">H", data, idx)
            consts[i] = ("c", name_idx)
            idx += 2
        elif tag == 8 or tag in (16, 19, 20):  # String / MethodType / Module / Package
            idx += 2
        elif tag == 15:  # MethodHandle
            idx += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            idx += 4
        elif tag in (5, 6):  # long/double occupy two pool slots
            consts[i] = ("x", None)
            consts[i + 1] = ("x", None)
            i += 1
            idx += 8
        else:
            raise ValueError(f"unknown constant-pool tag {tag}")
        i += 1
    (access_flags, this_cls, super_cls) = struct.unpack_from(">HHH", data, idx)

    def _utf8(ci: int) -> bytes | None:
        entry = consts[ci] if 0 <= ci < count else None
        if entry is not None and entry[0] == "u":
            return entry[1]
        return None

    def _class_name(ci: int) -> str | None:
        entry = consts[ci] if 0 <= ci < count else None
        if entry is None or entry[0] != "c":
            return None
        raw = _utf8(entry[1])
        if raw is None:
            return None
        name = raw.decode("utf-8", "replace")
        if name.startswith("[") or (name.startswith("L") and name.endswith(";")):
            return name  # already descriptor-form
        return "L" + name + ";"

    this_descriptor = _class_name(this_cls)
    refs: set[str] = set()
    for ci, entry in enumerate(consts):
        if entry is None:
            continue
        if entry[0] == "c":
            name = _class_name(ci)
            if name:
                refs.add(name)
        elif entry[0] == "u":
            raw: bytes = entry[1]
            start = 0
            while True:
                pos = raw.find(b"L", start)
                if pos < 0:
                    break
                end = raw.find(b";", pos)
                if end < 0:
                    break
                body = raw[pos + 1 : end]
                if body and all(
                    0x61 <= c <= 0x7A
                    or 0x41 <= c <= 0x5A
                    or 0x30 <= c <= 0x39
                    or c in (0x24, 0x2F, 0x5F)  # '$', '/', '_'
                    for c in body
                ):
                    refs.add("L" + body.decode("ascii") + ";")
                start = end + 1
    if this_descriptor is None:
        raise ValueError("unresolvable this_class")
    return this_descriptor, refs


def inspect_archive(path: Path) -> ArchiveInfo:
    """Inspect a JAR/AAR (with nested code containers) for definitions/references.

    Definitions are the ``this_class`` descriptors of every ``*.class`` entry
    (including entries inside nested ``.jar``/``.srcjar`` containers, which
    are scanned recursively); references are the union of every classfile's
    referenced descriptors. Every other ZIP entry is recorded in
    ``non_code_entries`` with its exact bytes.
    """
    info = ArchiveInfo()

    def scan_bytes(zbytes: bytes) -> None:
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                if name.endswith(_CLASS_SUFFIX):
                    this_d, refs = _scan_classfile(zf.read(name))
                    info.class_entry_names.add(name)
                    info.definitions.add(this_d)
                    info.references.update(refs)
                elif name.endswith(_CODE_CONTAINERS):
                    scan_bytes(zf.read(name))
                else:
                    info.non_code_entries[name] = zf.read(name)

    scan_bytes(Path(path).read_bytes())
    return info


def is_source_free(info: ArchiveInfo, sources: list[str]) -> bool:
    """True when no rule source (dotted FQCN) is referenced by the archive."""
    descs = {"L" + s.replace(".", "/") + ";" for s in sources}
    return not descs & info.references


# ---------------------------------------------------------------------------
# E3 ownership precondition
# ---------------------------------------------------------------------------


def _rule_descriptor(name: str) -> str:
    return "L" + name.replace(".", "/") + ";"


@dataclass
class E3Verdict:
    """Ownership precondition verdict for one candidate E3 artifact."""

    ok: bool
    defined_sources: set[str] = field(default_factory=set)


def check_e3_precondition(info: ArchiveInfo, rules: list[tuple[str, str]]) -> E3Verdict:
    """An artifact may only be transformed when it defines no rule source.

    Any rule source appearing as a definition inside the artifact means the
    artifact owns an original-name class (e.g. an app-bundled aconfig
    implementation); renaming it would break ownership safety. Such an
    artifact disqualifies the transformation (``ok=False``), never a silent
    skip; the caller records ``E3=FAIL`` and continues only independent
    experiments.
    """
    src_descs = {_rule_descriptor(s) for s, _t in rules}
    defined_sources = {d for d in info.definitions if d in src_descs}
    return E3Verdict(ok=not defined_sources, defined_sources=defined_sources)


def matching_source_refs(info: ArchiveInfo, rules: list[tuple[str, str]]) -> set[str]:
    """Return the dotted source names whose descriptors this archive references."""
    src_descs = {_rule_descriptor(s): s for s, _t in rules}
    return {src_descs[d] for d in info.references if d in src_descs}


# ---------------------------------------------------------------------------
# E2 AAR invariants
# ---------------------------------------------------------------------------


@dataclass
class AarCompareResult:
    """Comparison of a current AAR against its scratch repackaged candidate."""

    non_code_identical: bool
    class_names_equal: bool
    source_refs_gone: bool
    target_refs_present: bool
    target_definitions: int


def compare_aar(
    current: Path,
    scratch: Path,
    rules: list[tuple[str, str]],
    critical_sources: list[str] | None = None,
) -> AarCompareResult:
    """Compare a current AAR with its scratch repackaged counterpart.

    Invariants (a candidate passes only when all hold):
    * every non-code ZIP entry byte-identical between the two archives;
    * class entry-name sets equal (no unexplained addition/removal);
    * every rule source referenced by the current AAR is no longer
      referenced by the scratch candidate (``source_refs_gone``);
    * for every such rewritten rule, the target descriptor is now
      referenced (``target_refs_present``);
    * no rule target is defined in the scratch AAR (``target_definitions``
      must be zero: renamed platform classes must never be packaged).

    ``critical_sources`` optionally restricts the source-side rewrite check
    to a subset (e.g. the four runtime-critical sources); by default every
    rule source is checked.
    """
    cur = inspect_archive(current)
    new = inspect_archive(scratch)

    non_code_identical = cur.non_code_entries == new.non_code_entries
    class_names_equal = cur.class_entry_names == new.class_entry_names

    crit = set(critical_sources) if critical_sources is not None else {s for s, _t in rules}
    crit_descs = {_rule_descriptor(s) for s in crit}
    cur_crit_refs = crit_descs & cur.references
    new_crit_refs = crit_descs & new.references
    source_refs_gone = not new_crit_refs

    expected_targets = {
        _rule_descriptor(t) for s, t in rules if _rule_descriptor(s) in cur_crit_refs
    }
    target_refs_present = expected_targets <= new.references

    tgt_all_descs = {_rule_descriptor(t) for _s, t in rules}
    target_definitions = len(tgt_all_descs & new.definitions)

    return AarCompareResult(
        non_code_identical=non_code_identical,
        class_names_equal=class_names_equal,
        source_refs_gone=source_refs_gone,
        target_refs_present=target_refs_present,
        target_definitions=target_definitions,
    )


# ---------------------------------------------------------------------------
# E4 interpretation
# ---------------------------------------------------------------------------


@dataclass
class E4Verdict:
    """Positive/negative control interpretation for the standalone R8 probe."""

    passed: bool


def interpret_e4_positive(
    exit_code: int,
    stderr: str,
    output_refs_all_targets: bool,
    output_target_defs: int,
) -> E4Verdict:
    """Positive control: SysUISdk android.jar as ``--lib`` must fully resolve
    the four critical hidden targets. Pass requires exit 0, no missing-class
    diagnostic, all four target references retained in the output DEX, and
    zero target definitions in the output."""
    lowered = stderr.lower()
    passed = (
        exit_code == 0
        and "missing class" not in lowered
        and "missing-class" not in lowered
        and output_refs_all_targets
        and output_target_defs == 0
    )
    return E4Verdict(passed=passed)


def interpret_e4_negative(
    exit_code: int,
    stderr: str,  # noqa: ARG001 - kept for signature stability
    all_targets_in_diagnostics: bool,
) -> E4Verdict:
    """Negative control: official base SDK android.jar as ``--lib`` must fail.

    A negative control that exits 0 is ``E4_NEGATIVE=FAIL`` -- it means the
    probe could not capture unresolved classes and therefore proves nothing
    about the positive run; it must never be reinterpreted as success.
    """
    passed = exit_code != 0 and all_targets_in_diagnostics
    return E4Verdict(passed=passed)


# ---------------------------------------------------------------------------
# Stable summary output
# ---------------------------------------------------------------------------

_SUMMARY_KEYS = (
    "RULES",
    "RSP_INPUTS",
    "RSP_CLASSIFIED",
    "RSP_UNKNOWN",
    "RSP_JARS",
    "RSP_SRCJARS",
    "GRADLE_MODULES",
    "GRADLE_MODULES_CLASSIFIED",
    "E1",
    "E2",
    "E3",
    "E4_POSITIVE",
    "E4_NEGATIVE",
    "CANDIDATE",
    "EXPERIMENTS_COMPLETE",
)


def build_summary(
    rules: int = 0,
    rsp_inputs: int = 0,
    rsp_classified: int = 0,
    rsp_unknown: int = 0,
    rsp_jars: int = 0,
    rsp_srcjars: int = 0,
    gradle_modules: int = 0,
    gradle_modules_classified: int = 0,
    e1: str = "FAIL",
    e2: str = "FAIL",
    e3: str = "FAIL",
    e4_positive: str = "FAIL",
    e4_negative: str = "FAIL",
    candidate: str = "FAIL",
    experiments_complete: str = "FAIL",
) -> str:
    """Build the stable machine-checkable summary block.

    Keyword arguments use the lowercase names from the pinned test API; the
    output is exactly one ``KEY=value`` line per canonical key (see the Task
    079 brief acceptance).
    """
    values = {
        "RULES": rules,
        "RSP_INPUTS": rsp_inputs,
        "RSP_CLASSIFIED": rsp_classified,
        "RSP_UNKNOWN": rsp_unknown,
        "RSP_JARS": rsp_jars,
        "RSP_SRCJARS": rsp_srcjars,
        "GRADLE_MODULES": gradle_modules,
        "GRADLE_MODULES_CLASSIFIED": gradle_modules_classified,
        "E1": e1,
        "E2": e2,
        "E3": e3,
        "E4_POSITIVE": e4_positive,
        "E4_NEGATIVE": e4_negative,
        "CANDIDATE": candidate,
        "EXPERIMENTS_COMPLETE": experiments_complete,
    }
    return "\n".join(f"{k}={values[k]}" for k in _SUMMARY_KEYS)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    """CLI entry (staged): the full E1-E4 replay composes the primitives above."""
    import argparse

    parser = argparse.ArgumentParser(description="Task 079 E1-E4 experiment driver")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run the full E1-E4 evidence replay")
    run.add_argument("--repo-root", required=True, type=Path)
    run.add_argument("--aosp-root", required=True, type=Path)
    run.add_argument("--sysui-sdk", required=True, type=Path)
    run.add_argument("--base-sdk", required=True, type=Path)
    run.add_argument("--r8-jar", required=True, type=Path)
    run.add_argument("--scratch", required=True, type=Path)
    args = parser.parse_args(argv)
    print(
        "run driver: INCOMPLETE checkpoint; no E1-E4 experiment was run. "
        "Implement the frozen Task 079 replay before using this command."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
