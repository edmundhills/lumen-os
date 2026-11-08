<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0025. Codecs and hardware video decoding

- Status: **Proposed** (2026-11-08), at step 1.14. The owner chooses.
- Deciders: the owner, on the options below; lead engineer (Claude) wrote them.

This is a technical summary written to help with a legal choice. It is not legal advice. If Lumen is distributed widely, or commercially, ask a lawyer who knows software patents in the owner's country.

## Context

The spec asks for "codecs and hardware video decoding chosen and shipped deliberately (ADR, owner's decision)" ("What Lumen fixes"; "Image contents": "system codecs and hardware video decoding per the codecs ADR"; [risk 10](../risks.md#10-codec-patents-and-hardware-video-decoding)). Facts, read on 2026-11-08:

**What the image has today** (the packages of `lumen:dev`, from Kinoite 45):

- Fedora's free builds: `ffmpeg-free` and `libavcodec-free`, GStreamer's `-free` plugin sets with `gstreamer1-plugin-libav` and `-dav1d`, VLC's libraries for Phonon, `fdk-aac-free`, `faad2`, `lame`, `libvpx`, `libaom`, `libdav1d`, `svt-av1`, `rav1e`. These play MP3, AAC, Opus, Vorbis, FLAC, VP8, VP9 and AV1.
- No H.264 or HEVC decoder for host apps. Fedora uses Cisco's OpenH264 for H.264, but Cisco's patent licence only covers copies downloaded from Cisco, so Fedora's image-based desktops carry a placeholder, `noopenh264`, and so does Lumen.
- Fedora's Mesa is built without H.264, HEVC and VC-1 in its video drivers (since Fedora 37), so AMD graphics don't decode or encode those in hardware for host apps. AV1 and VP9 are in. Fedora's Intel driver, `libva-intel-media-driver`, is in the image; whether it decodes H.264 and HEVC is checked on real hardware at step 1.17.
- The NVIDIA editions have NVIDIA's own decoder and encoder (NVDEC, NVENC, through `xorg-x11-drv-nvidia-cuda-libs`), which don't depend on Mesa.

**Flatpak apps get every codec, and hardware decoding, from Flathub, whatever the image holds.** Flathub's runtime comes from freedesktop-sdk (`gitlab.com/freedesktop-sdk/freedesktop-sdk` at `76ded6f`, 2026-11-07):

- Its `codecs-extra` extension, an FFmpeg with every decoder and encoder and x264 and x265, is downloaded automatically with the runtime.
- Its Mesa comes in two builds under one name: one with only the free video codecs, and an "extra" one with H.264, HEVC and VC-1, added in 2022 "for users and distributors which are legally positioned to make use of them". When both are installed, which Flatpak does, the extra one wins. An Intel driver extension and an NVIDIA one exist too.
- So Lumen's apps, which the spec makes Flatpaks (browser, office, media player, editor, Bottles), play everything and decode in hardware already.

**What host apps would miss without system codecs:**

- **The browser, for now.** The image still has Kinoite's Firefox as an RPM, which plays video through the system's FFmpeg: H.264 and HEVC videos don't play in it, though VP9 and AV1 ones, YouTube included, do. The spec wants the browser as a Flatpak, preinstalled on first boot.
- **Thumbnails.** Dolphin's video thumbnails (`ffmpegthumbs`) use the system's FFmpeg, so most phone and camera videos, H.264 or HEVC, show no thumbnail.
- **Steam on the gaming editions** encodes in hardware for Remote Play and game recording through the host's video drivers. On AMD, without H.264 and HEVC in Mesa, it encodes on the CPU instead, which costs frames.
- Screen recording (Spectacle) records VP9 or AV1 rather than H.264; that works, in a less common format.

**RPM Fusion** has the full builds: `ffmpeg` with x264 and x265, `mesa-va-drivers-freeworld` and `mesa-vulkan-drivers-freeworld` (Mesa built with H.264, HEVC and VC-1, `rpmfusion/mesa-freeworld`), `intel-media-driver`, `gstreamer1-plugins-bad-freeworld` and `gstreamer1-plugins-ugly`. Freeworld Mesa must be the exact build of the image's Mesa (architecture 9.4). On 2026-11-08 RPM Fusion's is 26.2.6 and the image's 26.2.5, so a build that took it today would be held until Kinoite's weekly bump catches up.

**The patents**, in short:

- MP3's patents have expired. AAC as Fedora ships it is cleared by Fedora. AV1, VP8, VP9, Opus, Vorbis and FLAC are royalty-free.
- H.264 is licensed through a patent pool (Via LA, which took over MPEG LA's), and some of its patents are still in force in several countries.
- HEVC has several pools and independent holders, and patents in force for longer.
- Licences are sold per product that includes an encoder or decoder. Giving software away doesn't exempt it. Software patents are enforced in the United States, and less readily in Europe.
- Fedora, Red Hat, openSUSE and Debian leave H.264 and HEVC out of what they ship. Ubuntu and Linux Mint let the user download them, at install or later. Some Fedora-based community images, such as Universal Blue's, ship them in the image.

## Options

| | A. Fedora's codecs, apps from Flathub | B. RPM Fusion's codecs in every image | C. RPM Fusion's codecs on the gaming editions | D. The user downloads them (later) |
| --- | --- | --- | --- | --- |
| Flatpak apps (browser, player, editors) | Everything, with hardware decoding | Everything, with hardware decoding | Everything, with hardware decoding | Everything, with hardware decoding |
| Video thumbnails in Dolphin | VP9 and AV1 only | Everything | Gaming editions only | After the user opts in |
| Steam's hardware encoding on AMD | No (CPU instead) | Yes | Yes | After the user opts in |
| Who distributes H.264 and HEVC code | Flathub, for apps; Lumen doesn't | Lumen, in all four images | Lumen, in the two gaming images | The user's own machine downloads them from RPM Fusion |
| Engineering | None for codecs | RPM Fusion for every build; swaps of Fedora's packages; builds held while RPM Fusion's Mesa trails the image's | As B, for two images | A system extension built on the user's machine and rebuilt after every update (Phase 5 at the earliest) |

- **A** keeps Lumen where Fedora is. With it, the browser and a video player should come from Flathub now, through the same preinstall list as Bottles (ADR 0024), and the Firefox RPM go, as the spec already says; then only the thumbnails and Steam's encoding on AMD miss out.
- **B** gives the most complete experience, as Universal Blue's images do, and makes Lumen the distributor of patent-encumbered codecs to everyone who downloads an image.
- **C** limits B to the editions that already use RPM Fusion and whose users gain the most, but the legal position for those images is B's.
- **D** follows Ubuntu and Mint: a "More video formats" switch in Settings, later. It can be added to A.

## Recommendation

A now: Fedora's codecs in the image, the browser and a video player from Flathub, and the Firefox RPM removed. Lumen distributes nothing that Fedora doesn't, and every app plays everything. Plan D for Phase 5 if the thumbnails or Steam's encoding prove to matter to users. Choose B or C instead only after weighing the legal side.

## Decision

Waiting for the owner.
