<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# apps/store

Store (`org.lumen.Store`): finds, installs, updates and removes apps from Flathub with one button, and explains each app's permissions in plain English. Searching for a Windows or macOS app by name ("Photoshop", "Word") suggests the Linux alternatives, with the Windows app's compatibility rating beside them.

- **Language:** C++ and QML (Qt 6).
- **Talks to:** libflatpak and AppStream metadata; lumen-compat for compatibility ratings and the "Windows alternatives" collection.
- **Ships as:** RPM `lumen-store`, built in the image's `build-apps` stage.
- **Steps:** 6.1 to 6.4; the Windows features at 7.7.

Spec: [Lumen Store](../../docs/spec.md#lumen-store). Architecture: [4.7 Apps](../../docs/architecture.md#47-apps).
