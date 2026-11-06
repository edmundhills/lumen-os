#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check the NVIDIA edition: what the lumen-nvidia stage of image/Containerfile
# adds to the lumen image is in place, and what the kmods stage needed to build
# the modules isn't (step 1.11b, docs/decisions/0022-nvidia-edition.md).
#
# Usage: bash check-nvidia.sh
#
# The lumen-nvidia stage runs this inside the image it is building, after
# image/check-image.sh and just before `bootc container lint`. Exits 0 when
# every check passes, 1 otherwise, which stops the build.

set -u

kver=$(rpm --query --queryformat '%{VERSION}-%{RELEASE}.%{ARCH}' kernel-core)
readonly kver cert=/usr/share/pki/lumen/module-signing.der

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

# NVIDIA's driver is installed, and nothing that built its modules is.
packages() {
  local name status=0
  for name in "kmod-nvidia-$kver" xorg-x11-drv-nvidia xorg-x11-drv-nvidia-power xorg-x11-drv-nvidia-cuda-libs; do
    rpm --query --quiet "$name" || {
      printf '%s is not installed\n' "$name"
      status=1
    }
  done
  for name in akmod-nvidia akmods kernel-devel gcc rpmrebuild xorg-x11-drv-nvidia-kmodsrc; do
    if rpm --query --quiet "$name"; then
      printf '%s, which only the kmods stage needs, is in the image\n' "$name"
      status=1
    fi
  done
  return "$status"
}

# Each NVIDIA module is built for the image's kernel, is one of NVIDIA's open
# modules, and is signed with the key whose certificate the image carries, for
# users to enrol as a MOK (ADR 0021).
modules() {
  local signer module status=0 count=0
  if [[ ! -s $cert ]]; then
    printf '%s is missing\n' "$cert"
    return 1
  fi
  signer=$(openssl x509 -inform DER -in "$cert" -noout -subject -nameopt multiline |
    sed -n 's/^ *commonName *= //p')
  while read -r module; do
    count=$((count + 1))
    if [[ $(modinfo --field=vermagic "$module") != "$kver "* ]]; then
      printf '%s is built for %s, not %s\n' "$module" "$(modinfo --field=vermagic "$module")" "$kver"
      status=1
    fi
    if [[ $(modinfo --field=signer "$module") != "$signer" ]]; then
      printf '%s is signed by "%s", not "%s"\n' "$module" "$(modinfo --field=signer "$module")" "$signer"
      status=1
    fi
    # NVIDIA's open modules are under GPL-compatible licences, Dual MIT/GPL
    # and, for nvidia-peermem, Dual BSD/GPL; the proprietary ones say NVIDIA.
    if [[ $(modinfo --field=license "$module") != *GPL* ]]; then
      printf "%s is under %s: not one of NVIDIA's open modules\n" "$module" "$(modinfo --field=license "$module")"
      status=1
    fi
  done < <(rpm --query --list "kmod-nvidia-$kver" | grep -E '\.ko(\.xz|\.zst)?$')
  if ((count == 0)); then
    printf 'kmod-nvidia-%s holds no modules\n' "$kver"
    return 1
  fi
  if ! modinfo --set-version="$kver" nvidia >/dev/null; then
    printf "The kernel's module index doesn't list nvidia (depmod)\n"
    status=1
  fi
  return "$status"
}

# Nouveau and nova stay away from NVIDIA cards, and nouveau still loads when
# NVIDIA's module doesn't, so the desktop works before the key is enrolled
# (risk 7): the kernel arguments bootc applies, and RPM Fusion's fallback
# service, turned on, with a condition that matches them.
nouveau_fallback() {
  local kargs=/usr/lib/bootc/kargs.d/00-lumen-nvidia.toml status=0
  if ! grep -qF '"rd.driver.blacklist=nouveau,nova_core"' "$kargs" 2>/dev/null; then
    printf '%s does not keep nouveau and nova out of the initramfs\n' "$kargs"
    status=1
  fi
  if [[ $(systemctl is-enabled nvidia-fallback.service 2>&1) != enabled ]]; then
    printf 'nvidia-fallback.service is %s, not enabled\n' "$(systemctl is-enabled nvidia-fallback.service 2>&1)"
    status=1
  fi
  if ! systemctl cat nvidia-fallback.service | grep -qx 'ConditionKernelCommandLine=rd.driver.blacklist=nouveau,nova_core'; then
    printf "nvidia-fallback.service's condition no longer matches the kernel arguments\n"
    status=1
  fi
  if [[ ! -f /usr/lib/dracut/dracut.conf.d/99-nvidia-dracut.conf ]]; then
    printf 'Nothing keeps the NVIDIA modules out of the initramfs\n'
    status=1
  fi
  return "$status"
}

# What docs/nvidia-secure-boot.md asks users to run: mokutil to enrol the
# key, openssl to check its fingerprint (step 1.12a).
enrolment_tools() {
  local tool status=0
  for tool in mokutil openssl; do
    command -v "$tool" >/dev/null || {
      printf '%s is not installed\n' "$tool"
      status=1
    }
  done
  return "$status"
}

no_repository_left() {
  local found
  found=$(grep -lis rpmfusion /etc/yum.repos.d/*.repo)
  if [[ -n $found ]]; then
    printf 'An RPM Fusion repository is still configured: %s\n' "$found"
    return 1
  fi
}

# os-release names the edition: NVIDIA, or with the gaming layer on it both
# (step 1.12b).
os_release() {
  local want status=0 wants=('VARIANT_ID=nvidia' 'VARIANT="NVIDIA"' 'IMAGE_ID=lumen-nvidia')
  if grep -qx 'VARIANT_ID=gaming-nvidia' /usr/lib/os-release; then
    wants=('VARIANT_ID=gaming-nvidia' 'VARIANT="Gaming, NVIDIA"' 'IMAGE_ID=lumen-gaming-nvidia')
  fi
  for want in "${wants[@]}"; do
    if ! grep -qxF -- "$want" /usr/lib/os-release; then
      printf '/usr/lib/os-release has no line %s\n' "$want"
      status=1
    fi
  done
  return "$status"
}

printf 'Lumen NVIDIA edition checks\n'
check "NVIDIA's driver is installed, and nothing that built its modules" packages
check "The modules are NVIDIA's open ones, built for this kernel and signed with the image's certificate" modules
check "Nouveau stays away from NVIDIA cards, and loads when NVIDIA's module doesn't" nouveau_fallback
check "mokutil and openssl, which enrolling the key needs, are installed" enrolment_tools
check "No RPM Fusion repository is left in the image" no_repository_left
check "os-release names the NVIDIA edition" os_release

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
((failures == 0))
