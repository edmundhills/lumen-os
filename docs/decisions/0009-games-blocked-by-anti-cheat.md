<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0009. Help with games that anti-cheat blocks: cloud gaming, "Play in Windows", and checked ratings

- Status: **Accepted** (2026-10-29).
- Deciders: the owner, who asked for all three; lead engineer (Claude), who proposed them.

## Context

The spec shows a game's anti-cheat status before install and lists "games whose kernel anti-cheat the publisher hasn't enabled for Linux" among Lumen's honest limits. The owner asked whether Lumen could make those games run. What was found on 2026-10-29:

- **No operating system can switch them on.** Kernel anti-cheat (Riot's Vanguard, Call of Duty's Ricochet, FACEIT, EA's anti-cheat) is a Windows kernel driver, and Proton and Wine run Windows programs, not drivers. Easy Anti-Cheat and BattlEye do support Linux, through Proton, but only where the publisher turns that on. Making a game believe it runs on Windows is what cheat tools do, and gets accounts banned. SteamOS is Linux with the same Proton, and has the same limits.
- **What AreWeAntiCheatYet says** (its `games.json`, commit `6c26305e`): of 1,167 games with anti-cheat, 196 are supported on Linux by their publisher, 280 run without that, 2 are planned, 53 are denied (the publisher blocks Linux on purpose) and 636 are broken.
- **Why the broken ones are broken:**
  - 227 use Easy Anti-Cheat or BattlEye that was never switched on;
  - 66 are a competitive platform such as FACEIT or ESL, not the game itself;
  - about 280 use older anti-cheats, mostly in Asian online games (nProtect GameGuard 112, XIGNCODE3 63, X-Trap 46, Anti-Cheat Expert 27). Some of these fail on something Wine doesn't do yet rather than on a publisher's refusal, so Wine and Proton improvements can move them to "running";
  - 29 use PunkBuster, which is discontinued.
- **The data ages.** Only 32 of the 636 broken entries changed after 2025-01-01, so some may run today.
- **Cloud gaming works for some of them.** Services such as GeForce NOW and Xbox Cloud Gaming run the game on Windows in a data centre and stream it, so its anti-cheat is satisfied. They run in a web browser, and Lumen's Store can already install a website as an app. Which games each service carries changes often, and whether Lumen may use their catalogues needs checking.
- **Starting Windows once.** A firmware's one-time boot (UEFI `BootNext`) starts Windows Boot Manager directly, the way Windows starts on its own. Starting Windows from Lumen's boot menu instead measures Lumen's boot loader into the TPM as well, which can make BitLocker ask for its recovery key.

## Decision

1. **Cloud gaming as an alternative.** For a game that anti-cheat blocks on Linux, the compatibility database lists the cloud-gaming services that carry it as alternatives. The Store's game page, the "Open Windows app" dialog and `lumen app check` offer them, with what each needs (free, a subscription, or the game bought on that store). Where that list comes from, and whether its terms allow it, is part of step 7.1's check of every data source.
2. **"Play in Windows".** On a computer that also has Windows, a blocked game's Store page and dialog, and the app menu, offer a button that restarts the computer once into Windows through the firmware's `BootNext`. The next restart returns to Lumen. It asks first, shows only when the firmware has a Windows Boot Manager entry, and never uses Lumen's boot menu to start Windows.
3. **Checked ratings.** When step 7.2 imports AreWeAntiCheatYet, a game marked broken whose recent ProtonDB reports say it runs is rated "May work, not yet confirmed", not "Won't work". The nightly compatibility job and maintainers confirm it either way. Lumen still never helps a game get past its anti-cheat.

## Consequences

- The spec's Games section, compatibility database and honest limits, its Phase 7 list, PROGRESS.md steps 7.1, 7.2, 7.7, 7.10a and 7.11, and the gap list's games table say so.
- Setting `BootNext` needs root, so a privileged service does it through polkit. lumen-updated already owns restarts, so it is the likely place; step 7.10a decides.
- A cloud service may drop a game. The alternatives come with the signed database updates (step 7.3), and the database records when each was last checked.
