#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The checks inside the system that tests/boot/boot_disk.py starts from a
# build's qcow2 (step 1.9). Nobody logs in: the disk has no password for
# anyone. The VM's firmware tables carry this script as the systemd credential
# lumen.boot-check, and carry a service that runs it and a drop-in that starts
# that service at boot, as systemd.extra-unit and systemd.unit-dropin
# credentials (systemd-debug-generator), so the image stays as it is. The
# service writes what this prints to the VM's second serial port:
#
#   bash /run/credentials/@system/lumen.boot-check
#
# It waits for the login screen, and for the system to finish starting, then
# checks it. Prints LUMEN-CHECKS-BEGIN first and LUMEN-CHECKS-<status>-DONE
# last, which boot_disk.py waits for. Exits 0 when every check passes and 1
# when one fails.

set -u

printf 'LUMEN-CHECKS-BEGIN\n'

# The spec's budget: the login screen within 60 seconds (spec, "Boot test"),
# counted from the kernel's start, so the firmware and GRUB don't count.
readonly LOGIN_BUDGET=60

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

# The login screen's session, if logind has one: Plasma Login Manager's
# greeter runs in a session of the class "greeter" (ADR 0005).
greeter_session() {
  local id _
  # read drops the spaces loginctl puts before each session's number.
  while read -r id _; do
    if [[ $(loginctl show-session "$id" --property=Class --value) == greeter &&
    $(loginctl show-session "$id" --property=State --value) =~ ^(active|online)$ ]]; then
      printf '%s\n' "$id"
      return 0
    fi
  done < <(loginctl list-sessions --no-legend)
  return 1
}

# The login screen within the budget: the display manager is Plasma Login
# Manager and active, and its greeter's session, a Wayland one, started within
# LOGIN_BUDGET seconds of the kernel. Waits up to 4 minutes for it.
login_screen() {
  local deadline=$((SECONDS + 240)) id manager type started
  until id=$(greeter_session); do
    if ((SECONDS >= deadline)); then
      printf 'No greeter session after 4 minutes. display-manager.service is %s. Sessions:\n' \
        "$(systemctl is-active display-manager.service)"
      loginctl list-sessions --no-pager
      return 1
    fi
    sleep 1
  done
  manager=$(systemctl show --property=Id --value display-manager.service)
  type=$(loginctl show-session "$id" --property=Type --value)
  # The session's start, in microseconds since the kernel started.
  started=$(loginctl show-session "$id" --property=TimestampMonotonic --value)
  printf '%d s after the kernel started (session %s, %s, user %s)\n' "$((started / 1000000))" "$id" "$type" \
    "$(loginctl show-session "$id" --property=Name --value)" >"$work/login"
  if [[ $manager != plasmalogin.service || $(systemctl is-active display-manager.service) != active ]]; then
    printf 'The display manager is %s and %s, not plasmalogin.service and active\n' "$manager" \
      "$(systemctl is-active display-manager.service)"
    return 1
  fi
  if [[ $type != wayland ]]; then
    printf 'The greeter session %s is %s, not wayland\n' "$id" "$type"
    return 1
  fi
  if ((started > LOGIN_BUDGET * 1000000)); then
    printf 'The login screen came %s, over the budget of %d s\n' "$(cat "$work/login")" "$LOGIN_BUDGET"
    return 1
  fi
}

# No failed units once the system has finished starting (spec, "Boot test").
no_failed_units() {
  local state units unit
  state=$(timeout 300 systemctl is-system-running --wait)
  units=$(systemctl --failed --no-legend --plain | cut -d' ' -f1)
  if [[ -n $units ]]; then
    printf 'The system is %s, with failed units:\n' "$state"
    for unit in $units; do
      systemctl status --no-pager --lines=8 "$unit" 2>&1 | head -n 14
    done
    return 1
  fi
  if [[ $state != running ]]; then
    printf 'The system is %s, not running, after 5 minutes\n' "${state:-not answering}"
    return 1
  fi
}

# The Btrfs root is mounted with zstd compression: the qcow2's kernel
# arguments carry rootflags=compress=zstd:1 (image/disk.toml, ADR 0016).
btrfs_compression() {
  local options
  options=$(findmnt --raw --noheadings --output OPTIONS /sysroot)
  if [[ ,$options, != *,compress=zstd:1,* ]]; then
    printf '/sysroot is mounted %s, without compress=zstd:1\n' "${options:-not at all}"
    return 1
  fi
}

# No SELinux denial since the system started, in the journal or the audit
# log, as the ISO's tests check.
no_denials() {
  {
    journalctl --boot --no-pager --output=short-monotonic | grep -E 'avc: +denied|SELINUX_ERR|type=1401'
    if [[ -s /var/log/audit/audit.log ]]; then
      ausearch --message AVC,USER_AVC,SELINUX_ERR,USER_SELINUX_ERR 2>/dev/null | grep -v '^----$'
    fi
  } >"$work/denials"
  if [[ -s $work/denials ]]; then
    printf '%d lines of SELinux denials, the first 40 at the end of this report\n' "$(wc -l <"$work/denials")"
    return 1
  fi
}

check "Secure Boot on" secure_boot
check "SELinux enforcing, targeted policy" selinux
check "The login screen within $LOGIN_BUDGET s: Plasma Login Manager's greeter" login_screen
check "No failed units" no_failed_units
check "Btrfs mounted with zstd compression" btrfs_compression
check "No SELinux denials" no_denials

info "Login screen" "$(cat "$work/login" 2>/dev/null)"
info "Startup" "$(systemd-analyze time 2>&1 | head -n 1)"
info "Follows" "$(bootc status --format=json 2>/dev/null | python3 -c 'import json,sys
i=(json.load(sys.stdin)["status"].get("booted") or {}).get("image") or {}
r=i.get("image") or {}
print(r.get("image"), r.get("transport"), r.get("signature"), i.get("version"))' 2>&1)"
info "Kernel command line" "$(cat /proc/cmdline)"
info "Kernel lockdown" "$(cat /sys/kernel/security/lockdown 2>&1)"
info "Sleep states offered" "$(cat /sys/power/state 2>&1)"
info "Hibernation modes" "$(cat /sys/power/disk 2>&1)"
info "Failed units" "$(systemctl --failed --no-legend --plain | cut -d' ' -f1 | paste -sd ' ' -)"

if [[ -s $work/denials ]]; then
  printf '\nSELinux denials, the first 40:\n'
  head -n 40 "$work/denials"
fi

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
status=$((failures == 0 ? 0 : 1))
printf 'LUMEN-CHECKS-%d-DONE\n' "$status"
((status == 0))
