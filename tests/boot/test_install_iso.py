# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for install_iso.py, on stand-ins: the text Anaconda's text
# interface prints (simpleline's prompts and check boxes), and a VM that a
# thread plays on a socket pair, answering what the test types as the live
# session and the installed system would. `just test` runs them in the lint
# container:
#   python3 -m unittest discover --start-directory tests/boot

import io
import re
import shlex
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import boot_iso
import install_iso

REPO = Path(__file__).resolve().parent.parent.parent
ISO_YAML = REPO / "image/live/iso.yaml"
KICKSTART = REPO / "installer/anaconda/interactive-defaults.ks"
DIGEST = "sha256:" + "ab" * 32
NAME = "ghcr.io/edmundhills/lumen:dev"

# Anaconda 44.30's summary in its text interface, as the first install run
# showed it on 2026-10-31: two parts to a row, and a prompt that simpleline
# breaks over two lines.
HUB = """================================================================================
Installation

1) [x] Language settings                 2) [x] Time settings
       (English (United States))                (Etc/UTC timezone)
3) [{mark}] Installation Destination
       ({status})

Please make a selection from the above ['b' to begin installation, 'q' to quit,
'r' to refresh]: """
SCREEN_PROMPT = """
Please make a selection from the above ['c' to continue, 'q' to quit, 'r' to
refresh]: """
# The disk's three screens, as Anaconda's text StorageSpoke, PartTypeSpoke and
# PartitionSchemeSpoke draw them, with the kickstart's choices marked.
SCREENS = [
    "Installation Destination\n\n1) [x] Virtio Block Device (vda): 64 GiB free\n\n"
    "1 disk selected; 64 GiB capacity; 64 GiB free\n" + SCREEN_PROMPT,
    "Partitioning Options\n\n1) [ ] Replace Existing Linux system(s)\n2) [x] Use All Space\n"
    "3) [ ] Use Free Space\n4) [ ] Manually assign mount points\n" + SCREEN_PROMPT,
    "Partition Scheme Options\n\n1) [ ] Standard Partition\n2) [x] Btrfs\n3) [ ] LVM\n"
    "4) [ ] LVM Thin Provisioning\n" + SCREEN_PROMPT,
]


def hub(mark="x", status="Automatic partitioning selected"):
    return HUB.format(mark=mark, status=status)


PREPARE = f"""LUMEN-CHECKS-BEGIN
  PASS  SELinux enforcing in the live session
  PASS  No network: the VM has no network card
  INFO  The ISO's copy: {NAME} {DIGEST} 44.20261030.4

Passed: 2   Failed: 0
LUMEN-CHECKS-0-DONE
"""


class FakeVM:
    """A VM whose serial port a thread plays.

    Once started, it sends each part of OPENING a moment apart, as GRUB shows
    its menu, then starts its default entry. Then it answers each line typed
    with the text the first of RULES that matches gives; an answer of None
    switches the VM off.
    """

    def __init__(self, opening, rules):
        self.guest, ours = socket.socketpair()
        self.console = boot_iso.Console(ours, io.BytesIO())
        self.monitor = mock.Mock()
        self.monitor.run.side_effect = lambda command, **_: (
            threading.Thread(target=self._open, args=(opening,), daemon=True).start() if command == "cont" else None)
        self.off = threading.Event()
        self.proc = mock.Mock()
        self.proc.wait.side_effect = lambda timeout=None: self.off.wait(timeout) or (_ for _ in ()).throw(
            install_iso.subprocess.TimeoutExpired("qemu", timeout))
        self.rules, self.typed = rules, []
        threading.Thread(target=self._answer, daemon=True).start()

    def _open(self, opening):
        for part in opening:
            time.sleep(0.3)
            self.guest.sendall(part.encode())

    def _answer(self):
        buffer = b""
        while not self.off.is_set():
            data = self.guest.recv(4096)
            if not data:
                return
            buffer += data
            while b"\r" in buffer:
                line, buffer = buffer.split(b"\r", 1)
                line = line.decode()
                self.typed.append(line)
                for pattern, answer in self.rules:
                    if re.search(pattern, line):
                        if answer is None:
                            self.off.set()
                        else:
                            self.guest.sendall((answer() if callable(answer) else answer).encode())
                        break

    def alive(self):
        return not self.off.is_set()

    def screenshot(self, path):
        return None

    def close(self):
        self.off.set()
        self.guest.close()
        self.console.sock.close()


