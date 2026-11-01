# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for boot_disk.py: the credentials that start the checks inside
# the VM, its command line, and how it reads the checks' report, from a socket
# pair standing in for the VM's second serial port. `just test` runs them in
# the lint container:
#   python3 -m unittest discover --start-directory tests/boot

import io
import re
import socket
import unittest
from unittest import mock

import boot_disk
import boot_iso


class CredentialsTest(unittest.TestCase):
    def test_a_service_runs_the_script_at_boot(self):
        names = [name for name, _ in boot_disk.credentials()]
        self.assertEqual(names, ["lumen.boot-check", "systemd.extra-unit.lumen-boot-check.service",
                                 "systemd.unit-dropin.multi-user.target~lumen-boot-check"])
        unit = boot_disk.check_unit()
        self.assertIn("ExecStart=/bin/bash /run/credentials/@system/lumen.boot-check\n", unit)
        self.assertIn("StandardOutput=file:/dev/ttyS1\n", unit)
        # A oneshot service would keep the system "starting", which the checks wait out.
        self.assertIn("Type=simple\n", unit)
        self.assertEqual(boot_disk.start_dropin(), "[Unit]\nWants=lumen-boot-check.service\n")
        for name, data in boot_disk.credentials():
            self.assertNotIn(",", boot_iso.credential(name, data))  # QEMU's option syntax would split it there.

    def test_the_script_prints_the_markers(self):
        script = boot_disk.CHECK_SCRIPT.read_text()
        self.assertIn("printf 'LUMEN-CHECKS-BEGIN\\n'", script)
        self.assertIn("printf 'LUMEN-CHECKS-FIRST-BOOT-DONE\\n'", script)
        self.assertIn("printf 'LUMEN-CHECKS-SECOND-BOOT\\n'", script)
        self.assertIn("printf 'LUMEN-CHECKS-%d-DONE\\n' \"$status\"", script)
        self.assertRegex("LUMEN-CHECKS-0-DONE", boot_iso.DONE)
        self.assertRegex("LUMEN-CHECKS-FIRST-BOOT-DONE\n", boot_disk.FIRST_BOOT_DONE)
        self.assertNotRegex("LUMEN-CHECKS-FIRST-BOOT-DONE\n", boot_iso.DONE)

    def test_the_first_boot_restarts_the_system_once(self):
        script = boot_disk.CHECK_SCRIPT.read_text()
        self.assertEqual(script.count("systemctl reboot"), 1)
        self.assertIn("touch /etc/plasma-setup-done", script)


class CommandTest(unittest.TestCase):
    def test_a_qcow2_as_a_snapshot_with_a_port_for_the_report(self):
        fw = boot_iso.Firmware("x.json", "/fw/CODE.fd", "raw", "/fw/VARS.fd", "raw")
        disk = "/d/bootc-lumen-0.1-qcow2-x86_64.qcow2"
        cmd = boot_iso.qemu_command(fw, "v", True, "/r/serial", "/r/qmp", ["/r/c"], disk=disk,
                                    disk_format=boot_disk.disk_format(disk), snapshot=True, port="/r/port",
                                    reboot=True)
        joined = " ".join(cmd)
        self.assertIn(f"id=disk,format=qcow2,discard=unmap,snapshot=on,file={disk}", joined)
        self.assertIn("socket,id=port,path=/r/port,server=on,wait=off", joined)
        self.assertEqual(cmd.count("-serial"), 2)
        self.assertNotIn("-no-reboot", cmd)
        self.assertNotIn("cdrom", joined)
        self.assertEqual(boot_disk.disk_format("/d/check.raw"), "raw")


class ReadReportTest(unittest.TestCase):
    def setUp(self):
        self.vm_side, ours = socket.socketpair()
        self.console = boot_iso.Console(ours, io.BytesIO())
        self.report = boot_iso.Report(0, "disk")

    def tearDown(self):
        self.vm_side.close()
        self.console.sock.close()

    def test_takes_the_report_of_both_boots(self):
        self.vm_side.sendall(b"LUMEN-CHECKS-BEGIN\r\nThe first boot, with no user\r\n  PASS  Secure Boot on\r\n"
                             b"  FAIL  No failed units\r\n        mcelog.service\r\n"
                             b"  INFO  Kernel lockdown: [integrity]\r\nLUMEN-CHECKS-FIRST-BOOT-DONE\r\n")
        calls = []

        def first_boot_done():
            calls.append(self.report.passes)
            # The firmware and GRUB write to the port as the system restarts.
            self.vm_side.sendall(b"BdsDxe: loading Boot0003 \"Fedora\"\r\nBooting `Lumen OS 0.1 (ostree:0)'\r\n"
                                 b"LUMEN-CHECKS-SECOND-BOOT\r\n"
                                 b"\r\nThe second boot, with a user\r\n  PASS  The login screen within 60 s\r\n\r\n"
                                 b"Passed: 2   Failed: 1\r\nLUMEN-CHECKS-1-DONE\r\n")

        self.assertTrue(boot_disk.read_report(self.console, self.report, 1, lambda: True, first_boot_done))
        self.assertEqual(calls, [0])  # Once, before the second boot's report.
        self.assertEqual((self.report.passes, self.report.failures), (2, 1))
        self.assertIn("  FAIL  No failed units", self.report.lines)
        self.assertIn("The second boot, with a user", self.report.lines)
        self.assertFalse(any("FIRST-BOOT" in line or "SECOND-BOOT" in line for line in self.report.lines))
        self.assertFalse(any("BdsDxe" in line or "Booting" in line for line in self.report.lines))
        self.assertTrue(any(re.match(r"\s+The checks of both boots took \d+ s\.", line) for line in self.report.lines))

    def test_says_when_the_second_boot_never_reports(self):
        self.vm_side.sendall(b"LUMEN-CHECKS-BEGIN\r\n  PASS  Secure Boot on\r\nLUMEN-CHECKS-FIRST-BOOT-DONE\r\n"
                             b"BdsDxe: loading Boot0003\r\n")
        with mock.patch.dict(boot_disk.TIMEOUTS, {"second boot": 0.3}):
            self.assertFalse(boot_disk.read_report(self.console, self.report, 1, lambda: True))
        self.assertEqual((self.report.passes, self.report.failures), (1, 1))
        self.assertIn("  FAIL  The second boot's checks didn't finish", self.report.lines)
        # The firmware's lines show only in the port's last lines, after the failure.
        tail = next(i for i, line in enumerate(self.report.lines) if "Their last lines:" in line)
        self.assertFalse(any("BdsDxe" in line for line in self.report.lines[:tail]))
        self.assertTrue(any("BdsDxe" in line for line in self.report.lines[tail:]))

    def test_says_when_the_checks_never_start(self):
        with mock.patch.dict(boot_disk.TIMEOUTS, {"begin": 0.3}):
            self.assertFalse(boot_disk.read_report(self.console, self.report, 1, lambda: True))
        self.assertEqual(self.report.failures, 1)
        self.assertIn("lumen-boot-check.service", self.report.lines[0])


if __name__ == "__main__":
    unittest.main()
