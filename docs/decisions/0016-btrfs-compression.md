<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0016. Mount the Btrfs root with compression through the kernel arguments

- Status: **Accepted** (2026-10-31), at step 1.8e.
- Deciders: lead engineer (Claude). The owner reviews it at the Phase 1 acceptance (step 1.17).

## Context

The spec asks for a "Btrfs root with compression (zstd)". Step 1.4 left compression to the installer, as a mount option: Lumen's Anaconda profile (`installer/anaconda/lumen.conf`) sets `btrfs_compression = zstd:1`. Step 1.8c's install test showed what reaches a system installed from the ISO, on 2026-10-31 (ADR 0014, Follow-up):

- Anaconda mounts the new Btrfs with `compress=zstd:1` while it installs, so what it writes is compressed.
- bootc writes the system's kernel arguments, `root=UUID=… rootflags=subvol=/root rw …`. The root file system is mounted from those in the initramfs, so it runs without compression. Btrfs takes `compress` for the whole file system at its first mount, so `/var` and the `/home` subvolume, mounted later with Anaconda's `/etc/fstab` options, run without it too.
- Anaconda's `/etc/fstab` also has a line for `/` with `subvol=root,compress=zstd:1`. On a bootc system `/` is a composefs view, not the Btrfs, so `systemd-remount-fs.service` can't apply it and fails, as ADR 0011 warned; step 1.9 needs no failed units.
- image-builder's qcow2 has the same kernel arguments and names `compress=zstd:1` only in a `-.mount` unit for `/` (ADR 0011).

What the tools do, read in their source on 2026-10-31:

- systemd's fstab generator joins every `rootflags=` on the kernel command line into one list of mount options for the root (`strextend_with_separator(&arg_root_options, ",", value)` in `src/fstab-generator/fstab-generator.c`). So `rootflags=compress=zstd:1` next to bootc's `rootflags=subvol=/root` mounts the root with both.
- A kernel argument for a file system it doesn't fit stops the system booting: ext4 and XFS refuse `compress`. The installer's Custom partitioning can give the root another file system, and bootc's `kargs.d` drop-ins, which apply to every install and update of an image, can't depend on the file system.
- `ostree admin instutil set-kargs --merge --append=…` sets the kernel arguments of an installed, not booted, system from its own plus new ones, and keeps a second value for a key it already has. Its `kargs edit-in-place --append-if-missing` doesn't: it skips any key already there, and `rootflags` is.
- image-builder 88 passes a blueprint's `[customizations.kernel] append` to bootc as kernel arguments for a bootc disk (`pkg/distro/defs/bootc_imagetype.go`).

## Decision

1. **The installer adds `rootflags=compress=zstd:1` when the new root is Btrfs.** A `%post --nochroot` section of `installer/anaconda/interactive-defaults.ks` checks the file system of the disk's root as Anaconda mounts it (`/mnt/sysimage`) and, for Btrfs, runs `ostree admin --sysroot=/mnt/sysimage instutil set-kargs --merge --append=rootflags=compress=zstd:1`. ostree writes the new arguments as a new boot entry on `/boot`, which bootc leaves mounted read-only when it finishes, so the section makes it writable first. Another root gets nothing, so it still boots. ostree carries a deployment's kernel arguments into the next one, so updates keep it.
2. **The installer leaves `/` out of the new system's `/etc/fstab`.** A `%post` section in the new system deletes the line whose mount point is `/`. bootc mounts the root from the kernel arguments; the other lines (`/boot`, `/boot/efi`, `/home`) stay.
3. **The qcow2 gets the same argument from a blueprint.** `image/disk.toml` appends it, and `build-image.yml` passes it to image-builder. The disk's root is always Btrfs (`20-lumen.toml`). `image/disk.py` fails if the boot entry's `rootflags` lack `compress=zstd:1`.
4. **The install test checks both:** the installed system's `/sysroot` is mounted with `compress=zstd:1`, and `systemd-remount-fs.service` didn't fail.

## Consequences

- Installed systems and the qcow2 compress what they write from the first boot on, on the root, `/var` and `/home`.
- Compression stays a choice of the installer, as step 1.4 meant, and of the disk's builder, not of the image: an image update can't add it to a root that can't take it.
- Whether the qcow2's `-.mount` unit for `/` makes a failed unit of its own was step 1.9's to find: it doesn't (Follow-up).
- A user who adds a `/` line to `/etc/fstab` gets the failed remount back; Health (Phase 5) can say so.

## Follow-up

- 2026-10-31: the branch's image check (run 41223616906) passed with the blueprint: the qcow2's boot entry has `rootflags=compress=zstd:1`. The first install run (`iso` run 41223626193) stopped in the first `%post`: bootc leaves `/boot` read-only, and ostree writes the new boot entry there; the section now remounts it read-write first (Decision 1). Then `iso` run 41232677119, on `dev` `44.20261031`, passed the install test 27 of 27: the installed system's kernel command line ends in `rootflags=compress=zstd:1`, `/sysroot`, `/var` and `/var/home` are mounted `compress=zstd:1`, `/etc/fstab` has no `/` line, and `systemd-remount-fs.service` didn't fail. The one failed unit left is `mcelog.service`, on the runner's CPU.
- 2026-11-01, step 1.9: the qcow2's boot test (image run 41258990028) found no failed units on either boot, so image-builder's `-.mount` unit for `/` doesn't fail, and `/sysroot` is mounted with `compress=zstd:1` ([ADR 0017](0017-boot-test.md), Follow-up).
