# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for the gaming edition's files (step 1.10a, ADR 0019): RPM
# Fusion's key is the one whose fingerprint RPM Fusion publishes, keys.sha256
# pins it, the repository can bring nothing but Steam, and the Containerfile
# mounts the files where the repository file looks for them. `just test` runs
# them in the lint container:
#   python3 -m unittest discover --start-directory image

import base64
import configparser
import hashlib
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAMING = HERE / "gaming"
KEY = GAMING / "RPM-GPG-KEY-rpmfusion-nonfree-fedora-2020"
# RPM Fusion's nonfree key for Fedora 33 and later ("RPM Fusion nonfree
# repository for Fedora (2020)"), as its release package carries it.
FINGERPRINT = "79BDB88F9BBF73910FD4095B6A2AF96194843C65"


def fingerprint(armored):
    """The OpenPGP v4 fingerprint of the first public key in an ASCII-armored key block (RFC 4880, 12.2)."""
    body = armored.split("-----BEGIN PGP PUBLIC KEY BLOCK-----", 1)[1].split("-----END", 1)[0]
    lines = [line.strip() for line in body.strip().splitlines()]
    # Headers end at the first empty line; the line starting with = is the checksum.
    if "" in lines:
        lines = lines[lines.index("") + 1:]
    data = base64.b64decode("".join(line for line in lines if line and not line.startswith("=")))
    tag = data[0]
    if not tag & 0x80:
        raise ValueError("not an OpenPGP packet")
    if tag & 0x40:  # New format: the length's first octet decides its size.
        first = data[1]
        if first < 192:
            length, start = first, 2
        elif first < 224:
            length, start = ((first - 192) << 8) + data[2] + 192, 3
        else:
            length, start = int.from_bytes(data[2:6], "big"), 6
        kind = tag & 0x3F
    else:  # Old format: the low two bits give the length's size.
        size = {0: 1, 1: 2, 2: 4}[tag & 0x03]
        length, start = int.from_bytes(data[1:1 + size], "big"), 1 + size
        kind = (tag >> 2) & 0x0F
    if kind != 6:
        raise ValueError(f"the first packet is of type {kind}, not a public key")
    packet = data[start:start + length]
    if packet[0] != 4:
        raise ValueError(f"a version {packet[0]} key, not version 4")
    return hashlib.sha1(b"\x99" + len(packet).to_bytes(2, "big") + packet).hexdigest().upper()


class Key(unittest.TestCase):
    def test_rpm_fusions_nonfree_key(self):
        self.assertEqual(fingerprint(KEY.read_text()), FINGERPRINT)

    def test_keys_sha256_pins_it(self):
        line = (GAMING / "keys.sha256").read_text()
        self.assertEqual(line, f"{hashlib.sha256(KEY.read_bytes()).hexdigest()}  {KEY.name}\n")


class Repository(unittest.TestCase):
    def setUp(self):
        self.repo = configparser.ConfigParser(interpolation=None)
        self.repo.read(GAMING / "rpmfusion-nonfree.repo")

    def test_brings_only_steam_signed_with_rpm_fusions_key(self):
        self.assertEqual(self.repo.sections(), ["lumen-rpmfusion-nonfree", "lumen-rpmfusion-nonfree-updates"])
        for name in self.repo.sections():
            with self.subTest(name):
                section = self.repo[name]
                self.assertEqual(section["includepkgs"], "steam")
                self.assertEqual(section["gpgcheck"], "1")
                self.assertTrue(section["metalink"].startswith("https://mirrors.rpmfusion.org/metalink?repo=nonfree-fedora-"))
                self.assertEqual(section["gpgkey"], f"file:///run/lumen/gaming/{KEY.name}")

    def test_the_containerfile_mounts_it_there(self):
        containerfile = (HERE / "Containerfile").read_text()
        self.assertIn("--mount=type=bind,source=image/gaming,target=/run/lumen/gaming", containerfile)
        self.assertIn("sha256sum --check --strict keys.sha256", containerfile)
        # The repository is gone again by the end of the same step.
        step = re.search(r"cp /run/lumen/gaming/rpmfusion-nonfree.repo (\S+).*?rm (\S+)", containerfile, re.DOTALL)
        self.assertEqual(step.group(1), step.group(2))


class Fingerprint(unittest.TestCase):
    def test_rejects_what_isnt_a_key(self):
        block = "-----BEGIN PGP PUBLIC KEY BLOCK-----\n\n" + base64.b64encode(b"\x00\x01").decode() + \
            "\n-----END PGP PUBLIC KEY BLOCK-----\n"
        with self.assertRaises(ValueError):
            fingerprint(block)


if __name__ == "__main__":
    unittest.main()
