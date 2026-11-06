<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0019. Build the gaming edition with RPM Fusion's Steam and 32-bit packages at the image's versions

- Status: **Accepted** (2026-11-01), at step 1.10a.
- Deciders: lead engineer (Claude). The owner reviews it at the Phase 1 acceptance (step 1.17).

## Context

The spec's `lumen-gaming` image "adds Steam, Gamescope session, MangoHud, controller udev rules", and "Gaming and creative" lists Steam, Proton, Gamescope, MangoHud and GameMode. Architecture 9.5 says Steam's 32-bit libraries must match the 64-bit ones in `base` exactly (the rule of 9.4), and rule 3 of 9.1 lets packages come from RPM Fusion for the variants, through the package manifest. Facts, read on 2026-11-01:

- **Steam is RPM Fusion's.** Fedora doesn't package Valve's client. RPM Fusion nonfree's `steam` 1.0.0.87 (`rpmfusion/steam` at `b5c2d15`, `ExclusiveArch: x86_64`) is Valve's bootstrap: Steam downloads the rest of itself, Proton included, on its first start. It requires about forty 32-bit libraries, among them `mesa-dri-drivers(x86-32)`, `mesa-vulkan-drivers(x86-32)`, `glibc(x86-32)` and `vulkan-loader(x86-32)`, and `steam-devices`, which is Fedora's: the udev rules for Steam's and many other controllers.
- **Gamescope, MangoHud and GameMode are Fedora packages.**
- **RPM Fusion's repositories and key** are in its release package (`rpmfusion/rpmfusion-nonfree-release` at `aa70b42`, licence BSD-1-Clause): `rpmfusion-nonfree.repo` and `rpmfusion-nonfree-updates.repo`, signed with `RPM-GPG-KEY-rpmfusion-nonfree-fedora-2020`, fingerprint `79BD B88F 9BBF 7391 0FD4 095B 6A2A F961 9484 3C65`.
- **Fedora's mirrors carry only the newest build** of each package, and the base image is pinned for a week at a time (ADR 0004, step 1.5b). When Mesa is updated in between, dnf installs the newer 32-bit Mesa and upgrades the 64-bit one to match, so the gaming image would run another Mesa than the image it derives from. Koji, Fedora's build system, keeps every build, and the copies Fedora signed (`packages/<source>/<version>/<release>/data/signed/<key ID>/`).
- **CLAUDE.md says user apps come from Flathub**, but the spec puts Steam in the gaming image, and the Gamescope session (step 1.10b) starts Steam as the session's program, which the Flatpak can't be without workarounds. The spec wins (CLAUDE.md says so). The desktop edition gets Steam's Flatpak when the user ticks it in Welcome (spec, "Games").
- This session can't reach Fedora's mirrors, RPM Fusion or Koji, so CI's build is where the package facts are first checked.

## Decision

1. **A stage `lumen-gaming`** in `image/Containerfile`, `FROM ${LUMEN_GAMING_FROM}`, which is the `lumen` stage of the same build unless the argument names another image; step 1.12 puts the same layer on `lumen-nvidia` that way.
2. **RPM Fusion for Steam only, for one step.** `image/gaming/rpmfusion-nonfree.repo` holds RPM Fusion's two nonfree repositories, turned on and limited with `includepkgs=steam` (and, from step 1.12b, NVIDIA's libraries: Follow-up), with RPM Fusion's key from this repository (`image/gaming/`), which the step checks against `keys.sha256` first. The step copies the file into `/etc/yum.repos.d` and deletes it again, so the image keeps no RPM Fusion repository. `test_gaming.py` checks the key's fingerprint, the pin and the repository's limits. The key stays in rpm's keyring in the image, as the key that signed an installed package.
3. **`image/gaming/packages.toml`** installs `steam`, `steam-devices`, `gamescope`, `mangohud` and `gamemode`, through `packages.py`, with the option `exact_32bit = true`.
4. **32-bit packages at the image's versions** (`image/multilib.py`). dnf resolves the packages and downloads what it would install (`dnf download --resolve`) without installing it. Each 32-bit package whose 64-bit twin the image has at another version is swapped for the build at the twin's version, from the mirrors if they still have it, otherwise Fedora's signed copy on Koji. Upgrades of packages the image has are left out. Neither `dnf download` nor a local install checks signatures, so `rpmkeys` imports the enabled repositories' keys and checks every file, which must carry a signature by one of them (rpm alone passes an unsigned package on its digests). dnf then installs exactly those files with every repository turned off, and the step stops if any package the image had changed, or if any 32-bit package and its twin differ.
5. **os-release names the edition**: `VARIANT="Gaming"`, `VARIANT_ID=gaming`, `IMAGE_ID=lumen-gaming`, `PRETTY_NAME="Lumen OS 0.1 (Gaming)"` (`image/os-release.sh`), and the image's title label is "Lumen OS Gaming".
6. **Checks in the stage:** `image/check-image.sh` again, so the lumen image's checks still hold with the edition's packages; `image/gaming/check-gaming.sh` (the packages, Steam signed with RPM Fusion's key, the controller rules' `uaccess` tag, at least forty 32-bit packages all matching their twins, no RPM Fusion repository left, os-release, the programs and their libraries); then `bootc container lint`.
7. **CI builds it** in the image job right after `lumen`, reusing that build's stages, and deletes it again. Re-chunking, signing, pushing and the boot test of its qcow2 come with step 1.12's matrix and step 1.10c.

