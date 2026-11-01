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
2. **RPM Fusion for Steam only, for one step.** `image/gaming/rpmfusion-nonfree.repo` holds RPM Fusion's two nonfree repositories, turned on and limited with `includepkgs=steam`, with RPM Fusion's key from this repository (`image/gaming/`), which the step checks against `keys.sha256` first. The step copies the file into `/etc/yum.repos.d` and deletes it again, so the image keeps no RPM Fusion repository. `test_gaming.py` checks the key's fingerprint, the pin and the repository's limits. The key stays in rpm's keyring in the image, as the key that signed an installed package.
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

- The first CI build will say which 32-bit packages Steam brings, how many came from Koji, and how much the edition adds to the image.
