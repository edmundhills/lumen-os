# 0001. Make switching from Windows a primary goal

- Status: **Proposed** (2026-10-27), waiting for the owner's approval
- Deciders: owner (Edmund), lead engineer (Claude)

## Context

The owner wants Lumen OS to compete with Windows. The spec treats Windows apps as one row of the problems table, a Bottles shortcut, and step 6.4 near the end of the plan. Nothing tells a user *before* they install whether their apps and games will work, and several switching problems (BitLocker, Fast Startup, the 2026 Secure Boot certificate change, apps that came with the PC) aren't covered at all.

The full gap list, with what Linux does today and what Lumen would do, is in [docs/competing-with-windows.md](../competing-with-windows.md).

A custom kernel was considered and rejected. Windows apps call Windows libraries, not the kernel, and Wine reimplements those libraries. The one kernel feature Wine needed (`ntsync`) has been in mainline Linux since 6.14. The spec's own Strategy section already rules out a new kernel.

## Decision

1. Lumen's product goal gains a fourth pillar: **a real alternative to Windows**. Someone switching keeps their files, apps, games and devices, or is told honestly before installing what won't come with them.
2. Windows app support is built on Wine through Bottles (Flatpak) and Proton (Steam), plus a **Lumen compatibility database** that gives every Windows app a plain-English rating before install.
3. Ratings are computed offline from a signed data file. No per-app network lookups and no telemetry.
4. Switching from Windows gets its own phase (new Phase 7). The foundations (Wine base, compatibility database, nightly compatibility tests) move into Phase 1, so the database grows from the start.
5. `docs/spec.md` becomes the source of truth from now on, instead of the .docx (see open question 1).

## Spec errors found

CLAUDE.md asks me to stop and say so when the spec is technically wrong. Two places are:

1. **Suspend-then-hibernate conflicts with Secure Boot.** The battery row of "Problems to solve" and the Power & Battery page promise suspend-then-hibernate. With Secure Boot on, kernel lockdown blocks hibernation by design, because the kernel can't verify the resume image. An opt-in kernel patch was only proposed in July 2026 and isn't merged. Lumen must not turn off lockdown or Secure Boot to get hibernation. **Fix:** promise suspend plus a safe shutdown at critical battery; turn on hibernation only when a verified upstream method lands; verify the actual behaviour in a VM during Phase 1.
2. **"Resize NTFS" fails on BitLocker drives.** The installer's "Install alongside Windows" resizes NTFS, but many Windows 11 PCs have BitLocker on by default, and Linux tools can't resize a BitLocker partition. **Fix:** detect BitLocker and shrink from Windows instead (by hand with a guide, or through Lumen Setup for Windows).

There's also a new risk for the risk register (step 0.3). Microsoft's 2011 UEFI CA expired in June 2026. On a PC whose firmware lacks the 2023 CA, a shim signed only with the new key won't boot. The hardware check must catch that before the user erases Windows.

## Proposed changes to docs/spec.md

| Section | Change |
| --- | --- |
| Strategy | Add a paragraph: Lumen is built to be a real alternative to Windows; switching keeps files, apps, games and devices, and Lumen tells users honestly what won't come with them |
| Problems to solve | Rewrite the "Windows apps" row: compatibility rating before install, one-click install with a tested recipe, sandboxed bottles. Add rows for switching risks (BitLocker, Fast Startup, boot order, clock), media codecs, peripheral vendor apps, and "no honest answer about what will work". Fix the battery row (no hibernation promise) |
| Requirements | New subsection **Switching from Windows**, all testable: double-clicking an `.exe` or `.msi` always opens the Windows-app dialog, never "no app can open this file"; every app on the top-100 list has a rating and at least one path (runs, web app or named alternative), and at least 80% are covered; ratings work offline and send no network requests; Windows apps can't read the home folder unless the user allows it; removing a Windows app removes its bottle; anti-cheat status is shown before installing a game; the Windows drive can be imported even with BitLocker on; Wine's `ntsync` module is loaded |
| New section: **Spec: Windows apps and switching** | The compatibility database (fields, rating levels, data sources and licences, ODbL publication, signed updates through lumen-updated), the "Open Windows app" dialog, recipes, sandbox defaults, the Windows apps page in Settings, web apps, Lumen Setup for Windows, the Welcome app scan, and an honest-limits list (desktop Office, Adobe, kernel anti-cheat, 4K streaming DRM, face unlock) |
| Lumen Store | Ratings on results when someone searches a Windows app name; "Windows alternatives" collection driven by the database; install a website as an app; Heroic and Lutris in Gaming |
| Welcome | Step 7 import handles BitLocker; a new "Your Windows apps" view inside step 8 |
| Installer | "Install alongside Windows" detects BitLocker and Fast Startup; never resizes a BitLocker volume from Linux |
| Hardware report | Checks for the Microsoft UEFI CA 2023 in firmware |
| Settings | Wi-Fi & Network: OpenConnect VPNs. Power & Battery: drop "suspend-then-hibernate timing". Apps: Windows apps list. About & Health: "Reset Lumen" (keep files or erase everything) and "Get help from a friend" |
| System Health checks | Add: Fast Startup on, clock mismatch with Windows, Lumen boot entry missing, Secure Boot 2023 certificate missing |
| CLI reference | `lumen app check <file> [--json]`, `lumen app list --windows` |
| Package manifest | `ntsync` autoload, metric-compatible fonts, OpenConnect plugins, device rules for OpenRGB and Piper, `sane-airscan`; Bottles preinstalled as a Flatpak |
| Phases | Insert **Phase 7: Switching from Windows**; renumber hardening to Phase 8 and release to Phase 9. Phase 9 acceptance adds a Windows-switcher test |

