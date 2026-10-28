<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0006. Lumen's own look: light through glass

- Status: **Accepted** (2026-10-28). Applied to `docs/spec.md`, `PROGRESS.md`, `image/packages.toml` and `design/README.md`.
- Deciders: owner (Edmund), lead engineer (Claude)

## Context

On 2026-10-27 Claude made a clickable mockup of the desktop as the spec described it. It lives in the owner's claude.ai account, not in this repo. The owner's verdict was that it looked "way too much like macOS" and "another off-brand macOS". Lumen needs a character of its own.

The resemblance came from the spec's layout and from defaults nobody had chosen on purpose:

- A full-width top bar showing the focused app's name and its menu, which is how macOS's menu bar works.
- A centred dock of colourful rounded-square icons.
- Inter as the interface font. Inter is a neo-grotesque that reads much like Apple's system font.
- A blue accent and a pastel wallpaper.

A second mockup, made on 2026-10-28, built the look around one idea: Lumen is light passing through glass. The owner accepted it and asked for this ADR.

The first proposal used the Red Hat font family (Display, Text and Mono) for everything. On 2026-10-28 Claude checked the Fedora 44 font packages with `fc-query` against the pinned Kinoite. None of these fonts is in Kinoite yet.

| Family | Fedora package | Languages fontconfig reports | Russian, Ukrainian | Greek | Vietnamese |
| --- | --- | --- | --- | --- | --- |
| Inter 4.1 | `rsms-inter-fonts` | 185 | yes | yes | yes |
| Red Hat Display, Text and Mono 4.1.0 | `redhat-display-fonts`, `redhat-text-fonts`, `redhat-mono-fonts` | 126 | no | no | no |
| Source Sans 3 (3.052) | `adobe-source-sans-pro-fonts` | 178 | yes | yes | yes |
| JetBrains Mono 2.304 | `jetbrains-mono-fonts` | 154 | yes | yes | yes |

The Red Hat fonts cover Latin-script languages only. Used for all interface text, Cyrillic, Greek and Vietnamese would fall back to another font. Vietnamese would even mix fonts inside words, because its letters with stacked accents are missing. The owner chose Red Hat Display for display text and Source Sans 3 for everything else.

## Decision

1. **The top bar is three floating islands.**
   - Each island is 32 px tall, sits 6 px below the top edge of the screen, and is a separate glass surface with role `bar`.
   - **Left:** the Lumen mark (opens the overview, in place of the "Activities" button), a workspace indicator, and the focused app's name. The app's menu is not shown here.
   - **Centre:** the clock and date, with a count of unread notifications. A click opens the calendar and notifications.
   - **Right:** tray, network, sound, battery (with a level meter) and the user.
   - Each island is its own Plasma panel, floating and sized to its content, aligned left, centre or right. That keeps each island a single glass surface, so lumen-glass needs nothing new. Step 4.2 checks that Plasma 6.7 can place three such panels on one edge.
   - If Plasma can't, one transparent containment draws all three, with a glass rectangle per island. lumen-glass then has to clip several rounded rectangles in one surface, which changes step 3.5.

2. **App menus live in the window.**
   - Lumen's window decoration has an app menu button (⋯) next to minimise, maximise and close.
   - Apps that publish their menu over D-Bus show it there and hide their own menu bar. Qt and KDE apps do this through Plasma's app menu service.
   - Other apps keep their own menus, such as GTK header bars and hamburger menus.
   - Lumen's own apps put their menu behind the same button. Plasma's global menu widget is not used.
   - The title is left-aligned next to the app's icon. The window buttons are rounded rectangles, not circles.

3. **Fonts.**

   | Role | Font | Used for |
   | --- | --- | --- |
   | Display | Red Hat Display | The clock, headings and page titles, section labels, the lock screen time |
   | Interface | Source Sans 3 | Everything else: KDE's general, menu, toolbar, small and window title fonts, GTK, and app names in the top bar |
   | Code | JetBrains Mono | The terminal, code and fixed-width text |

   - Red Hat Display is only used where Lumen controls the text. The `org.lumen.style` module switches display text to Source Sans 3 Semibold when the interface language uses characters Red Hat Display lacks: Cyrillic, Greek, Vietnamese and every non-Latin script.
   - Lumen's fontconfig settings name Source Sans 3 as the fallback for Red Hat Display.
   - Window titles and app names come from the apps, so they always use Source Sans 3.
   - Inter is no longer installed.

