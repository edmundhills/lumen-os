#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# CI's disk tests (steps 1.9, 1.10c and 1.11c): make a qcow2 of each edition
# with image-builder, label and check it, and boot it in a VM with Secure Boot.
# The image workflow's jobs run it, one command per step.
#
# Usage:
#   image/ci-disks.sh make EDITIONS
#   image/ci-disks.sh check EDITIONS VERSION
#   image/ci-disks.sh boot EDITIONS
#
# EDITIONS is a file with a line per edition: EDITION IMAGE NAME, such as
# "gaming localhost/lumen-gaming:ci ghcr.io/edmundhills/lumen-gaming:dev":
# the edition's short name, the image in rootful Podman's storage, and the
# name its systems follow, which image-builder's bootc records (ADR 0011).
#
#   make   image-builder makes each qcow2 in $RUNNER_TEMP/disk/<edition>, with
#          image/disk.toml's kernel argument for compression (ADR 0016).
#   check  image/label-disk.sh gives two files the SELinux labels image-builder
#          can't (ADR 0018), image/check-disk.sh checks the disk read-only,
#          against NAME and VERSION, and the labeled disk becomes the qcow2.
#   boot   tests/boot/boot_disk.py boots each qcow2 twice (ADR 0017), with its
#          logs and screenshots in $RUNNER_TEMP/boot/<edition>.
#
# Needs RUNNER_TEMP, IMAGE_BUILDER (image-builder's container, by digest),
# sudo and rootful Podman; check and boot write their reports to
# $GITHUB_STEP_SUMMARY when it is set. Every edition is tried even when
# another fails. Exits 0 when all pass, 1 when one fails, 2 on a usage error.

set -euo pipefail

usage() {
  printf 'Usage: %s make EDITIONS | check EDITIONS VERSION | boot EDITIONS\n' "${0##*/}" >&2
  exit 2
}
(($# >= 2)) || usage
readonly command=$1 editions=$2
[[ -f $editions ]] || usage
case $command in
  make | boot) (($# == 2)) || usage ;;
  check) (($# == 3)) || usage ;;
  *) usage ;;
esac
: "${RUNNER_TEMP:?}" "${IMAGE_BUILDER:?}"
readonly summary=${GITHUB_STEP_SUMMARY:-/dev/null}
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly here root=${here%/image}

# report TITLE FILE: show a report and add it to the run's summary page.
report() {
  printf '%s:\n' "$1"
  cat -- "$2"
  # The backticks are Markdown, for the run's summary page.
  # shellcheck disable=SC2016
  {
    printf '### %s\n\n```text\n' "$1"
    cat -- "$2"
    printf '```\n'
  } >>"$summary"
}

# Commands in the loops read /dev/null, so none of them eats the editions list.
make_disks() {
  # osbuild mounts the new Btrfs root, which needs the host's module.
  sudo modprobe btrfs
  local edition image name dir
  while read -r edition image name; do
    dir=$RUNNER_TEMP/disk/$edition
    mkdir -p -- "$dir"
    sudo podman tag "$image" "$name"
    sudo podman run --rm --privileged --security-opt label=type:unconfined_t \
      --volume /var/lib/containers/storage:/var/lib/containers/storage \
      --volume "$dir:/output" --volume "$root/image/disk.toml:/disk.toml:ro" \
      "$IMAGE_BUILDER" build --output-dir /output --progress verbose \
      --blueprint /disk.toml --bootc-ref "$name" qcow2 </dev/null
    sudo podman untag "$image" "$name"
    sudo find "$dir" -type f -exec ls -ls {} +
  done <"$editions"
  df -h /
}

check_disks() {
  local version=$1 edition image name dir qcow2 out result status=0
  while read -r edition image name; do
    dir=$RUNNER_TEMP/disk/$edition out=$RUNNER_TEMP/disk-report-$edition result=0
    qcow2=$(sudo find "$dir" -name '*.qcow2' -printf '%P\n')
    qemu_img() {
      sudo podman run --rm --volume "$dir:/output" --entrypoint qemu-img "$IMAGE_BUILDER" "$@" </dev/null
    }
    qemu_img convert -O raw "/output/$qcow2" /output/check.raw
    # The runner, not root, writes the reports.
    # shellcheck disable=SC2024
    sudo "$root/image/label-disk.sh" "$dir/check.raw" >"$out" 2>&1 </dev/null || result=$?
    # shellcheck disable=SC2024
    sudo "$root/image/check-disk.sh" "$dir/check.raw" "$name" "$version" >>"$out" 2>&1 </dev/null || result=$?
    if ((result == 0)); then
      qemu_img convert -O qcow2 /output/check.raw /output/labeled.qcow2
      sudo mv -- "$dir/labeled.qcow2" "$dir/$qcow2"
    else
      status=1
    fi
    sudo rm -- "$dir/check.raw"
    report "The qcow2: $edition ($image)" "$out"
  done <"$editions"
  return "$status"
}

boot_disks() {
  if [[ ! -c /dev/kvm ]]; then
    echo "::error::This runner has no /dev/kvm, so it can't run the boot test's VM at a usable speed."
    return 1
  fi
  local fedora edition name dir out qcow2 log status=0
  fedora=$(sed -n 's/^FROM //p' "$root/tests/lint/Containerfile")
  sudo podman build --quiet --build-arg "FEDORA=$fedora" --tag localhost/lumen-boot "$root/tests/boot" </dev/null
  while read -r edition _ name; do
    dir=$RUNNER_TEMP/disk/$edition out=$RUNNER_TEMP/boot/$edition log=$RUNNER_TEMP/boot-report-$edition
    qcow2=$(sudo find "$dir" -name '*.qcow2' -printf '%P\n')
    mkdir -p -- "$out"
    # The runner, not root, writes the report.
    # shellcheck disable=SC2024
    sudo podman run --rm --network=none --device /dev/kvm \
      --volume "$dir:/disk:ro" --volume "$root:/src:ro" --volume "$out:/out" \
      localhost/lumen-boot python3 /src/tests/boot/boot_disk.py --require-kvm "/disk/$qcow2" /out \
      >"$log" 2>&1 </dev/null || status=1
    report "The boot test: $edition ($name)" "$log"
  done <"$editions"
  return "$status"
}

case $command in
  make) make_disks ;;
  check) check_disks "$3" ;;
  boot) boot_disks ;;
esac