## Proposed changes to PROGRESS.md

**Phase 0**
- 0.3 risks must include: the Secure Boot certificate change, hibernation under lockdown, codec patents, BitLocker, Windows code signing for Lumen Setup, and the licences of compatibility data.

**Phase 1** (new steps, before acceptance)
- 1.14 Windows-app base in the image: `ntsync` autoload, Bottles preinstalled, `.exe` and `.msi` open in Bottles for now, metric-compatible fonts. Boot test checks `/dev/ntsync`.
- 1.15 👤 Codecs and hardware video decoding: Claude writes the options and their legal trade-offs in an ADR; the owner chooses; Claude ships the choice.
- 1.16 Compatibility database v0: JSON schema, validation test, first 20 entries, published under ODbL.
- 1.17 Nightly CI compatibility tests: install and launch freely downloadable Windows apps under the image's Wine, take a screenshot, and update each entry's "last tested".
- 1.13 (acceptance) adds: double-clicking an `.exe` in the VM opens Bottles; the compatibility test job is green.

**Phase 4**
- 4.19a "Familiar" layout preset (taskbar-style dock with a Start-style launcher), only if the owner approves it (open question 2).

**Phase 5**
- 5.14 adds OpenConnect VPN import.
- 5.17 replaces suspend-then-hibernate with the fix above.
- 5.22 adds "Reset Lumen".
- 5.22a "Get help from a friend" (Plasma remote desktop, visible indicator, one-time code).

**Phase 6**
- 6.4 changes from "Bottles flow for `.exe` files" (moved to 7.5) to: Essentials adds a OneDrive client, OpenRGB, Piper and Solaar.
- 6.10 "Install alongside Windows" detects BitLocker and Fast Startup.
- 6.11 hardware check adds the Secure Boot 2023 certificate.

**New Phase 7: Switching from Windows**
- 7.1 👤 `docs/windows-apps.md`: the top 100 apps Windows users need, by category, with today's status and the data-source licence checks. The owner reviews the list.
- 7.2 Database v1: recipes, alternatives, anti-cheat status; import ProtonDB and AreWeAntiCheatYet data with attribution; fill the top 100.
- 7.3 Signed database updates through lumen-updated; offline lookup only; test that a lookup makes no network request.
- 7.4 `lumen-compat` Rust crate: identify an `.exe` or `.msi` (version info, installer type, file hash) and match it; `lumen app check`.
- 7.5 "Open Windows app" dialog: rating, reason, alternatives, Install anyway; creates the bottle with its recipe; adds the app to the menu.
- 7.6 Sandbox defaults for bottles; Windows apps page in Settings; `lumen app list --windows`; full removal.
- 7.7 Store: ratings on Windows-name searches, Windows alternatives collection, web apps, Heroic and Lutris, anti-cheat status.
- 7.8 Welcome: "Your Windows apps" scan of the Windows drive, with BitLocker unlock by recovery key.
- 7.9 ⚠️ 👤 Lumen Setup for Windows, a fork of Fedora Media Writer that adds the hardware check, the BitLocker, Fast Startup and Secure Boot checks, the partition shrink, the UTC clock fix and the USB writer. The owner needs a Windows code-signing certificate, or SmartScreen will warn users.
- 7.10 Dual-boot Health checks: Fast Startup, clock, missing boot entry, Secure Boot certificate.
- 7.11 Tests: every top-100 app has a rating and a path; the dialog and the CLI agree; offline lookup; sandbox defaults.
- 7.12 👤 Phase 7 acceptance: a Windows user installs Lumen using Lumen Setup, sees their apps' status, installs five Windows apps by double-clicking, and every rating is correct. At least 80% of the top-100 list is covered.

**Phases 7 and 8 become Phases 8 and 9**, with the steps renumbered. Phase 9 acceptance adds the Windows-switcher test.

## Proposed changes to CLAUDE.md

- Product line: "Easy by default, powerful underneath, never breaks, liquid-glass design, and a real alternative to Windows."
- Repo layout adds `compat/` (compatibility database and its tests) and `windows-setup/` (Lumen Setup for Windows).
- Fixed architecture adds: "Windows apps: Wine via Bottles (Flatpak) and Proton; ratings from the Lumen compatibility database, looked up offline."

## Open questions for the owner

1. **Spec source of truth.** PROGRESS.md says to regenerate `docs/spec.md` from the .docx instead of hand-editing it. These changes are large, and more will follow. Recommendation: make `docs/spec.md` the source of truth from now on. (pandoc can still produce a .docx from it when you want one.)
2. **"Familiar" layout.** Should Welcome offer a Windows-style taskbar layout, or should Lumen keep one layout (top bar plus dock) for everyone?
3. **Built-in AI assistant.** Out of scope unless you want one. If you do: local-first and opt-in.

## Consequences

- Roughly 30 new steps; v0.1 moves further out. The foundations land early, so the compatibility database has months of nightly test results by the time the dialog ships.
- The database becomes something the project must keep curating; ratings that go stale damage trust. Every entry records when and how it was last tested, and old entries drop to "Not tested yet".
- Lumen Setup for Windows is the project's first Windows program, with its own build (GitHub Actions Windows runner) and a code-signing cost.
- Some gaps stay unfixable (desktop Office, Adobe, kernel anti-cheat, 4K streaming). The plan's answer is to say so before install and offer the best alternative, never to hide it.
