# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for boot_iso.py, on stand-ins: firmware descriptors laid out as
# edk2-ovmf's, a socket pair for the serial port, and image/live/iso.yaml
# itself. `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory tests/boot

import base64
import io
import json
import shlex
import socket
import struct
import tempfile
import time
import unittest
import zlib
from pathlib import Path

import boot_iso

REPO = Path(__file__).resolve().parent.parent.parent
ISO_YAML = REPO / "image/live/iso.yaml"


def descriptor(code="/fw/CODE.secboot.fd", nvram="/fw/VARS.secboot.fd", features=None, machines=None,
               arch="x86_64", interface="uefi", fmt="raw"):
    return {
        "description": "test",
        "interface-types": [interface],
        "mapping": {
            "device": "flash",
            "mode": "split",
            "executable": {"filename": code, "format": fmt},
            "nvram-template": {"filename": nvram, "format": fmt},
        },
        "targets": [{"architecture": arch, "machines": machines or ["pc-q35-*"]}],
        "features": ["acpi-s3", "requires-smm", "secure-boot", "enrolled-keys", "verbose-dynamic"]
        if features is None else features,
        "tags": [],
    }


class FirmwareTest(unittest.TestCase):
    def find(self, descriptors):
        with tempfile.TemporaryDirectory() as d:
            for name, content in descriptors.items():
                (Path(d) / name).write_text(content if isinstance(content, str) else json.dumps(content))
            return boot_iso.find_firmware(d)

    def test_picks_the_first_secure_boot_firmware_in_name_order(self):
        fw = self.find({
            "60-ovmf-sb.json": descriptor(code="/fw/second.fd"),
            "50-ovmf-sb-qcow2.json": descriptor(code="/fw/first.qcow2", nvram="/fw/vars.qcow2", fmt="qcow2"),
        })
        self.assertEqual((fw.descriptor, fw.code, fw.code_format), ("50-ovmf-sb-qcow2.json", "/fw/first.qcow2", "qcow2"))
        self.assertEqual((fw.nvram, fw.nvram_format), ("/fw/vars.qcow2", "qcow2"))

    def test_skips_firmware_that_does_not_fit(self):
        sb = ["requires-smm", "secure-boot", "enrolled-keys"]
        fw = self.find({
            "10-no-keys.json": descriptor(features=["requires-smm", "secure-boot"]),
            "11-no-secure-boot.json": descriptor(features=["acpi-s3"]),
            "12-sev.json": descriptor(features=[*sb, "amd-sev-snp"]),
            "13-arm.json": descriptor(arch="aarch64", machines=["virt-*"]),
            "14-pc.json": descriptor(machines=["pc-i440fx-*"]),
            "15-bios.json": descriptor(interface="bios"),
            "16-broken.json": "{not json",
            "17-incomplete.json": {"interface-types": ["uefi"], "mapping": {"device": "flash"}, "features": sb,
                                   "targets": [{"architecture": "x86_64", "machines": ["pc-q35-*"]}]},
            "20-right.json": descriptor(code="/fw/right.fd"),
        })
        self.assertEqual(fw.code, "/fw/right.fd")

    def test_none_when_nothing_fits(self):
        self.assertIsNone(self.find({"10.json": descriptor(features=[])}))


class MenuTest(unittest.TestCase):
    def test_reads_iso_yaml(self):
        menu = boot_iso.load_menu(ISO_YAML)
        self.assertEqual((menu.default, menu.timeout), (0, 10))
        name, args = menu.entries[0]
        self.assertEqual(name, "Try or install Lumen OS")
        self.assertEqual(args, ["root=live:CDLABEL=Lumen-Live", "rd.live.image", "quiet", "rhgb"])
        self.assertIn("rd.live.check", menu.entries[1][1])

    def test_keys_move_from_the_default_entry(self):
        menu = boot_iso.Menu(1, 10, [("a", []), ("b", []), ("c", []), ("d", [])])
        self.assertEqual(boot_iso.menu_keys(menu, 3), "vv\r")
        self.assertEqual(boot_iso.menu_keys(menu, 0), "^\r")
        self.assertEqual(boot_iso.menu_keys(menu, 1), "\r")


