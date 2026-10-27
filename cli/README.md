<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# cli

The `lumen` command: everything the Settings app can do, from a terminal. Each command calls the same D-Bus methods as the GUI, and `--json` prints the same data they return, so the two always agree.

| Command | Does | Step |
| --- | --- | --- |
| `lumen settings` | Get, set, list, export and import any Lumen setting | 5.3 |
| `lumen update`, `lumen rollback` | Check for and apply updates; list versions and go back | 5.7 |
| `lumen health [--fix]` | Run the System Health checks, and apply safe fixes | 5.9 |
| `lumen hw report` | The hardware report | 5.10 |
| `lumen backup` | Back up now, list backups, restore | 5.11 |
| `lumen app`, `lumen dev enable`, `lumen glass tier` | Apps, developer mode, the glass tier | 5.12 |
| `lumen app check <file>` | The compatibility rating of a `.exe` or `.msi` | 7.4 |

- **Language:** Rust (clap), in the same Cargo workspace as the [services](../services/).
- **Ships as:** RPM `lumen-cli` (`/usr/bin/lumen`), built in the image's `build-rust` stage, with completions for bash, zsh and fish.

Spec: [CLI reference](../docs/spec.md#cli-reference). Architecture: [4.6 `lumen` CLI](../docs/architecture.md#46-lumen-cli).
