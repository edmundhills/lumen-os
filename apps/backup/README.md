<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# apps/backup

Backup (`org.lumen.Backup`): backs up the user's files on a schedule to an external drive, a network share (SMB) or S3-compatible storage, and restores them. It is the front end of lumen-backupd, which runs restic.

- **Language:** C++ and QML (Qt 6).
- **Talks to:** lumen-backupd (`org.lumen.Backup1`).
- **Ships as:** RPM `lumen-backup`, built in the image's `build-apps` stage.
- **Steps:** 6.8.

Spec: [Snapshots and backup](../../docs/spec.md#snapshots-and-backup). Architecture: [lumen-backupd](../../docs/architecture.md#lumen-backupd-orglumenbackup1).