class GuestTest(unittest.TestCase):
    def test_credential_holds_the_script(self):
        text = boot_iso.credential("lumen.live-check", b"echo hi\n")
        prefix = "io.systemd.credential.binary:lumen.live-check="
        self.assertTrue(text.startswith(prefix))
        self.assertEqual(base64.b64decode(text[len(prefix):]), b"echo hi\n")
        self.assertNotIn(",", text)  # QEMU's option syntax would split it there.

    def test_command_runs_the_checks_with_the_entry_arguments(self):
        cmd = boot_iso.guest_command(["root=live:CDLABEL=Lumen-Live", "rd.live.image", "rd.live.check", "quiet"])
        line, rest = cmd.split(";", 1)
        self.assertEqual(shlex.split(line), [
            "bash", "/run/credentials/@system/lumen.live-check",
            "root=live:CDLABEL=Lumen-Live rd.live.image rd.live.check quiet", "--media-check"])
        self.assertTrue(cmd.endswith("\r"))
        # The echoed command must not look like the end of the checks.
        self.assertNotRegex(cmd, boot_iso.DONE)
        self.assertNotRegex(cmd, boot_iso.BEGIN)
        self.assertNotIn("--media-check", boot_iso.guest_command(["rd.live.image"]))

    def test_guest_script_prints_the_begin_marker(self):
        script = boot_iso.GUEST_SCRIPT.read_text()
        self.assertIn("printf 'LUMEN-CHECKS-BEGIN\\n'", script)

    def test_report_counts_the_guest_lines(self):
        report = boot_iso.Report(0, "Try")
        report.step(True, "menu")
        report.guest("  PASS  a\n  FAIL  b\n        why\n  INFO  x: y\n\nPassed: 1   Failed: 1\n", 1)
        self.assertEqual((report.passes, report.failures), (2, 1))
        self.assertEqual(report.lines, ["  PASS  menu", "  PASS  a", "  FAIL  b", "        why", "  INFO  x: y"])

    def test_report_fails_a_bad_status_without_a_failed_check(self):
        report = boot_iso.Report(0, "Try")
        report.guest("Usage: ...\n", 2)
        self.assertEqual(report.failures, 1)


class QemuTest(unittest.TestCase):
    FIRMWARE = boot_iso.Firmware("x.json", "/fw/CODE.fd", "raw", "/fw/VARS.fd", "raw")

    def test_command(self):
        cmd = boot_iso.qemu_command(self.FIRMWARE, "/out/vars.fd", True, "/r/serial", "/r/qmp", ["/r/cred"],
                                    cdrom="/iso/lumen.iso")
        joined = " ".join(cmd)
        self.assertIn("q35,smm=on,accel=kvm", joined)
        self.assertIn("driver=cfi.pflash01,property=secure,value=on", joined)
        self.assertIn("if=pflash,unit=0,readonly=on,format=raw,file=/fw/CODE.fd", joined)
        self.assertIn("if=pflash,unit=1,format=raw,file=/out/vars.fd", joined)
        self.assertIn("media=cdrom,readonly=on,format=raw,file=/iso/lumen.iso", joined)
        self.assertIn("ide-cd,drive=cd,bootindex=0", joined)
        self.assertIn("-nic none", joined)
        self.assertIn("type=11,value=io.systemd.credential:getty.ttys.serial=ttyS0", joined)
        self.assertIn("type=11,path=/r/cred", joined)
        self.assertNotIn("virtio-blk", joined)
        self.assertEqual(cmd.count("-serial"), 1)
        self.assertEqual(cmd[-2:], ["-no-reboot", "-S"])
        self.assertIn("accel=tcg", " ".join(boot_iso.qemu_command(self.FIRMWARE, "v", False, "s", "q", ["c"])))

    def test_disk_logs_and_reboot(self):
        # The install: the CD boots first, then the disk; a second serial port for the logs.
        cmd = boot_iso.qemu_command(self.FIRMWARE, "v", True, "s", "q", ["/r/a", "/r/b"], cdrom="/iso/l.iso",
                                    disk="/d/lumen.raw", logs="/out/anaconda.log")
        joined = " ".join(cmd)
        self.assertIn("id=disk,format=raw,discard=unmap,file=/d/lumen.raw", joined)
        self.assertIn("virtio-blk-pci,drive=disk,bootindex=1", joined)
        self.assertIn("file,id=logs,path=/out/anaconda.log", joined)
        self.assertEqual(cmd.count("-serial"), 2)
        self.assertIn("type=11,path=/r/a", joined)
        self.assertIn("type=11,path=/r/b", joined)
        # The installed system: the disk alone, and a reboot restarts the VM.
        cmd = boot_iso.qemu_command(self.FIRMWARE, "v", True, "s", "q", [], disk="/d/lumen.raw", reboot=True)
        joined = " ".join(cmd)
        self.assertNotIn("cdrom", joined)
        self.assertIn("virtio-blk-pci,drive=disk,bootindex=0", joined)
        self.assertNotIn("-no-reboot", cmd)
        self.assertEqual(cmd[-1], "-S")


