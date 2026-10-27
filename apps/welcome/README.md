<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# apps/welcome

Welcome (`org.lumen.Welcome`), the first-run setup: language and keyboard, Wi-Fi, the user account with fingerprint, unlocking the encrypted disk with the TPM and saving the recovery key, privacy, the look, importing files from a Windows or macOS drive, apps, and a short gesture tour. Its "Your Windows apps" list shows what happens to each program installed on the Windows drive.

- **Language:** C++ and QML (Qt 6).
- **Runs as:** a first-boot session before any user exists, then the new user ([Q8](../../docs/architecture.md#8-spec-problems-and-open-questions) in the architecture).
- **Ships as:** RPM `lumen-welcome`, built in the image's `build-apps` stage.
- **Steps:** 6.5 to 6.7; "Your Windows apps" at 7.8.

Spec: [Welcome (first run)](../../docs/spec.md#welcome-first-run). Architecture: [4.7 Apps](../../docs/architecture.md#47-apps).