## Consequences

- The gaming edition runs exactly the image's Mesa, in 32 and 64 bits, whatever the mirrors carry that day.
- Steam needs the network on its first start, to download itself, and then updates itself in the user's home folder, outside the image's updates; Proton comes the same way. Games and Steam's own files live in the home folder, so they survive image updates and rollbacks.
- The gaming image carries nonfree software (Valve's bootstrap), as RPM Fusion distributes it; that is what the edition is for.
- The build now depends on RPM Fusion's mirrors and, when the mirrors have moved on, on Koji. Either being down fails the gaming build, not `lumen`'s.
- If a package Steam needs requires a newer build than the base image has, the build stops and says so, until the weekly bump brings it.

## Follow-up

- 2026-11-01: the first builds ran on Fedora 45 (Kinoite `45.20261101.0`, KWin and Plasma 6.8.2), which the base bump brought the same day. Kinoite 45 already has GameMode, so the manifest keeps it. The packages' scripts left `/run/setrans` in the image, which bootc's lint rejects; the install step now removes whatever it leaves in `/run` and names the package that owns it. Then image run 41309386656 (for `7001e33`) built the edition in 15 minutes and passed everything: RPM Fusion's key against its pin, Steam signed with it, every 32-bit package the build of its 64-bit twin, no RPM Fusion repository left, the lumen checks (14) and the edition's (6), and bootc's lint. The run's summary page lists Steam's version and the number of 32-bit packages, which a cloud session can't read.
- The build job now takes about 75 minutes, 15 of them the edition's.
- 2026-11-06, step 1.12b: the same stage makes `lumen-gaming-nvidia` from the `lumen-nvidia` image CI's `nvidia` job has just built (`--build-arg LUMEN_GAMING_FROM=localhost/lumen-nvidia:ci`; ADR 0022). Naming the stage instead doesn't work: Podman picks the stages a build needs from the `ARG` defaults, so it skipped `kmods` and `lumen-nvidia` and tried to pull an image of that name. Steam and most of its games are 32-bit programs, which on an NVIDIA card render in software without NVIDIA's 32-bit libraries. RPM Fusion's driver already sees to that: `xorg-x11-drv-nvidia-libs` requires `(xorg-x11-drv-nvidia-libs(x86-32) = E:V-R if mesa-libGL(x86-32))` (`rpmfusion/xorg-x11-drv-nvidia` at `335452f`), so Steam's 32-bit Mesa brings the 32-bit libraries at exactly the driver's version, through `multilib.py` and its signature checks like every other 32-bit package. The repository file allows `steam,xorg-x11-drv-nvidia-libs`, without which that dependency can't be met; on `lumen` nothing requires the second, and `check-gaming.sh` fails if it got in, or if it is missing on the NVIDIA edition. os-release says `VARIANT="Gaming, NVIDIA"`, `VARIANT_ID=gaming-nvidia`, `IMAGE_ID=lumen-gaming-nvidia` (`os-release.sh` takes IDs in parts joined by `-`), and the stage runs the NVIDIA edition's checks after its own.
- 2026-11-06: image run 42266385717 (for `ec08fc9`): the `nvidia` job passed in 85 minutes (lumen-nvidia 42, the gaming layer 16, two qcow2s 21, their checks 2, both boots 3). `lumen-gaming-nvidia` is 10.5 GB; Steam's 32-bit Mesa brought `xorg-x11-drv-nvidia-libs.i686` 615.78.08 from RPM Fusion, signature-checked, with 13 other 32-bit packages fetched at the image's versions. It passed the lumen checks (14), the gaming edition's (10), the NVIDIA edition's (6) and bootc's lint. Its qcow2 follows `lumen-gaming-nvidia:dev` and boots as "Lumen OS 0.1 (Gaming, NVIDIA)"; the boot test passed 13 of 13: Plasma Setup 21 s after the kernel, the greeter 11 s, Steam Big Picture and Plasma offered, nouveau from the fallback service, NVIDIA's module refused, no failed units or denials. `lumen-nvidia` passed 12 of 12 in the same job.
