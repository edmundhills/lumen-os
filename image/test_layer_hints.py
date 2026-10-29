# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for layer_hints.py, on a stand-in image root and overlay, and
# with a stand-in for os.setxattr. `just test` runs them in the lint container:
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
        self.root = Path(d.name) / "root"
        self.overlay = Path(d.name) / "overlay"
        self.overlay.mkdir()
        self.marks = []

    def add(self, base, path, link_to=None):
        p = base / path
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
            status = layer_hints.main(["layer_hints.py", str(self.overlay), str(self.root)],
                                      setxattr=self.setxattr)
        return status, err.getvalue()

    def add_build_state(self):
        for path in ("usr/share/rpm/rpmdb.sqlite", "usr/lib/sysimage/libdnf5/system.toml",
                     "usr/lib/fontconfig/cache/3830d5c3ddfd5cd38a049b759396e72e-le64.cache-9"):
            self.add(self.root, path)

    def test_marks_os_release_and_the_overlay_files(self):
        self.add(self.root, "usr/lib/os-release")
        self.add_build_state()
        for path in ("etc/xdg/kdeglobals", "usr/lib/systemd/system/lumen-home-snapshots.service"):
            self.add(self.root, path)
            self.add(self.overlay, path)
        # A package's file next to an overlay file is left alone.
        self.add(self.root, "usr/lib/systemd/system/firewalld.service")
        status, err = self.run_main()
        self.assertEqual(status, 0, err)
        self.assertEqual(self.marks, [
            ("usr/lib/os-release", "user.component", b"lumen-os-release"),
            ("usr/share/rpm/rpmdb.sqlite", "user.component", b"lumen-build-state"),
            ("usr/lib/sysimage/libdnf5/system.toml", "user.component", b"lumen-build-state"),
            ("usr/lib/fontconfig/cache/3830d5c3ddfd5cd38a049b759396e72e-le64.cache-9", "user.component",
             b"lumen-build-state"),
            ("etc/xdg/kdeglobals", "user.component", b"lumen-overlay"),
            ("usr/lib/systemd/system/lumen-home-snapshots.service", "user.component", b"lumen-overlay"),
        ])

    def test_a_missing_file_or_a_link_fails(self):
        self.add(self.root, "usr/lib/os-release.d/lumen")
        self.add(self.root, "usr/lib/os-release", link_to="os-release.d/lumen")
        self.add_build_state()
        self.add(self.overlay, "etc/xdg/kdeglobals")
        status, err = self.run_main()
        self.assertEqual(status, 1)
        self.assertIn("nothing matches /usr/lib/os-release", err)
        self.assertIn("nothing matches /etc/xdg/kdeglobals", err)
        self.assertEqual(self.marks, [])

    def test_the_real_overlay_has_only_regular_files(self):
        overlay = Path(layer_hints.__file__).resolve().parent / "overlay"
        links = [str(p) for p in overlay.rglob("*") if p.is_symlink()]
        self.assertEqual(links, [], "layer_hints.py can't mark links")

    def test_usage(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(layer_hints.main(["layer_hints.py"]), 2)
            self.assertEqual(layer_hints.main(["layer_hints.py", str(self.root / "missing")]), 2)


if __name__ == "__main__":
    unittest.main()
