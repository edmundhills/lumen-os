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
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import sbom

HERE = Path(sbom.__file__).resolve().parent


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
        # rpm keeps a trusted key as a package named gpg-pubkey, and syft lists it.
        key = package("gpg-pubkey", "pkg:rpm/fedora/gpg-pubkey@36f612dcf27f7d1a-6786af3b?distro=fedora-44")
        ok, report = sbom.check(*self.write([BASH, key], "bash 0:5.3.9-3.fc44 x86_64\n"
                                                         "gpg-pubkey 0:36f612dcf27f7d1a-6786af3b (none)\n"))
        self.assertTrue(ok, report)
        self.assertIn("lists the image's 1 RPM packages", report)

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


@unittest.skipUnless(os.environ.get("LUMEN_LINT_CONTAINER") == "1", "needs the lint container: run `just test`")
class SyftTest(unittest.TestCase):
    """sbom.sh, with the pinned syft, on the lint container's own files, as CI runs it on the image."""

    def test_the_sbom_lists_exactly_the_rpm_packages(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            out = work / "sbom.spdx.json"
            made = subprocess.run(["bash", str(HERE / "sbom.sh"), "/", "localhost/lumen-lint", "test", str(out)],
                                  capture_output=True, text=True, check=False)
            self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
            rpm = subprocess.run(["rpm", "--query", "--all", "--queryformat",
                                  "%{NAME} %{EPOCHNUM}:%{VERSION}-%{RELEASE} %{ARCH}\n"],
                                 capture_output=True, text=True, check=True)
            (work / "packages").write_text(rpm.stdout, encoding="utf-8")
            ok, report = sbom.check(str(out), str(work / "packages"))
            self.assertTrue(ok, report)
            document = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(document["spdxVersion"].startswith("SPDX-2."), document["spdxVersion"])
            # Packages only: the one file recorded is the rpm database they came from.
            files = [f["fileName"] for f in document.get("files") or []]
            self.assertEqual(len(files), 1, files)
            self.assertTrue(files[0].endswith("rpm/rpmdb.sqlite"), files)
            self.assertEqual(document["name"], "localhost/lumen-lint")

    def test_usage(self):
        result = subprocess.run(["bash", str(HERE / "sbom.sh"), "/"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
