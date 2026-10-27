<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# design/tokens

`tokens.json` holds every value of Lumen's design in one place: colours for light and dark with 8 accents, the type scale, radii, spacing, elevation, the glass preset for each surface role, and the spring animations. The exporters turn it into each toolkit's format during the image build, so a change here reaches every app.

| Output | Read by | Step |
| --- | --- | --- |
| `tokens.json` itself, at `/usr/share/lumen/tokens/` | lumen-glass, lumen-settingsd | 2.1, 2.2 |
| QML module `org.lumen.style` | lumen-shell and Lumen's apps | 2.3 |
| KDE colour schemes | Qt and KDE apps | 2.4 |
| Kvantum theme | Qt apps | 2.5 |
| GTK 4 / libadwaita CSS | GTK 4 apps | 2.6 |
| GTK 3 theme | GTK 3 apps | 2.7 |

- A JSON schema checks `tokens.json` in CI (steps 2.1 and 2.2).
- The exporters run during the image build (step 2.12).
- Light or dark and the accent are the user's choice, so lumen-settingsd applies them at run time.

Spec: [Design tokens](../../docs/spec.md#design-tokens). Architecture: [4.3 Design tokens](../../docs/architecture.md#43-design-tokens).
