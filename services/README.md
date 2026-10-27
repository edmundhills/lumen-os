<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# services

Lumen's background services, written in Rust with zbus. Each one owns one job and offers it over D-Bus. Settings, the shell and the `lumen` command all call the same methods, so the GUI and the command line can never disagree.

| Folder | Service | D-Bus name | Bus | Steps |
| --- | --- | --- | --- | --- |
| [updated/](updated/) | lumen-updated | `org.lumen.Updates1` | System | 5.4 to 5.7 |
| [health/](health/) | lumen-health | `org.lumen.Health1` | System | 5.8, 5.9 |
| [hwd/](hwd/) | lumen-hwd | `org.lumen.Hardware1` | System | 5.10 |
| [settingsd/](settingsd/) | lumen-settingsd | `org.lumen.Settings1` | Session | 5.2 |
| [backupd/](backupd/) | lumen-backupd | `org.lumen.Backup1` | Session | 5.11 |

- The services and the CLI form one Cargo workspace, built in the image's `build-rust` stage. Each service ships as its own RPM.
- Step 5.1 sets up the workspace, a shared crate for the D-Bus interfaces, and the templates for hardened systemd units and polkit policies. The architecture proposes keeping the D-Bus interface XML files in `services/interfaces/`.
- D-Bus activation starts each service on its first call. polkit checks every privileged call on a system service.

Spec: [lumen CLI and services](../docs/spec.md#spec-lumen-cli-and-services). Architecture: [2. Conventions](../docs/architecture.md#2-conventions), [4.5 Services](../docs/architecture.md#45-services).
