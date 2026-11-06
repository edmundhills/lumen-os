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
- **Flathub in Kinoite 45:** the image has Fedora's `fedora-flathub-remote` and `fedora-third-party` packages (the layers of `lumen:dev`), and Fedora 44's change "Filter Fedora Flatpaks for Atomic Desktops v2" turns Flathub on by default for the atomic desktops. Fedora's own hosts aren't reachable from the cloud session, so which file sets Flathub up is first seen in the image build, which checks it.
- **Bottles' desktop file** (bottlesdevs/Bottles at `fdeaff1`) declares `application/x-ms-dos-executable`, `application/x-msi`, `application/x-ms-shortcut` and `application/x-wine-extension-msp`. Which type the image's shared-mime-info gives `*.exe` files is also first seen in the build; newer releases have more than one name for Windows programs.
- **The fonts** are in already: Kinoite has Liberation, which the manifest keeps, and `image/packages.toml` installs Carlito and Caladea (step 1.1).

## Decision

1. **ntsync loads at every start**: `/usr/lib/modules-load.d/lumen-ntsync.conf` names it. `check-image.sh` checks the file and that the image's kernel has the module; the boot test checks that `/dev/ntsync` exists with mode 0666.
2. **Bottles comes through Flatpak's preinstall.** `/usr/share/flatpak/preinstall.d/lumen.preinstall` lists `com.usebottles.bottles` (branch `stable`), and `lumen-flatpak-preinstall.timer` starts `lumen-flatpak-preinstall.service` two minutes after each start: `flatpak preinstall --system --assumeyes --noninteractive`, at low CPU and I/O priority, and only once NetworkManager reports a connection (`nm-online`). Without one, the run is skipped, not failed, and the next start tries again. The timer keeps the download out of the way of the login screen and the first-run setup. Welcome and the Store add the other apps the spec preinstalls to the same list.
3. **Flathub is Fedora's remote**, from Kinoite's signed `fedora-flathub-remote` package, which Lumen trusts as it trusts the rest of Kinoite. `check-image.sh` requires a `remotes.d` file for `https://dl.flathub.org/repo/`, unfiltered, and that no other unit runs `flatpak preinstall`.
4. **`.exe` and `.msi` files open in Bottles**: `/usr/share/applications/mimeapps.list` makes Bottles the default, and adds it as an app, for `application/x-ms-dos-executable`, `application/x-msdownload`, `application/vnd.microsoft.portable-executable` and `application/x-msi`. A user's choice in `~/.config/mimeapps.list` wins. `image/windows_apps.py` checks in the build that shared-mime-info gives `*.exe` and `*.msi` types the list names, that no other list Plasma reads sets them, and that no package owns Lumen's list. Phase 7's dialog takes these types over.

## Consequences

- An online first start downloads Bottles and its GNOME runtime in the background, from two minutes after the start; an offline one gets them at the next online start. Until Bottles is there, double-clicking an `.exe` asks which app to use.
- The boot test's VM has no network, so CI checks that the timer waits and the service skips, not the download. Double-clicking an `.exe` and seeing Bottles is part of the Phase 1 acceptance (step 1.17), on a machine with a network.
- Fedora's own Flatpak remote stays as Kinoite sets it up. Whether the Store shows it is the Store's decision (Phase 4).
- If a later Kinoite drops Flathub from `remotes.d`, filters it, or starts running `flatpak preinstall` itself, the image check stops the build and says which.
