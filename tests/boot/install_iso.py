#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The install test (step 1.8c, docs/decisions/0014-install-from-the-iso.md):
# install Lumen from the install ISO onto a VM's empty disk, with no network,
# the way the live session's installer does, then start the installed system
# with Secure Boot and check that it runs the ISO's copy of the image and
# follows ghcr.io/edmundhills/lumen:dev with signatures checked.
#
# Usage: python3 tests/boot/install_iso.py [--require-kvm] ISO ISO_YAML DISK OUT
#
#   --require-kvm  Stop if the VM can't use KVM (CI), as boot_iso.py does.
#   ISO            The ISO, as the iso workflow made it.
#   ISO_YAML       Its boot menu: image/live/iso.yaml.
#   DISK           Where to make the VM's disk, a sparse file of 64 GiB. It is
#                  deleted at the end, unless something failed.
#   OUT            A folder for the logs and screenshots.
#
# The VM is boot_iso.py's, QEMU's q35 machine with Secure Boot and Microsoft's
# keys and no network card, with an empty disk added. It runs twice:
#
# 1. From the ISO, through the menu's default entry. As root on the serial
#    port, tests/boot/install-live.sh checks the ISO's copy of the image and
#    adds the test's install settings (install_settings below) to the
#    installer's kickstart, after the ISO's own. Then liveinst, which the live
#    desktop's installer icon starts, runs Anaconda with its text interface in
#    place of WebUI. In a live session Anaconda reads only that kickstart and
#    waits at its summary. The test goes through the disk's screens, where the
#    kickstart has chosen everything already, as a person would, checks that
#    nothing is left to fill in, and presses b. Anaconda's logs go to the VM's second serial port, which
#    QEMU writes to OUT/install-anaconda.log. Then the VM is switched off.
# 2. From the disk, with the firmware settings of the first run, which hold the
#    boot entry the installer wrote. As root on the serial port, with the
#    test's password, tests/boot/installed-system.sh checks the system.
#
# Exits 0 when everything passes, 1 when something fails, and 2 when the test
# can't start.

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

import yaml

import boot_iso
from boot_iso import CREDENTIALS, BootError, Report, Steps

HERE = Path(__file__).resolve().parent
LIVE_SCRIPT = HERE / "install-live.sh"
INSTALLED_SCRIPT = HERE / "installed-system.sh"
LIVE_CREDENTIAL = "lumen.install"
SETTINGS_CREDENTIAL = "lumen.install-ks"
INSTALLED_CREDENTIAL = "lumen.installed-check"
DISK_SIZE = 64 * 1024**3
# The installed system's root password, which only this VM ever has: it has
# no network, and its disk is deleted.
ROOT_PASSWORD = "lumen-install-test"

# How long each stage may take with KVM, in seconds. Installing copies the
# whole image out of the live system's container storage.
TIMEOUTS = {"prepare": 300, "summary": 900, "screen": 300, "install": 3600, "quit": 300, "report": 300,
            "off": 300, "checks": 600}

# Anaconda's text interface: its summary's prompt, which it shows until
# someone presses b; [!] before a part of the summary that is left to fill
# in; and its last prompt once it has installed.
SUMMARY = r"'b' to begin installation[^\]]*\]: *\Z"
INCOMPLETE = "[!]"
INSTALLED = r"Installation complete\. Press ENTER to quit: *\Z"
# What Anaconda shows when it can't go on.
ERROR = r"Traceback \(most recent call last\)|An unknown error has occurr?ed|[Ee]rror occurred|CmdlineError"
# What the test types after liveinst, which ends once Anaconda does.
LIVEINST_DONE = r"LUMEN-INSTALL-(\d+)-DONE"
# install-live.sh's report of the ISO's copy of the image: its name, digest
# and build version.
PAYLOAD = re.compile(r"INFO  The ISO's copy: (\S+) (sha256:[0-9a-f]{64}) (\S+)\s*$", re.MULTILINE)
# How long to wait before looking at Anaconda's summary again, while parts of
# it are still being checked.
RECHECK = 10
# A part of the summary: its number, mark and title, as in " 5) [!] Root password".
SPOKE = re.compile(r"^\s*\d+\) \[[x! ]\] .*$", re.MULTILINE)
# What a part of the summary says while Anaconda is still checking it.
PROCESSING = "Processing..."
# The disk's part of the summary, left to fill in, and its number. In a live
# session the text interface applies a kickstart's partitioning only once
# someone has gone through that part's screens (Anaconda 44.30, the text
# StorageSpoke: only an automated install applies it by itself).
DESTINATION = re.compile(r"(\d+)\) \[!\] Installation Destination")
# Its screens, in order, each with its choices marked [x] and this prompt.
DESTINATION_SCREENS = ("Installation Destination", "Partitioning Options", "Partition Scheme Options")
SCREEN_PROMPT = r"'c' to continue[^\]]*\]: *\Z"


