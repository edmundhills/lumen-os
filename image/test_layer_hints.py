# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for layer_hints.py, on a stand-in image root and with a stand-in
# for os.setxattr. `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory image

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import layer_hints


class LayerHints(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.marks = []

    def add(self, path, link_to=None):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        if link_to:
            p.symlink_to(link_to)
        else:
            p.write_text("x", encoding="utf-8")

    def setxattr(self, path, name, value, follow_symlinks=True):
        self.assertFalse(follow_symlinks)
        self.marks.append((str(Path(path).relative_to(self.root)), name, value))

    def run_main(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            status = layer_hints.main(["layer_hints.py", str(self.root)], setxattr=self.setxattr)
        return status, err.getvalue()

    def test_marks_the_initramfs_and_os_release(self):
        self.add("usr/lib/modules/7.2.12-200.fc44.x86_64/initramfs.img")
        self.add("usr/lib/modules/7.2.12-200.fc44.x86_64/vmlinuz")
        self.add("usr/lib/os-release")
        status, err = self.run_main()
        self.assertEqual(status, 0, err)
        self.assertEqual(self.marks, [
            ("usr/lib/modules/7.2.12-200.fc44.x86_64/initramfs.img", "user.component", b"initramfs"),
            ("usr/lib/os-release", "user.component", b"lumen-os-release"),
        ])

    def test_a_missing_file_or_a_link_fails(self):
        self.add("usr/lib/os-release.d/lumen")
        self.add("usr/lib/os-release", link_to="os-release.d/lumen")
        status, err = self.run_main()
        self.assertEqual(status, 1)
        self.assertIn("nothing matches /usr/lib/modules/*/initramfs.img", err)
        self.assertIn("nothing matches /usr/lib/os-release", err)
        self.assertEqual(self.marks, [])

    def test_usage(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(layer_hints.main(["layer_hints.py", "a", "b"]), 2)


if __name__ == "__main__":
    unittest.main()
