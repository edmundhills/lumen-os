# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for the NVIDIA edition's files (step 1.11b, ADR 0022): RPM
# Fusion's repository brings only NVIDIA's driver, the kernel arguments match
# what nvidia-fallback.service and check-nvidia.sh look for, and the module
# signing key reaches the build only as a secret, in the one step that signs.
# `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory image

import configparser
import re
import tomllib
import unittest
from pathlib import Path

import packages

HERE = Path(__file__).resolve().parent
NVIDIA = HERE / "nvidia"
CONTAINERFILE = (HERE / "Containerfile").read_text()
WORKFLOW = (HERE.parent / ".github" / "workflows" / "build-image.yml").read_text()


def stage(name):
    """The Containerfile's text from FROM … AS NAME to the next FROM."""
    m = re.search(rf"^FROM \S+ AS {re.escape(name)}\n(.*?)(?=^FROM |\Z)", CONTAINERFILE, re.MULTILINE | re.DOTALL)
    return m.group(1)


class Repository(unittest.TestCase):
    def test_brings_only_nvidias_driver_signed_with_rpm_fusions_key(self):
        repo = configparser.ConfigParser(interpolation=None)
        repo.read(NVIDIA / "rpmfusion-nonfree.repo")
        self.assertEqual(repo.sections(), ["lumen-rpmfusion-nonfree", "lumen-rpmfusion-nonfree-updates"])
        for name in repo.sections():
            with self.subTest(name):
                section = repo[name]
                self.assertEqual(section["includepkgs"].split(","),
                                 ["akmod-nvidia", "xorg-x11-drv-nvidia*", "nvidia-modprobe", "nvidia-persistenced",
                                  "nvidia-settings"])
                self.assertEqual(section["gpgcheck"], "1")
                self.assertEqual(section["gpgkey"],
                                 "file:///run/lumen/nvidia/RPM-GPG-KEY-rpmfusion-nonfree-fedora-2020")

    def test_the_manifest_changes_nothing_the_image_has(self):
        path = NVIDIA / "packages.toml"
        self.assertIn("xorg-x11-drv-nvidia", packages.load(path)["install"])
        self.assertEqual(packages.load_options(path), {"exact_32bit": True})


class Fallback(unittest.TestCase):
    def test_the_kernel_arguments_keep_nouveau_and_nova_away(self):
        kargs = tomllib.loads((NVIDIA / "overlay/usr/lib/bootc/kargs.d/00-lumen-nvidia.toml").read_text())
        self.assertEqual(kargs, {"kargs": ["rd.driver.blacklist=nouveau,nova_core",
                                           "modprobe.blacklist=nouveau,nova_core"]})
        # nvidia-fallback.service runs only with this argument (RPM Fusion's
        # ConditionKernelCommandLine), which check-nvidia.sh checks in the image.
        self.assertIn("ConditionKernelCommandLine=rd.driver.blacklist=nouveau,nova_core",
                      (NVIDIA / "check-nvidia.sh").read_text())

    def test_the_fallback_service_is_turned_on(self):
        preset = (NVIDIA / "overlay/usr/lib/systemd/system-preset/50-lumen-nvidia.preset").read_text()
        self.assertIn("\nenable nvidia-fallback.service\n", preset)
        self.assertIn("systemctl preset nvidia-fallback.service", stage("lumen-nvidia"))


class Key(unittest.TestCase):
    def test_the_key_is_a_secret_of_the_signing_step_only(self):
        for line in CONTAINERFILE.splitlines():
            if "module_signing" in line and not line.lstrip().startswith("#"):
                self.assertIn("--mount=type=secret,id=module_signing_", line)
        self.assertNotIn("ARG MODULE", CONTAINERFILE)
        kmods = stage("kmods")
        self.assertIn("--mount=type=secret,id=module_signing_key", kmods)
        build_step = kmods.split("bash /run/lumen/build-kmods.sh")[0]
        self.assertNotIn("type=secret", build_step)  # akmods and NVIDIA's build never see it.

    def test_no_shipped_image_derives_from_the_kmods_stage(self):
        self.assertNotIn("FROM kmods", CONTAINERFILE)
        self.assertIn("--mount=type=bind,from=kmods,source=/kmods", stage("lumen-nvidia"))

    def test_ci_signs_with_a_throwaway_key_by_another_name(self):
        self.assertIn('-subj "/O=Lumen OS/CN=Lumen OS kernel module signing (throwaway)"', WORKFLOW)
        # The key goes in a step that runs even when a build fails.
        removal = WORKFLOW.split("- name: Remove the throwaway key", 1)[1].split("- name:", 1)[0]
        self.assertRegex(removal, r"if: \$\{\{ always\(\)")
        self.assertIn('rm -rf -- "${keys:?}"', removal)


if __name__ == "__main__":
    unittest.main()
