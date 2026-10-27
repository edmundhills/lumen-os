<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# glass

lumen-glass, the KWin effect that draws Lumen's glass behind bars, docks, menus and other surfaces: blur, edge refraction, tint and rim light, in three tiers (Full, Lite and Solid) so it stays fast on every GPU. It is a fork of KWin's blur effect and takes the place of KWin's blur and contrast effects.

- **Language:** C++ and GLSL.
- **Runs in:** `kwin_wayland`, in the user's session.
- **Ships as:** RPM `lumen-glass`, built in the image's `build-glass` stage against that image's exact KWin. KWin has no stable plugin ABI, so building it against any other KWin is not allowed (CLAUDE.md, "Critical build rule").
- **Licence:** KWin's blur effect is GPL-2.0-or-later. The forked files keep their copyright lines and licence headers, and Lumen's changes are GPL-3.0-or-later ([ADR 0003](../docs/decisions/0003-licence.md)).
- **Steps:** 3.1 (the fork) to 3.16; acceptance at 3.17.

Spec: [lumen-glass effect](../docs/spec.md#spec-lumen-glass-effect). Architecture: [4.2 lumen-glass](../docs/architecture.md#42-lumen-glass-compositor-effect). Risks: [1](../docs/risks.md#1-kwin-and-plasma-change-their-internals-every-release), [8](../docs/risks.md#8-glass-misses-its-frame-time-and-contrast-budgets).
