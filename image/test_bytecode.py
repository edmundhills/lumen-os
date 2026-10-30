# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for live/bytecode.py, on a stand-in root with a Python package laid
# out as Fedora's are, its sources given the time 0 as the image gives them.
# `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory image

import contextlib
import importlib.util
import io
import os
import py_compile
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "live"))

import bytecode  # noqa: E402

TAG = sys.implementation.cache_tag
PYTHON = f"python{sys.version_info.major}.{sys.version_info.minor}"


class BytecodeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pkg = self.root / "usr/lib" / PYTHON / "site-packages/pkg"
        self.pkg.mkdir(parents=True)
        self.cache = self.pkg / "__pycache__"

    def tearDown(self):
        self.tmp.cleanup()

    def module(self, name, text="VALUE = 1\n", levels=(0, 1), mtime=0):
        """A module with bytecode compiled at build time, then its source given MTIME, as in the image."""
        source = self.pkg / f"{name}.py"
        source.write_text(text)
        os.utime(source, (1787391379, 1787391379))
        pycs = []
        for level in levels:
            pyc = self.cache / f"{name}.{TAG}{f'.opt-{level}' if level else ''}.pyc"
            py_compile.compile(str(source), cfile=str(pyc), optimize=level, doraise=True,
                               invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
            pycs.append(pyc)
        os.utime(source, (mtime, mtime))
        return source, pycs

    def run_main(self, command):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            status = bytecode.main(["bytecode.py", command, str(self.root)])
        return status, out.getvalue()

    def test_finds_bytecode_whose_source_time_differs(self):
        _, (stale, stale_opt) = self.module("stale")
        _, (fresh,) = self.module("fresh", levels=(0,), mtime=1787391379)
        total, found = bytecode.find_stale(self.root)
        self.assertEqual(total, 3)
        self.assertEqual(sorted(p for p, _, _ in found), sorted([str(stale), str(stale_opt)]))
        self.assertEqual({(Path(p).name, level) for p, _, level in found},
                         {(stale.name, 0), (stale_opt.name, 1)})
        self.assertNotIn(str(fresh), [p for p, _, _ in found])

    def test_ignores_other_pythons_and_bytecode_without_source(self):
        self.module("mod", levels=(0,))
        self.cache.joinpath("mod.cpython-27.pyc").write_bytes(b"\0" * 16)
        self.cache.joinpath(f"gone.{TAG}.pyc").write_bytes(b"\0" * 16)
        total, found = bytecode.find_stale(self.root)
        self.assertEqual((total, len(found)), (1, 1))

    def test_fix_compiles_stale_bytecode_checked_by_hash(self):
        source, (pyc, pyc_opt) = self.module("stale", text="def f():\n    assert False\n    return 2\n")
        status, out = self.run_main("fix")
        self.assertEqual(status, 0, out)
        self.assertIn("Compiled 2 of 2", out)
        for f in (pyc, pyc_opt):
            header = f.read_bytes()[:16]
            self.assertEqual(header[:4], importlib.util.MAGIC_NUMBER)
            self.assertEqual(struct.unpack("<I", header[4:8])[0], 0b11)  # hash-based, checked
            self.assertEqual(header[8:16], importlib.util.source_hash(source.read_bytes()))
        # The optimization level is kept: -O drops asserts.
        self.assertNotEqual(pyc.read_bytes()[16:], pyc_opt.read_bytes()[16:])
        self.assertEqual(self.run_main("check")[0], 0)

    def test_fix_names_the_installed_path(self):
        self.module("mod", text="def f():\n    raise ValueError\n", levels=(0,))
        self.run_main("fix")
        data = self.cache.joinpath(f"mod.{TAG}.pyc").read_bytes()
        self.assertIn(f"/usr/lib/{PYTHON}/site-packages/pkg/mod.py".encode(), data)
        self.assertNotIn(self.tmp.name.encode(), data)

    def test_fix_reports_what_does_not_compile(self):
        source, _ = self.module("bad", levels=(0,))
        source.write_text("def (:\n")
        os.utime(source, (0, 0))
        status, out = self.run_main("fix")
        self.assertEqual(status, 1)
        self.assertIn("could not be compiled", out)

    def test_check_lists_stale_bytecode(self):
        self.module("stale")
        status, out = self.run_main("check")
        self.assertEqual(status, 1)
        self.assertIn("2 of 2 .pyc files are stale", out)

    def test_bad_magic_is_stale(self):
        source, (pyc,) = self.module("mod", levels=(0,), mtime=1787391379)
        pyc.write_bytes(b"\0\0\0\0" + pyc.read_bytes()[4:])
        self.assertTrue(bytecode.is_stale(str(pyc), str(source)))

    def test_usage(self):
        self.assertEqual(bytecode.main(["bytecode.py", "fix"]), 2)
        self.assertEqual(bytecode.main(["bytecode.py", "mend", str(self.root)]), 2)


if __name__ == "__main__":
    unittest.main()
