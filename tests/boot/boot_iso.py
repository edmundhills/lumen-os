#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The install ISO's boot test (step 1.8b-3): boot the ISO in a VM the way a PC
# with Secure Boot on boots the USB, pick an entry of its boot menu, and check
# the live session from inside.
#
# Usage: python3 tests/boot/boot_iso.py [--require-kvm] ISO ISO_YAML OUT [ENTRY...]
#
#   --require-kvm  Stop if the VM can't use KVM (CI). Without KVM, QEMU
#                  emulates the CPU, and every wait is ten times as long.
#   ISO            The ISO, as the iso workflow made it.
#   ISO_YAML       Its label and boot menu: image/live/iso.yaml.
#   OUT            A folder for each boot's logs and screenshots.
#   ENTRY          The menu entries to boot, by number from 0. By default 0
#                  and 1: "Try or install Lumen OS" and "Check this USB, then
#                  try or install Lumen OS".
#
# The VM is QEMU's q35 machine with the UEFI firmware Fedora builds for it
# (edk2-ovmf), with Secure Boot on and Microsoft's keys enrolled, as on a PC
# sold with Windows, and the ISO in its CD drive. The firmware shows its
# console, and so GRUB's menu, on the serial port too, and reads keys from it.
# The default entry is left to start when the menu's time runs out, as it does
# for most people; another is picked with keys. Nothing in an entry is
# changed, so the kernel starts with exactly the arguments of iso.yaml.
#
# The VM's firmware tables carry two systemd credentials (SMBIOS type 11),
# which systemd reads only in a VM: getty.ttys.serial makes it start a login on
# the serial port, and lumen.live-check holds tests/boot/live-session.sh. The
# script logs in there as root, which the live session leaves without a
# password, and runs the checks, which wait for the live user's Plasma.
#
# Exits 0 when every boot passes, 1 when one fails, and 2 when the VM can't be
# started.

import argparse
import base64
import json
import os
import re
import shlex
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
GUEST_SCRIPT = HERE / "live-session.sh"
FIRMWARE_DESCRIPTORS = Path("/usr/share/qemu/firmware")
# What the firmware must do: check signatures, with Microsoft's keys already
# enrolled, and keep its variables out of the OS's reach with SMM, as PCs do.
SECURE_BOOT = {"secure-boot", "enrolled-keys", "requires-smm"}
# Firmware for confidential VMs, which boot differently.
CONFIDENTIAL = ("amd-sev", "intel-tdx")

# How long each stage may take with KVM, in seconds. The login takes longest
# for "Check this USB", which reads the whole ISO first. GRUB waits out its
# own timeout before it starts the default entry, which comes on top.
TIMEOUTS = {"menu": 120, "grub": 30, "login": 600, "shell": 180, "begin": 60, "checks": 900}
SLOWER_WITHOUT_KVM = 10

CREDENTIAL = "lumen.live-check"
# Where systemd keeps the credentials the system was given (systemd.system-credentials(7)).
CREDENTIALS = "/run/credentials/@system"
# What the checks print first, and last with their exit status. Neither is in
# the command typed, which the terminal echoes.
BEGIN = r"LUMEN-CHECKS-BEGIN\n"
DONE = r"LUMEN-CHECKS-(\d+)-DONE"

# Terminal escape sequences: CSI (colours, cursor moves), OSC, character sets,
# and the two-byte ones. The firmware and GRUB position every line with them.
ESCAPES = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[()][0-9A-Za-z]|[@-Z\\-_])")
CONTROLS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class BootError(Exception):
    pass


class Firmware:
    def __init__(self, descriptor, code, code_format, nvram, nvram_format):
        self.descriptor, self.code, self.code_format = descriptor, code, code_format
        self.nvram, self.nvram_format = nvram, nvram_format


class Menu:
    """The ISO's boot menu as iso.yaml gives it."""

    def __init__(self, default, timeout, entries):
        # entries: [(name, kernel arguments)]
        self.default, self.timeout, self.entries = default, timeout, entries


