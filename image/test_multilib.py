# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for multilib.py: how it sorts what dnf would install, where it
# finds a build on Koji, and the checks after installing. dnf and rpm don't run
# here; install() is tested with them stood in. `just test` runs them in the
# lint container:
#   python3 -m unittest discover --start-directory image

import subprocess
import unittest
from unittest import mock

import multilib

MESA = "0:25.2.5-1.fc44"
NEWER = "0:25.2.6-1.fc44"
HAVE = {
    ("mesa-dri-drivers", "x86_64"): MESA,
    ("mesa-filesystem", "x86_64"): MESA,
    ("glibc", "x86_64"): "0:2.42-5.fc44",
    ("kwin", "x86_64"): "0:6.7.5-1.fc44",
}


class Parse(unittest.TestCase):
    def test_reads_rpms_query_lines(self):
        text = "glibc x86_64 0:2.42-5.fc44\nglibc i686 0:2.42-5.fc44\n\n"
        self.assertEqual(multilib.parse(text), {("glibc", "x86_64"): "0:2.42-5.fc44",
                                                ("glibc", "i686"): "0:2.42-5.fc44"})

    def test_version_release_drops_the_epoch(self):
        self.assertEqual(multilib.version_release(MESA), "25.2.5-1.fc44")
        self.assertEqual(multilib.version_release("2:1.6.3-2.fc44"), "1.6.3-2.fc44")


class Plan(unittest.TestCase):
    def test_a_32bit_twin_at_the_images_version_is_kept(self):
        files = {"/d/a.rpm": ("mesa-dri-drivers", "i686", MESA), "/d/b.rpm": ("steam", "x86_64", "0:1.0.0.87-4.fc44")}
        self.assertEqual(multilib.plan(files, HAVE), (["/d/a.rpm", "/d/b.rpm"], [], []))

    def test_a_newer_32bit_twin_is_fetched_at_the_images_version(self):
        files = {"/d/a.rpm": ("mesa-dri-drivers", "i686", NEWER)}
        self.assertEqual(multilib.plan(files, HAVE), ([], [("mesa-dri-drivers", MESA)], []))

    def test_an_upgrade_of_an_installed_package_is_dropped(self):
        files = {"/d/f.rpm": ("mesa-filesystem", "x86_64", NEWER), "/d/l.rpm": ("libnsl", "i686", "0:2.0.1-4.fc44")}
        keep, fetch, dropped = multilib.plan(files, HAVE)
        self.assertEqual((keep, fetch), (["/d/l.rpm"], []))  # A 32-bit package with no twin comes as it is.
        self.assertEqual(dropped, [f"mesa-filesystem.x86_64 {MESA} -> {NEWER}"])


class Checks(unittest.TestCase):
    def test_mismatched_twins_are_named(self):
        have = {**HAVE, ("mesa-dri-drivers", "i686"): NEWER, ("glibc", "i686"): "0:2.42-5.fc44"}
        self.assertEqual(multilib.mismatches(have), [f"mesa-dri-drivers: i686 {NEWER}, x86_64 {MESA}"])

    def test_source_package_names(self):
        self.assertEqual(multilib.source_nvr("mesa-25.2.5-1.fc44.src.rpm"), ("mesa", "25.2.5", "1.fc44"))
        self.assertEqual(multilib.source_nvr("xorg-x11-server-Xwayland-24.1.9-1.fc44.src.rpm"),
                         ("xorg-x11-server-Xwayland", "24.1.9", "1.fc44"))
        with self.assertRaises(multilib.MultilibError):
            multilib.source_nvr("(none)")

    def test_key_id_from_rpms_signature_line(self):
        self.assertEqual(multilib.key_id("RSA/SHA256, Mon Oct 26 2026, Key ID 829B606631645531"), "31645531")
        with self.assertRaises(multilib.MultilibError):
            multilib.key_id("(none)")

    def test_kojis_signed_copy(self):
        self.assertEqual(
            multilib.koji_url("mesa-25.2.5-1.fc44.src.rpm", "31645531", "mesa-dri-drivers", MESA),
            "https://kojipkgs.fedoraproject.org/packages/mesa/25.2.5/1.fc44/data/signed/31645531/i686/"
            "mesa-dri-drivers-25.2.5-1.fc44.i686.rpm")


