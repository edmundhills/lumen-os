<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# installer

What the install USB adds to the Lumen image: Lumen's kickstart and its theme for Anaconda WebUI, the installer.

The install media is a live ISO built from the Lumen image ([ADR 0002](../docs/decisions/0002-fix-spec-errors-from-architecture-review.md)). It starts a Lumen live session that shows the hardware report, then starts Anaconda WebUI with the files from this folder. The installer offers three choices: Erase disk (the default, encrypted), Install alongside Windows, and Custom. Installing alongside Windows never resizes a BitLocker volume.

| Path | What it is | Step |
| --- | --- | --- |
| `anaconda/lumen.conf` | Anaconda's install profile for Lumen, installed in the live stage's `/etc/anaconda/profile.d/`: Btrfs with zstd compression, and `/home` as a subvolume of its own for snapper's snapshots. Without it, a system whose os-release says `ID=lumen` gets Anaconda's built-in LVM layout. The live stage's checks (`image/live/check-live.sh`) run Anaconda 44.30's own config loader on it | 1.4, 1.8b |

- **Ships as:** RPM `lumen-installer`, used only by the image's `live` stage, which makes the install media. Until the image has build stages for RPMs, the `live` stage copies these files in directly.
- **Steps:** 1.8b (the live ISO; the tool that builds it is recorded in an ADR), 1.8c (installing the ISO's copy of the image, so the system checks signatures from the start) and 6.10 (the theme and the three choices).

Spec: [Installer](../docs/spec.md#installer). Architecture: [4.8 Installer](../docs/architecture.md#48-installer), [9.6 Disk images and install media](../docs/architecture.md#96-disk-images-and-install-media). Risks: [5](../docs/risks.md#5-building-the-install-iso-as-a-live-iso-from-a-bootc-image).
