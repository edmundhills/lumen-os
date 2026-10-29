# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for sbom.py, on SPDX documents shaped like the ones syft writes
# for Lumen's image. `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory image

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sbom


def package(name, purl):
    return {"name": name, "SPDXID": f"SPDXRef-Package-{name}",
            "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER", "referenceType": "purl",
                              "referenceLocator": purl}]}


ROOT = {"name": "localhost/lumen", "SPDXID": "SPDXRef-DocumentRoot-Image-localhost-lumen",
        "primaryPackagePurpose": "CONTAINER"}
BASH = package("bash", "pkg:rpm/fedora/bash@5.3.9-3.fc44?arch=x86_64&distro=fedora-44"
               "&upstream=bash-5.3.9-3.fc44.src.rpm")
# Epochs are a qualifier, and a + in a name is percent-encoded.
SHADOW = package("shadow-utils", "pkg:rpm/fedora/shadow-utils@4.18.0-3.fc44?arch=x86_64&epoch=2&distro=fedora-44")
LIBSTDCXX = package("libstdc++", "pkg:rpm/fedora/libstdc%2B%2B@15.2.1-3.fc44?arch=x86_64&distro=fedora-44")
FONTS = package("fonts", "pkg:rpm/fedora/google-noto-sans-fonts@20251001-1.fc44?arch=noarch&distro=fedora-44")
# Multilib: the same package for two architectures.
GLIBC = package("glibc", "pkg:rpm/fedora/glibc@2.43-4.fc44?arch=x86_64&distro=fedora-44")
GLIBC32 = package("glibc-i686", "pkg:rpm/fedora/glibc@2.43-4.fc44?arch=i686&distro=fedora-44")
PYTHON = package("dnf", "pkg:pypi/dnf@5.2.0")
BINARY = package("go", "pkg:golang/stdlib@1.25.3")

PACKAGES = """bash 0:5.3.9-3.fc44 x86_64
shadow-utils 2:4.18.0-3.fc44 x86_64
libstdc++ 0:15.2.1-3.fc44 x86_64
google-noto-sans-fonts 0:20251001-1.fc44 noarch
glibc 0:2.43-4.fc44 x86_64
glibc 0:2.43-4.fc44 i686
"""


class SbomTest(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work)

    def write(self, packages, rpm_list=PACKAGES):
        (self.work / "sbom.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3", "packages": packages}),
                                             encoding="utf-8")
        (self.work / "packages").write_text(rpm_list, encoding="utf-8")
        return str(self.work / "sbom.json"), str(self.work / "packages")

    def test_matching(self):
        ok, report = sbom.check(*self.write([ROOT, BASH, SHADOW, LIBSTDCXX, FONTS, GLIBC, GLIBC32, PYTHON, BINARY]))
        self.assertTrue(ok, report)
        self.assertIn("lists the image's 6 RPM packages", report)
        self.assertIn("1 golang, 1 pypi", report)

    def test_gpg_pubkey_is_not_a_package(self):
        ok, report = sbom.check(*self.write([BASH], "bash 0:5.3.9-3.fc44 x86_64\n"
                                                    "gpg-pubkey 0:31645531-66b6dccf (none)\n"))
        self.assertTrue(ok, report)

    def test_missing_package(self):
        ok, report = sbom.check(*self.write([BASH, SHADOW, LIBSTDCXX, FONTS, GLIBC]))
        self.assertFalse(ok)
        self.assertIn("In the image but not in the SBOM", report)
        self.assertIn("`glibc 0:2.43-4.fc44 i686`", report)

    def test_extra_package(self):
        ok, report = sbom.check(*self.write([BASH], "\n"))
        self.assertFalse(ok)
        self.assertIn("In the SBOM but not in the image", report)

    def test_other_version(self):
        other = package("bash", "pkg:rpm/fedora/bash@5.3.9-4.fc44?arch=x86_64")
        ok, report = sbom.check(*self.write([other], "bash 0:5.3.9-3.fc44 x86_64\n"))
        self.assertFalse(ok)
        self.assertIn("`bash 0:5.3.9-4.fc44 x86_64`", report)

    def test_other_epoch(self):
        no_epoch = package("shadow-utils", "pkg:rpm/fedora/shadow-utils@4.18.0-3.fc44?arch=x86_64")
        ok, _ = sbom.check(*self.write([no_epoch], "shadow-utils 2:4.18.0-3.fc44 x86_64\n"))
        self.assertFalse(ok)

    def test_long_lists_are_cut(self):
        rpm_list = "".join(f"pkg{i} 0:1-1.fc44 x86_64\n" for i in range(30))
        ok, report = sbom.check(*self.write([], rpm_list))
        self.assertFalse(ok)
        self.assertIn(f"and {30 - sbom.SHOWN} more", report)

    def test_not_spdx(self):
        (self.work / "sbom.json").write_text('{"bomFormat": "CycloneDX"}', encoding="utf-8")
        (self.work / "packages").write_text(PACKAGES, encoding="utf-8")
        with self.assertRaises(sbom.InputError):
            sbom.check(str(self.work / "sbom.json"), str(self.work / "packages"))

    def test_bad_package_line(self):
        with self.assertRaises(sbom.InputError):
            sbom.check(*self.write([BASH], "bash 5.3.9\n"))

    def test_main(self):
        paths = self.write([BASH, SHADOW, LIBSTDCXX, FONTS, GLIBC, GLIBC32])
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(sbom.main(["sbom.py", "check", *paths]), 0)
            self.assertEqual(sbom.main(["sbom.py", "check", paths[0], str(self.work / "missing")]), 2)
            self.assertEqual(sbom.main(["sbom.py", "check"]), 2)
        self.assertIn("### SBOM", out.getvalue())


if __name__ == "__main__":
    unittest.main()
