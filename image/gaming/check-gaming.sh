#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check the gaming edition: what the lumen-gaming stage of image/Containerfile
# adds to the lumen image is in place, and nothing it leaves behind is (step
# 1.10a, docs/decisions/0019-gaming-edition.md).
#
# Usage: bash check-gaming.sh MULTILIB_PY
#
# The lumen-gaming stage runs this inside the image it is building, after
# image/check-image.sh and just before `bootc container lint`, with the path of
# image/multilib.py. Exits 0 when every check passes, 1 otherwise, which stops
# the build.

set -u

if (($# != 1)) || [[ ! -f $1 ]]; then
  printf 'Usage: %s MULTILIB_PY\n' "${0##*/}" >&2
  exit 2
fi
readonly multilib=$1

# Checking the image must not change it (image/Containerfile).
export PYTHONDONTWRITEBYTECODE=1

# What the edition adds (image/gaming/packages.toml).
readonly PACKAGES=(steam steam-devices gamescope mangohud gamemode)

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

packages() {
  local name status=0
  for name in "${PACKAGES[@]}"; do
    rpm --query --quiet "$name" || {
      printf '%s is not installed\n' "$name"
      status=1
    }
  done
  # Steam is RPM Fusion's build, signed with its nonfree key, whose
  # fingerprint ends in 9484 3C65 (image/gaming/keys.sha256 pins the key).
  local signature
  signature=$(rpm --query --queryformat '%{RSAHEADER:pgpsig}' steam 2>&1)
  if [[ ${signature,,} != *94843c65* ]]; then
    printf "steam isn't signed with RPM Fusion's nonfree key: %s\n" "$signature"
    status=1
  fi
  return "$status"
}

# steam-devices gives controllers' device files to the user at the seat, so
# Steam reads them without root (spec: "controller udev rules").
controller_rules() {
  local rules=()
  mapfile -t rules < <(rpm --query --list steam-devices | grep -E '^/usr/lib/udev/rules\.d/[^/]+\.rules$')
  if ((${#rules[@]} == 0)); then
    printf 'steam-devices installs no udev rules in /usr/lib/udev/rules.d\n'
    return 1
  fi
  if ! grep -qs 'uaccess' "${rules[@]}"; then
    printf 'No uaccess tag in %s\n' "${rules[*]}"
    return 1
  fi
}

# Every 32-bit package is the build of its 64-bit twin in the image, so Steam's
# 32-bit Mesa is the image's Mesa (image/multilib.py).
same_32bit_builds() {
  local count
  count=$(rpm --query --all --queryformat '%{ARCH}\n' | grep -cx i686)
  if ((count < 40)); then
    printf 'Only %d 32-bit packages: Steam needs some forty\n' "$count"
    return 1
  fi
  python3 "$multilib" check
}

# The stage turns RPM Fusion's repositories on for one step only, so the image
# keeps none.
no_repository_left() {
  local found
  found=$(grep -lis rpmfusion /etc/yum.repos.d/*.repo)
  if [[ -n $found ]]; then
    printf 'An RPM Fusion repository is still configured: %s\n' "$found"
    return 1
  fi
}

# os-release names the edition (image/os-release.sh).
os_release() {
  local want status=0
  for want in 'VARIANT_ID=gaming' 'VARIANT="Gaming"' 'IMAGE_ID=lumen-gaming'; do
    if ! grep -qxF -- "$want" /usr/lib/os-release; then
      printf '/usr/lib/os-release has no line %s\n' "$want"
      status=1
    fi
  done
  return "$status"
}

# Steam, Gamescope and MangoHud can start: their programs are there and find
# every library they link.
programs() {
  local program status=0 missing
  for program in /usr/bin/steam /usr/bin/gamescope /usr/bin/mangohud /usr/bin/gamemoded; do
    if [[ ! -x $program ]]; then
      printf '%s is missing\n' "$program"
      status=1
      continue
    fi
    # steam and mangohud are scripts, for which ldd finds nothing to check.
    missing=$(ldd "$program" 2>&1 | grep -F 'not found')
    if [[ -n $missing ]]; then
      printf '%s:\n%s\n' "$program" "$missing"
      status=1
    fi
  done
  return "$status"
}

printf 'Lumen gaming edition checks\n'
check "Steam (RPM Fusion's), steam-devices, Gamescope, MangoHud and GameMode are installed" packages
check "Controller udev rules give the devices to the user at the seat" controller_rules
check "Every 32-bit package is the build of its 64-bit twin" same_32bit_builds
check "No RPM Fusion repository is left in the image" no_repository_left
check "os-release names the gaming edition" os_release
check "Steam, Gamescope, MangoHud and GameMode's programs are in place" programs

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
((failures == 0))
