#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Sign the NVIDIA modules build-kmods.sh built, and pack them again (step
# 1.11b, docs/decisions/0022-nvidia-edition.md, ADR 0021). The kmods stage of
# image/Containerfile runs this in a step of its own, the only one that sees
# the key: it comes in as build secrets, which no layer keeps, so NVIDIA's
# build never sees it.
#
# Usage: bash sign-kmods.sh SECRETS
#   SECRETS  the folder holding the secrets module_signing_key (the private
#            key, PEM, maybe encrypted), module_signing_cert (its certificate,
#            DER) and module_signing_password (the key's pass phrase, empty for
#            a key without one). Builds of main use Lumen's key (step 1.11c);
#            every other build makes a throwaway key, so it signs the same way.
#
# Each module of kmod-nvidia is signed with the kernel's sign-file and its
# signer checked; xz modules are compressed again as the kernel needs them.
# Then rpmrebuild packs the installed package, with the signed modules, into
# /kmods, and the certificate goes there too, as module-signing.der.

set -euo pipefail

if (($# != 1)); then
  printf 'Usage: %s SECRETS\n' "${0##*/}" >&2
  exit 2
fi
readonly key=$1/module_signing_key cert=$1/module_signing_cert password=$1/module_signing_password
for secret in "$key" "$cert"; do
  if [[ ! -s $secret ]]; then
    printf 'No module signing secret %s: pass --secret id=%s to podman build (ADR 0022).\n' \
      "${secret##*/}" "${secret##*/}" >&2
    exit 1
  fi
done

kver=$(</kmods/kernel)
readonly kver signfile=/usr/src/kernels/$kver/scripts/sign-file
KBUILD_SIGN_PIN=$(cat "$password" 2>/dev/null || true)
export KBUILD_SIGN_PIN
signer=$(openssl x509 -inform DER -in "$cert" -noout -subject -nameopt multiline |
  sed -n 's/^ *commonName *= //p')

mapfile -t modules < <(rpm --query --list "kmod-nvidia-$kver" | grep -E '\.ko(\.xz|\.zst)?$')
if ((${#modules[@]} == 0)); then
  printf 'kmod-nvidia-%s holds no modules\n' "$kver" >&2
  exit 1
fi
for module in "${modules[@]}"; do
  case $module in
    *.ko.xz)
      xz --decompress "$module"
      "$signfile" sha256 "$key" "$cert" "${module%.xz}"
      # The kernel reads only xz modules with a CRC32 check.
      xz --check=crc32 --lzma2=dict=1MiB "${module%.xz}"
      ;;
    *.ko.zst)
      zstd --quiet --decompress --rm "$module"
      "$signfile" sha256 "$key" "$cert" "${module%.zst}"
      zstd --quiet --rm "${module%.zst}"
      ;;
    *) "$signfile" sha256 "$key" "$cert" "$module" ;;
  esac
  got=$(modinfo --field=signer "$module")
  if [[ $got != "$signer" ]]; then
    printf '%s is signed by "%s", not "%s"\n' "$module" "$got" "$signer" >&2
    exit 1
  fi
  printf 'Signed %s (%s)\n' "$module" "$signer"
done

rpmrebuild --batch --notest-install --directory=/kmods "kmod-nvidia-$kver"
install -m 0644 "$cert" /kmods/module-signing.der
find /kmods -name '*.rpm' -print
