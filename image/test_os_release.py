# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for os-release.sh's product version: image-builder, which makes
# Lumen's disk images, reads VERSION_ID as a version with at most one dot
# (docs/decisions/0011-disk-images.md). `just test` runs them in the lint
# container:
#   python3 -m unittest discover --start-directory image

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "os-release.sh"


def product_version(text):
    return re.search(r"^readonly PRODUCT_VERSION=(\S+)$", text, re.MULTILINE).group(1)


class OsReleaseTest(unittest.TestCase):
    def test_the_product_version_has_at_most_one_dot(self):
        version = product_version(SCRIPT.read_text(encoding="utf-8"))
        self.assertRegex(version, r"^[0-9]+(\.[0-9]+)?$")

    def test_a_version_with_two_dots_stops_the_script(self):
        # The check comes before the script reads the Fedora release or writes
        # anything, so a copy with a planted version can run anywhere.
        work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, work)
        text = SCRIPT.read_text(encoding="utf-8")
        planted = text.replace(f"readonly PRODUCT_VERSION={product_version(text)}\n",
                               "readonly PRODUCT_VERSION=0.1.1\n")
        self.assertNotEqual(planted, text)
        (work / "os-release.sh").write_text(planted, encoding="utf-8")
        result = subprocess.run(["bash", str(work / "os-release.sh"), "44.20261029"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('The product version "0.1.1" is not N or N.N', result.stderr)


if __name__ == "__main__":
    unittest.main()
