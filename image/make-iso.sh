#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Pack the live system, the image the live stage of image/Containerfile
# builds, into the install ISO, with every file labelled for SELinux so that
# the live session runs enforcing (step 1.8b, docs/decisions/0012-install-iso.md),
# and with the Lumen build the installer installs in the live system's
# container storage, so that installing needs no network (step 1.8c,
# docs/decisions/0014-install-from-the-iso.md).
#
# Usage: image/make-iso.sh IMAGE_BUILDER LIVE_IMAGE PAYLOAD ISO
#
#   IMAGE_BUILDER  image-builder's container, by release and digest, as
#                  .github/workflows/iso.yml pins it.
#   LIVE_IMAGE     The live system, in root's container storage.
#   PAYLOAD        The Lumen build the installer installs, in root's container
#                  storage under the name the installer's kickstart gives it
#                  (`image/iso.py install-image installer/anaconda/interactive-defaults.ks`).
#                  The live system holds it under the same name.
#   ISO            Where to write the ISO.
#
# image-builder's generic-iso type packs it, the way the container-native ISO
# contract says (ADR 0011), but it doesn't label the files it puts in the
# squashfs. So the script asks image-builder for its build plan, an osbuild
# manifest, adds osbuild's own SELinux stage to it with image/iso.py, and runs
# osbuild from the same container. Run it as root; it needs about 30 GB free
# in /var/tmp for osbuild's trees. Exits 0 when the ISO is written.

set -euo pipefail

if (($# != 4)); then
  printf 'Usage: %s IMAGE_BUILDER LIVE_IMAGE PAYLOAD ISO\n' "${0##*/}" >&2
  exit 2
fi
readonly image_builder=$1 live=$2 payload=$3 iso=$4
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

# --bootc-installer-payload-ref copies the payload into the live system's
# container storage, at the end of the os-tree pipeline, so the SELinux stage
# that image/iso.py adds after it labels its files too.
run "$image_builder" manifest --bootc-ref "$live" --bootc-installer-payload-ref "$payload" generic-iso \
  >"$work/output/generic-iso.json"
python3 "$here/iso.py" label "$work/output/generic-iso.json" >"$work/output/labelled.json"
run --entrypoint osbuild "$image_builder" \
  --store /var/cache/image-builder/store --output-directory /output \
  --export bootiso /output/labelled.json

mkdir -p -- "$(dirname -- "$iso")"
mv -- "$work/output/bootiso/install.iso" "$iso"
