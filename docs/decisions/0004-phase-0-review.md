<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0004. Decisions from the Phase 0 review

- Status: **Accepted** (2026-10-27). The owner reviewed the Phase 0 documents at step 0.8 and accepted every proposal as written. Applied to `docs/spec.md`, `CLAUDE.md`, `PROGRESS.md`, `docs/architecture.md`, `docs/risks.md` and `docs/versions.md`.
- Deciders: owner (Edmund), lead engineer (Claude)

## Context

Phase 0 wrote the architecture (steps 0.1 and 0.2), the risk register (0.3), the repository skeleton (0.4) and the version record (0.7). They left open questions for the owner's review at step 0.8:

- Q6 to Q15 in [architecture section 8](../architecture.md#8-spec-problems-and-open-questions), and Q16 and Q17 in [the risk register](../risks.md#questions-for-the-owner).
- About 30 smaller answers in the architecture, and some mitigations in the risk register, marked **Proposed**.
- Four points from the hand-off notes: the rule that an AI assistant never signs off a commit, the copyright line, a folder for the hardware report, and Kinoite base images that expire from quay.io after four weeks.

On 2026-10-27, `just lint` (10 checks) and `just test` (12 checks) passed in WSL, and both CI workflows were green on `d211f2d`.

## Decision

The owner accepted every proposal as written. The ones below change something now.

1. **Build chain (Q12).** Every package built from this repository is built in a stage of the image build, against the stage it ships in, so one commit makes one image. COPR is only for outside packages that Fedora lacks, and none are needed yet.
2. **Disk unlock (Q17): option (b), with (a) as the fallback.** TPM2 unlock stays automatic, with no PIN by default. It is bound to Lumen's own boot measurements as well as to PCR 7. systemd-pcrlock predicts the new values before an update, so updates don't ask for the recovery key. The volume key is measured into a PCR (`tpm2-measure-pcr=`), and a PIN stays optional. If step 6.6 finds that (b) can't be made reliable, Lumen falls back to (a): a PIN by default, with automatic unlock as an opt-in. Step 6.6 records which one shipped in a follow-up to this ADR.
3. **What "match" means for themes (Q16).** Every app gets the same light or dark mode, accent colour, contrast and fonts. Lumen's apps and apps in the image get the full style. GTK 3 Flatpaks get it through a theme extension on Flathub. libadwaita apps keep their own shapes. Lumen never adds filesystem overrides to Flatpak apps behind the user's back. Phase 2's acceptance tests this baseline.
4. **Sign-off.** The rule in `CONTRIBUTING.md` stays: only a person can certify the DCO, so an AI assistant never adds a `Signed-off-by:` line. The owner signs off Claude's commits before each push.
5. **Copyright line.** File headers keep "Lumen OS contributors".
6. **Hardware report folder.** The hardware report lives in `apps/hwreport`, which joins the repository layout.
7. **Base image pin.** From step 1.5, the Kinoite pin is bumped at least every two weeks, by Renovate or a scheduled job. Each pinned base is copied to Lumen's registry on ghcr.io, so older commits can still be built after quay.io deletes the dated build.

These are accepted as the plan and get built at their steps:

| # | Decision | Steps |
| --- | --- | --- |
| Q6 | Surfaces name their glass role through a small Lumen Wayland protocol, `lumen_glass_manager_v1`. Windows that don't use it get a role from their window type | 3.8 |
| Q7 | Machine-wide settings (update channel, automatic updates, firewall) go through lumen-settingsd to the system service that owns them. They are stored in `/etc/lumen/`, and changing them asks for the admin password | 5.2 |
| Q8 | Welcome's first part runs in a first-boot session as a locked-down system user. It creates the account through AccountsService and enrols the TPM through `org.lumen.Hardware1`. Check KDE's plasma-setup first | 6.5, 6.6 |
| Q9 | In v0.1, `lumen settings` doesn't wrap settings that upstream tools already own (Wi-Fi, displays, Bluetooth). Each Settings page's Advanced section shows the matching command instead | 5.2 |
| Q10 | Shared Rust crates get a small C interface (cbindgen) that the C++ programs link, on Linux and on Windows. There is no extra daemon | 7.4, 7.9 |
| Q11 | Web apps open in the user's browser where it supports app windows, otherwise in GNOME Web. Launchers come from the dynamic launcher portal | 7.7 |
| Q13 | The two choices are now independent: driver (open or NVIDIA) and edition (desktop or gaming). That adds a fourth image, `lumen-gaming-nvidia`, and `SwitchVariant` changes one choice and keeps the other | 1.10 to 1.12 |
| Q14 | Beta is the weekly promotion of a green `dev` build, on the same Fedora release as stable. During a Fedora rebase, beta carries the new release for 4 weeks while a maintenance branch keeps building stable on the old one | 9.1 |
| Q15 | The ISO's download host is chosen at step 9.5. Until then, test ISOs are short-lived CI artifacts | 9.5 |

Every other **Proposed** item in the architecture and the risk register is accepted as well, and no longer marked. If a step finds that one doesn't work, it records the change in a new ADR rather than changing it quietly. Choices that a proposal itself leaves to a later step, such as which re-chunking tool to use (1.5), are still made at that step.

## Changes made to docs/spec.md

- Powerful: settings that upstream tools own keep their own commands (Q9).
- Base and build chain: Lumen's packages are built in stages of the image build (Q12).
- Image variants: `lumen-gaming-nvidia`, and beta as a channel of every image (Q13, Q14).
- How surfaces ask for glass: the role protocol (Q6). Services: machine-wide settings (Q7).
- Welcome step 4 and the security table: TPM unlock (Q17). The security table's supply-chain row also gets the pin bump.
- Release train: the maintenance branch during a rebase (Q14). Before you start: COPR is optional (Q12).
- The copy of CLAUDE.md: the build rule covers every Lumen package (Q12), and the layout gains `apps/hwreport`.
- The Phase 1, 2 and 3 prompts: the fourth variant, the "match" baseline and the role protocol.

## Changes made to PROGRESS.md

Steps 1.5, 1.10, 1.12, 2.14, 3.8, 6.6 and 6.12 reworded to match. No steps added or removed.

## Consequences

- Phase 1 needs no COPR. The OS is built by one Containerfile in one CI workflow. Builds get longer as each phase adds a stage; Podman reuses the stages whose inputs didn't change.
- Four images to build and boot-test instead of three, so each commit takes more CI time ([risk 13](../risks.md#13-ci-capacity-disk-time-kvm-and-no-gpu)).
- Step 6.6 grows: the pcrlock policy must be updated before every change to the boot chain, and tested in CI with a software TPM. If that proves unreliable, users get the PIN fallback.
- The pin bump starts at step 1.5 instead of 8.2, and the copies of the base images use ghcr.io storage.
- Phase 2's acceptance becomes testable for Flatpak apps.
