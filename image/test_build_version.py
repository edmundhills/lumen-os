# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for build_version.py. `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory image

import datetime
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import build_version

HERE = Path(build_version.__file__).resolve().parent
DIGEST = "sha256:" + "0" * 64
DAY = datetime.date(2026, 10, 28)


class FedoraRelease(unittest.TestCase):
    def test_reads_the_release_from_the_base_stage(self):
        text = f"# Kinoite\nFROM quay.io/fedora-ostree-desktops/kinoite:45@{DIGEST} AS base\nFROM base AS lumen\n"
        self.assertEqual(build_version.fedora_release(text), "45")

    def test_the_real_containerfile_has_one(self):
        release = build_version.fedora_release((HERE / "Containerfile").read_text(encoding="utf-8"))
        self.assertRegex(release, r"^[0-9]+$")

    def assert_rejects(self, text):
        with self.assertRaises(build_version.VersionError):
            build_version.fedora_release(text)

    def test_rejects_a_base_that_isnt_pinned_by_digest(self):
        self.assert_rejects("FROM quay.io/fedora-ostree-desktops/kinoite:44 AS base\n")

    def test_rejects_a_base_without_a_release_tag(self):
        self.assert_rejects(f"FROM quay.io/fedora-ostree-desktops/kinoite@{DIGEST} AS base\n")

    def test_rejects_two_base_stages(self):
        line = f"FROM quay.io/fedora-ostree-desktops/kinoite:44@{DIGEST} AS base\n"
        self.assert_rejects(line + line)


class BuildVersion(unittest.TestCase):
    def test_first_build_of_the_day_has_no_suffix(self):
        self.assertEqual(build_version.build_version("44", DAY, []), "44.20261028")

    def test_further_builds_take_the_next_free_suffix(self):
        tags = ["dev", "dev-44.20261028", "dev-44.20261028.1", "sha-abc"]
        self.assertEqual(build_version.build_version("44", DAY, tags), "44.20261028.2")

    def test_only_dev_tags_count(self):
        tags = ["beta-44.20261028", "44.20261028", "dev-44.20261027"]
        self.assertEqual(build_version.build_version("44", DAY, tags), "44.20261028")

    def test_pads_the_date(self):
        self.assertEqual(build_version.build_version("45", datetime.date(2027, 1, 5), []), "45.20270105")


class Main(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(HERE / "build_version.py"), *args],
            capture_output=True, text=True, check=False,
        )

    def test_prints_todays_version_for_the_real_containerfile(self):
        result = self.run_script(str(HERE / "Containerfile"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"^[0-9]+\.20[0-9]{6}\n$")

    def test_reads_skopeo_tags(self):
        first = self.run_script(str(HERE / "Containerfile")).stdout.strip()
        with tempfile.TemporaryDirectory() as d:
            tags = Path(d, "tags.json")
            tags.write_text(json.dumps({"Repository": "ghcr.io/x/lumen", "Tags": ["dev-" + first]}))
            result = self.run_script(str(HERE / "Containerfile"), str(tags))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, first + ".1\n")

    def test_fails_on_a_tag_list_that_isnt_json(self):
        with tempfile.TemporaryDirectory() as d:
            tags = Path(d, "tags.json")
            tags.write_text("Error listing repository tags")
            result = self.run_script(str(HERE / "Containerfile"), str(tags))
        self.assertEqual(result.returncode, 1)
        self.assertIn("build_version.py:", result.stderr)


if __name__ == "__main__":
    unittest.main()
