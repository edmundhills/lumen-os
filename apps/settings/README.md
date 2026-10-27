<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# apps/settings

Settings (`org.lumen.Settings`): every setting in one app, with a glass sidebar, search across all pages, and System Health on the About & Health page. Other parts of Lumen open a page directly with a `lumen-settings://<page>` link.

- **Language:** C++ and QML (Qt 6).
- **Talks to:** lumen-settingsd, the system services, KDE's settings backends (KScreen, plasma-nm, BlueZ, plasma-pa, PowerDevil), AccountsService and firewalld.
- **Ships as:** RPM `lumen-settings`, built in the image's `build-apps` stage.
- **Steps:** 5.13 (the frame) to 5.22a (the pages); tests at 5.23.

Spec: [Lumen Settings and System Health](../../docs/spec.md#spec-lumen-settings-and-system-health). Architecture: [4.7 Apps](../../docs/architecture.md#47-apps).
