#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The image's boot test (step 1.9; spec, "Boot test"): start a build's qcow2
# in a VM with Secure Boot and check, from inside, that it reaches the login
# screen within 60 seconds with no failed units. The disk has no user, as a
# newly installed system has none, so the first boot comes to Plasma Setup,
# the first-run wizard; the checks finish it as its wizard does and restart,
# and the second boot comes to Plasma Login Manager's greeter.
#
# Usage: python3 tests/boot/boot_disk.py [--require-kvm] DISK OUT
#
#   --require-kvm  Stop if the VM can't use KVM (CI), as boot_iso.py does.
#   DISK           The disk, the qcow2 image-builder made of the build
#                  (build-image.yml), or a raw disk. The VM's writes go to a
#                  temporary snapshot, so the disk stays as it was.
#   OUT            A folder for the logs and the screenshots.
#
# The VM is boot_iso.py's: QEMU's q35 machine with Fedora's UEFI firmware,
# Secure Boot on and Microsoft's keys enrolled, and no network card. A reboot
# restarts it, and the snapshot keeps what the first boot wrote.
#
# Nobody logs in: the disk has no password for anyone. The VM's firmware
# tables carry three systemd credentials, so the image stays as it is:
# tests/boot/booted-disk.sh as lumen.boot-check; a service that runs it, as
# systemd.extra-unit.lumen-boot-check.service; and a drop-in that makes
# multi-user.target start that service, as systemd.unit-dropin
# (systemd-debug-generator, systemd 256 and later). The service writes the
# checks' report to the VM's second serial port, which this reads.
#
# Exits 0 when every check passes, 1 when one fails, and 2 when the VM can't be
# started.

import argparse
import os
import shlex
import shutil
import sys
import tempfile
import time
from pathlib import Path

import boot_iso
from boot_iso import BEGIN, CREDENTIALS, DONE, BootError, Report

HERE = Path(__file__).resolve().parent
CHECK_SCRIPT = HERE / "booted-disk.sh"
CHECK_CREDENTIAL = "lumen.boot-check"
UNIT = "lumen-boot-check.service"
# Printed by the checks before they restart the system for the second boot,
# and when the second boot's checks start. The firmware and GRUB write to the
# port in between, which the report leaves out.
FIRST_BOOT_DONE = r"LUMEN-CHECKS-FIRST-BOOT-DONE\n"
SECOND_BOOT = r"LUMEN-CHECKS-SECOND-BOOT\n"
# How long each stage may take with KVM, in seconds. On each boot the checks
# wait up to 4 minutes for the screen and 5 more for the system to finish
# starting.
TIMEOUTS = {"begin": 300, "first boot": 900, "second boot": 1200}


def check_unit():
    """Return the service that runs the checks at boot and writes their report to the second serial port."""
    return (
        "[Unit]\n"
        "Description=Lumen's boot test (tests/boot/boot_disk.py)\n"
        "\n"
        "[Service]\n"
        # simple, not oneshot: a oneshot service's start job would keep the
        # system "starting", and the checks wait for it to finish starting.
        "Type=simple\n"
        f"ExecStart=/bin/bash {CREDENTIALS}/{CHECK_CREDENTIAL}\n"
        "StandardOutput=file:/dev/ttyS1\n"
        "StandardError=inherit\n"
    )


def start_dropin():
    """Return the drop-in that makes multi-user.target start the checks."""
    return f"[Unit]\nWants={UNIT}\n"


def credentials():
    """Return the (name, data) of each credential the VM gets."""
    return [
        (CHECK_CREDENTIAL, CHECK_SCRIPT.read_bytes()),
        (f"systemd.extra-unit.{UNIT}", check_unit().encode()),
        (f"systemd.unit-dropin.multi-user.target~{UNIT.removesuffix('.service')}", start_dropin().encode()),
    ]


def disk_format(path):
    return "qcow2" if str(path).endswith(".qcow2") else "raw"


