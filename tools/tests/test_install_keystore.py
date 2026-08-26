#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/install_keystore.py — arg parsing, aosp_paths
integration, command-chain structure, and missing-input error handling.

Per the task brief (task 067), the openssl/keytool chain itself is NOT covered
here (it requires the AOSP platform test key + openssl/keytool on PATH); only
the Python-orchestrated logic is exercised.
"""
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

_SCRIPT = _TOOLS_DIR / "install_keystore.py"
_spec = importlib.util.spec_from_file_location("install_keystore", _SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)


class TestSecurityDir(unittest.TestCase):
    def test_override_takes_precedence(self):
        d = module.security_dir("/some/override")
        self.assertEqual(d, Path("/some/override/build/target/product/security"))

    def test_default_uses_aosp_paths(self):
        # Without override, security_dir derives from aosp_paths.aosp_root(),
        # which honours AOSP_ROOT env then DEFAULT_AOSP_ROOT.
        with mock.patch.dict("os.environ", {"AOSP_ROOT": "/env/aosp"}, clear=False):
            d = module.security_dir(None)
        self.assertEqual(d, Path("/env/aosp/build/target/product/security"))


class TestBuildCommandChain(unittest.TestCase):
    def test_three_commands_in_order(self):
        cmds = module.build_command_chain(
            Path("/a/platform.pk8"),
            Path("/o/platform.key.pem"),
            Path("/o/platform.crt.pem"),
            Path("/o/platform.p12"),
            Path("/o/platform.keystore"),
        )
        self.assertEqual(len(cmds), 3)
        # Step 1: openssl pkcs8 (DER → PEM private key)
        self.assertEqual(cmds[0][0], "openssl")
        self.assertEqual(cmds[0][1], "pkcs8")
        self.assertIn("-inform", cmds[0])
        self.assertIn("DER", cmds[0])
        self.assertIn("-nocrypt", cmds[0])
        self.assertEqual(cmds[0][cmds[0].index("-in") + 1], "/a/platform.pk8")
        self.assertEqual(cmds[0][cmds[0].index("-out") + 1], "/o/platform.key.pem")

        # Step 3: openssl pkcs12 -export
        self.assertEqual(cmds[1][0], "openssl")
        self.assertEqual(cmds[1][1], "pkcs12")
        self.assertIn("-export", cmds[1])
        self.assertEqual(cmds[1][cmds[1].index("-in") + 1], "/o/platform.crt.pem")
        self.assertEqual(cmds[1][cmds[1].index("-inkey") + 1], "/o/platform.key.pem")
        self.assertEqual(cmds[1][cmds[1].index("-out") + 1], "/o/platform.p12")
        self.assertEqual(cmds[1][cmds[1].index("-name") + 1], "AndroidDebugKey")
        # password pass:android
        self.assertIn("pass:android", cmds[1])

        # Step 4: keytool -importkeystore
        self.assertEqual(cmds[2][0], "keytool")
        self.assertEqual(cmds[2][1], "-importkeystore")
        self.assertEqual(cmds[2][cmds[2].index("-deststorepass") + 1], "android")
        self.assertEqual(cmds[2][cmds[2].index("-destkeystore") + 1], "/o/platform.keystore")
        self.assertEqual(cmds[2][cmds[2].index("-srckeystore") + 1], "/o/platform.p12")
        self.assertEqual(cmds[2][cmds[2].index("-srcstoretype") + 1], "PKCS12")
        self.assertEqual(cmds[2][cmds[2].index("-srcstorepass") + 1], "android")

    def test_no_cp_in_chain(self):
        """The cp step is handled by shutil.copyfile, not in the command chain."""
        cmds = module.build_command_chain(
            Path("/a/p.pk8"), Path("/o/k.pem"), Path("/o/c.pem"),
            Path("/o/p.p12"), Path("/o/p.keystore"),
        )
        for cmd in cmds:
            self.assertNotIn("cp", cmd)


class TestGenerateMissingInput(unittest.TestCase):
    def test_raises_when_aosp_inputs_absent(self):
        """generate() must raise FileNotFoundError before invoking openssl."""
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(module, "subprocess") as fake_subproc:
                with self.assertRaises(FileNotFoundError) as cm:
                    module.generate(
                        aosp="/nonexistent/aosp/for/task067",
                        key_name="platform",
                        dest=d,
                    )
            self.assertIn("platform.pk8", str(cm.exception))
            # Crucially, openssl/keytool were never invoked.
            fake_subproc.run.assert_not_called()


class TestDefaultDest(unittest.TestCase):
    def test_default_dest_is_project_keystore(self):
        # _DEFAULT_DEST == <project>/keystore (matches .sh SCRIPT_DIR/../keystore)
        expected = module._TOOLS_DIR.parent / "keystore"
        self.assertEqual(module._DEFAULT_DEST, expected)


if __name__ == "__main__":
    unittest.main()