def install_settings(password=ROOT_PASSWORD):
    """Return the kickstart lines that stand in for what a person picks in the installer."""
    return textwrap.dedent(f"""\

        # The install test's settings (tests/boot/install_iso.py), after the
        # installer's own: what a person picks in the installer.
        lang en_US.UTF-8
        # Both the console keymap and the X layouts, as the installer's own
        # keyboard choice gives them. With one missing, Anaconda in a live
        # session asks the live user's desktop for its layouts, through the
        # user pkexec started it as, which the test, logged in as root, has
        # none of (Anaconda 44.30, get_missing_keyboard_configuration).
        keyboard --vckeymap=us --xlayouts=us
        timezone Etc/UTC
        # The VM's one disk, emptied and laid out by Lumen's install profile.
        ignoredisk --only-use=vda
        zerombr
        clearpart --all --initlabel
        autopart
        rootpw --plaintext {password}
        """)


def liveinst_command():
    """Return the line typed at the live session's root prompt that runs the installer as the desktop does, in text."""
    return "LIVECMD='anaconda --liveinst --text' liveinst; echo LUMEN-INSTALL-$?-DONE\r"


def guest_command(credential, *args):
    """Return the line that runs the script in CREDENTIAL with ARGS and then says it is done."""
    return f"bash {CREDENTIALS}/{credential} {shlex.join(args)}; echo LUMEN-CHECKS-$?-DONE\r"


def summary_spokes(text):
    """Return the parts of Anaconda's summary in TEXT, one line each."""
    return [m.group(0).strip() for m in SPOKE.finditer(text)]


def wait_for_summary(steps, deadline):
    """Wait for Anaconda's summary, looking again while a part of it is being checked; return (its parts, its text) or None."""
    console = steps.console
    while True:
        start = console.mark
        left = max(1, (deadline - time.monotonic()) / steps.scale)
        m = steps.expect(rf"(?P<summary>{SUMMARY})|(?P<error>{ERROR})|{LIVEINST_DONE}", left)
        if not m or not m.group("summary"):
            return steps.failed("Anaconda didn't show its summary") or None
        text = console.text()[start:console.mark]
        if PROCESSING not in text or time.monotonic() > deadline:
            return summary_spokes(text), text
        time.sleep(RECHECK)
        console.type("r\r")


def choose_destination(steps, number):
    """Go through the screens of the summary's part NUMBER, Installation Destination, taking what the kickstart chose on each."""
    console, report = steps.console, steps.report
    console.type(f"{number}\r")
    for title in DESTINATION_SCREENS:
        start = console.mark
        m = steps.expect(rf"(?P<prompt>{SCREEN_PROMPT})|(?P<error>{ERROR})", TIMEOUTS["screen"])
        if not m or not m.group("prompt"):
            return steps.failed(f"Anaconda's {title} screen didn't show")
        screen = console.text()[start:console.mark]
        chosen = [line.strip() for line in screen.splitlines() if "[x]" in line]
        if title not in screen or not chosen:
            return steps.failed(f"Anaconda's {title} screen has nothing chosen:\n{screen.strip()}")
        report.note(f"{title}: {'; '.join(chosen)}")
        console.type("c\r")
    report.step(True, "Installation Destination, with the kickstart's choice on each of its screens")
    return True


