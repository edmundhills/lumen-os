<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# services/settingsd

lumen-settingsd (`org.lumen.Settings1`) owns the user's Lumen settings. Each setting is a key in a TOML file in `~/.config/lumen/`. Every change, whether it comes from Settings, from `lumen settings` or from editing the file by hand, is announced with a `Changed` signal, which the shell, the glass effect and the apps react to.

- **Language:** Rust (zbus).
- **Runs as:** the user, on the session bus.
- **Ships as:** RPM `lumen-settingsd`, built in the image's `build-rust` stage.
- **Steps:** 5.2.

Spec: [lumen CLI and services](../../docs/spec.md#spec-lumen-cli-and-services). Architecture: [lumen-settingsd](../../docs/architecture.md#lumen-settingsd-orglumensettings1).
