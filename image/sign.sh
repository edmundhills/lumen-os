#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Sign a pushed Lumen image with cosign and attach its SBOM to it as a signed
# attestation, or check both (step 1.6, docs/decisions/0008-image-signing.md).
#
# Usage:
#   image/sign.sh sign IMAGE@DIGEST KEY [SBOM]
#       Sign the image, and attach SBOM, its SPDX JSON SBOM from syft, as an
#       attestation of type spdxjson. KEY is cosign's private key: a file, or
#       env://COSIGN_PRIVATE_KEY as in CI. COSIGN_PASSWORD holds its password.
#   image/sign.sh verify IMAGE@DIGEST PUBLIC_KEY [--sbom]
#       Check that the image is signed with the key whose public half is the
#       file PUBLIC_KEY, and with --sbom that its SBOM attestation is too.
#
# IMAGE@DIGEST is the pushed image by digest, such as
# ghcr.io/edmundhills/lumen@sha256:<digest>. The signature is for the digest,
# so it holds for every tag of that image. Exits 0 on success.
#
# The image workflow (.github/workflows/build-image.yml) runs this for builds
# of main, and image/test_signatures.py runs it against a stand-in registry,
# so what the tests accept is what CI writes.
#
# The signature has to be one that containers/image can check, because bootc
# pulls through it: a simple signing payload under the tag sha256-<digest>.sig
# (use-sigstore-attachments in registries.d). cosign 3 writes a Sigstore
# bundle instead unless told --new-bundle-format=false, which it accepts only
# with --use-signing-config=false. Nothing goes to Sigstore's public
# transparency log (--tlog-upload=false): containers/image checks the
# signature with the key alone, so checks with cosign say
# --insecure-ignore-tlog=true. With no log, cosign never asks to confirm, so
# there is no --yes: if a setting ever sent the signature to the public log,
# cosign would stop at its question instead. cosign 3 marks these flags
# deprecated and cosign 4 will drop them; ADR 0008 says what then.

set -euo pipefail

usage() {
  printf 'Usage: %s sign IMAGE@DIGEST KEY [SBOM]\n       %s verify IMAGE@DIGEST PUBLIC_KEY [--sbom]\n' \
    "${0##*/}" "${0##*/}" >&2
  exit 2
}

(($# >= 3)) || usage
readonly mode=$1 image=$2 key=$3
if [[ ! $image =~ ^[^@]+@sha256:[0-9a-f]{64}$ ]]; then
  printf 'Give the image by digest, as NAME@sha256:<digest>, not "%s".\n' "$image" >&2
  exit 2
fi

case $mode in
  sign)
    (($# <= 4)) || usage
    sbom=${4:-}
    if [[ -n $sbom && ! -f $sbom ]]; then
      printf 'There is no SBOM at %s.\n' "$sbom" >&2
      exit 2
    fi
    flags=(--key="$key" --new-bundle-format=false --use-signing-config=false --tlog-upload=false)
    printf 'Signing %s\n' "$image"
    cosign sign "${flags[@]}" "$image" </dev/null
    if [[ -n $sbom ]]; then
      printf 'Attaching the SBOM %s to %s\n' "$sbom" "$image"
      cosign attest "${flags[@]}" --type=spdxjson --predicate="$sbom" "$image" </dev/null
    fi
    ;;
  verify)
    (($# == 3)) || [[ $# == 4 && $4 == --sbom ]] || usage
    if [[ ! -f $key ]]; then
      printf 'There is no public key at %s.\n' "$key" >&2
      exit 2
    fi
    cosign verify --key="$key" --insecure-ignore-tlog=true "$image" >/dev/null
    printf '%s is signed with %s.\n' "$image" "$key"
    if (($# == 4)); then
      cosign verify-attestation --key="$key" --insecure-ignore-tlog=true --type=spdxjson "$image" >/dev/null
      printf 'Its SBOM attestation is signed with %s.\n' "$key"
    fi
    ;;
  *) usage ;;
esac
