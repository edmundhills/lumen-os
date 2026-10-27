<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# services/updated

lumen-updated (`org.lumen.Updates1`) keeps the whole system up to date: the OS image through bootc, Flatpak apps, firmware through fwupd, and the compatibility database. It downloads in the background at low priority, holds back on metered connections and low battery, and tells the shell when an update is ready. After an update it checks that the system booted properly and goes back to the previous version if it didn't. It also keeps the history of installed versions, so the user can go back to any of them.

- **Language:** Rust (zbus).
- **Runs as:** root, on the system bus. Started by D-Bus activation and by a timer.
- **Ships as:** RPM `lumen-updated`, built in the image's `build-rust` stage.
- **Steps:** 5.4 to 5.7; signed compatibility database updates at 7.3.

Spec: [updates, rollback and backup](../../docs/spec.md#spec-updates-rollback-and-backup). Architecture: [lumen-updated](../../docs/architecture.md#lumen-updated-orglumenupdates1).
