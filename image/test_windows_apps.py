# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for the Windows-app base (step 1.13, ADR 0024): windows_apps.py,
# which makes .exe and .msi files open in Bottles and checks that they do, and
# Lumen's Flathub remote, whose key must be Flathub's. `just test` runs them in
# the lint container:
#   python3 -m unittest discover --start-directory image

import base64
import configparser
import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

import windows_apps

HERE = Path(__file__).resolve().parent
FLATHUB = HERE / "overlay" / "usr" / "share" / "flatpak" / "remotes.d" / "flathub.flatpakrepo"
# Flathub's repository signing key ("Flathub Repo Signing Key").
FLATHUB_FINGERPRINT = "6E5C05D979C76DAF93C081354184DD4D907A7CAE"

MIME_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-ms-dos-executable">
    <alias type="application/x-msdownload"/>
    <glob pattern="*.exe"/>
  </mime-type>
  <mime-type type="application/x-dosexec">
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

FEDORA_LIST = """# A vendor list
[Default Applications]
text/html=firefox.desktop;
application/x-msi=wine.desktop;

[Removed Associations]
text/plain=gedit.desktop;
"""


class Apply(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.path = self.dir / "applications" / "kde-mimeapps.list"

    def test_makes_the_list(self):
        windows_apps.apply(self.path)
        sections = windows_apps.read_list(self.path.read_text())
        for section in windows_apps.SECTIONS:
            self.assertEqual(sections[section], {mime: [windows_apps.BOTTLES] for mime in windows_apps.TYPES})
        self.assertTrue(self.path.read_text().startswith("# Plasma's default apps"))
        self.assertIn("application/x-msi=com.usebottles.bottles.desktop;\n", self.path.read_text())

    def test_keeps_the_rest_of_a_list_and_puts_bottles_first(self):
        self.path.parent.mkdir()
        self.path.write_text(FEDORA_LIST)
        windows_apps.apply(self.path)
        sections = windows_apps.read_list(self.path.read_text())
        self.assertEqual(sections["Default Applications"]["text/html"], ["firefox.desktop"])
        self.assertEqual(sections["Default Applications"]["application/x-msi"], [windows_apps.BOTTLES, "wine.desktop"])
        self.assertEqual(sections["Removed Associations"], {"text/plain": ["gedit.desktop"]})

    def test_applying_twice_changes_nothing(self):
        windows_apps.apply(self.path)
        once = self.path.read_text()
        windows_apps.apply(self.path)
        self.assertEqual(self.path.read_text(), once)


class Check(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.write(windows_apps.MIME_PACKAGES / "freedesktop.org.xml", MIME_XML)
        windows_apps.apply(self.root / windows_apps.LIST)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_the_applied_list_covers_the_types(self):
        self.assertEqual(windows_apps.check(self.root), [])

    def test_finds_every_type_of_a_glob(self):
        self.assertEqual(windows_apps.types_for([MIME_XML], "*.exe"),
                         ["application/x-ms-dos-executable", "application/x-dosexec"])
        self.assertEqual(windows_apps.types_for([MIME_XML], "*.msi"), ["application/x-msi"])

    def test_a_type_the_list_lacks(self):
        self.write(windows_apps.MIME_PACKAGES / "freedesktop.org.xml",
                   MIME_XML.replace("application/x-msi", "application/x-ole-storage"))
        self.assertIn(f"{windows_apps.LIST} doesn't make Bottles the default for application/x-ole-storage, "
                      "a type of *.msi", windows_apps.check(self.root))

    def test_a_pattern_with_no_type(self):
        self.write(windows_apps.MIME_PACKAGES / "freedesktop.org.xml", MIME_XML.replace('"*.msi"', '"*.msp"'))
        self.assertIn("shared-mime-info gives *.msi no type", windows_apps.check(self.root))

    def test_a_list_plasma_reads_first_with_another_default(self):
        self.write("etc/xdg/kde-mimeapps.list", "[Default Applications]\napplication/x-msi=wine.desktop;\n")
        self.assertEqual(windows_apps.check(self.root), [f"{self.root}/etc/xdg/kde-mimeapps.list, which Plasma "
                                                         "reads first, sets wine.desktop as the default for "
                                                         "application/x-msi"])

    def test_a_list_plasma_reads_first_that_removes_bottles(self):
        self.write("usr/share/kde-settings/kde-profile/default/xdg/mimeapps.list",
                   "[Removed Associations]\napplication/x-dosexec=com.usebottles.bottles.desktop;\n")
        self.assertEqual(len(windows_apps.check(self.root)), 1)

    def test_fedoras_list_comes_after_lumens(self):
        self.write("usr/share/applications/mimeapps.list", "[Default Applications]\napplication/x-msi=wine.desktop;\n")
        self.assertEqual(windows_apps.check(self.root), [])

    def test_no_mime_database(self):
        shutil.rmtree(self.root / windows_apps.MIME_PACKAGES)
        self.assertEqual(len(windows_apps.check(self.root)), 1)

    def test_no_list(self):
        (self.root / windows_apps.LIST).unlink()
        self.assertEqual(len(windows_apps.check(self.root)), 1)


def fingerprint(key):
    """The OpenPGP v4 fingerprint of the first public key in binary KEY (RFC 4880, 12.2)."""
    tag = key[0]
    if tag & 0x40:  # New format: the length's first octet decides its size.
        first = key[1]
        if first < 192:
            length, start = first, 2
        elif first < 224:
            length, start = ((first - 192) << 8) + key[2] + 192, 3
        else:
            length, start = int.from_bytes(key[2:6], "big"), 6
        kind = tag & 0x3F
    else:  # Old format: the low two bits give the length's size.
        size = {0: 1, 1: 2, 2: 4}[tag & 0x03]
        length, start = int.from_bytes(key[1:1 + size], "big"), 1 + size
        kind = (tag >> 2) & 0x0F
    if kind != 6:
        raise ValueError(f"the first packet is of type {kind}, not a public key")
    packet = key[start:start + length]
    return hashlib.sha1(b"\x99" + len(packet).to_bytes(2, "big") + packet).hexdigest().upper()


class Flathub(unittest.TestCase):
    def setUp(self):
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(FLATHUB)
        self.repo = parser["Flatpak Repo"]

    def test_is_flathub_unfiltered(self):
        self.assertEqual(self.repo["Url"], "https://dl.flathub.org/repo/")
        self.assertNotIn("Filter", self.repo)

    def test_the_key_is_flathubs(self):
        self.assertEqual(fingerprint(base64.b64decode(self.repo["GPGKey"])), FLATHUB_FINGERPRINT)

    def test_the_comment_names_the_fingerprint(self):
        spaced = " ".join(FLATHUB_FINGERPRINT[i:i + 4] for i in range(0, 40, 4))
        self.assertIn(spaced, FLATHUB.read_text())


if __name__ == "__main__":
    unittest.main()
