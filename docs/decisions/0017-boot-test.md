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
- **A system with no user starts in Plasma Setup, not at the login screen.** Kinoite turns on `plasma-setup.service` (step 1.3), KDE's first-run wizard, which creates the first user. Until `/etc/plasma-setup-done` exists, it writes `/etc/plasmalogin.conf.d/99-plasma-setup.conf` before the display manager starts, and Plasma Login Manager logs its `plasma-setup` user straight into a Plasma session with the wizard. When someone completes the wizard, it runs `useradd -m -U`, creates `/etc/plasma-setup-done` and removes that file (plasma-setup at `016e3d6`, `files/plasma-setup.service.in`, `src/bootutil/bootutil.cpp`, `src/auth/authhelper.cpp`). The qcow2 has no user, so the first run of this test, image run 41253258219, found the `plasma-setup` session on `seat0` and no greeter after 4 minutes. That is the screen a newly installed Lumen shows: the install test's installer creates no user either, and Welcome takes Plasma Setup's place at step 6.5.
- **mcelog fails on AMD processors.** Kinoite turns on `mcelog.service`. mcelog supports no AMD processor since family 16 (2008) and no Hygon one: it prints "mcelog does not support this processor. Please use the edac_mce_amd module instead" and exits with an error (`mcelog.c`, at `90d5875`). Its unit skips itself only if `edac_mce_amd` is loaded, which isn't so in a VM, nor on every AMD PC. So the install test's installed system and the ISO's live session listed `mcelog.service` as failed on the runners with AMD processors, and not on one with an Intel one (steps 1.8b-3 to 1.8e).

## Decision

1. **`tests/boot/boot_disk.py` boots the qcow2** in the ISO tests' VM (q35, Fedora's UEFI firmware with Secure Boot on and Microsoft's keys, no network), with its writes going to a snapshot. `build-image.yml` runs it right after the qcow2's read-only check, on every build, and keeps its logs as the `boot-qcow2` artifact.
2. **The checks come in as credentials:** `tests/boot/booted-disk.sh` as `lumen.boot-check`, a service that runs it as `systemd.extra-unit.lumen-boot-check.service`, and a drop-in that makes `multi-user.target` start it. The service writes its report to the VM's second serial port. Nothing is added to the image, and nobody logs in.
3. **The disk boots twice**, as a new system does. The first boot must come to Plasma Setup within 60 seconds of the kernel's start: Plasma Login Manager as the display manager, active, and a Wayland session of the `plasma-setup` user on `seat0` that started within the budget. Then the checks finish Plasma Setup as its wizard does (a user made with `useradd -m -U`, `/etc/plasma-setup-done`, the autologin file removed) and restart the system; the snapshot keeps what the first boot wrote. The second boot must come to the login screen within 60 seconds: a Wayland greeter session. The spec's "login screen" is the screen each boot comes to, so both are held to its budget.
4. **What else it checks:** Secure Boot on and SELinux enforcing; no failed units once the system has finished starting, on both boots; the Btrfs root mounted with `compress=zstd:1` (ADR 0016); and no SELinux denial on either boot. Each boot records its screen's time, the startup time and the slowest units; the first also records the image followed, the kernel arguments, kernel lockdown, and the sleep and hibernation states offered. The budget leaves out the firmware and GRUB, which a PC's own firmware sets.
5. **`mcelog.service` skips itself on AMD and Hygon processors,** through a drop-in in the image (`/usr/lib/systemd/system/mcelog.service.d/50-lumen-cpu.conf`) whose `ExecCondition=` looks for their `vendor_id` in `/proc/cpuinfo`. A unit skipped by its condition isn't a failed one. Intel processors keep mcelog. `check-image.sh` runs the condition on stand-ins for both.

## Consequences

- Every build, branches and pull requests included, is booted to its first-run screen and then to its login screen before it can be pushed.
- When Welcome replaces Plasma Setup (step 6.5), the first boot's check and the way the test finishes the first run change with it.
- "No failed units" holds on the runners whatever their processor, and on AMD PCs, the owner's among them.
- The kernel reports machine checks on AMD processors itself (and `edac_mce_amd` where it loads), so skipping mcelog there loses nothing that mcelog would have given.
- The 60 seconds are measured from the kernel's start in a CI VM; the boot time on real hardware is for the performance budget (Phase 9).

## Follow-up

- 2026-11-01: the first run (image run 41253258219, for `5338d5e`) passed Secure Boot, SELinux, no failed units (the mcelog drop-in worked) and compression, and failed two checks: no greeter after 4 minutes, which led to Plasma Setup and the two boots (Context, Decision 3), and 18 lines of SELinux denials from bootupd, on two files image-builder's build machine left unlabeled ([ADR 0018](0018-disk-labels.md)).
- 2026-11-01: with both fixes, image run 41258990028 (for `1dc5c5d`, `dev` base `44.20261101`) **passed 10 of 10**. First boot: Plasma Setup 29 s after the kernel started (session 1, Wayland, user `plasma-setup`); startup finished in 48.9 s (3.5 s kernel, 3.3 s initrd, 42.1 s userspace), the slowest units being two that run on a first boot only, `fedora-atomic-desktop-mandb-update.service` (22.4 s, the manual pages' index) and `ldconfig.service` (11.6 s), after the screen was up. Second boot: the greeter 14 s after the kernel started (session `c1`, Wayland, user `plasmalogin`); startup 15.5 s (2.8 s, 4.0 s, 8.8 s). No failed units and no denials on either boot; the two labels are `root_t` and `boot_t`. Both boots' checks took 99 s, the step 2 minutes.
- 2026-11-01, step 1.10c: the image job makes and boots a qcow2 of the gaming edition too, with the same checks, and on its second boot checks that the login screen offers the Gamescope session ([ADR 0020](0020-gamescope-session.md)). The disk steps loop over the editions, each in a folder of its own, and check every edition even when another fails.
