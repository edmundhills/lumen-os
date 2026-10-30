#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The checks inside the live session that tests/boot/boot_iso.py boots from
# the install ISO (step 1.8b-3). The VM's firmware tables carry this script as
# the systemd credential lumen.live-check, and boot_iso.py runs it as root on
# the serial port:
#
#   bash /run/credentials/@system/lumen.live-check ARGS [--media-check]
#
#   ARGS           The kernel arguments of the menu entry it booted, from
#                  image/live/iso.yaml, as one string.
#   --media-check  The entry checks the USB first (rd.live.check).
#
# It waits up to 5 minutes for the live user's Plasma, and 30 seconds more for
# the session to settle, before it reads the journal and the audit log for
# SELinux denials. Prints LUMEN-CHECKS-BEGIN first, which boot_iso.py waits
# for. Exits 0 when every check passes, 1 when one fails, and 2 on a usage
# error.

set -u

printf 'LUMEN-CHECKS-BEGIN\n'
if (($# < 1 || $# > 2)) || [[ $# == 2 && $2 != --media-check ]]; then
  printf 'Usage: %s ARGS [--media-check]\n' "${0##*/}" >&2
  exit 2
fi
readonly want_args=$1 media_check=${2:-}

work=$(mktemp -d)
readonly work
# The trap below runs it, which shellcheck doesn't see.
# shellcheck disable=SC2329
cleanup() { rm -rf "$work"; }
trap cleanup EXIT

passes=0 failures=0

# check NAME FUNCTION: run one check, and show its output only if it fails:
# its first 40 lines, as image/check-iso.sh does.
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

# info NAME VALUE: something the boot test records without judging it.
info() { printf '  INFO  %s: %s\n' "$1" "${2:-none}"; }

# The firmware started the system with Secure Boot on. Its SecureBoot
# variable holds 4 bytes of attributes, then 1 for on.
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

# The kernel started with exactly the arguments of the menu entry, less the
# one GRUB adds (BOOT_IMAGE), so this is the entry boot_iso.py meant, as
# iso.yaml has it.
command_line() {
  local arg have=() got=()
  read -r -a have </proc/cmdline
  for arg in "${have[@]}"; do
    [[ $arg == BOOT_IMAGE=* ]] || got+=("$arg")
  done
  if [[ ${got[*]} != "$want_args" ]]; then
    printf 'The kernel started with "%s", not "%s" as the menu entry says\n' "${got[*]}" "$want_args"
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

# "Check this USB": dracut ran checkisomd5 on the ISO in the initramfs, as the
# service checkisomd5@<device>, and it finished. A failed check stops the boot,
# and only Esc on the screen's keyboard, which nothing presses here, ends it
# early with success. journald keeps the initramfs's messages.
media_check() {
  local log=$work/media-check
  journalctl --boot --no-pager --output=json --unit='checkisomd5@*' >"$log"
  if ! grep -E '"JOB_TYPE" ?: ?"start"' "$log" | grep -qE '"JOB_RESULT" ?: ?"done"'; then
    printf 'The journal has no finished media check (checkisomd5@*.service). What it has:\n'
    journalctl --boot --no-pager --output=short-monotonic --unit='checkisomd5@*' | tail -n 20
    return 1
  fi
}

# The live user's Plasma: livesys makes the user liveuser and logs it in
# through the login screen, into a Plasma (Wayland) session. Both KWin and the
# shell run, the session is the user's graphical one and active on its seat,
# and the shell still runs 30 seconds later.
plasma() {
  local deadline=$((SECONDS + 300)) shell session type state up
  until pgrep --uid liveuser --exact kwin_wayland >/dev/null && shell=$(pgrep --uid liveuser --exact plasmashell); do
    if ((SECONDS >= deadline)); then
      printf 'No KWin and Plasma shell for liveuser after 5 minutes. Its processes:\n'
      ps --user liveuser -o pid=,comm= 2>&1 | head -n 20
      loginctl list-sessions --no-pager
      return 1
    fi
    sleep 2
  done
  read -r up _ </proc/uptime
  printf '%.0f s after the kernel started\n' "$up" >"$work/plasma-time"
  session=$(loginctl show-user liveuser --property=Display --value)
  type=$(loginctl show-session "$session" --property=Type --value)
  state=$(loginctl show-session "$session" --property=State --value)
  if [[ $type != wayland || $state != active ]]; then
    printf 'The session of liveuser (%s) is %s and %s, not wayland and active\n' "$session" "$type" "$state"
    return 1
  fi
  sleep 30
  if [[ $(pgrep --uid liveuser --exact plasmashell) != "$shell" ]]; then
    printf 'The Plasma shell (process %s) stopped within 30 seconds\n' "$shell"
    return 1
  fi
}

# No SELinux denial since the system started, in the journal (which has the
# kernel's messages) or in the audit log, while auditd runs. A denial is fixed
# by labelling or policy, never by running permissive (ADR 0012).
denials() {
  {
    journalctl --boot --no-pager --output=short-monotonic | grep -E 'avc: +denied|SELINUX_ERR|type=1401'
    if [[ -s /var/log/audit/audit.log ]]; then
      ausearch --message AVC,USER_AVC,SELINUX_ERR,USER_SELINUX_ERR 2>/dev/null | grep -v '^----$'
    fi
  } >"$work/denials"
  if [[ -s $work/denials ]]; then
    printf '%d lines of SELinux denials, all of them at the end of this report. The first:\n' "$(wc -l <"$work/denials")"
    head -n 10 "$work/denials"
    return 1
  fi
}

check "Secure Boot on" secure_boot
check "The menu entry's kernel arguments" command_line
check "SELinux enforcing, targeted policy" selinux
if [[ -n $media_check ]]; then
  check "Media check passed (checkisomd5)" media_check
fi
check "The live user reaches Plasma" plasma
check "No SELinux denials" denials

info "Plasma running" "$(cat "$work/plasma-time" 2>/dev/null)"
info "Startup" "$(systemd-analyze time 2>&1 | head -n 1)"
info "Kernel lockdown" "$(cat /sys/kernel/security/lockdown 2>&1)"
info "Sleep states offered" "$(cat /sys/power/state 2>&1)"
info "Secure Boot certificates (db)" "$(mokutil --db 2>&1 | sed -n 's/.*Subject:.*CN=//p' | paste -sd ';' -)"
info "Failed units" "$(systemctl --failed --no-legend --plain | cut -d' ' -f1 | paste -sd ' ' -)"

if [[ -s $work/denials ]]; then
  printf '\nSELinux denials:\n'
  cat "$work/denials"
fi

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
((failures == 0))
