#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Build NVIDIA's kernel modules for the image's kernel (step 1.11b,
# docs/decisions/0022-nvidia-edition.md). The kmods stage of
# image/Containerfile runs this; the stage is never shipped, so its compiler
# and headers stay out of the image. sign-kmods.sh then signs the modules in a
# step of its own.
#
# Usage: bash build-kmods.sh FILES
#   FILES  where the stage mounts multilib.py, and nvidia/ with RPM Fusion's
#          repository file, its key and keys.sha256.
#
# 1. kernel-devel, and kernel-devel-matched, which akmods needs to tie it to
#    the kernel, at exactly the version of the image's kernel-core, from the
#    mirrors or Fedora's signed copies on Koji (multilib.py fetch). The mirrors
#    keep only the release's and the newest kernel's.
# 2. RPM Fusion's akmod-nvidia from its nonfree repositories, limited to
#    NVIDIA's driver, with NVIDIA's open modules forced: RPM Fusion otherwise
#    picks them by what lspci shows on the build machine.
#    akmod-nvidia goes in with its scripts off: its %post would start a build
#    at once, as root, which akmodsbuild refuses, and dnf then fails the whole
#    transaction. akmods itself builds as its own user.
# 3. akmods builds kmod-nvidia for that kernel and installs it here, unsigned.
# Writes the kernel's version to /kmods/kernel for the next step.

set -euo pipefail

if (($# != 1)); then
  printf 'Usage: %s FILES\n' "${0##*/}" >&2
  exit 2
fi
readonly files=$1
export PYTHONDONTWRITEBYTECODE=1

kver=$(rpm --query --queryformat '%{VERSION}-%{RELEASE}.%{ARCH}' kernel-core)
printf 'Building NVIDIA modules for kernel %s\n' "$kver"
mkdir -p /var/tmp/lumen-kernel-devel /kmods
devel=()
for name in kernel-devel kernel-devel-matched; do
  devel+=("$(python3 "$files/multilib.py" fetch "$name" kernel-core /var/tmp/lumen-kernel-devel | tail -n 1)")
done

(cd "$files/nvidia" && sha256sum --check --strict keys.sha256)
cp "$files/nvidia/rpmfusion-nonfree.repo" /etc/yum.repos.d/lumen-rpmfusion-nvidia.repo
printf '%%_with_kmod_nvidia_open 1\n' >/etc/rpm/macros.lumen-nvidia-open

dnf --assumeyes --setopt=install_weak_deps=False install "${devel[@]}" akmods rpmrebuild
dnf --assumeyes --setopt=install_weak_deps=False --setopt=tsflags=noscripts install akmod-nvidia
# akmods builds in /tmp and /var/tmp as its own user (as Universal Blue's
# builds make sure too).
chmod 1777 /tmp /var/tmp
if ! akmods --force --kernels "$kver" --kmod nvidia; then
  printf "akmods couldn't build kmod-nvidia for %s. Its logs:\n" "$kver" >&2
  cat /var/cache/akmods/nvidia/*.log >&2 || true
  exit 1
fi
if ! rpm --query --quiet "kmod-nvidia-$kver"; then
  printf 'akmods ran, but kmod-nvidia-%s is not installed\n' "$kver" >&2
  exit 1
fi
printf '%s\n' "$kver" >/kmods/kernel
rpm --query --list "kmod-nvidia-$kver" | grep -E '\.ko(\.xz|\.zst)?$'
