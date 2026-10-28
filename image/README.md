<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# image

The Lumen OS image: an OCI container image built `FROM` Fedora Kinoite and managed by bootc. It is the whole operating system, and it updates as one piece.

| Path | What it is | Step |
| --- | --- | --- |
| `packages.toml` | The package manifest: the Fedora packages Lumen keeps from Kinoite, adds and removes, by the areas of the spec's manifest | 1.1 |
| `packages.py` | Checks the manifest (`just lint`) and applies it in the `base` stage. It stops the build if the manifest doesn't match Kinoite, or if dnf removes a package the manifest doesn't list. `test_packages.py` holds its unit tests (`just test`) | 1.1 |
| `Containerfile` | The multi-stage build. Phase 1 has `base` (Kinoite plus the manifest) and `lumen` (the image users get, ending with `bootc container lint`); `devel`, the build stages, the variants and `live` come with their steps | 1.2 |
| `overlay/` | Files copied into the image as they are: vendor defaults in `/usr/lib` and `/usr/share`, and the image's `/etc` only where a setting can live nowhere else. Never `/usr/etc` (ADR 0002) | 1.3 |
| `check-image.sh` | Checks the built image: the overlay's files and their modes, the units Lumen turns on and masks, Lumen's units valid, a Btrfs root for `bootc install`, SELinux enforcing, Discover gone, Lumen's global theme the default, and os-release. The `lumen` stage runs it before `bootc container lint` | 1.3, 1.4, 1.5a |
| `build_version.py` | Works out the build version, `<Fedora release>.<build date>` with `.1`, `.2` for further builds on the same day ([architecture 9.7](../docs/architecture.md#97-versions-tags-and-keys)), for `just build-image` and CI. `test_build_version.py` holds its unit tests | 1.5a |
| `os-release.sh` | Writes Lumen's `/usr/lib/os-release` in the `lumen` stage: `ID=lumen`, `ID_LIKE=fedora`, the product version as `VERSION_ID` and the build version as `IMAGE_VERSION`. The stage also sets the image labels, among them `org.opencontainers.image.version` | 1.5a |
| `test_home_snapshots.py` | Unit tests for the snapshots of `/home`: the setup script's choices, with stand-ins for `stat`, `snapper` and `restorecon`, and the template's limits against the spec (`just test`) | 1.4 |

What the overlay sets up so far:

| Path in the image | What it does | Step |
| --- | --- | --- |
| `/usr/lib/systemd/system-preset/40-lumen.preset` | Turns on firewalld, `fwupd-refresh.timer`, snapper's timers, tuned and tuned-ppd. The build applies it, and so does systemd on a new machine's first boot. The Containerfile also masks Fedora's own updaters and its countme ping | 1.3 |
| `/usr/share/plasma/look-and-feel/org.lumen.desktop/` | Lumen's interim global theme: Fedora's look, with an interim 32 px top bar (app menu, open windows, system tray, clock) in place of Kinoite's stock panel. Step 2.11 replaces the theme, step 4.2 the bar | 1.3 |
| `/etc/xdg/kdeglobals` | Makes that theme the default. KDE reads system-wide defaults only from its config folders, and `/etc/xdg` is the first | 1.3 |
| `/usr/lib/systemd/system/lumen-home-snapshots.service`, `/usr/libexec/lumen-home-snapshots` | On the first boot, makes snapper's `home` config for `/var/home` (where `/home` points) from Lumen's template, if `/var/home` is a Btrfs subvolume. Otherwise it says why there are no snapshots and exits without failing. It runs at each boot until the config exists | 1.4 |
| `/usr/share/snapper/config-templates/lumen-home` | The snapshot settings: 24 hourly, 7 daily and 4 weekly (spec, "Snapshots and backup"); everything else is snapper's default | 1.4 |
| `/usr/lib/bootc/install/20-lumen.toml` | `bootc install`, and bootc-image-builder with it, make a Btrfs root. Compression is a mount option the installer sets ([`installer/anaconda/lumen.conf`](../installer/anaconda/lumen.conf)); bootc has no setting for it, so disks bootc makes itself aren't compressed | 1.4 |

- Kinoite is pinned by digest. Every Lumen package that links KWin or Plasma is built in a stage of this Containerfile against that exact base (CLAUDE.md, "Critical build rule").
- Everything in `overlay/` lands in the image's root folder, so `overlay/` holds only files meant for the image, and no README.
- The build copies the overlay with modes it sets itself: 0644 for files and 0755 for new folders, and 0755 for Lumen's programs in `/usr/libexec`. A Windows checkout seen from WSL shows every file as 0777, and the image must not inherit that.
- Variants: `lumen` (the default), `lumen-gaming` (step 1.10), `lumen-nvidia` (step 1.11) and `lumen-gaming-nvidia` (step 1.12, ADR 0004).

Spec: [image build and layout](../docs/spec.md#spec-image-build-and-layout). Architecture: [4.1 Base image](../docs/architecture.md#41-base-image), [9.3 Inside the image build](../docs/architecture.md#93-inside-the-image-build), [9.5 Variants](../docs/architecture.md#95-variants).