def find_firmware(directory=FIRMWARE_DESCRIPTORS):
    """Return the Secure Boot firmware for q35 that the descriptors in DIRECTORY name, or None.

    The descriptors are the JSON files edk2 packages install for QEMU's users
    (QEMU's docs/interop/firmware.json). As libvirt does, the first one in name
    order that fits wins.
    """
    for path in sorted(Path(directory).glob("*.json")):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            mapping = d.get("mapping", {})
            features = set(d.get("features", []))
            if ("uefi" not in d.get("interface-types", []) or mapping.get("device") != "flash"
                    or mapping.get("mode", "split") != "split" or not SECURE_BOOT <= features
                    or any(f.startswith(CONFIDENTIAL) for f in features)):
                continue
            if not any(t.get("architecture") == "x86_64" and any(m.startswith("pc-q35") for m in t.get("machines", []))
                       for t in d.get("targets", [])):
                continue
            code, nvram = mapping["executable"], mapping["nvram-template"]
            return Firmware(path.name, code["filename"], code.get("format", "raw"),
                            nvram["filename"], nvram.get("format", "raw"))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    return None


def load_menu(iso_yaml):
    """Return the boot menu in ISO_YAML."""
    with open(iso_yaml, encoding="utf-8") as f:
        grub = yaml.safe_load(f)["grub2"]
    # The linux line is the kernel's path, then its arguments.
    entries = [(e["name"], shlex.split(e["linux"])[1:]) for e in grub["entries"]]
    return Menu(int(grub.get("default", 0)), int(grub["timeout"]), entries)


def plain(text):
    """Return TEXT as a terminal shows it, without escape sequences and control characters."""
    return CONTROLS.sub("", ESCAPES.sub("", text))


def menu_keys(menu, number):
    """Return the keys that move GRUB's highlight from the default entry to entry NUMBER, then start it.

    'v' and '^' are GRUB's other keys for the down and up arrows: one byte
    each, which the firmware passes on as they are.
    """
    move = number - menu.default
    return ("v" * move if move > 0 else "^" * -move) + "\r"


def credential(name, data):
    """Return the SMBIOS type 11 string that gives the system the credential NAME holding DATA."""
    return f"io.systemd.credential.binary:{name}={base64.b64encode(data).decode()}"


def guest_command(args):
    """Return the line typed at the VM's root prompt, which runs the checks for an entry with ARGS."""
    media = " --media-check" if "rd.live.check" in args else ""
    return f"bash {CREDENTIALS}/{CREDENTIAL} {shlex.quote(' '.join(args))}{media}; echo LUMEN-CHECKS-$?-DONE\r"


def qemu_command(firmware, nvram, iso, kvm, serial, monitor, credential_file):
    """Return the command line that starts the VM, paused."""
    return [
        "qemu-system-x86_64",
        "-name", "lumen-boot-test",
        # SMM keeps the firmware's variables, the Secure Boot keys among them,
        # out of the OS's reach; Secure Boot firmware won't start without it.
        "-machine", f"q35,smm=on,accel={'kvm' if kvm else 'tcg'}",
        "-global", "driver=cfi.pflash01,property=secure,value=on",
        "-global", "ICH9-LPC.disable_s3=1",
        "-cpu", "host" if kvm else "max",
        "-smp", "4",
        "-m", "6144",
        "-drive", f"if=pflash,unit=0,readonly=on,format={firmware.code_format},file={firmware.code}",
        "-drive", f"if=pflash,unit=1,format={firmware.nvram_format},file={nvram}",
        "-drive", f"if=none,id=cd,media=cdrom,readonly=on,format=raw,file={iso}",
        "-device", "ide-cd,drive=cd,bootindex=0",
        "-vga", "std",
        "-display", "none",
        "-nic", "none",
        "-chardev", f"socket,id=serial,path={serial},server=on,wait=off",
        "-serial", "chardev:serial",
        "-qmp", f"unix:{monitor},server=on,wait=off",
        "-smbios", "type=11,value=io.systemd.credential:getty.ttys.serial=ttyS0",
        "-smbios", f"type=11,path={credential_file}",
        "-no-reboot",
        "-S",
    ]


