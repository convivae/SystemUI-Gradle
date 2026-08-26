#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/package_compilelib_jars.py — determinism."""

import importlib.util
import sys
import tempfile
import time
import unittest
from pathlib import Path

# The script under test imports aosp_paths; make tools/ importable no matter
# where the test runner is invoked from.
_TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

_SCRIPT = _TOOLS_DIR / "package_compilelib_jars.py"
_spec = importlib.util.spec_from_file_location("package_compilelib_jars", _SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)


class TestCompilelibJarDeterminism(unittest.TestCase):
    def test_repeated_builds_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "Compile.java"
            src.write_text(
                "package com.android.systemui.util; "
                "public final class Compile { "
                "public static final boolean IS_DEBUG = true; }",
                encoding="utf-8",
            )
            first = root / "first.jar"
            second = root / "second.jar"
            module._compile_one(src, first)
            time.sleep(2)
            module._compile_one(src, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
