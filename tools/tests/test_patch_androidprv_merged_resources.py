#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for tools/patch_androidprv_merged_resources.py.

All fixtures are throwaway trees under tempfile.TemporaryDirectory. AAPT2 is
simulated by a tiny fake executable (never the real SDK binary), so the tests
exercise namespace injection, selection, flat-name mapping, replacement
atomicity, error exits, and idempotence — not AAPT2 itself.
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Make tools/ importable.
_TOOLS = Path(__file__).resolve().parent.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import patch_androidprv_merged_resources as p  # noqa: E402


# --- fake AAPT2 ------------------------------------------------------------

_FAKE_AAPT2 = """\
#!/usr/bin/env python3
import sys
from pathlib import Path

args = sys.argv[1:]
if len(args) == 4 and args[0] == 'compile' and args[2] == '-o':
    src = Path(args[1])
    out_dir = Path(args[3])
    out_dir.mkdir(parents=True, exist_ok=True)
    flat = out_dir / (src.parent.name + '_' + src.stem + '.arsc.flat')
    flat.write_bytes(b'FLAT:' + str(src.name).encode())
    sys.exit(0)
sys.stderr.write('usage: aapt2 compile <file> -o <dir>\\n')
sys.exit(2)
"""

_FAKE_AAPT2_FAIL = """\
#!/usr/bin/env python3
import sys
sys.stderr.write('fake compile failure\\n')
sys.exit(1)
"""

_FAKE_AAPT2_SILENT = """\
#!/usr/bin/env python3
import sys
sys.exit(0)
"""


def _write_exec(dir_path: Path, name: str, text: str) -> Path:
    p = dir_path / name
    p.write_text(text, encoding='utf-8')
    p.chmod(0o755)
    return p


# --- fixture helpers ---------------------------------------------------------

def _values_xml(body: str, extra_root_attrs: str = '') -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<resources xmlns:android="http://schemas.android.com/apk/res/android"{extra_root_attrs}>\n'
        f'{body}'
        '</resources>\n'
    )


PRV_BODY = (
    '    <color name="c1">@androidprv:color/system_under_surface_light</color>\n'
)
NO_PRV_BODY = (
    '    <color name="c2">#ff000000</color>\n'
)


class FixtureBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.merged = self.root / 'merged.dir'
        self.compiled = self.root / 'compiled'
        self.merged.mkdir()
        self.compiled.mkdir()
        self.aapt2 = _write_exec(self.root, 'fake-aapt2.py', _FAKE_AAPT2)

    def tearDown(self):
        self._tmp.cleanup()

    def _add(self, rel: str, text: str) -> Path:
        p = self.merged / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def _add_flat(self, flat_name: str, data: bytes = b'ORIGINAL') -> Path:
        p = self.compiled / flat_name
        p.write_bytes(data)
        return p

    def _run_cli(self, aapt2=None):
        cmd = [
            sys.executable, str(_TOOLS / 'patch_androidprv_merged_resources.py'),
            '--merged-dir', str(self.merged),
            '--compiled-dir', str(self.compiled),
            '--aapt2', str(aapt2 or self.aapt2),
        ]
        return subprocess.run(cmd, capture_output=True, text=True)


# --- pure-function tests ------------------------------------------------------

class TestFlatNameMapping(unittest.TestCase):
    def test_plain_values_maps_to_values_values_flat(self):
        self.assertEqual(
            p.flat_name(Path('values/values.xml')), 'values_values.arsc.flat')

    def test_qualified_values_dir_maps_to_dir_underscore_file(self):
        self.assertEqual(
            p.flat_name(Path('values-night-v8/values-night-v8.xml')),
            'values-night-v8_values-night-v8.arsc.flat')
        self.assertEqual(
            p.flat_name(Path('values-sw600dp-land-v13/values-sw600dp-land-v13.xml')),
            'values-sw600dp-land-v13_values-sw600dp-land-v13.arsc.flat')


class TestInjectDeclaration(unittest.TestCase):
    def test_injects_on_root_exactly_once(self):
        out = p.inject_declaration(_values_xml(PRV_BODY))
        self.assertEqual(out.count(p.PRV_DECL), 1)
        root = re.search(r'<resources\b[^>]*>', out).group(0)
        self.assertIn(p.PRV_DECL, root)
        # android namespace still declared on the root
        self.assertIn('xmlns:android=', root)

    def test_existing_declaration_returned_unchanged(self):
        src = _values_xml(PRV_BODY, extra_root_attrs=' ' + p.PRV_DECL)
        self.assertEqual(p.inject_declaration(src), src)

    def test_duplicate_declaration_raises(self):
        src = _values_xml(PRV_BODY, extra_root_attrs=' ' + p.PRV_DECL + ' ' + p.PRV_DECL)
        with self.assertRaises(p.PatchError):
            p.inject_declaration(src)

    def test_missing_resources_root_raises(self):
        with self.assertRaises(p.PatchError):
            p.inject_declaration('<other><item/></other>')