def ppm_to_png(ppm):
    """Return the PNG of the binary PPM (P6) image PPM, which QEMU's screendump writes."""
    m = re.match(rb"P6\s+(\d+)\s+(\d+)\s+(\d+)\s", ppm)
    if not m or m[3] != b"255":
        raise ValueError("not an 8-bit binary PPM image")
    width, height = int(m[1]), int(m[2])
    pixels = ppm[m.end():m.end() + 3 * width * height]
    if len(pixels) != 3 * width * height:
        raise ValueError("the PPM image is cut short")
    row = 3 * width
    raw = b"".join(b"\0" + pixels[y * row:(y + 1) * row] for y in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


class Console:
    """The VM's serial port: everything it writes, logged as it comes, and the keys typed into it."""

    def __init__(self, sock, log):
        self.sock, self.log = sock, log
        self.raw = bytearray()
        self.lock = threading.Lock()
        self.closed = False
        # Waits look only at what came after the mark.
        self.mark = 0
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        while True:
            try:
                data = self.sock.recv(65536)
            except OSError:
                data = b""
            if not data:
                self.closed = True
                return
            with self.lock:
                self.raw += data
            self.log.write(data)
            self.log.flush()

    def text(self):
        with self.lock:
            raw = bytes(self.raw)
        return plain(raw.decode("utf-8", "replace"))

    def wait(self, find, timeout, alive=lambda: True):
        """Return FIND's result on the text after the mark once it has one, or None after TIMEOUT seconds or once the VM stops."""
        deadline = time.monotonic() + timeout
        while True:
            # Read before checking: what came just before the VM stopped counts.
            stopped = self.closed or not alive()
            if found := find(self.text()[self.mark:]):
                return found
            if stopped or time.monotonic() > deadline:
                return None
            time.sleep(0.2)

    def expect(self, pattern, timeout, alive=lambda: True):
        """Wait for the regular expression PATTERN, and move the mark past it."""
        start = self.mark
        m = self.wait(lambda text: re.search(pattern, text, re.MULTILINE), timeout, alive)
        if m:
            self.mark = start + m.end()
        return m

    def skip(self):
        """Move the mark to the end, so later waits see only what comes next."""
        self.mark = len(self.text())

    def type(self, keys, gap=0.0):
        """Type KEYS; with GAP, one key at a time, for the firmware, which reads the port slowly."""
        for chunk in keys if gap else [keys]:
            self.sock.sendall(chunk.encode())
            time.sleep(gap)

    def tail(self, lines=30):
        return "\n".join(self.text().splitlines()[-lines:])


class Monitor:
    """QEMU's machine protocol (QMP)."""

    def __init__(self, sock):
        self.file = sock.makefile("rw", encoding="utf-8")
        self._read()  # The greeting.
        self.run("qmp_capabilities")

    def _read(self):
        line = self.file.readline()
        if not line:
            raise BootError("QEMU closed its monitor")
        return json.loads(line)

    def run(self, command, **arguments):
        self.file.write(json.dumps({"execute": command, "arguments": arguments}) + "\n")
        self.file.flush()
        while True:
            reply = self._read()
            if "return" in reply:
                return reply["return"]
            if "error" in reply:
                raise BootError(f"QEMU's {command}: {reply['error'].get('desc', reply['error'])}")
            # Anything else is an event.


class VM:
    """One QEMU, started paused, with its serial port and monitor connected."""

    def __init__(self, command, sockets, serial_log, qemu_log):
        self.proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=qemu_log, stderr=subprocess.STDOUT)
        self.console = self.monitor = None
        try:
            serial, monitor = (self._connect(path) for path in sockets)
            self.console = Console(serial, serial_log)
            self.monitor = Monitor(monitor)
        except (OSError, ValueError, BootError):
            self.stop()
            raise

    def _connect(self, path):
        deadline = time.monotonic() + 30
        while True:
            if not self.alive():
                raise BootError(f"QEMU stopped with status {self.proc.returncode}: see its log")
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect(str(path))
                return sock
            except OSError:
                sock.close()
                if time.monotonic() > deadline:
                    raise BootError(f"QEMU didn't open {path}") from None
                time.sleep(0.2)

    def alive(self):
        return self.proc.poll() is None

    def screenshot(self, path):
        """Save what the VM's screen shows as the PNG PATH; return a note if that fails."""
        ppm = path.with_suffix(".ppm")
        try:
            self.monitor.run("screendump", filename=str(ppm))
            path.write_bytes(ppm_to_png(ppm.read_bytes()))
            return None
        except (OSError, ValueError, BootError) as e:
            return f"No screenshot {path.name}: {e}"
        finally:
            ppm.unlink(missing_ok=True)

    def stop(self):
        if self.alive() and self.monitor:
            try:
                self.monitor.run("quit")
            except (OSError, ValueError, BootError):
                pass
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()


