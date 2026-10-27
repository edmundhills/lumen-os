<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# shell

lumen-shell, the desktop itself: the Plasma shell package `org.lumen.desktop` with Lumen's own containments and plasmoids. It draws the top bar, the dock, the command palette, quick settings, the notification centre, the overview and tiling, the lock and login screens, and the on-screen displays.

- **Language:** QML, with small C++ QML plugins and KWin scripts (JavaScript).
- **Runs in:** `plasmashell`, in the user's session.
- **Ships as:** RPM `lumen-shell`, built in the image's `build-shell` stage against that image's exact Plasma (CLAUDE.md, "Critical build rule").
- **Steps:** 4.1 to 4.19; acceptance at 4.20.

Spec: [lumen-shell](../docs/spec.md#spec-lumen-shell), [Default shortcuts and gestures](../docs/spec.md#default-shortcuts-and-gestures). Architecture: [4.4 lumen-shell](../docs/architecture.md#44-lumen-shell).
