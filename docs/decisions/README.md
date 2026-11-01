<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# docs/decisions

Architecture decision records (ADRs). Each one records a decision that changes the spec or the architecture, patches an upstream component, or settles an open question: what was decided, why, and what follows from it. Later work can then build on it instead of reopening it.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-compete-with-windows.md) | Make switching from Windows a primary goal | Accepted |
| [0002](0002-fix-spec-errors-from-architecture-review.md) | Fix the spec errors found while writing the architecture | Accepted |
| [0003](0003-licence.md) | Licence: GPL-3.0-or-later for code, ODbL for the compatibility data | Accepted |
| [0004](0004-phase-0-review.md) | Decisions from the Phase 0 review: build chain, disk unlock, theme baseline, variants and the rest | Accepted |
| [0005](0005-plasma-login-manager.md) | Plasma Login Manager for the login screen, not SDDM | Accepted |
| [0006](0006-lumen-look.md) | Lumen's own look: top-bar islands, app menus in the window, lens icons, Sunbeam accent, Red Hat Display and Source Sans 3 | Accepted |
| [0007](0007-rechunking.md) | Re-chunk the image with rpm-ostree, against a download budget | Accepted |
| [0008](0008-image-signing.md) | Sign images with a cosign key, attach a syft SBOM, and trust Lumen's images only with that signature | Accepted |
| [0009](0009-games-blocked-by-anti-cheat.md) | Help with games that anti-cheat blocks: cloud gaming, "Play in Windows", and checked ratings | Accepted |
| [0010](0010-hardware-phase.md) | A phase of its own for making full use of each device; the old Phases 8 and 9 become 9 and 10 | Accepted |
| [0011](0011-disk-images.md) | Make the disk images with osbuild's image-builder, which bootc-image-builder became | Accepted |
| [0012](0012-install-iso.md) | Pack the install ISO with image-builder's generic-iso, and label its files for SELinux | Accepted |
| [0013](0013-tuned-profiles.md) | Lumen's own tuned profiles, so tuned never runs bootc | Accepted |
| [0014](0014-install-from-the-iso.md) | Install the ISO's own copy of the image with Anaconda's bootc command | Accepted |
| [0015](0015-installer-enforcing.md) | Run the installer with SELinux enforcing | Accepted |
| [0016](0016-btrfs-compression.md) | Mount the Btrfs root with compression through the kernel arguments | Accepted |
| [0017](0017-boot-test.md) | Boot each build's qcow2 in CI, with the checks given as credentials, and skip mcelog on AMD | Accepted |
| [0018](0018-disk-labels.md) | Correct two SELinux labels on the qcow2 that image-builder makes | Accepted |
| [0019](0019-gaming-edition.md) | Build the gaming edition with RPM Fusion's Steam and 32-bit packages at the image's versions | Accepted |
| [0020](0020-gamescope-session.md) | Take the Gamescope session from ChimeraOS, pinned file by file, without SteamOS's helpers | Accepted |

ADRs 0001 to 0009 use the step numbers of their time. Since ADR 0010, the old Phase 8 is Phase 9 and the old Phase 9 is Phase 10, so their "step 8.2" is now step 9.2, and "step 9.1" is now step 10.1.

## Writing an ADR

- Name the file `NNNN-short-title.md`, using the next free number, and start it with `# NNNN. Title`. Add it to the table above.
- Under the title, list the **Status** (Proposed, Accepted, Rejected, or Superseded by NNNN, with the date) and the **Deciders**.
- Then the sections **Context** (the problem and the facts, with the date they were checked), **Decision** and **Consequences**. Add others where they help, such as the changes made to the spec.
- Don't rewrite an accepted ADR. Record a later correction in a dated **Follow-up** section, or write a new ADR that supersedes it.
