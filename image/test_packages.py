# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for packages.py. `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory image

import tempfile
import unittest
from pathlib import Path

import packages

MANIFEST = """
[desktop]
keep = ["kwin"]
remove = ["plasma-discover"]

[system]
keep = ["bootc"]
install = ["tuned-ppd"]
remove = ["power-profiles-daemon"]
"""


def load_text(text):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d, "packages.toml")
        path.write_text(text)
        return packages.load(path)


class Load(unittest.TestCase):
    def test_merges_the_areas_in_file_order(self):
        self.assertEqual(load_text(MANIFEST), {
            "keep": ["kwin", "bootc"],
            "install": ["tuned-ppd"],
            "remove": ["plasma-discover", "power-profiles-daemon"],
        })

    def test_the_real_manifest_loads(self):
        lists = packages.load(Path(packages.__file__).with_name("packages.toml"))
        self.assertTrue(lists["keep"] and lists["install"] and lists["remove"])

    def assert_rejects(self, text, words):
        with self.assertRaises(packages.ManifestError) as caught:
            load_text(text)
        self.assertIn(words, str(caught.exception))

    def test_rejects_a_package_listed_twice(self):
        self.assert_rejects('[a]\nkeep = ["kwin"]\n[b]\nremove = ["kwin"]\n', "kwin is already listed in [a] keep")

    def test_rejects_an_unknown_list(self):
        self.assert_rejects('[a]\nadd = ["kwin"]\n', "unknown list")

    def test_rejects_a_name_that_isnt_a_package(self):
        self.assert_rejects('[a]\ninstall = ["kwin; rm -rf /"]\n', "isn't a package name")

    def test_rejects_a_list_outside_a_table(self):
        self.assert_rejects('keep = ["kwin"]\n', "expected a table")

    def test_rejects_a_string_instead_of_a_list(self):
        self.assert_rejects('[a]\nkeep = "kwin"\n', "expected a list of package names")

    def test_rejects_toml_errors(self):
        self.assert_rejects('[a]\nkeep = ["kwin"\n', "packages.toml")


class Checks(unittest.TestCase):
    lists = {"keep": ["kwin"], "install": ["tuned-ppd"], "remove": ["power-profiles-daemon"]}
    base = {"kwin": "6.7.5-1.fc44", "power-profiles-daemon": "0.30-3.fc44", "bash": "5.3-1.fc44"}

    def test_a_matching_base_passes(self):
        self.assertEqual(packages.check_before(self.lists, self.base), [])

    def test_before_catches_a_kept_package_the_base_lacks(self):
        problems = packages.check_before(self.lists, {"power-profiles-daemon": "0.30"})
        self.assertEqual(problems, ["kwin is listed under keep, but the base image doesn't have it"])

    def test_before_catches_a_removed_package_the_base_lacks(self):
        problems = packages.check_before(self.lists, {"kwin": "6.7.5"})
        self.assertIn("power-profiles-daemon is listed under remove, but the base image doesn't have it", problems)

    def test_before_catches_an_installed_package_the_base_already_has(self):
        problems = packages.check_before(self.lists, {**self.base, "tuned-ppd": "2.28"})
        self.assertEqual(problems, ["tuned-ppd is listed under install, but the base image already has it: "
                                    "move it to keep"])

    def test_a_correct_result_passes(self):
        after = {"kwin": "6.7.5-1.fc44", "tuned-ppd": "2.28", "tuned": "2.28", "bash": "5.3-2.fc44"}
        self.assertEqual(packages.check_after(self.lists, self.base, after), [])

    def test_after_catches_a_package_removed_as_a_dependency(self):
        after = {"tuned-ppd": "2.28", "bash": "5.3-1.fc44"}
        problems = packages.check_after(self.lists, self.base, after)
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("kwin was removed, but isn't listed under remove"))

    def test_after_catches_a_package_that_wasnt_installed_or_removed(self):
        after = {**self.base}
        problems = packages.check_after(self.lists, self.base, after)
        self.assertEqual(problems, ["tuned-ppd is listed under install, but isn't installed",
                                    "power-profiles-daemon is listed under remove, but is still installed"])


if __name__ == "__main__":
    unittest.main()
