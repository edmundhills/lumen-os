#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Give two files on a disk that image-builder made from a Lumen image the
# SELinux labels a system installed from the ISO has (step 1.9,
# docs/decisions/0018-disk-labels.md): bootupd's state, /boot/bootupd-state.json,
# and bootc's record of the install, .bootc-aleph.json at the top of the root
# filesystem. image-builder runs bootc and bootupd on a build machine where
# SELinux is off, so the kernel labels neither, and bootupd, which reads both at
# every boot, is denied. image/disk.py's LABELS has the labels.
# Usage: image/label-disk.sh DISK
#   DISK  The disk as a raw file, such as `qemu-img convert -O raw` makes from
#         the qcow2.
# Run it as root: it attaches the disk read-write as a loop device, mounts
# /boot and the root filesystem, and sets the two labels. Nothing else on the
# disk changes. Exits 0 when both files have their labels, 1 when one doesn't
# (a file is missing), and 2 when the disk can't be read.

set -euo pipefail

if (($# != 1)); then
  printf 'Usage: %s DISK\n' "${0##*/}" >&2
  exit 2
fi
readonly disk=$1
here=$(dirname -- "${BASH_SOURCE[0]}")
readonly here
if [[ ! -f $disk ]]; then
  printf '%s is not a file.\n' "$disk" >&2
  exit 2
fi

work=$(mktemp -d)
loop=
# The trap below runs it, which shellcheck doesn't see.
# shellcheck disable=SC2329
cleanup() {
  local m
  for m in "$work"/boot "$work"/root; do
    if mountpoint -q "$m"; then umount "$m"; fi
  done
  if [[ -n $loop ]]; then losetup --detach "$loop"; fi
  rm -rf "$work"
}
trap cleanup EXIT

loop=$(losetup --find --show --partscan -- "$disk")
# lsblk reads the filesystem types from udev, which needs a moment to probe the
# new partitions.
udevadm settle --timeout=30 || true
lsblk --json --bytes --tree --output PATH,TYPE,SIZE,PTTYPE,PARTTYPE,FSTYPE,LABEL -- "$loop" >"$work/lsblk.json"

result=0
python3 "$here/disk.py" partitions "$work/lsblk.json" >"$work/roles" 2>"$work/partitions" || result=$?
if ((result != 0)); then
  cat "$work/partitions" >&2
  exit 2
fi

status=0
while read -r role device fstype; do
  [[ $role == boot || $role == root ]] || continue
  mkdir "$work/$role"
  # A Btrfs root is mounted at the top of the filesystem, which holds
  # image-builder's subvolume for the root, as image/check-disk.sh does.
  options=rw
  [[ $fstype != btrfs ]] || options=rw,subvolid=5
  mount -o "$options" -- "$device" "$work/$role"
  result=0
  python3 "$here/disk.py" label "$role" "$work/$role" || result=$?
  ((result != 2)) || exit 2
  ((result == 0)) || status=1
  umount "$work/$role"
done <"$work/roles"
exit "$status"
