<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0020. Take the Gamescope session from ChimeraOS, pinned file by file, without SteamOS's helpers

- Status: **Accepted** (2026-11-01), at step 1.10b.
- Deciders: lead engineer (Claude). The owner reviews it at the Phase 1 acceptance (step 1.17).

## Context

The spec's gaming image "adds Steam, Gamescope session, MangoHud, controller udev rules": Steam's Big Picture mode, full screen in Gamescope, as a session of its own, the way a Steam Deck starts. ADR 0019 put Steam and Gamescope in the `lumen-gaming` stage. What the session needs, read on 2026-11-01:

- **Fedora doesn't package a Gamescope session.** ChimeraOS's two repositories do, both MIT: `gamescope-session` (at `73d2da8`) has `gamescope-session-plus`, which runs a client in Gamescope through a systemd user unit, `gamescope-session-plus@.service`, with device quirks and a Gamescope script; `gamescope-session-steam` (at `1a3fdb7`) has the Steam client's settings (`sessions.d/steam`, which starts `steam -gamepadui -steamos3 …`), the login screen's entry (`wayland-sessions/gamescope-session-steam.desktop`, "Steam Big Picture", `Exec=gamescope-session-plus steam`) and `steamos-session-select`.
- **`gamescope-session-steam` also has SteamOS's helpers**: `steamos-update` (which updates ChimeraOS with its `frzr` tool), `jupiter-biosupdate` (a Steam Deck's firmware), `steamos-select-branch`, the `steamos-polkit-helpers` and a polkit policy, `org.chimeraos.update.policy`, that lets the session run them as root. They update another operating system.
- **Steam asks the system about updates** with `-steamos3`: `steamos-update --supports-duplicate-detection` should do nothing, `steamos-update [--enable-duplicate-detection] check` checks, and without `check` it applies one. Exit status 7 tells Steam there is no update; ChimeraOS's script answers that when its updater is missing.
- **"Switch to Desktop"** in Steam runs `steamos-session-select desktop`. It calls the operating system's hook, `/usr/lib/os-session-select`, if there is one, and otherwise shuts Steam down, which ends the session and brings back the login screen. Plasma Login Manager offers every session in `/usr/share/wayland-sessions` and remembers the last one each user chose.
- **The architecture leaves outside software that Fedora doesn't carry to COPR** (9.2), and no COPR is set up. Copying ChimeraOS's scripts into this repository would put foreign shell under Lumen's own lint (`shellcheck`, `shfmt`), which they don't follow, or need exceptions to it.

## Decision

1. **The files come from ChimeraOS's repositories, pinned file by file.** `image/gaming/session.toml` names each file by repository, full commit hash and SHA-256, with its mode and, for the licences, where it goes. In the `lumen-gaming` stage, `image/gaming/session.py` downloads each from `raw.githubusercontent.com` at that commit, stops the build if its SHA-256 differs, refuses to replace any file already in the image, and installs it unchanged; `check` reads the manifest in `just lint`, and `verify` checks the installed files in `check-gaming.sh`. Files may only go to `/usr/bin`, `/usr/lib/systemd/user` and `/usr/share`, with mode 0644 or 0755.
2. **Ten files, no helpers:** `gamescope-session-plus` (both parts), `device-quirks`, the user unit, the Gamescope script, the Steam session's settings, its login-screen entry, `steamos-session-select`, and both licences in `/usr/share/licenses`. Left out: SteamOS's update, firmware and branch helpers and their polkit policy, ChimeraOS's interactive `export-gpu`, and `steam-http-loader`.
3. **Lumen's own `steamos-update`** (`image/gaming/overlay/usr/bin/steamos-update`) answers 0 to `--supports-duplicate-detection` and 7, no update, to everything else. System updates are lumen-updated's (Phase 5), which applies them safely and asks first; Steam never updates the system.
4. **"Switch to Desktop" ends the session.** Lumen adds no `os-session-select` hook, so Steam shuts down, the session ends, and the login screen comes back, where the user picks Plasma. Going straight back to the desktop would mean changing Plasma Login Manager's autologin as root from the session, which Lumen doesn't do.
5. **Checks** in `image/gaming/check-gaming.sh`: the login-screen entry runs `gamescope-session-plus steam` from `PATH`, and the user unit and the Steam session's settings are there; every session file is the pinned one, with its mode; none of SteamOS's helpers or their policy are in the image, and `steamos-update` answers as above. Step 1.10c boots the gaming image's qcow2 and checks that the login screen offers the session.

## Consequences

- The gaming edition starts Steam the way a Steam Deck does, with nothing that runs SteamOS's updaters as root.
- The build fetches ten files from GitHub; if GitHub is down, the gaming build fails, not `lumen`'s. A new upstream version needs a new commit and new hashes in `session.toml`; nothing moves them automatically yet.
- The session's files belong to no RPM, as the overlay's don't.
- The login-screen entry's name, "Steam Big Picture", is ChimeraOS's English and isn't translated. When Welcome and Lumen's own session work arrive (Phase 6), a Lumen entry with translations can replace it.
- "Switch to Desktop" returns to the login screen rather than straight to the desktop.

## Follow-up

- 2026-11-01: image run 41322623199 (for `2ff7ec0`) built the gaming edition with the session in 17.8 minutes and passed: all ten files downloaded and matched their pins, and `check-gaming.sh`'s nine checks and bootc's lint passed. Whether the login screen offers the session, and whether it starts, is step 1.10c's boot test.