class Report:
    """The report of one boot: its steps, each passed or failed, and what the checks inside printed."""

    def __init__(self, number, name):
        self.title = f"Entry {number}: {name}"
        self.lines, self.passes, self.failures = [], 0, 0

    def step(self, ok, text):
        self.lines.append(f"  {'PASS' if ok else 'FAIL'}  {text}")
        if ok:
            self.passes += 1
        else:
            self.failures += 1

    def note(self, text):
        self.lines.extend(f"        {line}" for line in text.splitlines())

    def guest(self, output, status):
        """Take the checks' own report: their PASS and FAIL lines count as this boot's."""
        failures = self.failures
        for line in output.splitlines():
            line = line.rstrip()
            if line.startswith("  PASS  "):
                self.passes += 1
            elif line.startswith("  FAIL  "):
                self.failures += 1
            elif not line.strip() or line.startswith("Passed: "):
                continue
            self.lines.append(line)
        if status != 0 and self.failures == failures:
            self.step(False, f"The checks inside the live session ended with status {status}")


def boot_entry(number, menu, iso, firmware, out, kvm):
    """Boot menu entry NUMBER of the ISO and return its report."""
    report = Report(number, menu.entries[number][0])
    prefix = out / f"entry-{number}"
    nvram = Path(f"{prefix}-ovmf-vars.{firmware.nvram_format}")
    shutil.copyfile(firmware.nvram, nvram)  # Each boot starts from the firmware's own settings.
    with tempfile.TemporaryDirectory(prefix="lumen-vm-") as run:
        # Kept short: a Unix socket's path may be at most 107 bytes.
        sockets = (Path(run) / "serial", Path(run) / "qmp")
        credential_file = Path(run) / "credential"
        credential_file.write_text(credential(CREDENTIAL, GUEST_SCRIPT.read_bytes()), encoding="ascii")
        command = qemu_command(firmware, nvram, iso, kvm, *sockets, credential_file)
        with open(f"{prefix}-serial.log", "wb") as serial_log, open(f"{prefix}-qemu.log", "wb") as qemu_log:
            qemu_log.write(shlex.join(command).encode() + b"\n\n")
            qemu_log.flush()
            vm = None
            try:
                vm = VM(command, sockets, serial_log, qemu_log)
                run_boot(vm, report, number, menu, 1 if kvm else SLOWER_WITHOUT_KVM, prefix)
            except (OSError, ValueError, BootError) as e:
                report.step(False, str(e))
            finally:
                if vm:
                    vm.stop()
    if not report.failures:
        nvram.unlink()
    return report


