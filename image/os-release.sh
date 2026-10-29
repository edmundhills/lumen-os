#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Write Lumen's /usr/lib/os-release in place of Kinoite's (docs/architecture.md,
# section 9.7). /etc/os-release is a link to it.
#
# Usage: bash os-release.sh BUILD_VERSION
#
# The lumen stage of the Containerfile runs this inside the image it is
# building. BUILD_VERSION is <Fedora release>.<build date>[.N], from
# build_version.py; it must name the image's own Fedora release. Exits 0 when
# the file is written, 1 otherwise, which stops the build.

set -euo pipefail

# Lumen's product version. The release step (10.5) moves it on.
readonly PRODUCT_VERSION=0.1
readonly REPO_URL=https://github.com/edmundhills/lumen-os

if (($# != 1)); then
  printf 'Usage: %s BUILD_VERSION\n' "${0##*/}" >&2
  exit 2
fi
readonly build_version=$1

fedora=$(rpm --eval '%{fedora}')
if [[ ! $build_version =~ ^${fedora}\.[0-9]{8}(\.[1-9][0-9]*)?$ ]]; then
  printf 'The build version "%s" is not %s.<date>[.N]: the image is Fedora %s.\n' \
    "$build_version" "$fedora" "$fedora" >&2
  exit 1
fi

# Kinoite's file is a hard link inside the image; replace it rather than write
# through it.
rm -f /usr/lib/os-release
cat >/usr/lib/os-release <<EOF
NAME="Lumen OS"
VERSION="$PRODUCT_VERSION ($build_version)"
ID=lumen
ID_LIKE=fedora
VERSION_ID=$PRODUCT_VERSION
PRETTY_NAME="Lumen OS $PRODUCT_VERSION"
IMAGE_ID=lumen
IMAGE_VERSION=$build_version
DEFAULT_HOSTNAME=lumen
HOME_URL="$REPO_URL"
DOCUMENTATION_URL="$REPO_URL/tree/main/docs"
BUG_REPORT_URL="$REPO_URL/issues"
EOF
chmod 0644 /usr/lib/os-release