def write_credentials(folder, items):
    """Write each (name, data) in ITEMS as a credential file in FOLDER; return their paths."""
    paths = []
    for name, data in items:
        path = Path(folder) / name
        path.write_text(boot_iso.credential(name, data), encoding="ascii")
        paths.append(path)
    return paths


def run_vm(command, sockets, prefix, run):
    """Start the VM, give it to RUN(vm), and stop it; failures go to RUN's report, which RUN returns."""
    with open(f"{prefix}-serial.log", "wb") as serial_log, open(f"{prefix}-qemu.log", "wb") as qemu_log:
        qemu_log.write(shlex.join(str(c) for c in command).encode() + b"\n\n")
        qemu_log.flush()
        vm = None
        try:
            vm = boot_iso.VM(command, sockets, serial_log, qemu_log)
            return run(vm)
        finally:
            if vm:
                vm.stop()


def install(steps, menu):
    """Install from the live session; return (name, digest, version) of the ISO's copy once installed, or None."""
    report, console = steps.report, steps.console
    if not (boot_iso.start_entry(steps, menu, menu.default) and boot_iso.log_in(steps)):
        return None
    result = boot_iso.run_guest(steps, guest_command(LIVE_CREDENTIAL, "prepare"), TIMEOUTS["prepare"])
    if not result:
        return None
    report.guest(*result)
    payload = PAYLOAD.search(result[0])
    if result[1] != 0 or not payload:
        if not payload:
            report.step(False, "install-live.sh didn't report the ISO's copy of the image")
        return None

    # liveinst, with Anaconda's text interface on the serial port.
    console.skip()
    console.type(liveinst_command())
    started = steps.since()
    deadline = time.monotonic() + TIMEOUTS["summary"] * steps.scale
    if not (shown := wait_for_summary(steps, deadline)):
        return None
    report.step(True, f"Anaconda's summary (liveinst started {started})")
    if m := DESTINATION.search(shown[1]):
        if not (choose_destination(steps, m[1]) and (shown := wait_for_summary(steps, deadline))):
            return None
    spokes = shown[0]
    if not spokes or any(INCOMPLETE in s for s in spokes):
        return steps.failed("Anaconda's summary has parts left to fill in:\n" + "\n".join(spokes)) or None
    report.step(True, "Nothing left to fill in")
    report.note("\n".join(spokes))

    console.type("b\r")
    m = steps.expect(rf"(?P<done>{INSTALLED})|(?P<error>{ERROR})|{LIVEINST_DONE}", TIMEOUTS["install"])
    if not m or not m.group("done"):
        return steps.failed("Anaconda didn't finish installing: install-anaconda.log has its logs") or None
    report.step(True, f"Anaconda installed Lumen, {steps.since()}")
    console.type("\r")
    if not steps.expect(LIVEINST_DONE, TIMEOUTS["quit"]):
        return steps.failed("liveinst didn't end after Anaconda") or None

    name = payload.group(1)
    if result := boot_iso.run_guest(steps, guest_command(LIVE_CREDENTIAL, "report", name), TIMEOUTS["report"]):
        report.guest(*result)

    # Switched off from inside, so the system writes out what it holds.
    console.type("systemctl poweroff\r")
    try:
        steps.vm.proc.wait(TIMEOUTS["off"] * steps.scale)
    except subprocess.TimeoutExpired:
        return steps.failed("The live system didn't switch off") or None
    report.step(True, "The live system switched off")
    return payload.groups()


def check_installed(steps, payload):
    """Start the installed system and run installed-system.sh in it."""
    report = steps.report
    steps.vm.monitor.run("cont")
    if not (boot_iso.wait_for_login(steps, "the installed system") and boot_iso.log_in(steps, ROOT_PASSWORD)):
        return
    if result := boot_iso.run_guest(steps, guest_command(INSTALLED_CREDENTIAL, *payload), TIMEOUTS["checks"]):
        report.guest(*result)
        steps.screenshot("screen")


