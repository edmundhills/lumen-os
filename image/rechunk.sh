#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Re-chunk a built Lumen image, so that an update downloads only the layers
# whose packages changed (step 1.5c, ADR 0007, risk 14 in docs/risks.md). Then
# check that the result is the same image: the same labels and settings, and
# the same checks passing as in the build.
#
# Usage: sudo image/rechunk.sh IMAGE OUTPUT [PREVIOUS]
#
#   IMAGE     The built image in root's Podman storage, such as localhost/lumen:ci.
#   OUTPUT    A folder that doesn't exist yet. The re-chunked image is written
#             there as an OCI layout, tagged "latest", with compressed layers,
#             ready for `skopeo copy` to push as it is. It is also copied into
#             Podman's storage as IMAGE-rechunked, to be checked.
#   PREVIOUS  Optional. An earlier re-chunked build whose layer plan to keep,
#             such as docker://ghcr.io/edmundhills/lumen@sha256:<digest> or
#             oci:/path/to/layout:latest. Packages stay in the layers they were
#             in, so a package that didn't change keeps its layer, digest and
#             all. Without it, rpm-ostree plans the layers afresh.
#
# The tool is `rpm-ostree compose build-chunked-oci`, run from IMAGE itself, so
# its version always matches the base. It reads IMAGE from Podman's storage,
# which it needs mounted, so this runs as root. Exits 0 when the image is
# re-chunked and passes every check, 1 otherwise.

set -euo pipefail

# Kinoite comes in 257 layers: the ostree commit and 256 of packages. Lumen
# uses as many, so a package update downloads as little as it does on Kinoite.
# rpm-ostree packs the packages into this many layers, one each for the
# biggest, and keeps one empty for packages added later.
readonly MAX_LAYERS=256

if (($# < 2 || $# > 3)); then
  printf 'Usage: %s IMAGE OUTPUT [PREVIOUS]\n' "${0##*/}" >&2
  exit 2
fi
readonly image=$1 output=$2 previous=${3:-}
readonly rechunked=$image-rechunked
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly here

args=(--bootc --format-version=2 --max-layers="$MAX_LAYERS")
mounts=(--volume=/var/lib/containers:/var/lib/containers)
case $previous in
  '') ;;
  oci:*)
    # An OCI layout on this machine: mount its folder.
    ref=${previous#oci:}
    dir=${ref%%:*} tag=
    [[ $ref != *:* ]] || tag=:${ref#*:}
    if [[ ! -f $dir/index.json ]]; then
      printf '%s is not an OCI layout.\n' "$dir" >&2
      exit 2
    fi
    mounts+=(--volume="$(realpath -- "$dir")":/run/rechunk/previous:ro)
    args+=(--previous-build="oci:/run/rechunk/previous$tag")
    ;;
  docker://*) args+=(--previous-build="$previous") ;;
  *)
    printf 'PREVIOUS must start with docker:// or oci:, not "%s".\n' "$previous" >&2
    exit 2
    ;;
esac
if [[ -e $output ]]; then
  printf '%s already exists. Give a folder that does not exist yet.\n' "$output" >&2
  exit 2
fi

# rpm-ostree first looks for an earlier build at the output. An empty OCI
# layout tells it there is none; a missing folder would be an error.
mkdir -p -- "$output"
printf '{"imageLayoutVersion": "1.0.0"}\n' >"$output/oci-layout"
printf '{"schemaVersion": 2, "manifests": []}\n' >"$output/index.json"

# rpm-ostree builds an ostree repository as big as the image in /var/tmp.
# Mount a folder next to the output there, on the same disk.
work=$(mktemp -d -- "$(dirname -- "$(realpath -- "$output")")/rechunk-work.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
mounts+=(--volume="$(realpath -- "$output")":/run/rechunk/output --volume="$work":/var/tmp)

# Format version 2 writes each layer's parent folders into it, which makes the
# layers reproducible (rpm-ostree's documentation). rpm-ostree keeps IMAGE's
# settings and labels, replacing only ostree.commit and ostree.final-diffid.
# Podman records the base image as annotations on IMAGE's manifest, which
# re-chunking would drop, so keep them as labels.
manifest=$(skopeo inspect --raw "containers-storage:$image")
for key in org.opencontainers.image.base.name org.opencontainers.image.base.digest; do
  value=$(python3 -c 'import json, sys; print(json.loads(sys.argv[1]).get("annotations", {}).get(sys.argv[2], ""))' \
    "$manifest" "$key")
  if [[ -z $value ]]; then
    printf '%s has no %s annotation on its manifest.\n' "$image" "$key" >&2
    exit 1
  fi
  args+=(--label="$key=$value")
done

printf 'Re-chunking %s into %s/ with at most %d layers\n' "$image" "$output" "$MAX_LAYERS"
[[ -z $previous ]] || printf 'Keeping the layer plan of %s\n' "$previous"
podman run --rm --privileged --pull=never --security-opt=label=disable "${mounts[@]}" \
  --entrypoint=rpm-ostree "$image" \
  compose build-chunked-oci "${args[@]}" --from="$image" --output=oci:/run/rechunk/output:latest

# Check the result. First, the same settings and labels.
podman image rm --ignore -- "$rechunked" >/dev/null
skopeo copy --quiet "oci:$output:latest" "containers-storage:$rechunked"
python3 "$here/rechunk.py" labels \
  <(skopeo inspect --config "containers-storage:$image") \
  <(skopeo inspect --config "oci:$output:latest")

# Then the checks the Containerfile's lumen stage ends with, on the re-chunked
# image: image/check-image.sh and bootc container lint.
printf 'Checking %s\n' "$rechunked"
podman build --pull=never --no-cache --build-arg=IMAGE="$rechunked" \
  --file=- --tag="$rechunked-checked" -- "$here/.." <<'EOF'
ARG IMAGE
FROM $IMAGE
RUN --mount=type=bind,source=image,target=/run/lumen/image \
    bash /run/lumen/image/check-image.sh /run/lumen/image/overlay
RUN rm -rf /run/lumen && bootc container lint --fatal-warnings
EOF
podman image rm -- "$rechunked-checked" >/dev/null
printf '%s is re-chunked and passes the checks.\n' "$output"
