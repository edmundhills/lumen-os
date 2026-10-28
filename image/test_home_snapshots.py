# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the hourly snapshots of /home (step 1.4).

lumen-home-snapshots runs on a temporary folder, with stand-ins for stat,
snapper and restorecon that print what they were asked, so the tests need
neither Btrfs nor root. `just test` runs them.
"""

import os
import pathlib
import subprocess
import tempfile
import unittest

OVERLAY = pathlib.Path(__file__).resolve().parent / "overlay"
SCRIPT = OVERLAY / "usr/libexec/lumen-home-snapshots"
TEMPLATE = OVERLAY / "usr/share/snapper/config-templates/lumen-home"


class SetupTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        self.home = root / "home"
        self.home.mkdir()
        self.bin = root / "bin"
        self.bin.mkdir()
        self.calls = root / "calls"
        self.calls.touch()

    def stub(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def run_setup(self, fstype, inode, snapper_status=0):
        """Run the script as if the folder were on FSTYPE with INODE as its inode number."""
        self.stub(
            "stat",
            f'case "$*" in *--file-system*) echo {fstype} ;; *) echo {inode} ;; esac',
        )
        self.stub("snapper", f'echo "snapper $*" >>"{self.calls}"; exit {snapper_status}')
        self.stub("restorecon", f'echo "restorecon $*" >>"{self.calls}"')
        env = dict(os.environ, PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}")
        result = subprocess.run(
            ["bash", str(SCRIPT), str(self.home)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return result, self.calls.read_text().splitlines()

    def test_not_btrfs(self):
        result, calls = self.run_setup("ext2/ext3", 2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("is not on Btrfs", result.stdout)
        self.assertEqual(calls, [])

    def test_btrfs_folder_that_is_not_a_subvolume(self):
        result, calls = self.run_setup("btrfs", 257)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("is not a Btrfs subvolume", result.stdout)
        self.assertEqual(calls, [])

    def test_subvolume_gets_the_lumen_config(self):
        result, calls = self.run_setup("btrfs", 256)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls[0],
            f"snapper --no-dbus --config home create-config --template lumen-home {self.home}",
        )
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[1].startswith("restorecon -R "), calls[1])
        self.assertIn(f"{self.home}/.snapshots", calls[1].split())

    def test_snapper_failure_fails_the_unit(self):
        result, calls = self.run_setup("btrfs", 256, snapper_status=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)  # snapper ran; restorecon didn't


class TemplateTest(unittest.TestCase):
    def test_keeps_what_the_spec_says(self):
        """Spec, "Snapshots and backup": 24 hourly, 7 daily, 4 weekly."""
        settings = {}
        for line in TEMPLATE.read_text().splitlines():
            if line and not line.startswith("#"):
                key, _, value = line.partition("=")
                settings[key] = value.strip('"')
        self.assertEqual(settings["TIMELINE_CREATE"], "yes")
        self.assertEqual(settings["TIMELINE_CLEANUP"], "yes")
        self.assertEqual(settings["TIMELINE_LIMIT_HOURLY"], "24")
        self.assertEqual(settings["TIMELINE_LIMIT_DAILY"], "7")
        self.assertEqual(settings["TIMELINE_LIMIT_WEEKLY"], "4")
        for key in ("MONTHLY", "QUARTERLY", "YEARLY"):
            self.assertEqual(settings[f"TIMELINE_LIMIT_{key}"], "0", key)


if __name__ == "__main__":
    unittest.main()