def run_test(menu, iso, disk, firmware, out, kvm):
    """Install, then check the installed system; return the two reports."""
    scale = 1 if kvm else boot_iso.SLOWER_WITHOUT_KVM
    live, installed = Report(0, ""), Report(0, "")
    live.title = f"Install from the ISO, with no network: {menu.entries[menu.default][0]}, then liveinst"
    installed.title = "The installed system, started from the disk"
    nvram = out / f"install-ovmf-vars.{firmware.nvram_format}"
    shutil.copyfile(firmware.nvram, nvram)  # The firmware's own settings; the installer adds a boot entry.
    with open(disk, "wb") as f:
        f.truncate(DISK_SIZE)

    payload = None
    with tempfile.TemporaryDirectory(prefix="lumen-vm-") as run:
        sockets = (Path(run) / "serial", Path(run) / "qmp")
        credentials = write_credentials(run, [(LIVE_CREDENTIAL, LIVE_SCRIPT.read_bytes()),
                                              (SETTINGS_CREDENTIAL, install_settings().encode())])
        command = boot_iso.qemu_command(firmware, nvram, kvm, *sockets, credentials, cdrom=iso, disk=disk,
                                        logs=out / "install-anaconda.log")
        prefix = out / "install-live"
        try:
            payload = run_vm(command, sockets, prefix, lambda vm: install(Steps(vm, live, prefix, scale), menu))
        except (OSError, ValueError, BootError) as e:
            live.step(False, str(e))

    if payload:
        with tempfile.TemporaryDirectory(prefix="lumen-vm-") as run:
            sockets = (Path(run) / "serial", Path(run) / "qmp")
            credentials = write_credentials(run, [(INSTALLED_CREDENTIAL, INSTALLED_SCRIPT.read_bytes())])
            # No CD now, and a reboot restarts the VM: shim may restart it once
            # to add its boot entry.
            command = boot_iso.qemu_command(firmware, nvram, kvm, *sockets, credentials, disk=disk, reboot=True)
            prefix = out / "install-installed"
            try:
                run_vm(command, sockets, prefix, lambda vm: check_installed(Steps(vm, installed, prefix, scale), payload))
            except (OSError, ValueError, BootError) as e:
                installed.step(False, str(e))
    else:
        installed.step(False, "Not started: the install didn't finish")

    if not live.failures and not installed.failures:
        nvram.unlink()
        Path(disk).unlink()
    return live, installed


def main(argv):
    parser = argparse.ArgumentParser(description="Install Lumen from the install ISO in a VM and check the result.")
    parser.add_argument("--require-kvm", action="store_true")
    parser.add_argument("iso", type=Path)
    parser.add_argument("iso_yaml", type=Path)
    parser.add_argument("disk", type=Path)
    parser.add_argument("out", type=Path)
    try:
        options = parser.parse_args(argv[1:])
    except SystemExit:
        return 2
    try:
        menu = boot_iso.load_menu(options.iso_yaml)
    except (OSError, ValueError, yaml.YAMLError, KeyError, TypeError) as e:
        print(f"install_iso.py: {options.iso_yaml}: {e}", file=sys.stderr)
        return 2
    if not options.iso.is_file():
        print(f"install_iso.py: no ISO at {options.iso}", file=sys.stderr)
        return 2
    firmware = boot_iso.find_firmware()
    if not firmware:
        print(f"install_iso.py: no UEFI firmware with Secure Boot for q35 in {boot_iso.FIRMWARE_DESCRIPTORS}",
              file=sys.stderr)
        return 2
    kvm = os.access("/dev/kvm", os.R_OK | os.W_OK)
    if options.require_kvm and not kvm:
        print("install_iso.py: /dev/kvm is missing or can't be opened, so the VM can't use KVM", file=sys.stderr)
        return 2
    options.out.mkdir(parents=True, exist_ok=True)

    print(f"Installing from {options.iso.name} with {'KVM' if kvm else 'no KVM (emulated, slow)'}, no network,")
    print(f"onto an empty disk of {DISK_SIZE // 1024**3} GiB. Firmware: {firmware.code} ({firmware.descriptor}),")
    print("Secure Boot on and Microsoft's keys enrolled.\n")
    passes = failures = 0
    for report in run_test(menu, options.iso, options.disk, firmware, options.out, kvm):
        print(report.title)
        print("\n".join(report.lines))
        print(flush=True)
        passes, failures = passes + report.passes, failures + report.failures
    print(f"Passed: {passes}   Failed: {failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