class SettingsTest(unittest.TestCase):
    def test_settings_stand_in_for_a_person(self):
        settings = install_iso.install_settings("pw")
        lines = [line for line in settings.splitlines() if line and not line.startswith("#")]
        self.assertTrue(settings.startswith("\n"), "kept apart from the installer's own lines")
        self.assertIn("ignoredisk --only-use=vda", lines)
        self.assertIn("autopart", lines)
        self.assertIn("rootpw --plaintext pw", lines)
        # A whole keyboard setting, so Anaconda doesn't ask the live desktop for one.
        self.assertIn("keyboard --vckeymap=us --xlayouts=us", lines)
        # The source stays the installer's own: the test adds no other.
        for command in ("bootc", "ostreecontainer", "ostreesetup", "liveimg", "url", "%include"):
            self.assertFalse([line for line in lines if line.split()[0] == command], command)
        # The installed system keeps the kernel arguments a person's install gives it.
        self.assertNotIn("bootloader", settings)

    def test_commands_typed_are_not_their_own_markers(self):
        line = install_iso.liveinst_command()
        self.assertTrue(line.endswith("\r"))
        self.assertIn("LIVECMD='anaconda --liveinst --text' liveinst", line)
        self.assertNotRegex(line, install_iso.LIVEINST_DONE)
        line = install_iso.guest_command("lumen.install", "report", NAME)
        self.assertEqual(shlex.split(line.split(";")[0]),
                         ["bash", "/run/credentials/@system/lumen.install", "report", NAME])
        self.assertNotRegex(line, boot_iso.DONE)
        self.assertNotRegex(line, boot_iso.BEGIN)

    def test_guest_scripts_print_the_begin_marker(self):
        for script in (install_iso.LIVE_SCRIPT, install_iso.INSTALLED_SCRIPT):
            self.assertIn("printf 'LUMEN-CHECKS-BEGIN\\n'", script.read_text(), script.name)

    def test_the_live_script_reads_the_kickstart_the_iso_has(self):
        # install-live.sh finds the image's name in the kickstart's bootc line.
        text = install_iso.LIVE_SCRIPT.read_text()
        self.assertIn("readonly KICKSTART=/usr/share/anaconda/interactive-defaults.ks", text)
        bootc = [line for line in KICKSTART.read_text().splitlines() if line.startswith("bootc ")]
        self.assertEqual(len(bootc), 1)
        self.assertIn(f"--source-imgref=containers-storage:{NAME} ", bootc[0] + " ")


class TextInterfaceTest(unittest.TestCase):
    def test_the_prompts(self):
        self.assertRegex(boot_iso.plain(hub()), install_iso.SUMMARY)
        self.assertNotRegex("Please make a selection from the above ['h' to help]: ", install_iso.SUMMARY)
        for screen in SCREENS:
            self.assertRegex(screen, install_iso.SCREEN_PROMPT)
            self.assertNotRegex(screen, install_iso.SUMMARY)
        self.assertNotRegex(hub(), install_iso.SCREEN_PROMPT)

    def test_parts_of_the_summary(self):
        spokes = install_iso.summary_spokes(hub("!"))
        self.assertEqual(spokes, ["1) [x] Language settings                 2) [x] Time settings",
                                  "3) [!] Installation Destination"])
        self.assertEqual(install_iso.DESTINATION.search(hub("!"))[1], "3")
        self.assertIsNone(install_iso.DESTINATION.search(hub()))
        self.assertFalse(any(install_iso.INCOMPLETE in s for s in install_iso.summary_spokes(hub())))

    def test_the_end(self):
        self.assertRegex("Installation complete\nInstallation complete. Press ENTER to quit: ", install_iso.INSTALLED)
        self.assertRegex("Traceback (most recent call last):", install_iso.ERROR)
        self.assertRegex("An unknown error has occured, look at the /tmp/anaconda-tb* file(s)", install_iso.ERROR)

    def test_the_iso_s_copy(self):
        m = install_iso.PAYLOAD.search(PREPARE)
        self.assertEqual(m.groups(), (NAME, DIGEST, "44.20261030.4"))


