#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Pack the live system, the image the live stage of image/Containerfile
# builds, into the install ISO, with every file labelled for SELinux so that
# the live session runs enforcing (step 1.8b, docs/decisions/0012-install-iso.md).
#
# Usage: image/make-iso.sh IMAGE_BUILDER LIVE_IMAGE ISO
#
#   IMAGE_BUILDER  image-builder's container, by release and digest, as
#                  .github/workflows/iso.yml pins it.
#   LIVE_IMAGE     The live system, in root's container storage.
#   ISO            Where to write the ISO.
#
# image-builder's generic-iso type packs it, the way the container-native ISO
# contract says (ADR 0011), but it doesn't label the files it puts in the
# squashfs. So the script asks image-builder for its build plan, an osbuild
# manifest, adds osbuild's own SELinux stage to it with image/iso.py, and runs
# osbuild from the same container. Run it as root; it needs about 30 GB free
# in /var/tmp for osbuild's trees. Exits 0 when the ISO is written.

set -euo pipefail

if (($# != 3)); then
  printf 'Usage: %s IMAGE_BUILDER LIVE_IMAGE ISO\n' "${0##*/}" >&2
  exit 2
fi
readonly image_builder=$1 live=$2 iso=$3
here=$(dirname -- "${BASH_SOURCE[0]}")
readonly here

work=$(mktemp -d /var/tmp/lumen-iso.XXXXXX)
# The trap below runs it, which shellcheck doesn't see.
# shellcheck disable=SC2329
cleanup() { rm -rf "$work"; }
trap cleanup EXIT
mkdir "$work/output" "$work/store"

# Both run privileged and unconfined, as for the qcow2 (build-image.yml):
# osbuild mounts filesystems and loop devices, and labels files.
run() {
  podman run --rm --privileged --security-opt label=type:unconfined_t \
    --volume /var/lib/containers/storage:/var/lib/containers/storage \
    --volume "$work/output:/output" \
    --volume "$work/store:/var/cache/image-builder/store" \
    "$@"
}

run "$image_builder" manifest --bootc-ref "$live" generic-iso >"$work/output/generic-iso.json"
python3 "$here/iso.py" label "$work/output/generic-iso.json" >"$work/output/labelled.json"
run --entrypoint osbuild "$image_builder" \
  --store /var/cache/image-builder/store --output-directory /output \
  --export bootiso /output/labelled.json

mkdir -p -- "$(dirname -- "$iso")"
mv -- "$work/output/bootiso/install.iso" "$iso"