class TestSelectCandidates(unittest.TestCase):
    def test_only_files_with_androidprv_selected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / 'values').mkdir()
            (root / 'values-land').mkdir()
            (root / 'values' / 'values.xml').write_text(
                _values_xml(PRV_BODY), encoding='utf-8')
            (root / 'values-land' / 'values-land.xml').write_text(
                _values_xml(NO_PRV_BODY), encoding='utf-8')
            scanned, candidates = p.select_candidates(root)
            self.assertEqual(len(scanned), 2)
            self.assertEqual([c.name for c in candidates], ['values.xml'])


# --- CLI behavior tests -------------------------------------------------------

class TestCliErrors(FixtureBase):
    def test_missing_merged_dir_fails(self):
        r = self._run_cli()
        # merged dir exists here; test the real missing case via direct call
        r2 = subprocess.run([
            sys.executable, str(_TOOLS / 'patch_androidprv_merged_resources.py'),
            '--merged-dir', str(self.root / 'nope'),
            '--compiled-dir', str(self.compiled),
            '--aapt2', str(self.aapt2),
        ], capture_output=True, text=True)
        self.assertNotEqual(r2.returncode, 0)

    def test_zero_candidates_fails(self):
        self._add('values/values.xml', _values_xml(NO_PRV_BODY))
        r = self._run_cli()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('no androidprv', (r.stdout + r.stderr).lower())

    def test_duplicate_declaration_fails(self):
        self._add('values/values.xml',
                  _values_xml(PRV_BODY, extra_root_attrs=' ' + p.PRV_DECL * 1 + ' ' + p.PRV_DECL))
        r = self._run_cli()
        self.assertNotEqual(r.returncode, 0)

    def test_compile_failure_fails(self):
        bad = _write_exec(self.root, 'bad-aapt2.py', _FAKE_AAPT2_FAIL)
        self._add('values/values.xml', _values_xml(PRV_BODY))
        self._add_flat('values_values.arsc.flat')
        r = self._run_cli(aapt2=bad)
        self.assertNotEqual(r.returncode, 0)

    def test_missing_flat_output_fails(self):
        silent = _write_exec(self.root, 'silent-aapt2.py', _FAKE_AAPT2_SILENT)
        self._add('values/values.xml', _values_xml(PRV_BODY))
        self._add_flat('values_values.arsc.flat')
        r = self._run_cli(aapt2=silent)
        self.assertNotEqual(r.returncode, 0)


class TestCliSuccess(FixtureBase):
    def test_patch_compile_replace_and_summary(self):
        src = self._add('values/values.xml', _values_xml(PRV_BODY))
        self._add('values-night-v8/values-night-v8.xml',
                  _values_xml(PRV_BODY.replace('_light', '_dark')))
        self._add('values-land/values-land.xml', _values_xml(NO_PRV_BODY))
        original_bytes = self._add_flat('values_values.arsc.flat').read_bytes()
        self._add_flat('values-night-v8_values-night-v8.arsc.flat')
        self._add_flat('values-land_values-land.arsc.flat')
        land_before = (self.compiled / 'values-land_values-land.arsc.flat').read_bytes()

        src_before = src.read_bytes()
        r = self._run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        m = re.search(
            r'scanned=(\d+) patched=(\d+) compiled=(\d+) unresolved=(\d+)',
            r.stdout)
        self.assertIsNotNone(m, r.stdout)
        self.assertEqual(m.group(1), '3')   # scanned all three files
        self.assertEqual(m.group(2), '2')   # only the two androidprv files
        self.assertEqual(m.group(3), '2')   # two flats recompiled
        self.assertEqual(m.group(4), '0')

        # flats for patched files replaced; untouched flat preserved
        self.assertEqual(
            (self.compiled / 'values_values.arsc.flat').read_bytes(),
            b'FLAT:values.xml')
        self.assertEqual(
            (self.compiled / 'values-night-v8_values-night-v8.arsc.flat').read_bytes(),
            b'FLAT:values-night-v8.xml')
        self.assertEqual(
            (self.compiled / 'values-land_values-land.arsc.flat').read_bytes(),
            land_before)
        self.assertNotEqual(
            (self.compiled / 'values_values.arsc.flat').read_bytes(),
            original_bytes)

        # merged-dir XML never modified
        self.assertEqual(src.read_bytes(), src_before)

    def test_second_run_is_idempotent(self):
        self._add('values/values.xml', _values_xml(PRV_BODY))
        self._add_flat('values_values.arsc.flat')
        r1 = self._run_cli()
        r2 = self._run_cli()
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(
            (self.compiled / 'values_values.arsc.flat').read_bytes(),
            b'FLAT:values.xml')
        self.assertEqual(r1.stdout, r2.stdout)

    def test_existing_declaration_file_is_left_alone(self):
        # a candidate that already declares androidprv needs no patch
        self._add('values/values.xml',
                  _values_xml(PRV_BODY, extra_root_attrs=' ' + p.PRV_DECL))
        self._add_flat('values_values.arsc.flat', b'KEEP')
        r = self._run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('patched=0', r.stdout)
        self.assertEqual(
            (self.compiled / 'values_values.arsc.flat').read_bytes(), b'KEEP')


if __name__ == '__main__':
    unittest.main()
