<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0005. Plasma Login Manager for the login screen, not SDDM

- Status: **Accepted** (2026-10-27). Applied to `docs/spec.md`, `docs/architecture.md`, `PROGRESS.md` and `image/packages.toml`.
- Deciders: owner (Edmund), lead engineer (Claude)

## Context

The spec named SDDM as Lumen's login manager in four places: the login screen row of the lumen-shell table ("SDDM theme (Wayland greeter)"), the boot test in the test layers table, and the Phase 1 and Phase 4 prompts. The architecture named it in sections 4.4 (login screen) and 4.5 (the post-boot health check), and `PROGRESS.md` in steps 1.9, 4.15 and 5.6.

Step 1.2, on 2026-10-27, read the package list of the pinned base, Kinoite `44.20261027.0` ([versions](../versions.md)). It has no SDDM. Fedora 44's KDE image ships KDE's **Plasma Login Manager** instead:

- `plasma-login-manager` 6.7.5, from KDE's Plasma group (`invent.kde.org/plasma/plasma-login-manager`) and released with Plasma, at the same version as KWin and Plasma in the image. Also `kcm-plasmalogin`, its page in Plasma's settings, and `kde-settings-plasmalogin`, Fedora's defaults.
- `plasmalogin.service` is installed as `display-manager.service`, which `graphical.target` starts.
- Its configuration follows SDDM's layout: `/etc/plasmalogin.conf` with a `plasmalogin.conf.d` folder, vendor defaults in `/usr/lib/plasmalogin/`, and the same session scripts (`Xsetup`, `Xstop`, `wayland-session`).
- It has no folder of greeter themes like SDDM's. Its greeter (`/usr/libexec/plasma-login-greeter`) runs a session of its own with KWin (`plasma-login-kwin_wayland.service`) and Plasma's wallpaper service.

The owner chose between two options:

1. **Keep Plasma Login Manager**, Fedora's default, and fix the documents.
2. **Add SDDM back**: install `sddm` and remove `plasma-login-manager` in `image/packages.toml`. This leaves Fedora's KDE defaults, so Lumen would carry a combination Fedora no longer tests, and its login screen would follow a different project from the rest of Plasma.

## Decision

Lumen uses Plasma Login Manager for its login screen (option 1).

- The documents say "login screen" where they mean the screen, and name Plasma Login Manager where they mean the component.
- `image/packages.toml` lists `plasma-login-manager` under `keep` in `[desktop]`, so the build stops if a future Kinoite drops it.
- The boot test (step 1.9) and the post-boot health check (step 5.6) check that the login screen is up: `display-manager.service` is active and its greeter is running.
- Step 4.15 restyles the greeter rather than writing an SDDM theme. Because the greeter runs on KWin and Plasma, Lumen's Plasma style, and possibly lumen-glass, may apply to it directly; step 4.15 works out how, and which settings it reads.

## Changes made to docs/spec.md

- Package manifest: the Desktop row includes Plasma Login Manager.
- Spec: lumen-shell: the login screen is built on Plasma Login Manager's greeter, restyled.
- Test layers: the boot test boots to the login screen in under 60 seconds.
- The Phase 1 and Phase 4 prompts: "the login screen" instead of SDDM.

## Changes made elsewhere

- `docs/architecture.md`: sections 4.4 and 4.5.
- `PROGRESS.md`: steps 1.9, 4.15 and 5.6.

## Consequences

- Lumen follows Fedora's KDE defaults for the login screen, so Fedora's updates and testing cover it.
- Plasma Login Manager is newer than SDDM and less documented. Step 4.15 may find that some of the spec's login screen features (glass theme, user avatars, accessibility menu) need upstream changes; any patch gets its own ADR.
- Plasma Login Manager is released with Plasma, so it moves with every Plasma feature release, like KWin. The login screen's styling is checked at each one, together with lumen-glass ([architecture 9.4](../architecture.md#94-matching-the-base-image-exactly)).
