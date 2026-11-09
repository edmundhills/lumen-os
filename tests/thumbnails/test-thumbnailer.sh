#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test Lumen's video thumbnailer (step 1.14b, docs/decisions/0025-codecs.md)
# against Flathub's real runtime: H.264 and HEVC videos, wide, tall and
# shorter than its seek, get thumbnails of the right size, and a file that
# isn't a video gets none.
#
# Usage: bash tests/thumbnails/test-thumbnailer.sh
#
# Needs Flatpak and the network. It adds Flathub through Lumen's own remote
# file and installs org.freedesktop.Platform, at the branch Lumen's
# preinstall list names, into the user's installation; its codecs-extra
# extension comes with it, as on a Lumen system. The runtime's own encoders
# make the test videos. The thumbnails workflow runs this; it runs the same on
# any machine with Flatpak. Exits 0 when every case passes, 1 otherwise.

set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
readonly root overlay=$root/image/overlay
readonly thumbnailer=$overlay/usr/libexec/lumen-video-thumbnailer
readonly RUNTIME=org.freedesktop.Platform SIZE=256

branch=$(
  python3 - "$overlay/usr/share/flatpak/preinstall.d/lumen.preinstall" "$RUNTIME" <<'EOF'
import configparser
import sys

parser = configparser.ConfigParser(interpolation=None)
parser.optionxform = str
parser.read(sys.argv[1])
print(parser[f"Flatpak Preinstall {sys.argv[2]}"]["Branch"])
EOF
)
readonly branch
work=$(mktemp -d)
readonly work
trap 'rm -rf -- "$work"' EXIT

printf 'Installing %s//%s from Flathub\n' "$RUNTIME" "$branch"
flatpak remote-add --user --if-not-exists flathub "$overlay/usr/share/flatpak/remotes.d/flathub.flatpakrepo"
flatpak install --user --noninteractive --assumeyes flathub "$RUNTIME//$branch"
flatpak list --runtime --columns=application,branch,origin
if ! flatpak list --runtime --columns=application | grep -qxF "$RUNTIME.codecs-extra"; then
  printf '%s.codecs-extra did not come with the runtime\n' "$RUNTIME"
  exit 1
fi

# ffmpeg ARG...: the runtime's ffmpeg, which may write only into $work.
ffmpeg() {
  flatpak run --filesystem="$work" --command=ffmpeg "$RUNTIME//$branch" \
    -nostdin -hide_banner -loglevel error -y "$@"
}
clip() { ffmpeg -f lavfi -i "testsrc2=size=$1:rate=25:duration=$2" -pix_fmt yuv420p "${@:3}"; }
clip 640x360 6 -c:v libx264 "$work/h264.mp4"
clip 640x360 6 -c:v libx265 -tag:v hvc1 "$work/hevc.mp4"
clip 640x360 6 -c:v libx265 "$work/hevc.mkv"
clip 360x640 6 -c:v libx264 "$work/tall.mp4"
clip 640x360 1 -c:v libx264 "$work/short.mp4"
printf 'This is not a video.\n' >"$work/text.mp4"
ls -l "$work"

passes=0 failures=0

# png_size FILE: "WIDTH HEIGHT" of a PNG, or nothing if FILE isn't one.
png_size() {
  python3 - "$1" <<'EOF'
import struct
import sys

with open(sys.argv[1], "rb") as f:
    head = f.read(24)
if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
    print(*struct.unpack(">II", head[16:24]))
EOF
}

# expect NAME FILE SIZE: the thumbnailer makes a PNG of SIZE ("" for none).
expect() {
  local name=$1 file=$2 want=$3 out=$work/$2.png got="" status=0 want_status=0
  rm -f -- "$out"
  bash "$thumbnailer" "$SIZE" "$work/$file" "$out" || status=$?
  [[ ! -f $out ]] || got=$(png_size "$out")
  # No thumbnail is exit 1.
  [[ -n $want ]] || want_status=1
  if [[ $got == "$want" ]] && ((status == want_status)); then
    passes=$((passes + 1))
    printf '  PASS  %s\n' "$name"
  else
    failures=$((failures + 1))
    printf '  FAIL  %s: exit %d, a thumbnail of "%s", not "%s"\n' "$name" "$status" "$got" "$want"
  fi
}

printf '\nLumen video thumbnailer tests (%s//%s)\n' "$RUNTIME" "$branch"
expect "H.264 in MP4" h264.mp4 "256 144"
expect "HEVC in MP4" hevc.mp4 "256 144"
expect "HEVC in Matroska" hevc.mkv "256 144"
expect "A tall video keeps its shape" tall.mp4 "144 256"
expect "A video shorter than the seek" short.mp4 "256 144"
expect "A file that isn't a video gets none" text.mp4 ""

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
((failures == 0))
