# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for windows_apps.py, the check that .exe and .msi files open in
# Bottles (step 1.13), and for Lumen's own mimeapps.list. `just test` runs
# them in the lint container:
#   python3 -m unittest discover --start-directory image

import shutil
import tempfile
import unittest
from pathlib import Path

import windows_apps

HERE = Path(__file__).resolve().parent
OVERLAY_LIST = HERE / "overlay" / windows_apps.LUMEN_LIST

MIME_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-msdownload">
    <comment>Windows executable</comment>
    <alias type="application/x-ms-dos-executable"/>
    <glob pattern="*.exe"/>
  </mime-type>
  <mime-type type="application/x-msi">
    <glob pattern="*.msi"/>
  </mime-type>
  <mime-type type="text/plain">
    <glob pattern="*.txt"/>
  </mime-type>
</mime-info>
"""


class Check(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.write(windows_apps.MIME_PACKAGES / "freedesktop.org.xml", MIME_XML)
        self.write(windows_apps.LUMEN_LIST, OVERLAY_LIST.read_text())

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def check(self, owner=lambda path: None):
        return windows_apps.check(self.root, owner=owner)

    def test_lumens_list_covers_the_types(self):
        self.assertEqual(self.check(), [])

    def test_finds_the_types_by_glob(self):
        self.assertEqual(windows_apps.types_for([MIME_XML], "*.exe"), ["application/x-msdownload"])
        self.assertEqual(windows_apps.types_for([MIME_XML], "*.msi"), ["application/x-msi"])

    def test_a_type_lumens_list_lacks(self):
        self.write(windows_apps.MIME_PACKAGES / "freedesktop.org.xml",
                   MIME_XML.replace("application/x-msi", "application/x-ole-storage"))
        problems = self.check()
        self.assertIn("Lumen's mimeapps.list doesn't make Bottles the default for application/x-ole-storage, "
                      "the type of *.msi", problems)

    def test_a_pattern_with_no_type(self):
        self.write(windows_apps.MIME_PACKAGES / "freedesktop.org.xml", MIME_XML.replace('"*.msi"', '"*.msp"'))
        self.assertIn("shared-mime-info gives *.msi no type", self.check())

    def test_another_list_with_a_default(self):
        self.write("etc/xdg/kde-mimeapps.list", "[Default Applications]\napplication/x-msi=wine.desktop;\n")
        self.assertEqual(self.check(), [f"{self.root}/etc/xdg/kde-mimeapps.list sets a default app for "
                                        "application/x-msi: wine.desktop"])

    def test_another_list_that_removes_bottles(self):
        self.write("usr/share/applications/kde-mimeapps.list",
                   "[Removed Associations]\napplication/x-msdownload=com.usebottles.bottles.desktop;\n")
        self.assertEqual(self.check(), [f"{self.root}/usr/share/applications/kde-mimeapps.list removes Bottles "
                                        "from application/x-msdownload"])

    def test_other_types_in_other_lists_are_fine(self):
        self.write("etc/xdg/mimeapps.list", "[Default Applications]\ntext/plain=org.kde.kwrite.desktop;\n")
        self.assertEqual(self.check(), [])

    def test_a_list_a_package_owns(self):
        problems = self.check(owner=lambda path: "kde-settings")
        self.assertEqual(problems, [f"{self.root}/{windows_apps.LUMEN_LIST} belongs to the package kde-settings, "
                                    "whose file Lumen's replaced"])

    def test_no_mime_database(self):
        shutil.rmtree(self.root / windows_apps.MIME_PACKAGES)
        self.assertEqual(len(self.check()), 1)


class LumensList(unittest.TestCase):
    def test_bottles_is_first_for_every_type_it_names(self):
        sections = windows_apps.read_list(OVERLAY_LIST.read_text())
        defaults = sections["Default Applications"]
        self.assertEqual(set(defaults), set(sections["Added Associations"]))
        for mime, apps in defaults.items():
            with self.subTest(mime):
                self.assertEqual(apps, [windows_apps.BOTTLES])

    def test_names_the_types_bottles_declares(self):
        # Bottles' desktop file (bottlesdevs/Bottles at fdeaff1) declares these two.
        defaults = windows_apps.read_list(OVERLAY_LIST.read_text())["Default Applications"]
        for mime in ("application/x-ms-dos-executable", "application/x-msi"):
            self.assertIn(mime, defaults)


if __name__ == "__main__":
    unittest.main()
