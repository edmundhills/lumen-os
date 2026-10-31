# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# What the installer installs (step 1.8c, docs/decisions/0014-install-from-the-iso.md).
# The live stage of image/Containerfile installs this file as
# /usr/share/anaconda/interactive-defaults.ks, in place of Anaconda's own,
# which has no commands. Anaconda reads it whenever it runs from the live
# session (liveinst), and only it: there, Anaconda ignores any other
# kickstart.
#
# bootc installs the Lumen build that the ISO carries in its own container
# storage, under this name (image/make-iso.sh puts it there), so the install
# needs no network. The installed system then follows the same name on
# ghcr.io for its updates. bootc reads Lumen's install settings from the live
# system (/usr/lib/bootc/install/20-lumen.toml), which make it record the image
# as ostree-image-signed: every update must carry Lumen's signature (ADR 0008).
# The name in --source-imgref must stay the same as --target-imgref:
# image/iso.py reads it from here.
bootc --source-imgref=containers-storage:ghcr.io/edmundhills/lumen:dev --target-imgref=ghcr.io/edmundhills/lumen:dev

# Btrfs compression in the running system (step 1.8e,
# docs/decisions/0016-btrfs-compression.md). The installer mounts a Btrfs
# root with compress=zstd:1 while it installs (installer/anaconda/lumen.conf),
# but bootc gives the new system's kernel only rootflags=subvol=/root. On a
# Btrfs root, add rootflags=compress=zstd:1 to its kernel arguments; systemd
# joins the two. A root of another file system, which Custom can make, gets
# nothing, so it still boots. /mnt/sysimage is the disk's root as Anaconda
# mounts it for an ostree system (conf.target.physical_root). ostree writes
# the new arguments as a new boot entry on /boot, which bootc leaves mounted
# read-only when it finishes, so it is made writable first.
%post --nochroot --erroronfail
set -eu
physroot=/mnt/sysimage
test -d "$physroot/ostree/deploy"
if [ "$(findmnt --noheadings --output FSTYPE --target "$physroot")" = btrfs ]; then
    if mountpoint -q "$physroot/boot"; then
        mount -o remount,rw "$physroot/boot"
    fi
    ostree admin --sysroot="$physroot" instutil set-kargs --merge --append=rootflags=compress=zstd:1
fi
%end

# The new system mounts its root through its kernel arguments, as a composefs
# view, so a "/" line in /etc/fstab, which Anaconda writes, can't be applied
# and makes systemd-remount-fs.service fail (ADR 0011, ADR 0016). This runs in
# the new system.
%post --erroronfail
sed -E -i '/^[^#[:space:]]+[[:space:]]+\/[[:space:]]/d' /etc/fstab
%end
