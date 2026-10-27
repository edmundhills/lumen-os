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

## Writing an ADR

- Name the file `NNNN-short-title.md`, using the next free number, and start it with `# NNNN. Title`. Add it to the table above.
- Under the title, list the **Status** (Proposed, Accepted, Rejected, or Superseded by NNNN, with the date) and the **Deciders**.
- Then the sections **Context** (the problem and the facts, with the date they were checked), **Decision** and **Consequences**. Add others where they help, such as the changes made to the spec.
- Don't rewrite an accepted ADR. Record a later correction in a dated **Follow-up** section, or write a new ADR that supersedes it.
