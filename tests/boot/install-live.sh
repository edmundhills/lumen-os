#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The live session's part of the install test (step 1.8c,
# tests/boot/install_iso.py). The VM's firmware tables carry this script as the
# systemd credential lumen.install, and the test's own install settings as
# lumen.install-ks. install_iso.py runs it as root on the serial port, before
# and after it runs the installer:
#
#   bash /run/credentials/@system/lumen.install prepare
#       Checks the ISO's copy of the Lumen image and the installer's
#       kickstart, adds the test's settings to the kickstart, after the ISO's
#       own, and sends the installer's logs to the VM's second serial port.
#   bash /run/credentials/@system/lumen.install report IMAGE
#       Checks how the installer ran: bootc installed the image IMAGE from the
#       live system's container storage, and SELinux stayed enforcing, with no
#       denials.
#
# Prints LUMEN-CHECKS-BEGIN first, which install_iso.py waits for. Exits 0 when
# every check passes, 1 when one fails, and 2 on a usage error.

set -u

printf 'LUMEN-CHECKS-BEGIN\n'
if ! { (($# == 1)) && [[ $1 == prepare ]]; } && ! { (($# == 2)) && [[ $1 == report ]]; }; then
  printf 'Usage: %s prepare | report IMAGE\n' "${0##*/}" >&2
  exit 2
fi
readonly command=$1 image=${2:-}

# The installer's kickstart, which Anaconda reads in the live session, and
# the settings the test adds to it: the disk, the language and a root
# password, which a person gives the installer instead.
readonly KICKSTART=/usr/share/anaconda/interactive-defaults.ks
readonly ADDITIONS=/run/credentials/@system/lumen.install-ks
# Anaconda's logs, which the VM's second serial port carries to the test.
readonly LOGS=(/tmp/anaconda.log /tmp/program.log /tmp/storage.log /tmp/packaging.log)

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

selinux() {
  local mode
  mode=$(getenforce)
  if [[ $mode != Enforcing ]]; then
    printf 'SELinux is %s, not Enforcing\n' "$mode"
    return 1
  fi
}

# The installer may need no network: the VM has no network card, only the
# loopback interface.
no_network() {
  local links
  links=$(ip -o link show | cut -d: -f2 | tr -d ' ' | grep -vx lo)
  if [[ -n $links ]]; then
    printf 'The VM has network interfaces: %s\n' "$(paste -sd ' ' - <<<"$links")"
    return 1
  fi
}

# The image the installer's kickstart installs from container storage
# (installer/anaconda/interactive-defaults.ks).
install_name() {
  sed -n 's/^bootc .*--source-imgref=containers-storage:\([^ ]*\).*/\1/p' "$KICKSTART"
}

# The ISO's copy of the image is in the live system's container storage under
# the kickstart's name, and it is the build the live system itself is made
# from. Reading it also shows that Podman's storage works on the live
# session's overlay root, as bootc's must.
payload() {
  local found digest version own
  if [[ -z $(install_name) ]]; then
    printf '%s has no bootc command that installs from container storage:\n' "$KICKSTART"
    grep -v '^#' "$KICKSTART" | head -n 20
    return 1
  fi
  found=$(podman image inspect --format '{{.Digest}} {{index .Labels "org.opencontainers.image.version"}}' \
    "$(install_name)") || return 1
  read -r digest version <<<"$found"
  own=$(sed -n 's/^IMAGE_VERSION=//p' /usr/lib/os-release)
  printf '%s %s\n' "$digest" "$version" >"$work/payload"
  if [[ $version != "$own" ]]; then
    printf "The ISO's copy is build %s, but the live system is build %s\n" "$version" "$own"
    return 1
  fi
}

# The test's settings go after the ISO's own, which they leave as they are.
# Anaconda in the live session reads no other kickstart.
add_settings() {
  if [[ ! -s $ADDITIONS ]]; then
    printf 'The credential with the test settings, %s, is missing\n' "$ADDITIONS"
    return 1
  fi
  cat -- "$ADDITIONS" >>"$KICKSTART"
}

# Anaconda's logs, as they grow, on the second serial port, which QEMU writes
# to a file the test keeps; and, should Anaconda fail, the report of the error
# it writes (/tmp/anaconda-tb-*), once it is there.
stream_logs() {
  setsid --fork tail --lines=+1 --follow=name --retry -- "${LOGS[@]}" </dev/null >/dev/ttyS1 2>&1
  # shellcheck disable=SC2016 # The glob is the inner shell's.
  setsid --fork bash -c 'until compgen -G "/tmp/anaconda-tb-*" >/dev/null; do sleep 2; done
    sleep 3; cat /tmp/anaconda-tb-*' </dev/null >/dev/ttyS1 2>&1
}

# bootc installed the image from the live system's container storage, as
# Anaconda ran it, and the system it made follows the same name. Anaconda logs
# each program it runs ("Running... ") in program.log, and its modules send
# their logs to the journal too.
bootc_install() {
  local line
  line=$({
    grep -h 'bootc install to-filesystem' -- "${LOGS[@]}"
    journalctl --boot --no-pager --output=cat --grep 'bootc install to-filesystem'
  } 2>/dev/null | grep -- '--source-imgref' | tail -n 1)
  if [[ -z $line ]]; then
    printf "Anaconda's logs have no bootc install. The end of anaconda.log:\n"
    tail -n 30 /tmp/anaconda.log 2>&1
    return 1
  fi
  printf '%s\n' "$line" >"$work/bootc"
  if [[ $line != *"--source-imgref=containers-storage:$image "* || $line != *"--target-imgref=$image "* ]]; then
    printf 'bootc did not install %s from container storage: %s\n' "$image" "$line"
    return 1
  fi
}

# SELinux stayed enforcing all along. The kernel logs each change of mode
# ("enforcing=0 old_enforcing=1" for a switch to permissive); Fedora's liveinst
# made one while Anaconda ran, Lumen's makes none
# (docs/decisions/0015-installer-enforcing.md).
stayed_enforcing() {
  local permissive
  # grep rather than journalctl --grep, which prints "-- No entries --".
  permissive=$(journalctl --boot --no-pager --output=short-monotonic | grep 'enforcing=0 old_enforcing=1')
  if [[ -n $permissive ]]; then
    printf 'SELinux was switched to permissive since boot:\n%s\n' "$permissive"
    return 1
  fi
}

# No SELinux denial since the system started, in the journal or the audit
# log, as tests/boot/live-session.sh checks: none while the installer ran.
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

if [[ $command == prepare ]]; then
  check "SELinux enforcing in the live session" selinux
  check "No network: the VM has no network card" no_network
  check "The ISO's copy of the image, the live system's own build, is in container storage" payload
  check "The test's install settings follow the installer's kickstart" add_settings
  check "Anaconda's logs go to the second serial port" stream_logs
  info "The installer's kickstart" "$(grep '^bootc ' "$KICKSTART")"
  info "The ISO's copy" "$(install_name) $(cat "$work/payload" 2>/dev/null)"
else
  check "Anaconda ran bootc install from the ISO's container storage" bootc_install
  check "SELinux stayed enforcing while the installer ran" stayed_enforcing
  check "SELinux enforcing once the installer has ended" selinux
  check "No SELinux denials, the installer's included" no_denials
  info "bootc install, as Anaconda ran it" "$(sed 's/^.*\(bootc install\)/\1/' "$work/bootc" 2>/dev/null)"
  info "SELinux mode changes since boot" \
    "$(journalctl --boot --no-pager --grep 'enforcing=[01] old_enforcing=[01]' 2>/dev/null | grep -c 'old_enforcing')"
  if [[ -s $work/denials ]]; then
    printf '\nSELinux denials, the first 40:\n'
    head -n 40 "$work/denials"
  fi
fi

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
((failures == 0))
