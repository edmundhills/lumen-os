<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# services/backupd

lumen-backupd (`org.lumen.Backup1`) runs the user's backups with restic, on a schedule, to external drives, network shares and S3-compatible storage, and restores from them. Backup passwords are kept in the Secret Service (KWallet), never in config files.

- **Language:** Rust (zbus).
- **Runs as:** the user, on the session bus. The schedules are systemd user timers.
- **Ships as:** RPM `lumen-backupd`, built in the image's `build-rust` stage.
- **Steps:** 5.11; the [Backup app](../../apps/backup/) at 6.8.

Spec: [Snapshots and backup](../../docs/spec.md#snapshots-and-backup). Architecture: [lumen-backupd](../../docs/architecture.md#lumen-backupd-orglumenbackup1).