def run_boot(vm, report, number, menu, scale, prefix):
    name, args = menu.entries[number]
    console, started = vm.console, time.monotonic()

    def screenshot(shot):
        if note := vm.screenshot(Path(f"{prefix}-{shot}.png")):
            report.note(note)

    def failed(text):
        report.step(False, text)
        report.note("The serial port's last lines:\n" + console.tail())
        screenshot("failed")

    vm.monitor.run("cont")

    # GRUB's menu, with every entry of iso.yaml, through the firmware's console.
    names = [n for n, _ in menu.entries]
    if not console.wait(lambda text: all(n in text for n in names), TIMEOUTS["menu"] * scale, vm.alive):
        return failed("GRUB's menu, with the entries of iso.yaml, didn't show on the serial port")
    report.step(True, f"GRUB's menu on the serial port, {time.monotonic() - started:.0f} s after the VM started")
    screenshot("menu")
    console.skip()

    # The default entry starts by itself when the menu's time runs out, and
    # GRUB says so; another entry is picked with keys, after which GRUB starts
    # it without a word.
    if number == menu.default:
        timeout = (menu.timeout + TIMEOUTS["grub"]) * scale
        if not console.expect(re.escape(f"Booting `{name}'"), timeout, vm.alive):
            return failed(f"GRUB didn't start its default entry after {menu.timeout} s")
        report.step(True, f"GRUB starts its default entry after {menu.timeout} s")
    else:
        console.type(menu_keys(menu, number), gap=0.5)

    # A login on the serial port: systemd starts it because of the
    # getty.ttys.serial credential, so the live system has booted.
    if not console.expect(r"login: *\Z", TIMEOUTS["login"] * scale, vm.alive):
        return failed("No login prompt on the serial port")
    report.step(True, f"Login prompt on the serial port, {time.monotonic() - started:.0f} s after the VM started")

    # The live session leaves root without a password. Until livesys has run,
    # root is locked, so a login that comes too early is tried again.
    deadline = time.monotonic() + TIMEOUTS["shell"] * scale
    while True:
        console.type("root\r")
        m = console.expect(r"(Password: *\Z)|(Login incorrect)|([#$] *\Z)", 30 * scale, vm.alive)
        if m and m[1]:  # Asked for the empty password after all.
            console.type("\r")
            m = console.expect(r"(Password: *\Z)|(Login incorrect)|([#$] *\Z)", 30 * scale, vm.alive)
        if m and m[3]:
            break
        if time.monotonic() > deadline or not vm.alive():
            return failed("Could not log in as root on the serial port")
        console.expect(r"login: *\Z", 30 * scale, vm.alive)
        time.sleep(5)
    report.step(True, "Root login on the serial port")

    # The checks, from the credential the VM was given.
    console.skip()
    console.type(guest_command(args))
    if not console.expect(BEGIN, TIMEOUTS["begin"] * scale, vm.alive):
        return failed(f"The checks didn't start: is the credential {CREDENTIAL} in {CREDENTIALS}?")
    start = console.mark
    done = console.expect(DONE, TIMEOUTS["checks"] * scale, vm.alive)
    if not done:
        return failed("The checks inside the live session didn't finish")
    report.guest(console.text()[start:console.mark - len(done[0])], int(done[1]))
    screenshot("desktop")


def main(argv):
    parser = argparse.ArgumentParser(description="Boot the install ISO in a VM with Secure Boot and check its live session.")
    parser.add_argument("--require-kvm", action="store_true")
    parser.add_argument("iso", type=Path)
    parser.add_argument("iso_yaml", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("entries", type=int, nargs="*", default=[0, 1])
    try:
        options = parser.parse_args(argv[1:])
    except SystemExit:
        return 2
    try:
        menu = load_menu(options.iso_yaml)
    except (OSError, ValueError, yaml.YAMLError, KeyError, TypeError) as e:
        print(f"boot_iso.py: {options.iso_yaml}: {e}", file=sys.stderr)
        return 2
    if not options.iso.is_file():
        print(f"boot_iso.py: no ISO at {options.iso}", file=sys.stderr)
        return 2
    if bad := [n for n in options.entries if not 0 <= n < len(menu.entries)]:
        print(f"boot_iso.py: iso.yaml has {len(menu.entries)} entries, so no entry {bad[0]}", file=sys.stderr)
        return 2
    firmware = find_firmware()
    if not firmware:
        print(f"boot_iso.py: no UEFI firmware with Secure Boot for q35 in {FIRMWARE_DESCRIPTORS}", file=sys.stderr)
        return 2
    kvm = os.access("/dev/kvm", os.R_OK | os.W_OK)
    if options.require_kvm and not kvm:
        print("boot_iso.py: /dev/kvm is missing or can't be opened, so the VM can't use KVM", file=sys.stderr)
        return 2
    options.out.mkdir(parents=True, exist_ok=True)

    print(f"Booting {options.iso.name} with {'KVM' if kvm else 'no KVM (emulated, slow)'}.")
    print(f"Firmware: {firmware.code} with {firmware.nvram} ({firmware.descriptor}),")
    print("Secure Boot on and Microsoft's keys enrolled.\n")
    passes = failures = 0
    for number in options.entries:
        report = boot_entry(number, menu, options.iso, firmware, options.out, kvm)
        print(report.title)
        print("\n".join(report.lines))
        print(flush=True)
        passes, failures = passes + report.passes, failures + report.failures
    print(f"Passed: {passes}   Failed: {failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