class Signatures(unittest.TestCase):
    def checked(self, stdout, returncode=0):
        result = subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")
        with mock.patch.object(multilib.subprocess, "run", return_value=result):
            multilib.verify("/d/steam.rpm")

    def test_a_signed_package_passes(self):
        self.checked("/d/steam.rpm: digests signatures OK\n")

    def test_an_unsigned_package_fails_though_rpm_passes_it(self):
        with self.assertRaises(multilib.MultilibError):
            self.checked("/d/steam.rpm: digests OK\n")

    def test_a_package_signed_with_an_unknown_key_fails(self):
        with self.assertRaises(multilib.MultilibError):
            self.checked("/d/steam.rpm: digests SIGNATURES NOT OK\n", returncode=1)

    def test_imports_the_keys_of_enabled_repositories(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            key = Path(d, "RPM-GPG-KEY-fedora-44-x86_64")
            key.write_text("key")
            other = Path(d, "RPM-GPG-KEY-other")
            other.write_text("key")
            repo = Path(d, "fedora.repo")
            repo.write_text(f"[fedora]\nenabled=1\ngpgkey=file://{d}/RPM-GPG-KEY-fedora-$releasever-$basearch\n"
                            f"[off]\nenabled=0\ngpgkey=file://{other}\n"
                            f"[updates]\ngpgkey=file://{d}/RPM-GPG-KEY-fedora-$releasever_major-$basearch "
                            "https://example.org/key\n")
            runs = []

            def run(cmd, **kwargs):
                runs.append(cmd)
                return subprocess.CompletedProcess(cmd, 0, stdout="44\n", stderr="")
            with (mock.patch.object(multilib.glob, "glob", return_value=[str(repo)]),
                  mock.patch.object(multilib.subprocess, "run", side_effect=run)):
                self.assertEqual(multilib.import_keys(), [str(key)])
            self.assertEqual(runs[-1], ["rpmkeys", "--import", str(key)])


class Install(unittest.TestCase):
    """install() with dnf, rpm and curl stood in: the mirrors have an older Mesa than dnf picks first."""

    def setUp(self):
        self.have = dict(HAVE)
        self.calls = []
        patches = [
            mock.patch.object(multilib, "installed", side_effect=lambda: dict(self.have)),
            mock.patch.object(multilib, "headers", side_effect=self.headers),
            mock.patch.object(multilib, "downloaded", side_effect=lambda d: [f"{d}/mesa-dri-drivers.i686.rpm",
                                                                            f"{d}/steam.rpm"]),
            mock.patch.object(multilib.subprocess, "run", side_effect=self.fake_run),
            mock.patch.object(multilib.glob, "glob", side_effect=self.glob),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.fetched = []

    def headers(self, paths):
        return {p: ("mesa-dri-drivers", "i686", NEWER) if "mesa" in p else ("steam", "x86_64", "0:1.0.0.87-4.fc44")
                for p in paths}

    def glob(self, pattern):
        if pattern.endswith("exact/*.rpm"):
            return list(self.fetched)
        return []

    def fake_run(self, cmd, **kwargs):
        self.calls.append(cmd)
        if cmd[:2] == ["rpm", "--eval"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="44\n", stderr="")
        if cmd[:2] == ["rpmkeys", "--checksig"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=f"{cmd[2]}: digests signatures OK\n", stderr="")
        if "download" in cmd and "--resolve" not in cmd:
            self.fetched.append(cmd[-1] + ".rpm")
        if "--disablerepo=*" in cmd:
            self.have[("steam", "x86_64")] = "0:1.0.0.87-4.fc44"
            self.have[("mesa-dri-drivers", "i686")] = MESA
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def test_installs_the_32bit_build_at_the_images_version(self):
        multilib.install(["steam"])
        self.assertIn("--resolve", self.calls[0])
        checked = [c[2] for c in self.calls if c[:2] == ["rpmkeys", "--checksig"]]
        self.assertEqual(len(checked), 2)  # Every file, Steam's included.
        final = self.calls[-1]
        self.assertIn("--disablerepo=*", final)
        self.assertIn("mesa-dri-drivers-25.2.5-1.fc44.i686.rpm", final)
        self.assertTrue(any(a.endswith("/steam.rpm") for a in final))
        # dnf's first pick, the newer Mesa, is left out.
        self.assertFalse(any(a.endswith("mesa-dri-drivers.i686.rpm") for a in final))

    def test_stops_when_the_twins_still_differ(self):
        def run(cmd, **kwargs):
            result = self.fake_run(cmd, **kwargs)
            if "--disablerepo=*" in cmd:
                self.have[("mesa-dri-drivers", "i686")] = NEWER
            return result
        multilib.subprocess.run.side_effect = run
        with self.assertRaises(multilib.MultilibError) as caught:
            multilib.install(["steam"])
        self.assertIn("32-bit and 64-bit builds differ: mesa-dri-drivers", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
