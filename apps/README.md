<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# apps

Lumen's own apps. They are part of the OS, so they ship as RPMs in the image, not as Flatpaks: they need the system services and must match the image's version. Other apps come from Flathub.

| Folder | App | App ID | Steps |
| --- | --- | --- | --- |
| [settings/](settings/) | Settings | `org.lumen.Settings` | 5.13 to 5.22a |
| [store/](store/) | Store | `org.lumen.Store` | 6.1 to 6.4, 7.7 |
| [welcome/](welcome/) | Welcome, the first-run setup | `org.lumen.Welcome` | 6.5 to 6.7, 7.8 |
| [backup/](backup/) | Backup | `org.lumen.Backup` | 6.8 |
| [windows-app/](windows-app/) | The "Open Windows app" dialog | `org.lumen.WindowsApp` | 7.5, 7.6 |

- All of them are C++ and QML (Qt 6), built in the image's `build-apps` stage.
- On Wayland the app ID is how KWin and the dock match a window to its app, so it must equal the name of the app's desktop file.
- The hardware report (`org.lumen.HardwareReport`, step 6.12) has no folder yet. The architecture proposes `apps/hwreport`, which the owner reviews at step 0.8.

Architecture: [4.7 Apps](../docs/architecture.md#47-apps).
