#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preserve ``xmlns:androidprv`` through the AGP 9.3.1 resource pipeline.

AGP's ``MergeResources`` reserializes merged values XML and drops the
``xmlns:androidprv`` namespace declaration because the prefix only occurs
inside attribute *values* (``name="androidprv:..."`` style references), never
as an XML attribute prefix. AAPT2's ``ExtractPackageFromNamespace`` can then no
longer resolve ``androidprv:`` references at link time.

This helper is a deterministic post-merge / pre-link repair:

1. scan ``--merged-dir`` (AGP merger XML output) for values XML files that
   reference ``androidprv:``;
2. copy those files to a temporary tree and inject the missing declaration on
   the ``<resources>`` root (the merger XML itself is NEVER modified);
3. compile each patched copy with the AAPT2 executable selected by AGP
   (``androidComponents.sdkComponents.aapt2``);
4. atomically replace only the matching ``.arsc.flat`` files under
   ``--compiled-dir``.

Summary line on success: ``scanned=<n> patched=<n> compiled=<n> unresolved=0``.
Exit codes: 0 success; 2 missing/unusable inputs; 3 zero candidates;
4 duplicate namespace declaration; 5 AAPT2 compile failure; 6 expected flat
output missing.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PRV_URI = "http://schemas.android.com/apk/prv/res/android"
PRV_DECL = f'xmlns:androidprv="{PRV_URI}"'

_ROOT_RE = re.compile(r"<resources\b[^>]*>")

_EXIT_USAGE = 2
_EXIT_NO_CANDIDATES = 3
_EXIT_DUPLICATE = 4
_EXIT_COMPILE = 5
_EXIT_MISSING_FLAT = 6


class PatchError(Exception):
    """Raised for unrecoverable patch-input problems."""


def flat_name(rel_xml: Path) -> str:
    """Map a merged values XML path to AAPT2's compiled flat filename.

    AAPT2 ``compile`` names outputs ``<parent-dir>_<file-stem>.arsc.flat``
    (e.g. ``values-night-v8/values-night-v8.xml`` ->
    ``values-night-v8_values-night-v8.arsc.flat``).
    """
    return f"{rel_xml.parent.name}_{rel_xml.stem}.arsc.flat"


def inject_declaration(xml_text: str) -> str:
    """Return *xml_text* with the androidprv declaration on <resources>.

    Idempotent: a text that already carries exactly one declaration is
    returned unchanged; more than one is a hard error.
    """
    count = xml_text.count(PRV_DECL)
    if count > 1:
        raise PatchError(
            f"duplicate {PRV_DECL} declarations ({count} occurrences)")
    if count == 1:
        return xml_text
    match = _ROOT_RE.search(xml_text)
    if match is None:
        raise PatchError("no <resources ...> root element found")
    root = match.group(0)
    patched = root[:-1] + " " + PRV_DECL + ">"
    return xml_text.replace(root, patched, 1)


def select_candidates(merged_dir: Path) -> tuple[list[Path], list[Path]]:
    """Return (all scanned xml files, files referencing androidprv:)."""
    scanned = sorted(p for p in merged_dir.rglob("*.xml") if p.is_file())
    candidates = [p for p in scanned if "androidprv:" in p.read_text(encoding="utf-8")]
    return scanned, candidates


def _compile_one(aapt2: str, src: Path, out_dir: Path, original: Path) -> None:
    """Compile *src* with AAPT2; the flat records the original path's name."""
    result = subprocess.run(
        [aapt2, "compile", str(src), "-o", str(out_dir)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(
            f"aapt2 compile failed for {original} "
            f"(exit {result.returncode}):\n{result.stdout}{result.stderr}")
        sys.exit(_EXIT_COMPILE)


def _atomic_replace(src: Path, dest: Path) -> None:
    tmp = dest.with_name(dest.name + ".tmp-patch-androidprv")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dest)


def run(merged_dir: Path, compiled_dir: Path, aapt2: str) -> int:
    for label, path in (("--merged-dir", merged_dir), ("--compiled-dir", compiled_dir)):
        if not path.is_dir():
            sys.stderr.write(f"{label} is not a directory: {path}\n")
            return _EXIT_USAGE
    if not (os.path.isfile(aapt2) and os.access(aapt2, os.X_OK)):
        sys.stderr.write(f"--aapt2 is not an executable file: {aapt2}\n")
        return _EXIT_USAGE

    scanned, candidates = select_candidates(merged_dir)
    if not candidates:
        sys.stderr.write(
            "no androidprv references found under --merged-dir; "
            "nothing to patch (is this the AGP merger output?)\n")
        return _EXIT_NO_CANDIDATES

    to_patch: list[Path] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        try:
            new_text = inject_declaration(text)
        except PatchError as exc:
            sys.stderr.write(f"{path}: {exc}\n")
            return _EXIT_DUPLICATE
        if new_text != text:
            to_patch.append(path)

    compiled_count = 0
    with tempfile.TemporaryDirectory(prefix="agp-merged-values-staging-") as tmp:
        tmp_dir = Path(tmp)
        staging = tmp_dir / "staging"
        out = tmp_dir / "out"
        out.mkdir()
        for path in to_patch:
            rel = path.relative_to(merged_dir)
            staged = staging / rel
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(inject_declaration(
                path.read_text(encoding="utf-8")), encoding="utf-8")
            # Compile from a path whose basename matches the original so the
            # generated flat name is identical to AGP's.
            _compile_one(aapt2, staged, out, path)
            flat = out / flat_name(rel)
            if not flat.is_file():
                sys.stderr.write(
                    f"expected flat output missing after compile: "
                    f"{flat.name} (for {path})\n")
                return _EXIT_MISSING_FLAT
            dest = compiled_dir / flat.name
            if not dest.is_file():
                sys.stderr.write(
                    f"no existing flat to replace in --compiled-dir: {dest}\n")
                return _EXIT_MISSING_FLAT
            _atomic_replace(flat, dest)
            compiled_count += 1

    print(f"scanned={len(scanned)} patched={len(to_patch)} "
          f"compiled={compiled_count} unresolved=0")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preserve xmlns:androidprv in AGP merged values resources.")
    parser.add_argument("--merged-dir", required=True,
                        help="AGP merger XML output directory (never modified)")
    parser.add_argument("--compiled-dir", required=True,
                        help="AGP compiled merged-res flat directory")
    parser.add_argument("--aapt2", required=True,
                        help="AAPT2 executable (from sdkComponents.aapt2)")
    args = parser.parse_args(argv)
    return run(Path(args.merged_dir), Path(args.compiled_dir), args.aapt2)


if __name__ == "__main__":
    sys.exit(main())
