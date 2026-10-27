<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0001. Make switching from Windows a primary goal

- Status: **Accepted** (2026-10-27). Proposed and accepted the same day; applied to `docs/spec.md`, `PROGRESS.md` and `CLAUDE.md`.
- Deciders: owner (Edmund), lead engineer (Claude)

## Context

The owner wants Lumen OS to compete with Windows. The spec treated Windows apps as one row of the problems table, a Bottles shortcut, and step 6.4 near the end of the plan. Nothing told a user *before* they install whether their apps and games would work, and several switching problems (BitLocker, Fast Startup, the 2026 Secure Boot certificate change, apps that came with the PC) weren't covered at all.

The full gap list, with what Linux does today and what Lumen does about each item, is in [docs/competing-with-windows.md](../competing-with-windows.md).

A custom kernel was considered and rejected. Windows apps call Windows libraries, not the kernel, and Wine reimplements those libraries. The one kernel feature Wine needed (`ntsync`) has been in mainline Linux since 6.14. The spec's own Strategy section already rules out a new kernel.

## Decision

1. Lumen's product goal gains a fourth pillar: **a real alternative to Windows**. Someone switching keeps their files, apps, games and devices, or is told honestly before installing what won't come with them.
2. Windows app support is built on Wine through Bottles (Flatpak) and Proton (Steam), plus a **Lumen compatibility database** that gives every Windows app a plain-English rating before install.
3. Ratings are computed offline from a signed data file. No per-app network lookups and no telemetry.
4. Switching from Windows gets its own phase (new Phase 7). The foundations (Wine base, compatibility database, nightly compatibility tests) are in Phase 1, so the database grows from the start.
5. `docs/spec.md` is the source of truth from now on. The original .docx is historical and no longer kept in sync.

## Spec errors found and fixed

1. **Suspend-then-hibernate conflicted with Secure Boot.** The battery row of "Problems to solve" and the Power & Battery page promised suspend-then-hibernate. With Secure Boot on, kernel lockdown blocks hibernation by design, because the kernel can't verify the resume image. An opt-in kernel patch was only proposed in July 2026 and isn't merged. **Fix applied:** the spec now promises suspend plus a safe shutdown at critical battery, and offers hibernation only where lockdown allows it. Lumen never turns off lockdown or Secure Boot to get hibernation.
2. **"Resize NTFS" fails on BitLocker drives.** Many Windows 11 PCs have BitLocker on by default, and Linux tools can't resize a BitLocker partition. **Fix applied:** "Install alongside Windows" uses space made from inside Windows (by hand or through Lumen Setup for Windows), resizes only plain NTFS, and never touches a BitLocker volume.

There's also a new risk for step 0.3. Microsoft's 2011 UEFI CA expired in June 2026. On a PC whose firmware lacks the 2023 CA, a shim signed only with the new key won't boot. The hardware check and a Health check now catch that before the user erases Windows.

## Changes made to docs/spec.md

| Section | Change |
| --- | --- |
| Strategy | New paragraph: Lumen is built to be a real alternative to Windows |
| Problems to solve | Windows-apps row rewritten (ratings, recipes, sandboxed bottles). New rows: honest answer about what comes with you, switching risks, peripheral vendor apps, codecs. Gaming row adds launchers and anti-cheat status; battery row fixed |
| Requirements | New **Switching from Windows** subsection with testable items |
| New section **Spec: Windows apps and switching** | Rating levels, the compatibility database (fields, recipes, sources and licences, ODbL, signed offline delivery), the dialog, sandbox, games, Lumen Setup for Windows, honest limits, after-v0.1 list |
| Package manifest | ntsync autoload, sane-airscan, OpenRGB and ratbagd device rules, OpenConnect, metric-compatible fonts, codecs per the step 1.14 ADR; Bottles preinstalled as a Flatpak |
| Settings | OpenConnect VPNs; Power & Battery without the hibernation promise; Windows apps under Apps; "Get help from a friend" and "Reset Lumen" under About & Health |
| System Health checks | Fast Startup, clock mismatch, missing boot entry, missing UEFI CA 2023 |
| Store, Welcome, Installer, Hardware report | Ratings on Windows-name searches, web apps, Heroic and Lutris; BitLocker-aware import and "Your Windows apps"; BitLocker-safe install alongside Windows; UEFI CA 2023 check |
| Services, CLI | lumen-updated also updates the compatibility database; `lumen app check`, `lumen app list --windows` |
| Security model | Lockdown stays on; out-of-tree kmods signed like NVIDIA's; new threat row for malicious Windows programs; offline ratings in the privacy line |
| Testing | New "Windows compatibility" nightly test layer |
| Claude Code prompt | Embedded CLAUDE.md matches the real one; Phase 0 risk examples; Phase 1 items 7–10; Phase 6 adjusted; new Phase 7; hardening and release renumbered to Phases 8 and 9 |

## Changes made to PROGRESS.md

- Notes: `docs/spec.md` is the source of truth; ADR 0001 accepted; Familiar layout and AI assistant deferred.
- 0.3: required risks listed.
- 1.9: record lockdown state and whether hibernation is offered under Secure Boot.
- New 1.13 (Windows-app base), 1.14 👤 (codecs ADR), 1.15 (compatibility database v0), 1.16 (nightly compatibility job). Acceptance moves to 1.17 and adds the `.exe` and compatibility-job checks.
- 5.14 OpenConnect, 5.17 Power & Battery fix, 5.22 "Reset Lumen", new 5.22a "Get help from a friend".
- 6.4 becomes "Essentials adds OneDrive, OpenRGB, Piper, Solaar" (the `.exe` flow moved to 7.5); 6.10 BitLocker-safe installer; 6.11 UEFI CA 2023 check.
- New Phase 7, steps 7.1–7.12. Old Phases 7 and 8 become 8 and 9; 8.2 covers Windows-app bottles and Lumen Setup; 9.4 FAQ covers what won't come over; 9.6 includes an install alongside Windows.

## Changes made to CLAUDE.md

- Product line adds "and a real alternative to Windows".
- Fixed architecture adds the Windows-apps line.
- Repo layout adds `apps/windows-app`, `compat/` and `windows-setup/`.

## Owner's answers to the open questions

1. Spec source of truth: `docs/spec.md`, from now on.
2. Windows-style "Familiar" layout: deferred. Not in the spec or the plan; ask before adding.
3. Built-in AI assistant: deferred. Not in the spec or the plan; ask before adding.

## Follow-up

- Step 1.9 records whether kernel lockdown is actually on, and whether hibernation is offered, on our image under Secure Boot. (CVE-2025-1272 reported Fedora kernels from 6.12 shipping with lockdown off.) If lockdown is off, that is a security gap to fix, not a way to get hibernation.

## Consequences

- About 30 new steps; v0.1 moves further out. The foundations land early, so the compatibility database has months of nightly test results by the time the dialog ships.
- The database becomes something the project must keep curating; ratings that go stale damage trust. Every entry records when and how it was last tested, and entries older than 6 months show as "Not tested yet".
- Lumen Setup for Windows is the project's first Windows program, with its own build (GitHub Actions Windows runner) and a code-signing cost.
- Some gaps stay unfixable (desktop Office, Adobe, kernel anti-cheat, 4K streaming). Lumen says so before install and offers the best alternative, never hides it.
