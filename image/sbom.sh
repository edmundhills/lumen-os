#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Make the SBOM of a Lumen image with syft: an SPDX JSON list of its packages
# (step 1.6, docs/decisions/0008-image-signing.md).
#
# Usage: image/sbom.sh ROOT NAME VERSION OUTPUT
#
#   ROOT     The image's files, such as where `podman image mount` put them.
#   NAME     The image's name for the SBOM, such as ghcr.io/edmundhills/lumen.
#   VERSION  Its build version, such as 44.20261029.
#   OUTPUT   The SPDX JSON file to write.
#
# The image workflow (.github/workflows/build-image.yml) runs this on the
# mounted image, and image/test_sbom.py on the lint container's own files.
#
# syft reads only the rpm database, which lists every package the image has,
# and records no file of its own. Scanning the image as syft does by default,
# with every cataloguer, took about 7.6 GB of memory, and a CI runner gave up
# under it. syft doesn't ask the network whether it is current.

set -euo pipefail

if (($# != 4)); then
  printf 'Usage: %s ROOT NAME VERSION OUTPUT\n' "${0##*/}" >&2
  exit 2
fi
readonly root=$1 name=$2 version=$3 output=$4
if [[ ! -d $root ]]; then
  printf '%s is not a folder.\n' "$root" >&2
  exit 2
fi

export SYFT_CHECK_FOR_APP_UPDATE=false
export SYFT_FILE_METADATA_SELECTION=none
export SYFT_RELATIONSHIPS_PACKAGE_FILE_OWNERSHIP=false
syft scan --quiet --override-default-catalogers rpm-db-cataloger \
  --exclude './proc/**' --exclude './sys/**' --exclude './dev/**' \
  --source-name "$name" --source-version "$version" \
  --output "spdx-json=$output" "dir:$root"
