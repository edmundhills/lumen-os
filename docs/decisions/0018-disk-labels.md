<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0018. Correct two SELinux labels on the qcow2 that image-builder makes

- Status: **Accepted** (2026-11-01), at step 1.9, the owner's choice of fix.
- Deciders: the owner, on the lead engineer's (Claude) recommendation.

## Context

The first run of the qcow2's boot test (image run 41253258219, ADR 0017) found 18 lines of SELinux denials, all from `bootupctl` in `bootloader-update.service`, which runs at every boot:

- `getattr`, `read` and `open` on `/sysroot/.bootc-aleph.json`, labeled `default_t`;
- `read`, `open` and `getattr` on `/boot/bootupd-state.json`, labeled `unlabeled_t`.

Each was logged with `permissive=1`: Fedora's policy runs bootupd in a permissive domain, so nothing was refused. A system installed from the ISO has neither denial (the install test's last run, `iso` run 41232677119, counted 0). What the sources say, read on 2026-11-01:

- **Neither tool labels these files.** bootc writes its record of the install, `.bootc-aleph.json`, at the top of the root filesystem with `atomic_replace_with` (`crates/lib/src/install/aleph.rs`, at `709dfe5`); bootupd writes its state to `/boot/bootupd-state.json` (`src/backend/statefile.rs`, at `a100a09`). Where SELinux is on, the kernel labels a new file from its folder, as in the ISO's installer.
- **image-builder runs them where SELinux is off.** It runs `bootc install to-filesystem` on its build machine, GitHub's Ubuntu runners here. Since September 2026 it labels the two mount points before (`genMountpointSELinuxStages` in `pkg/manifest/raw_bootc.go`, which 88.0.0 has), but files created afterwards get no label from the kernel.
- **Fedora's policy has no line for bootc's file.** It gives `root_t` to the older `/sysroot/.aleph-version.json` and `boot_t` to `/boot/.*` (`policy/modules/kernel/files.fc`, at `8a22f44`). So a relabel by the policy gives `.bootc-aleph.json` `default_t`, which bootupd may not read.

## Decision

1. **CI gives the two files their labels** after image-builder makes the qcow2: `image/label-disk.sh` attaches a raw copy of the disk, mounts `/boot` and the root filesystem read-write, and `image/disk.py label` sets `system_u:object_r:boot_t:s0` on `/boot/bootupd-state.json` and `system_u:object_r:root_t:s0` on `.bootc-aleph.json` at the top of the root (`/sysroot` in the booted system), as the policy labels the older record. It fails if either file is missing.
2. **`image/check-disk.sh` checks both labels** on every qcow2, with the other disk checks.
3. **The boot test starts the qcow2 made again from the labeled disk**, in the same workflow step, so the disk CI tests is the one it checked.
4. **The image doesn't change.** Systems installed from the ISO already get these labels from the kernel.

## Consequences

- The qcow2's boot test holds "no SELinux denials" with no exception.
- Disks that other people make from a Lumen image with image-builder, on a machine without SELinux, still get the two benign denials until the tools or the policy change upstream. A line for `/sysroot/\.bootc-aleph\.json` in Fedora's policy, or labels from bootc and bootupd, would fix it there; reporting it upstream is the owner's call.
- The qcow2 CI keeps is image-builder's disk plus these two labels, converted back by `qemu-img`.
