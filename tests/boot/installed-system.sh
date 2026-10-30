#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The checks inside the system the install test installed from the ISO (step
# 1.8c, tests/boot/install_iso.py), on its first boot from the VM's disk. The
# VM's firmware tables carry this script as the systemd credential
# lumen.installed-check, and install_iso.py runs it as root on the serial port:
#
#   bash /run/credentials/@system/lumen.installed-check NAME DIGEST VERSION
#
#   NAME     The image the installer's kickstart installs, which the system
#            follows: ghcr.io/edmundhills/lumen:dev.
#   DIGEST   The digest of the ISO's copy of it, the signed build.
#   VERSION  That build's version.
#
# Prints LUMEN-CHECKS-BEGIN first, which install_iso.py waits for. Exits 0 when
# every check passes, 1 when one fails, and 2 on a usage error.

set -u

printf 'LUMEN-CHECKS-BEGIN\n'
if (($# != 3)); then
  printf 'Usage: %s NAME DIGEST VERSION\n' "${0##*/}" >&2
  exit 2
fi
readonly name=$1 digest=$2 version=$3

work=$(mktemp -d)
readonly work
# The trap below runs it, which shellcheck doesn't see.
# shellcheck disable=SC2329
cleanup() { rm -rf "$work"; }
trap cleanup EXIT

passes=0 failures=0

# check NAME FUNCTION: run one check, and show its output only if it fails:
# its first 40 lines, as tests/boot/live-session.sh does.
check() {
  local name=$1 out lines
  if out=$("$2" 2>&1); then
    passes=$((passes + 1))
    printf '  PASS  %s\n' "$name"
  else
    failures=$((failures + 1))
    printf '  FAIL  %s\n' "$name"
    [[ -n $out ]] || return 0
    lines=$(wc -l <<<"$out")
    head -n 40 <<<"$out" | sed 's/^/        /'
    ((lines <= 40)) || printf '        (and %d more lines)\n' "$((lines - 40))"
  fi
}

# info NAME VALUE: something the test records without judging it.
info() { printf '  INFO  %s: %s\n' "$1" "${2:-none}"; }

# The firmware started the system with Secure Boot on, as for the ISO
# (tests/boot/live-session.sh).
secure_boot() {
  local var=/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c value
  if [[ ! -e $var ]]; then
    printf 'The firmware has no SecureBoot variable: did the system start with UEFI?\n'
    return 1
  fi
  value=$(od --address-radix=n --format=u1 --skip-bytes=4 --read-bytes=1 "$var")
  value=${value// /}
  if [[ $value != 1 ]]; then
    printf 'Secure Boot is off: SecureBoot is %s\n' "$value"
    return 1
  fi
}

selinux() {
  local mode policy
  mode=$(getenforce)
  policy=$(sestatus | sed -n 's/^Loaded policy name: *//p')
  if [[ $mode != Enforcing || $policy != targeted ]]; then
    printf 'SELinux is %s, with the policy %s, not Enforcing with targeted\n' "$mode" "${policy:-none}"
    return 1
  fi
}

# bootc's view of the booted system, as JSON, for the checks below.
bootc_status() {
  [[ -s $work/status.json ]] || bootc status --format=json >"$work/status.json"
}

# booted FIELD...: print fields of the booted image from bootc status.
booted() {
  bootc_status || return 1
  python3 - "$work/status.json" "$@" <<'EOF'
import json
import sys

image = (json.load(open(sys.argv[1]))["status"].get("booted") or {}).get("image") or {}
for field in sys.argv[2:]:
    value = image
    for key in field.split("."):
        value = (value or {}).get(key) if isinstance(value, dict) else None
    print(value)
EOF
}

# The system follows NAME on its registry, and checks each update against the
# trust policy, which wants Lumen's signature for it (ADR 0008): bootc says
# so, and the deployment's origin file records ostree-image-signed, the
# signed transport.
follows_signed() {
  local fields origins status=0
  mapfile -t fields < <(booted image.image image.transport image.signature)
  if [[ ${fields[0]} != "$name" || ${fields[1]} != registry || ${fields[2]} != containerPolicy ]]; then
    printf 'bootc status says the system follows %s from %s, with signature checks %s; not %s from registry with containerPolicy\n' \
      "${fields[@]:0:3}" "$name"
    status=1
  fi
  origins=$(grep -h '^container-image-reference=' /sysroot/ostree/deploy/*/deploy/*.origin)
  if [[ $origins != "container-image-reference=ostree-image-signed:docker://$name" ]]; then
    printf 'The origin file records %s, not ostree-image-signed:docker://%s\n' "${origins:-nothing}" "$name"
    status=1
  fi
  return "$status"
}

# It runs the ISO's copy of the image, byte for byte: so the first update
# downloads only what changed since.
runs_the_build() {
  local fields
  mapfile -t fields < <(booted imageDigest version)
  if [[ ${fields[0]} != "$digest" || ${fields[1]} != "$version" ]]; then
    printf 'The system runs build %s, %s, not %s, %s\n' "${fields[1]}" "${fields[0]}" "$version" "$digest"
    return 1
  fi
}

# The installer laid out the disk with Lumen's install profile
# (installer/anaconda/lumen.conf): a Btrfs root, mounted with zstd
# compression (spec: "Btrfs root with compression (zstd)").
btrfs_root() {
  local found
  found=$(findmnt --noheadings --output FSTYPE,OPTIONS /sysroot)
  if [[ $found != btrfs* || $found != *compress=zstd:1* ]]; then
    printf '/sysroot is mounted as %s, not Btrfs with compress=zstd:1\n' "${found:-nothing}"
    return 1
  fi
}

check "Secure Boot on" secure_boot
check "SELinux enforcing, targeted policy" selinux
check "Follows $name, with signatures checked" follows_signed
check "Runs build $version, $digest, the ISO's copy" runs_the_build
check "Root on Btrfs with zstd compression" btrfs_root

info "bootc status" "$(bootc status 2>&1 | head -n 4 | sed 's/^ *//' | paste -sd ';' -)"
info "Kernel command line" "$(cat /proc/cmdline)"
for path in /sysroot /var /var/home /boot /boot/efi; do
  info "Mounted at $path" "$(findmnt --noheadings --output SOURCE,FSTYPE,OPTIONS "$path" 2>&1 | head -n 1)"
done
info "Home snapshots (lumen-home-snapshots.service)" \
  "$(systemctl show --property=Result,ExecMainStatus --value lumen-home-snapshots.service | paste -sd ' ' -)"
info "Startup" "$(systemd-analyze time 2>&1 | head -n 1)"
info "Kernel lockdown" "$(cat /sys/kernel/security/lockdown 2>&1)"
info "Sleep states offered" "$(cat /sys/power/state 2>&1)"
info "Failed units" "$(systemctl --failed --no-legend --plain | cut -d' ' -f1 | paste -sd ' ' -)"
journalctl --boot --no-pager --output=short-monotonic | grep -E 'avc: +denied|SELINUX_ERR' >"$work/denials"
info "SELinux denials" "$(wc -l <"$work/denials")"
if [[ -s $work/denials ]]; then
  printf '\nSELinux denials, the first 40:\n'
  head -n 40 "$work/denials"
fi

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
((failures == 0))
