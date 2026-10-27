<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# installer

What the install USB adds to the Lumen image: Lumen's kickstart and its theme for Anaconda WebUI, the installer.

The install media is a live ISO built from the Lumen image ([ADR 0002](../docs/decisions/0002-fix-spec-errors-from-architecture-review.md)). It starts a Lumen live session that shows the hardware report, then starts Anaconda WebUI with the files from this folder. The installer offers three choices: Erase disk (the default, encrypted), Install alongside Windows, and Custom. Installing alongside Windows never resizes a BitLocker volume.

- **Ships as:** RPM `lumen-installer`, used only by the image's `live` stage, which makes the install media.
- **Steps:** 1.8 (the live ISO; the tool that builds it is recorded in an ADR) and 6.10 (the theme and the three choices).

Spec: [Installer](../docs/spec.md#installer). Architecture: [4.8 Installer](../docs/architecture.md#48-installer), [9.6 Disk images and install media](../docs/architecture.md#96-disk-images-and-install-media). Risks: [5](../docs/risks.md#5-building-the-install-iso-as-a-live-iso-from-a-bootc-image).
