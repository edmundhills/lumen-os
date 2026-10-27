<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# apps/windows-app

The "Open Windows app" dialog (`org.lumen.WindowsApp`) opens when someone double-clicks a `.exe` or `.msi` file. It shows the program's compatibility rating, the reason, and the alternatives. Install then puts the program in its own Bottles sandbox with tested settings and adds it to the app menu; for a program nobody has tested yet, it offers Try it. Nothing installs until the user presses a button.

- **Language:** C++ and QML (Qt 6).
- **Talks to:** lumen-compat (the offline compatibility lookup) and Bottles.
- **Ships as:** RPM `lumen-windows-app`, built in the image's `build-apps` stage.
- **Steps:** 7.5 and 7.6. Until then, `.exe` and `.msi` files open in Bottles directly (step 1.13).

Spec: ["Open Windows app" dialog](../../docs/spec.md#open-windows-app-dialog). Architecture: [4.9 Windows apps and switching](../../docs/architecture.md#49-windows-apps-and-switching).
