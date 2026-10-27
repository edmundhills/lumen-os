# 0003. Licence: GPL-3.0-or-later for code, ODbL for the compatibility data

- Status: **Accepted** (2026-10-27). The owner chose the licence before step 0.4; applied to `docs/spec.md` and `PROGRESS.md`.
- Deciders: owner (Edmund), lead engineer (Claude)

## Context

The spec named no licence, and step 0.4 creates the repository skeleton, so one was needed first. Four things limit the choice:

- lumen-glass forks KWin's blur effect. Its source is GPL-2.0-or-later (`SPDX-License-Identifier: GPL-2.0-or-later` in `src/plugins/blur/blur.cpp`, checked 2026-10-27).
- Lumen Setup for Windows forks Fedora Media Writer. Its source headers say GPL version 2 "or (at your option) any later version" (checked in `src/app/main.cpp`, 2026-10-27).
- The compatibility database includes ProtonDB's report exports, which are ODbL 1.0, so the database must be published under ODbL 1.0 (spec, "Compatibility database").
- SignPath Foundation's free Windows code signing needs an OSI-approved licence for every component, with no commercial dual licensing ([risk 9](../risks.md#9-windows-code-signing-for-lumen-setup)).

## Decision

1. **Lumen's code is GPL-3.0-or-later.** Everything in the repository is under it unless a file or folder says otherwise.
2. **The compatibility database is ODbL 1.0.** This covers `compat/windows-apps.json` and the data files beside it. The `lumen-compat` crate in the same folder is code, so it is GPL-3.0-or-later. Whether each entry's contents also carry DbCL 1.0, as ProtonDB's do, is settled at step 1.15, which adds the ODbL licence file.
3. **Third-party files keep their notices.** Files forked from KWin and Fedora Media Writer keep their copyright lines and GPL-2.0-or-later headers; Lumen's changes are GPL-3.0-or-later, and the combined program is distributed under GPL-3.0-or-later. Fonts, icons and other assets taken from upstream sets keep their own licences.
4. **Every file says its licence.** Source files start with an SPDX header (`SPDX-License-Identifier: GPL-3.0-or-later`) and a copyright line, following the REUSE specification. **Proposed** (step 0.5): `reuse lint` becomes part of `just lint`, so a file without a licence fails CI.
5. **Proposed** (step 0.4): contributions carry a DCO sign-off (`Signed-off-by:`), with no contributor licence agreement. For `compat/` the sign-off offers the entry under ODbL 1.0 ([risk 12](../risks.md#12-licences-of-compatibility-data)).

## Why it fits

- The "or later" in the KWin and Fedora Media Writer licences allows their code to be combined into a GPL-3.0-or-later program.
- GPLv3 is compatible with Apache-2.0, which many Rust crates use; GPLv2 isn't. That matters for the services' and the CLI's dependencies.
- Qt and KDE Frameworks (LGPL) and the Plasma libraries can be linked from GPLv3 code.
- It is OSI-approved, so SignPath's free signing stays open to Lumen Setup.
- GPLv3's rule on "Installation Information" applies to software shipped in or with a consumer device. Lumen ships software on its own, and users can still run modified builds (as admin they can switch images, change the signature policy and enrol their own MOK), so signed images and Secure Boot don't conflict with it.

## Consequences

- Code that is GPL-2.0-only can't be copied into Lumen. Check the header of every file before forking or copying it (step 3.1 for KWin, 7.9 for Fedora Media Writer).
- Programs Lumen only runs or ships alongside, such as the kernel, the NVIDIA driver and Flatpak apps, keep their own licences; they aren't combined with Lumen's code.
- With DCO and no contributor licence agreement, every contributor keeps their copyright, so Lumen's code can't later be relicensed under non-GPL terms without each contributor's agreement.
- Step 0.4 adds the GPL-3.0 text as `LICENSE` (copied unchanged from gnu.org, not retyped), a licence section in the top-level README and a `CONTRIBUTING.md` with the DCO rule. Step 1.15 adds the ODbL licence file in `compat/`.