class InstallTest(unittest.TestCase):
    """install() and check_installed() against a VM that a thread plays."""

    def setUp(self):
        self.menu = boot_iso.load_menu(ISO_YAML)
        self.patches = [mock.patch.object(install_iso, "RECHECK", 0)]
        for p in self.patches:
            p.start()
        self.out = tempfile.TemporaryDirectory()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.out.cleanup()

    def live_vm(self, install_ends="Installing...\nInstallation complete. Press ENTER to quit: "):
        names = "\n".join(f"  {name}" for name, _ in self.menu.entries)
        default = self.menu.entries[self.menu.default][0]
        prompt = "[root@localhost-live ~]# "
        # Still checking the disk, then waiting for someone to go through its
        # screens, then done.
        hubs = iter([hub("!", install_iso.PROCESSING), hub("!"), hub()])
        screens = iter(SCREENS[1:] + [hub()])
        return FakeVM([f"{names}\n", f"Booting `{default}'\n\nlocalhost-live login: "], [
            (r"^root$", prompt),
            (r"lumen\.install prepare", PREPARE + prompt),
            (r"liveinst", lambda: next(hubs)),
            (r"^r$", lambda: next(hubs)),
            (r"^3$", SCREENS[0]),
            (r"^c$", lambda: next(screens)),
            (r"^b$", install_ends),
            (r"^$", "\nLUMEN-INSTALL-0-DONE\n" + prompt),
            (r"lumen\.install report", "LUMEN-CHECKS-BEGIN\n  PASS  bootc\n\nLUMEN-CHECKS-0-DONE\n" + prompt),
            (r"systemctl poweroff", None),
        ])

    def steps(self, vm, report):
        return boot_iso.Steps(vm, report, Path(self.out.name) / "t", 1)

    def test_installs_through_the_text_interface(self):
        vm, report = self.live_vm(), boot_iso.Report(0, "install")
        try:
            payload = install_iso.install(self.steps(vm, report), self.menu)
        finally:
            vm.close()
        self.assertEqual(report.failures, 0, "\n".join(report.lines))
        self.assertEqual(payload, (NAME, DIGEST, "44.20261030.4"))
        # It looked at the summary again while the disk was being checked,
        # went through the disk's screens, and began.
        typed = [t for t in vm.typed if t in ("r", "3", "c", "b")]
        self.assertEqual(typed, ["r", "3", "c", "c", "c", "b"])
        self.assertIn("        Partition Scheme Options: 2) [x] Btrfs", report.lines)
        self.assertIn(f"bash /run/credentials/@system/lumen.install report {NAME}; echo LUMEN-CHECKS-$?-DONE",
                      vm.typed)
        self.assertTrue(any("Anaconda installed Lumen" in line for line in report.lines))

    def test_stops_when_anaconda_fails(self):
        vm, report = self.live_vm("Traceback (most recent call last):\n  File ...\n"), boot_iso.Report(0, "install")
        try:
            self.assertIsNone(install_iso.install(self.steps(vm, report), self.menu))
        finally:
            vm.close()
        self.assertEqual(report.failures, 1)
        self.assertTrue(any("Anaconda didn't finish installing" in line for line in report.lines))
        self.assertNotIn("systemctl poweroff", vm.typed)

    def test_checks_the_installed_system(self):
        vm = FakeVM(["\nlumen login: "], [
            (r"^root$", "Password: "),
            (rf"^{install_iso.ROOT_PASSWORD}$", "[root@lumen ~]# "),
            (r"lumen\.installed-check", "LUMEN-CHECKS-BEGIN\n  PASS  Follows\n  FAIL  Runs\n\nLUMEN-CHECKS-1-DONE\n"),
        ])
        report = boot_iso.Report(0, "installed")
        try:
            install_iso.check_installed(self.steps(vm, report), (NAME, DIGEST, "44.20261030.4"))
        finally:
            vm.close()
        self.assertEqual((report.passes, report.failures), (3, 1), "\n".join(report.lines))
        self.assertIn(f"bash /run/credentials/@system/lumen.installed-check {NAME} {DIGEST} 44.20261030.4; "
                      "echo LUMEN-CHECKS-$?-DONE", vm.typed)


if __name__ == "__main__":
    unittest.main()
