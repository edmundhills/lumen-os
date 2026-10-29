#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check a disk that image-builder made from a Lumen image, such as the qcow2
# for the boot test (step 1.8a, docs/decisions/0011-disk-images.md).
#
# Usage: image/check-disk.sh DISK IMAGE VERSION
#
#   DISK     The disk as a raw file, such as `qemu-img convert -O raw` makes
#            from the qcow2.
#   IMAGE    The image the installed system should follow, such as
#            ghcr.io/edmundhills/lumen:dev.
#   VERSION  The build version the system should be, such as 44.20261029.1.
#
# Run it as root: it attaches the disk read-only as a loop device and mounts
# each partition read-only, then image/disk.py checks the partition table, the
# EFI system partition, /boot and the deployment on the root filesystem.
# Nothing on the disk changes. Exits 0 when all is as it should be, 1 when
# something isn't, and 2 when the disk can't be read.

set -euo pipefail

if (($# != 3)); then
  printf 'Usage: %s DISK IMAGE VERSION\n' "${0##*/}" >&2
  exit 2
fi
readonly disk=$1 image=$2 version=$3
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
  for m in "$work"/esp "$work"/boot "$work"/root; do
    if mountpoint -q "$m"; then umount "$m"; fi
  done
  if [[ -n $loop ]]; then losetup --detach "$loop"; fi
  rm -rf "$work"
}
trap cleanup EXIT

loop=$(losetup --find --show --read-only --partscan -- "$disk")
# lsblk reads the filesystem types from udev, which needs a moment to probe the
# new partitions.
udevadm settle --timeout=30 || true
lsblk --json --bytes --tree --output PATH,TYPE,SIZE,PTTYPE,PARTTYPE,FSTYPE,LABEL -- "$loop" >"$work/lsblk.json"

status=0
python3 "$here/disk.py" partitions "$work/lsblk.json" >"$work/roles" || status=$?
((status != 2)) || exit 2

# Mount and check each partition the table check found, even when it found
# problems, so one run reports all of them. A Btrfs root is mounted at the top
# of the filesystem, which holds image-builder's subvolume for the root.
while read -r role device fstype; do
  mkdir "$work/$role"
  options=ro
  [[ $fstype != btrfs ]] || options=ro,subvolid=5
  mount -o "$options" -- "$device" "$work/$role"
  args=("$work/$role")
  [[ $role != root ]] || args+=("$image" "$version")
  result=0
  python3 "$here/disk.py" "$role" "${args[@]}" || result=$?
  ((result != 2)) || exit 2
  ((result == 0)) || status=1
done <"$work/roles"

if ((status == 0)); then
  printf '%s is a Lumen disk that follows %s, at version %s.\n' "$disk" "$image" "$version" >&2
fi
exit "$status"
