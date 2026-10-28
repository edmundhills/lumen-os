#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copy each base image that the given Containerfiles pin to REGISTRY, keeping
# its digest, so that commits pinning it stay buildable after its own registry
# deletes it (step 1.5b, ADR 0004). The base workflow runs it, logged in to
# REGISTRY with skopeo (.github/workflows/base.yml).
#
# Usage: image/copy-bases.sh REGISTRY CONTAINERFILE...
#
# image/bump_bases.py names each copy, for example
# ghcr.io/edmundhills/kinoite:44-9f71aa8ed152. A base that is already copied is
# skipped. --all copies every architecture, so the index, and with it the
# pinned digest, stays the same. Each copy must be public, because builds of
# pull requests pull it without logging in. Exits 0 when every base is copied
# and public, 1 otherwise.

set -euo pipefail

if (($# < 2)); then
  printf 'Usage: %s REGISTRY CONTAINERFILE...\n' "$0" >&2
  exit 2
fi

bases=$(python3 "$(dirname -- "${BASH_SOURCE[0]}")/bump_bases.py" list "$@")
status=0
while read -r -u 3 image digest copy tag; do
  if skopeo inspect --raw "docker://$copy@$digest" >/dev/null 2>&1; then
    printf '%s@%s is already copied to %s.\n' "$image" "$digest" "$copy"
  else
    printf 'Copying %s@%s to %s:%s\n' "$image" "$digest" "$copy" "$tag"
    skopeo copy --all --preserve-digests --retry-times 3 "docker://$image@$digest" "docker://$copy:$tag"
    if [[ -n ${GITHUB_STEP_SUMMARY:-} ]]; then
      # The backticks are Markdown, for the run's summary page.
      # shellcheck disable=SC2016
      printf -- '- Copied `%s@%s` to `%s:%s`\n' "$image" "$digest" "$copy" "$tag" >>"$GITHUB_STEP_SUMMARY"
    fi
  fi
  if ! skopeo inspect --no-creds --raw "docker://$copy@$digest" >/dev/null; then
    owner=${copy#*/}
    printf '::error::%s needs a login to pull. Make the package public: %s\n' "$copy" \
      "https://github.com/users/${owner%%/*}/packages/container/${copy##*/}/settings"
    status=1
  fi
done 3<<<"$bases"
exit "$status"
