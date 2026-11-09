<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0025. Keep Fedora's codecs in the image; apps, thumbnails and an opt-in video driver get the rest

- Status: **Accepted** (2026-11-09), at step 1.14: option A, with two additions the owner asked for.
- Deciders: the owner, on the options below; lead engineer (Claude) wrote them and the way to ship them.

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

The owner chose A, and asked for H.264 and HEVC video thumbnails and Steam's hardware encoding on AMD to work too, without Lumen's image carrying those codecs. More facts, read on 2026-11-09:

- KDE's previews (KIO, `KDE/kio` at `929eeac`) run freedesktop thumbnailers, `.thumbnailer` files in `/usr/share/thumbnailers` whose command makes a PNG, and turn every one on by default; a KIO plugin such as `ffmpegthumbs` that takes the same type comes first.
- `flatpak run` runs a runtime as well as an app, and `--sandbox` drops every permission it would otherwise have. freedesktop's runtime has the `ffmpeg` and `ffprobe` commands, which use `codecs-extra` when it is there (freedesktop-sdk's own `tests/ffmpeg-test.py`).
- KDE's runtime (`KDE/flatpak-kde-runtime`, branch `qt6.11`) inherits freedesktop's `codecs-extra` and GL extensions. Haruna, KDE's video player on Flathub (`org.kde.haruna`), uses it and has the GPU (`--device=dri`).
- RPM Fusion's `mesa-va-drivers-freeworld` keeps its video drivers and its own `libgallium` in `/usr/lib64/dri-freeworld`, which an `ld.so.conf.d` file adds to the library path.

So:

1. **The image keeps Fedora's codecs.** Lumen ships no H.264, HEVC or VC-1 code, and no RPM Fusion codec package.
2. **The browser and the video player come from Flathub** on first boot, with every codec and hardware decoding: Mozilla's Firefox (`org.mozilla.firefox`) and KDE's Haruna (`org.kde.haruna`), in the preinstall list that brings Bottles (ADR 0024). Kinoite's Firefox RPM goes, and the image check makes sure nothing still names it as a default app (step 1.14a).
3. **Video thumbnails come from Flathub's codecs** (step 1.14b). `ffmpegthumbs` goes, and Lumen's `.thumbnailer` runs a small script that has the newest installed freedesktop runtime's `ffmpeg` make the thumbnail, in `flatpak run --sandbox` with read access to that one file only. The runtime joins the preinstall list. The script is all Lumen ships, so Flathub distributes the codec. Parsing an untrusted video file moves from Dolphin's own process into a sandbox, which the security model welcomes. CI tests it with H.264 and HEVC clips.
4. **Steam's hardware encoding on AMD is an opt-in on each machine** (step 1.14c). A command, and from Phase 5 a switch in Settings, downloads RPM Fusion's `mesa-va-drivers-freeworld` at exactly the image's Mesa version, checks its signature with RPM Fusion's key, which the image carries, and unpacks it into `/var/lib/lumen/codecs`. An `ld.so.conf.d` entry and `LIBVA_DRIVERS_PATH` in `/etc` point the video drivers there. At every start, before the login screen, a service checks that the download still matches the image's Mesa: after an update that changed Mesa it turns the drivers off, falling back to Fedora's, until it has the matching download. The user's machine downloads the codec, as with Ubuntu's and Linux Mint's codec downloads; Lumen's image never contains it. The NVIDIA editions don't need it (NVENC).

## Consequences

- Every app the user gets from Lumen plays everything, with hardware decoding, and Lumen distributes nothing that Fedora doesn't.
- The first start downloads Firefox and Haruna as well as Bottles, with their runtimes; until it has, there is no browser. Welcome (Phase 6) will show the progress.
- Thumbnails of videos cost a sandboxed process each, cached once made.
- Steam on AMD encodes on the CPU until its user opts in, and again for each update that moves Mesa until the matching download is there.
- If RPM Fusion has no build of the image's Mesa yet, the opt-in waits for it.

## Follow-up

- 2026-11-09, step 1.14a: image run 42583538022 (for `f7ba77c`) was green without the Firefox RPM: `lumen` 12 of 12 (51 minutes), `lumen-gaming` 13 of 13 (81), `lumen-nvidia` 14 of 14 (97), `lumen-gaming-nvidia` 15 of 15 (116), every image check passing, the new ones included. `lumen`'s update from the exempted `dev` `45.20261106.1` is now 420.4 MiB in 10 of 252 layers: removing Firefox and its language packs took two layers away, and re-chunking against `dev`'s plan moved packages between three more and `python3-libs`'s, once, on top of step 1.13's changes.
- 2026-11-09, step 1.14b: the thumbnailer as decision 3 says, with the runtime at 26.08 in the preinstall list; KIO matches `.thumbnailer` types exactly, then by parent, then by `video/*`, so `ffmpegthumbs`' list carries over whole. Its CI test is the `thumbnails` workflow.
- 2026-11-09, step 1.14b: the `thumbnails` workflow passed 6 of 6 against Flathub's `org.freedesktop.Platform//26.08` (run 42630412264), and image run 42640758130 (for `c8d0ee7`) was green on Kinoite 45.20261102.0: every edition passed the 18 lumen image checks, the thumbnail check included, and booted: `lumen` 12 of 12 (58 minutes; its update from `dev` `45.20261108`, exempt, 364.9 MiB), `lumen-gaming` 13 of 13 (86), `lumen-nvidia` 14 of 14 (98), `lumen-gaming-nvidia` 15 of 15 (114).
