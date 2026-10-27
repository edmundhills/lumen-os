<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# design

Lumen's look: the design tokens and everything made from them.

| Part | What it is | Steps |
| --- | --- | --- |
| [tokens/](tokens/) | `tokens.json`, its schema, and the exporters that turn it into each toolkit's theme | 2.1 to 2.7, 2.12 |
| Window decoration | A KDecoration plugin: rounded corners and the glass title bar | 2.8, 2.9 |
| Cursor and icon themes | Configuration for an open icon set, recoloured with the accent | 2.10 |
| Global theme | The Plasma look-and-feel package `org.lumen.desktop` | 2.11 |

It ships as two RPMs built in the image's `build-design` stage:

- `lumen-theme`: the tokens, the exporters' output, the `org.lumen.style` QML module and the global theme.
- `lumen-decoration`: the decoration plugin. KWin loads it, so it is built against the image's exact KWin, like every KWin plugin.

Spec: [Liquid glass](../docs/spec.md#liquid-glass-how-to-do-it-right), [Design tokens](../docs/spec.md#design-tokens). Architecture: [4.3 Design tokens](../docs/architecture.md#43-design-tokens).
