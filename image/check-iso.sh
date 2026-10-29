#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check an install ISO that image/make-iso.sh made (step 1.8b,
# docs/decisions/0012-install-iso.md): how it boots, and the live system in it.
#
# Usage: image/check-iso.sh ISO ISO_YAML VERSION
#
#   ISO       The ISO.
#   ISO_YAML  The label and boot menu it should have: image/live/iso.yaml.
#   VERSION   The build version of the Lumen image its live system is made
#             from, such as 44.20261029.4.
#
# Run it as root inside the live system it was made from, as a privileged
# container with the ISO and the checkout mounted, so that it reads the
# labels with the live system's own setfiles and policy (iso.yml does). It
# mounts the ISO, its EFI system partition and its squashfs read-only, so
# nothing in the ISO changes. Exits 0 when every check passes, 1 when one
# fails, and 2 when the ISO can't be read.

set -u

if (($# != 3)) || [[ ! -f $1 || ! -f $2 ]]; then
  printf 'Usage: %s ISO ISO_YAML VERSION\n' "${0##*/}" >&2
  exit 2
fi
readonly iso=$1 iso_yaml=$2 version=$3
here=$(dirname -- "${BASH_SOURCE[0]}")
readonly here
# The checkout is mounted read-only.
export PYTHONDONTWRITEBYTECODE=1

work=$(mktemp -d)
readonly work
# The trap below runs it, which shellcheck doesn't see.
# shellcheck disable=SC2329
cleanup() {
  local m
  for m in "$work"/live "$work"/esp "$work"/iso; do
    if mountpoint -q "$m"; then umount "$m"; fi
  done
  rm -rf "$work"
}
trap cleanup EXIT
mkdir "$work/iso" "$work/esp" "$work/live"

if ! mount -o loop,ro -- "$iso" "$work/iso"; then
  printf 'Could not mount %s.\n' "$iso" >&2
  exit 2
fi
readonly root=$work/iso live=$work/live
label=$(blkid --output value --match-tag LABEL -- "$iso")
for image in "$root/images/efiboot.img:$work/esp" "$root/LiveOS/squashfs.img:$live"; do
  if ! mount -o loop,ro -- "${image%%:*}" "${image#*:}"; then
    printf 'Could not mount %s from the ISO.\n' "${image%%:*}" >&2
    exit 2
  fi
done

passes=0 failures=0

# check NAME FUNCTION: run one check, and show its output only if it fails.
check() {
  local name=$1 out
  if out=$("$2" 2>&1); then
    passes=$((passes + 1))
    printf '  PASS  %s\n' "$name"
  else
    failures=$((failures + 1))
    printf '  FAIL  %s\n' "$name"
    [[ -z $out ]] || printf '%s\n' "$out" | sed 's/^/        /'
  fi
}

# The label and menus of iso.yaml, no entry that turns SELinux off, and the
# files UEFI and BIOS firmware start (image/iso.py).
boot() { python3 "$here/iso.py" boot "$iso_yaml" "$root" "$label"; }

# UEFI firmware starts the copy in the ISO's EFI system partition, so it must
# hold the same boot files and menu as the ISO's own EFI folder.
esp() { diff --recursive --brief -- "$root/EFI/BOOT" "$work/esp/EFI/BOOT"; }

# The checksum implantisomd5 wrote, which "Check this USB" compares with.
media_checksum() { checkisomd5 --verbose -- "$iso"; }

# The kernel and initramfs the menus start are the live system's own.
kernel() {
  local dirs=("$live"/usr/lib/modules/*/) status=0
  if ((${#dirs[@]} != 1)); then
    printf 'The live system has %d kernels, not one\n' "${#dirs[@]}"
    return 1
  fi
  cmp -- "${dirs[0]}vmlinuz" "$root/images/pxeboot/vmlinuz" || status=1
  cmp -- "${dirs[0]}initramfs.img" "$root/images/pxeboot/initrd.img" || status=1
  return "$status"
}

# The squashfs holds the live system of the Lumen build named, with this ISO's
# settings, and SELinux set to enforcing.
live_system() {
  local status=0 release=$live/usr/lib/os-release
  grep -qx 'ID=lumen' "$release" || {
    printf '%s does not say ID=lumen\n' "${release#"$live"}"
    status=1
  }
  grep -qx "IMAGE_VERSION=$version" "$release" || {
    printf 'The live system is not build %s: %s\n' "$version" "$(grep '^IMAGE_VERSION=' "$release")"
    status=1
  }
  cmp -- "$iso_yaml" "$live/usr/lib/bootc-image-builder/iso.yaml" || status=1
  grep -qx 'SELINUX=enforcing' "$live/etc/selinux/config" || {
    printf 'The live system does not set SELINUX=enforcing\n'
    status=1
  }
  return "$status"
}

# Every file in the squashfs has the label the live system's own policy gives
# it: setfiles, asked to change nothing (-n), lists each file it would relabel.
# -m: this host's mounts don't matter, -F: compare the whole label.
selinux_labels() {
  local policy=("$live"/etc/selinux/targeted/policy/policy.*) wrong
  wrong=$(setfiles -n -v -F -m -r "$live" -c "${policy[0]}" \
    "$live/etc/selinux/targeted/contexts/files/file_contexts" "$live") || return 1
  if [[ -n $wrong ]]; then
    printf '%d files would get another label, for example:\n' "$(wc -l <<<"$wrong")"
    head -n 10 <<<"$wrong"
    return 1
  fi
}

printf 'Checking %s (%s, label %s)\n' "${iso##*/}" "$(du --apparent-size --human-readable -- "$iso" | cut -f1)" "$label"
check "Boot menus and files (image/iso.py)" boot
check "EFI system partition" esp
check "Media checksum (checkisomd5)" media_checksum
check "Kernel and initramfs" kernel
check "Live system, build $version" live_system
check "SELinux labels (setfiles)" selinux_labels

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
((failures == 0))
