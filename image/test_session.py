# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for gaming/session.py, which installs the Gamescope session's
# files (step 1.10b, ADR 0020): the real manifest, what a manifest may say, and
# installing and verifying with downloads stood in. `just test` runs them in
# the lint container, which has no network:
#   python3 -m unittest discover --start-directory image

import hashlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "gaming"))
import session  # noqa: E402

MANIFEST = HERE / "gaming" / "session.toml"
COMMIT = "0" * 40


def manifest(text):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d, "session.toml")
        path.write_text(text)
        # load() reads it straight away, so the file needn't outlive this.
        return session.load(path)


def entry(path="usr/bin/tool", **extra):
    fields = {"path": path, "sha256": hashlib.sha256(b"tool").hexdigest(), **extra}
    return "{ " + ", ".join(f'{k} = "{v}"' for k, v in fields.items()) + " }"


def source(*entries, repository="https://github.com/example/tool", commit=COMMIT):
    return f'[[source]]\nrepository = "{repository}"\ncommit = "{commit}"\nfiles = [\n  {",\n  ".join(entries)},\n]\n'


class RealManifest(unittest.TestCase):
    def setUp(self):
        self.files = session.load(MANIFEST)
        self.installed = {f["install"] for f in self.files}

    def test_pins_every_file_to_a_commit(self):
        self.assertEqual(len(self.files), 10)
        for f in self.files:
            self.assertRegex(f["url"], r"^https://raw\.githubusercontent\.com/ChimeraOS/gamescope-session(-steam)?/[0-9a-f]{40}/")

    def test_brings_the_session_and_its_licences(self):
        for path in ("usr/share/wayland-sessions/gamescope-session-steam.desktop", "usr/bin/gamescope-session-plus",
                     "usr/lib/systemd/user/gamescope-session-plus@.service", "usr/bin/steamos-session-select",
                     "usr/share/licenses/gamescope-session/LICENSE",
                     "usr/share/licenses/gamescope-session-steam/LICENSE"):
            self.assertIn(path, self.installed)

    def test_leaves_out_steamos_helpers(self):
        for f in self.files:
            for helper in ("steamos-update", "jupiter-biosupdate", "steamos-select-branch", "steamos-polkit-helpers",
                           "polkit-1", "export-gpu", "steam-http-loader"):
                self.assertNotIn(helper, f["install"])

    def test_lumens_steamos_update_is_in_the_editions_overlay(self):
        self.assertTrue(os.access(HERE / "gaming" / "overlay" / "usr" / "bin" / "steamos-update", os.X_OK))


class Load(unittest.TestCase):
    def rejects(self, text, words):
        with self.assertRaises(session.SessionError) as caught:
            manifest(text)
        self.assertIn(words, str(caught.exception))

    def test_a_short_commit(self):
        self.rejects(source(entry(), commit="73d2da8"), "isn't a full 40-character commit hash")

    def test_a_repository_outside_github(self):
        self.rejects(source(entry(), repository="https://example.org/tool"), "isn't https://github.com/OWNER/REPO")

    def test_a_path_out_of_the_repository(self):
        self.rejects(source(entry("../etc/passwd")), "isn't a path in the repository")

    def test_a_file_outside_the_vendor_folders(self):
        self.rejects(source(entry("etc/sudoers")), "outside /usr/bin/")
        self.rejects(source(entry("usr/bin/tool", install="usr/lib/polkit-1/rules.d/x.rules")), "outside /usr/bin/")

    def test_a_mode_with_more_than_read_and_execute(self):
        self.rejects(source(entry(mode="4755")), "isn't 0644 or 0755")

    def test_a_file_installed_twice(self):
        self.rejects(source(entry(), entry()), "is installed twice")

    def test_an_unknown_key(self):
        self.rejects(source(entry(owner="root")), "unknown keys")

    def test_a_short_sha256(self):
        self.rejects(source(entry(sha256="abc")), "sha256 isn't 64 lowercase hex digits")


class Install(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.files = manifest(source(entry(mode="0755"), entry("LICENSE", install="usr/share/licenses/tool/LICENSE")))

    def test_installs_with_the_mode_and_verifies(self):
        session.install(self.files, self.root, fetch=lambda url: b"tool")
        tool = self.root / "usr/bin/tool"
        self.assertEqual(tool.read_bytes(), b"tool")
        self.assertEqual(tool.stat().st_mode & 0o7777, 0o755)
        self.assertEqual((self.root / "usr/share/licenses/tool/LICENSE").stat().st_mode & 0o7777, 0o644)
        self.assertEqual(session.verify(self.files, self.root), [])
        tool.write_bytes(b"changed")
        os.chmod(tool, 0o644)
        problems = session.verify(self.files, self.root)
        self.assertTrue(any("not the pinned" in p for p in problems))
        self.assertTrue(any("mode 0644, not 0755" in p for p in problems))

    def test_stops_on_a_changed_download(self):
        with self.assertRaises(session.SessionError) as caught:
            session.install(self.files, self.root, fetch=lambda url: b"something else")
        self.assertIn("not the pinned", str(caught.exception))
        self.assertFalse((self.root / "usr/bin/tool").exists())

    def test_never_replaces_a_file_in_the_image(self):
        (self.root / "usr/bin").mkdir(parents=True)
        (self.root / "usr/bin/tool").write_bytes(b"rpm's")
        with self.assertRaises(session.SessionError):
            session.install(self.files, self.root, fetch=lambda url: b"tool")
        self.assertEqual((self.root / "usr/bin/tool").read_bytes(), b"rpm's")

    def test_missing_files_are_named(self):
        self.assertEqual(session.verify(self.files[:1], self.root), ["/usr/bin/tool is missing"])


if __name__ == "__main__":
    unittest.main()
