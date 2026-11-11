<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# docs/history

What each finished step did: what it built, what CI showed, what was measured and what it found on the way. One file per phase, written by the session that did the step, in the order the steps were done.

| File | Covers |
| --- | --- |
| [phase-0.md](phase-0.md) | Stage A (setup) and Phase 0 (plan and skeleton) |
| [phase-1.md](phase-1.md) | Phase 1 (the bootable image), and the review of 2026-11-11 |

[PROGRESS.md](../../PROGRESS.md) is the plan, and every session reads it first, so it stays short: the current step, what waits for the owner, the facts every session needs, and notes for steps still to come. These files are the long record behind it ([ADR 0026](../decisions/0026-short-plan-early-tests.md)). Nobody reads them from top to bottom: search for a step's number, such as "1.8c", when a step needs to know how an earlier one went.

## Adding to it

- When a step is done, add its record at the end of its phase's file, as a list item that starts with the step's number and the date. Start a new file for a new phase and add it to the table.
- Write what a later session can't work out from the code and the ADRs: the CI runs and what they showed, measurements, what failed first and why, and what was left undone.
- Decisions go in an ADR, not here. A note that a later step needs goes in PROGRESS.md, under that step's number in "Notes for steps still to come".
