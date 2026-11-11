<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0026. Keep the plan short, and build tests and translation tooling before what they check

- Status: **Accepted** (2026-11-11), in a review the owner asked for.
- Deciders: lead engineer (Claude), on the owner's request to improve the work so far and to adapt the plan where needed. The owner reviews it with the branch that carries it (`ccr-d3f590a0-rbcjnh`).

## Context

On 2026-11-11 the owner asked for a look at the project so far and at the plan. Facts found that day:

- **PROGRESS.md was 147 KB.** CLAUDE.md's "Step mode" has every session read it first, and the owner works in short sessions to stay within usage limits. Its section "Notes for the next session" had become the record of every finished step, 110 KB of it: CI run numbers, timings, what failed first. A session doing step 1.14c needed almost none of it, and the few lines a later step does need ("lumen-updated must pass `--enforce-container-sigpolicy`", "Welcome must replace Plasma Setup") were buried in the record of the step that found them.
- **Its "Current step" section had gone stale**: it still said to close pull request #4, which had been merged, and asked a question about bump pull requests that step 1.10a had answered. What waited for the owner was spread over three paragraphs and the notes.
- **The plan built its test harnesses last.** CLAUDE.md's working rules say every feature ships with tests. But the glass test harness was step 3.15, after the twelve steps of shader work it tests (3.3 to 3.14), and the shell's session test was 4.18, after every surface. Those steps could only have been checked by eye.
- **The plan built its translation tooling in Phase 9.** The working rules say every user-facing string is translatable. String extraction and the pseudo-locale, which show a string that isn't, were step 9.7, after the shell, Settings, the Store, Welcome and the rest had been written.
- Step numbers are used across the ADRs, the risk register and the architecture, so renumbering steps would break those references. The plan already has lettered steps (5.22a, 7.10a).

The review's changes to the image and to CI are recorded where they belong: the Follow-ups of [ADR 0007](0007-rechunking.md) (the one-time download label), [ADR 0023](0023-edition-per-runner.md) (the `publish` workflow, and no image build for pushes of documents alone), and [ADR 0024](0024-windows-app-base.md) and [ADR 0025](0025-codecs.md) (the first-boot apps).

## Decision

1. **PROGRESS.md is the plan and nothing else.** It holds how to resume, the current step, what waits for the owner as one numbered list, the facts every session needs, notes for steps still to come under each step's number, and the step lists. It stays short enough to read at the start of every session.
2. **A finished step's record goes in `docs/history/`**, one file per phase, added at the end by the session that did the step. The notes written up to 2026-11-11 moved there unchanged. Sessions search it by step number when they need it; nobody reads it from top to bottom.
3. **CLAUDE.md's "Step mode" says so**: where a step's record goes, that a session stopping mid-step writes where it stopped under "Current step", and that code is pushed before notes, because a push of documents alone starts no image build.
4. **Tests come before what they test.** No step is dropped and no number changes:
   - **2.13** builds the headless session harness (`kwin_wayland --virtual`, a screenshot, a golden-image compare) as well as its first use, the four kinds of app.
   - **3.2a** (new) is the glass test harness on top of it, straight after the plain fork ships in the image. Each shader step adds the scenes for what it draws. 3.15 keeps the full set of the spec's 12 scenes, and 3.16 the contrast figures and the frame-time benchmark.
   - **4.1a** (new) is the shell's test scaffold: the QML unit-test runner and a session test that opens a surface and takes a screenshot. Each surface's step adds its own. 4.18 keeps full coverage.
   - **5.1** adds the Rust checks (`cargo fmt`, `clippy`, `cargo test`) to `just lint` and `just test` with the first crate.
5. **Translation tooling comes before the first screen with text**: **4.1b** (new) extracts every component's strings in its build and runs the session test in a pseudo-locale. 9.7 keeps Weblate and the full pass over every app.

## Consequences

- A session starts by reading about 51 KB instead of 147 KB. The step lists are now most of it; folding up the steps of finished phases would shorten it further, and is left for later.
- The history files are long and unstructured, as the notes were. They are a record, not a guide: what a later step must know belongs in PROGRESS.md under that step, and a session that finishes a step has to sort its findings into the two.
- Phases 3 and 4 each start with a harness step before any visible progress, and 2.13 is larger than it was, so it is marked ⚠️ and may split.
- The glass harness runs on software rendering in CI, so it checks pictures and contrast, not speed: frame times still need real hardware (risk 8), as before.
- The spec's phase prompts list tests last within each phase. They give the content of each phase, not the order of its steps, so the spec is unchanged.

## Changes made to PROGRESS.md and CLAUDE.md

- `PROGRESS.md`: rewritten above the step lists (decision 1); a "Changes to the plan" section; steps 3.2a, 4.1a and 4.1b added; steps 1.17, 2.13, 3.15, 3.16, 4.18, 5.1 and 9.7 reworded.
- `CLAUDE.md`, "Step mode": the opening sentence, the rule for stopping, and two new rules (decision 3).
- `docs/history/`: new, with a README, `phase-0.md` and `phase-1.md`.
