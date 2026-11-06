<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0024. Load ntsync at every start, bring Bottles with Flatpak's preinstall, and open Windows files in it

- Status: **Accepted** (2026-11-06), at step 1.13.
- Deciders: lead engineer (Claude). The owner reviews it at the Phase 1 acceptance (step 1.17).

## Context

Step 1.13 is the base for Windows apps (spec, "Windows apps", "Image contents" and Phase 1, item 7): Wine's `ntsync` module loaded on every image, Bottles preinstalled on first boot, `.exe` and `.msi` files opening in Bottles until the "Open Windows app" dialog exists (Phase 7), and the metric-compatible fonts. The boot test checks that `/dev/ntsync` exists. Facts, read on 2026-11-06:

- **ntsync** (`drivers/misc/ntsync.c` in Linux): a module (`CONFIG_NTSYNC`, tristate) that drives no hardware, so nothing loads it on demand. Its device is created with mode 0666. Wine and Proton use it whenever `/dev/ntsync` exists. Bottles' Flatpak has `--device=all` (flathub/com.usebottles.bottles at `65b266d`, on the GNOME 50 runtime), so its sandbox sees the device.
- **Flatpak's preinstall** (Flatpak 1.17.0, 2025-11-03; `man flatpak-preinstall`): the OS lists apps in `.preinstall` files in `/usr/share/flatpak/preinstall.d/` and runs `flatpak preinstall -y` at startup, which installs what is missing. An app the user uninstalls stays uninstalled.
- **Flatpak's remotes.d:** a `.flatpakrepo` file in `/usr/share/flatpak/remotes.d/` or `/etc/flatpak/remotes.d/` becomes a system remote the first time Flatpak runs.
- **Flathub in Kinoite 45:** the image has Fedora's `fedora-flathub-remote` and `fedora-third-party` packages (the layers of `lumen:dev`), and Fedora 44's change "Filter Fedora Flatpaks for Atomic Desktops v2" turns Flathub on by default for the atomic desktops. But the first build (image run 42301346343) found no `.flatpakrepo` file anywhere under `/usr/share/flatpak` or `/etc/flatpak`: Kinoite sets Flathub up some other way, if at all, and nothing makes it a remote on first use. Flathub's repository signing key has the fingerprint `6E5C 05D9 79C7 6DAF 93C0 8135 4184 DD4D 907A 7CAE`; Pop!_OS's copy of Flathub's `.flatpakrepo` (pop-os/default-settings) carries that key.
- **Bottles' desktop file** (bottlesdevs/Bottles at `fdeaff1`) declares `application/x-ms-dos-executable`, `application/x-msi`, `application/x-ms-shortcut` and `application/x-wine-extension-msp`. Kinoite 45's shared-mime-info gives `*.exe` files those and `application/x-dosexec`, `application/x-ms-ne-executable` and `application/x-lx-executable` too (the first build).
- **Fedora's `/usr/share/applications/mimeapps.list` belongs to shared-mime-info** (the first build). Plasma reads `kde-mimeapps.list` in the same folder before it, and the users' and `/etc/xdg`'s lists before both.
- **The fonts** are in already: Kinoite has Liberation, which the manifest keeps, and `image/packages.toml` installs Carlito and Caladea (step 1.1).

## Decision

1. **ntsync loads at every start**: `/usr/lib/modules-load.d/lumen-ntsync.conf` names it. `check-image.sh` checks the file and that the image's kernel has the module; the boot test checks that `/dev/ntsync` exists with mode 0666.
2. **Bottles comes through Flatpak's preinstall.** `/usr/share/flatpak/preinstall.d/lumen.preinstall` lists `com.usebottles.bottles` (branch `stable`), and `lumen-flatpak-preinstall.timer` starts `lumen-flatpak-preinstall.service` two minutes after each start: `flatpak preinstall --system --assumeyes --noninteractive`, at low CPU and I/O priority, and only once NetworkManager reports a connection (`nm-online`). Without one, the run is skipped, not failed, and the next start tries again. The timer keeps the download out of the way of the login screen and the first-run setup. Welcome and the Store add the other apps the spec preinstalls to the same list.
3. **Lumen sets Flathub up**: `/usr/share/flatpak/remotes.d/flathub.flatpakrepo`, Flathub's own settings with its key, which `test_windows_apps.py` checks against the fingerprint above. Flatpak adds it as the system remote `flathub`, unfiltered, the first time it runs. `check-image.sh` requires a `remotes.d` file for `https://dl.flathub.org/repo/` without a filter, and that no other unit runs `flatpak preinstall`.
4. **`.exe` and `.msi` files open in Bottles**: the `lumen` stage runs `image/windows_apps.py apply`, which puts Bottles first, as the default and as an added app, for the seven Windows program and installer types in Plasma's vendor list `/usr/share/applications/kde-mimeapps.list`, keeping whatever Fedora has there, or making the file. A user's choice in `~/.config/mimeapps.list` wins. `windows_apps.py check` checks in the image that every type shared-mime-info gives `*.exe` and `*.msi` is Bottles' in that list, and that no list Plasma reads before it says otherwise. Phase 7's dialog takes these types over.

## Consequences

- An online first start downloads Bottles and its GNOME runtime in the background, from two minutes after the start; an offline one gets them at the next online start. Until Bottles is there, double-clicking an `.exe` asks which app to use.
- The boot test's VM has no network, so CI checks that the timer waits and the service skips, not the download. Double-clicking an `.exe` and seeing Bottles is part of the Phase 1 acceptance (step 1.17), on a machine with a network.
- Fedora's own Flatpak remote stays as Kinoite sets it up. Whether the Store shows it is the Store's decision (Phase 4).
- If a later Kinoite drops Flathub from `remotes.d`, filters it, or starts running `flatpak preinstall` itself, the image check stops the build and says which.

## Follow-up

- 2026-11-06: the first build (image run 42301346343, for `3eacde7`) passed the ntsync check and found that Flatpak can preinstall, but stopped on the other two: Kinoite has no Flathub `remotes.d` file, and Lumen's `/usr/share/applications/mimeapps.list` would have replaced shared-mime-info's, which also lacked three of the `.exe` types. Decisions 3 and 4 were changed before the step closed: Lumen ships Flathub's `.flatpakrepo`, and the build puts Bottles into `kde-mimeapps.list`.
- 2026-11-06: the second build (image run 42304385533, for `7d18564`) passed every image check in `lumen`, but its update from `dev` went over the download budget: 339.5 MiB, because the new folders and the timer's preset link change the layer of files no package owns, which holds the initramfs, and Bottles in `kde-mimeapps.list` changes `plasma-desktop`'s layer, which owns that file. Each happens once, so the update from `45.20261106.1` is exempt (ADR 0007, Follow-up).