4. **App icons are lenses.**
   - In the shell (dock, command palette, overview, notifications) and in the Store, every app icon is a round lens: a disc with the app's symbol and a ring in the app's colour.
   - Lumen's own apps and the apps in the image get lens icons drawn for Lumen.
   - Other apps, such as Flatpak apps that bring their own icons, are shown inside a lens frame: their own icon scaled into a disc, with a ring tinted from the icon's main colour.
   - Symbolic icons in the interface stay an open icon set, recoloured with the accent.

5. **Accents are named for kinds of light, and Sunbeam is the default.** These are starting values; step 2.1 tunes them.

   | Accent | Starting value |
   | --- | --- |
   | Sunbeam (default) | `#eca516` |
   | Ember | `#ee6a3a` |
   | Rose | `#ec5a8c` |
   | Orchid | `#b06cf2` |
   | Iris | `#6f7dff` |
   | Glacier | `#3ea2f0` |
   | Lagoon | `#1fbfae` |
   | Moss | `#7cc04a` |

   Each accent gets three token values, and each is checked for 4.5:1 contrast:
   - a fill;
   - the text colour on that fill: dark on light accents, white on deep ones;
   - an "ink" shade for accent-coloured text on light and on dark surfaces.

   Sunbeam shows why all three are needed. With the starting value, dark text on it reaches about 8.9:1, but white text on it, or gold text on white, only about 2.1:1.

6. **The focused window is lit.**
   - A thin line of accent light runs along the top edge of the focused window's title bar, with a soft glow.
   - Other windows are unlit, and their title bar icon turns grey.
   - Lumen's window decoration draws it for windows with server-side title bars. lumen-glass draws it for apps that draw their own title bars.
   - With Reduce Motion it appears without fading in.

7. **The dock has a search field and lights its running apps.**
   - The dock starts with a "Search or run" field that opens the command palette (Super+Space).
   - A running app shows a short line of light in its own colour under its icon, longer for the focused app. This replaces the running dot.
   - Download and install progress is a ring round the icon.

These stay as the spec has them:

- the glass material, its tiers and parameters, the corner radii, and the springs;
- the 32 px height of the top bar, and the dock at the bottom centre;
- the command palette, the shortcuts and the Settings pages.

Not decided here: the default wallpaper, and how strongly glass edges show the RGB dispersion the spec already has. The mockup's wallpaper was a band of white light splitting into colour at its edges ("Dispersion"). Step 2.11 (the global theme, which sets the wallpaper) and step 3.6 (the rim light) settle them. The optional Windows-style "Familiar" layout stays deferred ([competing with Windows](../competing-with-windows.md)).

## Changes made to docs/spec.md

- Liquid glass: a new "Lumen's look" section after "Design tokens", summarising the decisions above.
- Easy by default, powerful underneath → The shell: the top bar as three islands, and the dock with its search field.
- Package manifest: the Input row lists Source Sans 3, Red Hat Display and JetBrains Mono instead of Inter.
- Spec: lumen-shell: the top bar and dock rows.
- The Phase 2 prompt: the type scale (Source Sans 3 and Red Hat Display), the eight named accents with three values each, the decoration's app menu button and lit edge, and lens icons.
- The Phase 3 prompt: the lit edge for apps that draw their own title bars.
- The Phase 4 prompt: the three islands and the dock's search field.

## Changes made elsewhere

- `image/packages.toml`: installs `redhat-display-fonts` and `adobe-source-sans-pro-fonts` instead of `rsms-inter-fonts`; `jetbrains-mono-fonts` stays.
- `PROGRESS.md`: steps 2.1, 2.9, 2.10, 2.11, 3.9, 4.2, 4.4 and 4.5. Step 2.11 sets the fonts and the fontconfig fallback.
- `design/README.md`: the window decoration and icon rows.

## Consequences

- Lumen no longer reads as a macOS imitation. Its layout still uses a top bar and a dock, but the islands, lens icons, gold accent and lit window are its own.
- Drawing lens icons for Lumen's apps and the image's apps is new design work in step 2.10. Before, that step only configured an existing icon set. The lens frame for other apps' icons is shell code (steps 4.4 and 4.6).
- Interface text in languages Red Hat Display doesn't cover gets the same quality as English, because all of it uses Source Sans 3. Only Lumen's display text changes font with the language, and the style module handles that in one place.
- Source Sans 3 has a smaller x-height than Inter, so the base interface size may need to be larger than Inter's 10 pt. Step 2.1 sets it.
- The three-island bar depends on Plasma panel features. If step 4.2 has to use the fallback, step 3.5's shader gains a multi-rectangle clip.
- The app menu button depends on apps publishing their menus. Apps that don't keep menus inside their windows, as they would on GNOME.