def read_report(console, report, scale, alive, first_boot_done=lambda: None):
    """Wait for the checks' report of both boots on CONSOLE, the second serial port, and take it into REPORT.

    Calls FIRST_BOOT_DONE once the first boot's checks have ended, before the restart.
    """
    started = time.monotonic()
    if not console.expect(BEGIN, TIMEOUTS["begin"] * scale, alive):
        report.step(False, f"The checks didn't start within {TIMEOUTS['begin'] * scale} s: "
                    f"did systemd take the credentials {UNIT}?")
        return False
    start = console.mark
    first = console.expect(FIRST_BOOT_DONE, TIMEOUTS["first boot"] * scale, alive)
    if not first:
        report.guest(console.text()[start:], 0)
        report.step(False, "The first boot's checks didn't finish")
        report.note("Their last lines:\n" + console.tail())
        return False
    first_boot = console.text()[start:console.mark - len(first[0])]
    first_boot_done()
    second_start = console.expect(SECOND_BOOT, TIMEOUTS["second boot"] * scale, alive) and console.mark
    done = second_start and console.expect(DONE, TIMEOUTS["second boot"] * scale, alive)
    if not done:
        report.guest(first_boot + (console.text()[second_start:] if second_start else ""), 0)
        report.step(False, "The second boot's checks didn't finish")
        report.note("Their last lines:\n" + console.tail())
        return False
    report.guest(first_boot + console.text()[second_start:console.mark - len(done[0])], int(done[1]))
    report.note(f"The checks of both boots took {time.monotonic() - started:.0f} s.")
    return True


def boot(disk, firmware, out, kvm):
    """Start DISK and return the report of its checks."""
    report = Report(0, "")
    report.title = f"The disk: {Path(disk).name}"
    scale = 1 if kvm else boot_iso.SLOWER_WITHOUT_KVM
    nvram = out / f"disk-ovmf-vars.{firmware.nvram_format}"
    shutil.copyfile(firmware.nvram, nvram)
    with tempfile.TemporaryDirectory(prefix="lumen-vm-") as run:
        serial, monitor, port = (Path(run) / name for name in ("serial", "qmp", "port"))
        paths = []
        for name, data in credentials():
            path = Path(run) / name
            path.write_text(boot_iso.credential(name, data), encoding="ascii")
            paths.append(path)
        command = boot_iso.qemu_command(firmware, nvram, kvm, serial, monitor, paths, disk=disk,
                                        disk_format=disk_format(disk), snapshot=True, port=port, reboot=True)
        with (open(out / "disk-serial.log", "wb") as serial_log, open(out / "disk-qemu.log", "wb") as qemu_log,
              open(out / "disk-checks.log", "wb") as checks_log):
            qemu_log.write(shlex.join(str(c) for c in command).encode() + b"\n\n")
            qemu_log.flush()
            vm = None
            try:
                vm = boot_iso.VM(command, (serial, monitor), serial_log, qemu_log)
                checks = boot_iso.Console(vm._connect(port), checks_log)
                vm.monitor.run("cont")

                def first_boot_done():
                    if note := vm.screenshot(out / "disk-first-boot.png"):
                        report.note(note)

                if read_report(checks, report, scale, vm.alive, first_boot_done):
                    if note := vm.screenshot(out / "disk-second-boot.png"):
                        report.note(note)
                else:
                    report.note("The serial port's last lines:\n" + vm.console.tail())
                    if note := vm.screenshot(out / "disk-failed.png"):
                        report.note(note)
            except (OSError, ValueError, BootError) as e:
                report.step(False, str(e))
            finally:
                if vm:
                    vm.stop()
    if not report.failures:
        nvram.unlink()
    return report


def main(argv):
    parser = argparse.ArgumentParser(description="Start a Lumen disk in a VM with Secure Boot and check it.")
    parser.add_argument("--require-kvm", action="store_true")
    parser.add_argument("disk", type=Path)
    parser.add_argument("out", type=Path)
    try:
        options = parser.parse_args(argv[1:])
    except SystemExit:
        return 2
    if not options.disk.is_file():
        print(f"boot_disk.py: no disk at {options.disk}", file=sys.stderr)
        return 2
    firmware = boot_iso.find_firmware()
    if not firmware:
        print(f"boot_disk.py: no UEFI firmware with Secure Boot for q35 in {boot_iso.FIRMWARE_DESCRIPTORS}",
              file=sys.stderr)
        return 2
    kvm = os.access("/dev/kvm", os.R_OK | os.W_OK)
    if options.require_kvm and not kvm:
        print("boot_disk.py: /dev/kvm is missing or can't be opened, so the VM can't use KVM", file=sys.stderr)
        return 2
    options.out.mkdir(parents=True, exist_ok=True)

    print(f"Starting {options.disk.name} with {'KVM' if kvm else 'no KVM (emulated, slow)'}, no network.")
    print(f"Firmware: {firmware.code} ({firmware.descriptor}), Secure Boot on and Microsoft's keys enrolled.\n")
    report = boot(options.disk, firmware, options.out, kvm)
    print(report.title)
    print("\n".join(report.lines))
    print(f"\nPassed: {report.passes}   Failed: {report.failures}")
    return 0 if report.failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
