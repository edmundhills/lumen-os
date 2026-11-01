#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Make Lumen's kernel module signing key (step 1.11a,
# docs/decisions/0021-module-signing-key.md). The owner runs this once, in WSL
# from the project folder, after `just lint` has built the lint container:
#
#   bash image/nvidia/make-module-key.sh ~/lumen-module-key
#
# openssl runs in the lint container with no network and writes to DIR:
#   module-signing.key  the private key, RSA 4096, encrypted with the password
#                       openssl asks for twice. It never goes into the
#                       repository or to Claude.
#   module-signing.der  the certificate, which users enrol as a MOK and the
#                       repository keeps as image/nvidia/module-signing.der.
# Then image/nvidia/module_key.py checks the certificate and prints its SHA-256
# fingerprint. Refuses to overwrite a key DIR already holds.

set -euo pipefail

if (($# != 1)); then
  printf 'Usage: %s DIR\n' "${0##*/}" >&2
  exit 2
fi
dir=$(realpath -m -- "$1")
readonly dir
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly here image=localhost/lumen-lint

if [[ -e $dir/module-signing.key || -e $dir/module-signing.der ]]; then
  printf '%s already holds a module signing key. Move it away first: this script never replaces one.\n' "$dir" >&2
  exit 1
fi
if ! podman image exists "$image"; then
  printf 'The lint container %s is missing: run "just lint" first.\n' "$image" >&2
  exit 1
fi
mkdir -p -- "$dir"
chmod 700 -- "$dir"

# Universal Blue's module keys, which Fedora's kernels accept once enrolled, use
# the same profile: self-signed RSA 4096 with SHA-256, not a CA, for digital
# signatures. The kernel ignores the dates, so the certificate runs 100 years
# rather than making every user enrol a new one.
podman run --rm -it --network=none --volume "$dir:/keys:Z" --workdir /keys "$image" \
  openssl req -new -x509 -newkey rsa:4096 -sha256 -days 36500 \
  -subj "/O=Lumen OS/CN=Lumen OS kernel module signing" \
  -addext "basicConstraints=critical,CA:FALSE" -addext "keyUsage=digitalSignature" \
  -addext "subjectKeyIdentifier=hash" \
  -keyout module-signing.key -outform DER -out module-signing.der
chmod 600 -- "$dir/module-signing.key"

podman run --rm --network=none --volume "$dir:/keys:ro,Z" --volume "$here:/check:ro,Z" "$image" \
  python3 /check/module_key.py check /keys/module-signing.der