class ScreenshotTest(unittest.TestCase):
    def test_ppm_to_png(self):
        pixels = bytes(range(18))  # 3 x 2, RGB
        png = boot_iso.ppm_to_png(b"P6\n3 2\n255\n" + pixels)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        chunks, i = {}, 8
        while i < len(png):
            length, kind = struct.unpack(">I4s", png[i:i + 8])
            data = png[i + 8:i + 8 + length]
            self.assertEqual(struct.unpack(">I", png[i + 8 + length:i + 12 + length])[0], zlib.crc32(kind + data))
            chunks[kind] = data
            i += 12 + length
        self.assertEqual(struct.unpack(">IIBBBBB", chunks[b"IHDR"]), (3, 2, 8, 2, 0, 0, 0))
        self.assertEqual(zlib.decompress(chunks[b"IDAT"]), b"\0" + pixels[:9] + b"\0" + pixels[9:])
        self.assertIn(b"IEND", chunks)

    def test_rejects_what_is_not_ppm(self):
        for bad in (b"P5\n1 1\n255\n\0", b"P6\n2 2\n255\n\0\0\0", b"P6\n1 1\n65535\n\0\0\0\0\0\0"):
            with self.assertRaises(ValueError):
                boot_iso.ppm_to_png(bad)


class ConsoleTest(unittest.TestCase):
    def setUp(self):
        self.vm_side, ours = socket.socketpair()
        self.log = io.BytesIO()
        self.console = boot_iso.Console(ours, self.log)

    def tearDown(self):
        self.vm_side.close()
        self.console.sock.close()

    def test_plain_drops_escapes(self):
        grub = "\x1b[0m\x1b[30m\x1b[47m\x1b[2;3H*Try or install Lumen OS\x1b[K\r\n\x1b(B\x1b[?25l"
        self.assertEqual(boot_iso.plain(grub), "*Try or install Lumen OS\n")

    def test_expect_moves_the_mark(self):
        self.vm_side.sendall(b"\x1b[1;1HFedora\r\nlocalhost-live login: ")
        m = self.console.expect(r"login: *\Z", 5)
        self.assertIsNotNone(m)
        self.vm_side.sendall(b"root\r\n[root@localhost-live ~]# ")
        self.assertTrue(self.console.expect(r"[#$] *\Z", 5))
        # The old prompt is behind the mark now.
        self.assertIsNone(self.console.expect(r"login:", 0.3))

    def test_wait_gives_up(self):
        start = time.monotonic()
        self.assertIsNone(self.console.wait(lambda text: "never" in text, 0.3))
        self.assertLess(time.monotonic() - start, 3)
        self.assertIsNone(self.console.wait(lambda text: "never" in text, 30, alive=lambda: False))

    def test_logs_what_comes_and_sends_keys(self):
        self.vm_side.sendall(b"menu")
        self.assertTrue(self.console.wait(lambda text: "menu" in text, 5))
        self.assertEqual(self.log.getvalue(), b"menu")
        self.console.type("v\r", gap=0.01)
        self.vm_side.settimeout(5)
        got = b""
        while len(got) < 2:
            got += self.vm_side.recv(10)
        self.assertEqual(got, b"v\r")


if __name__ == "__main__":
    unittest.main()
