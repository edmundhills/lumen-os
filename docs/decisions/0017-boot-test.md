<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0017. Boot each build's qcow2 in CI, with the checks given as credentials, and skip mcelog on AMD

- Status: **Accepted** (2026-10-31), at step 1.9.
- Deciders: lead engineer (Claude). The owner reviews it at the Phase 1 acceptance (step 1.17).

## Context

The spec's boot test: "QEMU + qcow2 from bootc-image-builder, run in CI with KVM. Boots to the login screen in under 60 s; no failed units". Step 1.9 adds it, and boots once with Secure Boot to record kernel lockdown and hibernation for ADR 0001. Facts, checked on 2026-10-31:

- CI makes a qcow2 of every build with image-builder (ADR 0011) and checks it read-only, in the build job. The runners have KVM (step 1.8b-3).
- The qcow2 has no password for any user, so a test can't log in on it, and its image must not change for the test's sake.
- systemd 256 and later turn credentials named `systemd.extra-unit.<unit>` into units and `systemd.unit-dropin.<unit>~<name>` into drop-ins (systemd-debug-generator, `process_unit_credentials`; Fedora 44 has systemd 259). QEMU passes credentials to a VM in its SMBIOS tables, as the ISO's tests already do.
- Plasma Login Manager's greeter runs in a logind session of the class `greeter` (ADR 0005), whose start logind keeps in microseconds since the kernel started (`TimestampMonotonic`).
- **mcelog fails on AMD processors.** Kinoite turns on `mcelog.service`. mcelog supports no AMD processor since family 16 (2008) and no Hygon one: it prints "mcelog does not support this processor. Please use the edac_mce_amd module instead" and exits with an error (`mcelog.c`, at `90d5875`). Its unit skips itself only if `edac_mce_amd` is loaded, which isn't so in a VM, nor on every AMD PC. So the install test's installed system and the ISO's live session listed `mcelog.service` as failed on the runners with AMD processors, and not on one with an Intel one (steps 1.8b-3 to 1.8e).

## Decision

1. **`tests/boot/boot_disk.py` boots the qcow2** in the ISO tests' VM (q35, Fedora's UEFI firmware with Secure Boot on and Microsoft's keys, no network), with its writes going to a snapshot. `build-image.yml` runs it right after the qcow2's read-only check, on every build, and keeps its logs as the `boot-qcow2` artifact.
2. **The checks come in as credentials:** `tests/boot/booted-disk.sh` as `lumen.boot-check`, a service that runs it as `systemd.extra-unit.lumen-boot-check.service`, and a drop-in that makes `multi-user.target` start it. The service writes its report to the VM's second serial port. Nothing is added to the image, and nobody logs in.
3. **What it checks:** Secure Boot on; SELinux enforcing; the login screen within 60 seconds of the kernel's start (Plasma Login Manager as the display manager, active, and a Wayland greeter session that started within the budget); no failed units once the system has finished starting; the Btrfs root mounted with `compress=zstd:1` (ADR 0016); and no SELinux denial. It records the time to the login screen, the startup time, the image followed, the kernel arguments, kernel lockdown, and the sleep and hibernation states offered. The budget leaves out the firmware and GRUB, which a PC's own firmware sets.
4. **`mcelog.service` skips itself on AMD and Hygon processors,** through a drop-in in the image (`/usr/lib/systemd/system/mcelog.service.d/50-lumen-cpu.conf`) whose `ExecCondition=` looks for their `vendor_id` in `/proc/cpuinfo`. A unit skipped by its condition isn't a failed one. Intel processors keep mcelog. `check-image.sh` runs the condition on stand-ins for both.

## Consequences

- Every build, branches and pull requests included, is booted to its login screen before it can be pushed.
- "No failed units" holds on the runners whatever their processor, and on AMD PCs, the owner's among them.
- The kernel reports machine checks on AMD processors itself (and `edac_mce_amd` where it loads), so skipping mcelog there loses nothing that mcelog would have given.
- The 60 seconds are measured from the kernel's start in a CI VM; the boot time on real hardware is for the performance budget (Phase 9).
