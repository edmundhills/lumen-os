<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0023. Build, test and publish each edition on a runner of its own

- Status: **Accepted** (2026-11-06), at step 1.12c.
- Deciders: lead engineer (Claude). The owner reviews it at the Phase 1 acceptance (step 1.17).

## Context

Lumen has four images (spec, "Image variants"; [ADR 0004](0004-phase-0-review.md); architecture 9.5): `lumen`, `lumen-gaming`, `lumen-nvidia` and `lumen-gaming-nvidia`. Step 1.12c publishes all four, each re-chunked, with its SBOM, pushed, signed and its `dev` moved (ADR 0007, ADR 0008). Facts from image runs 42266385717 and earlier, on 2026-11-06:

- **Two jobs build them today.** The build job builds `lumen` (23 minutes) and the gaming layer on it (20), re-chunks and measures `lumen` (14), makes its SBOM (4), and makes, checks and boots both qcow2s (25): about 95 minutes of its 120. The `nvidia` job builds `lumen`, `kmods` and `lumen-nvidia` (42), the gaming layer on it (16), and both qcow2s and their tests (26): 85 minutes ([ADR 0022](0022-nvidia-edition.md), [ADR 0019](0019-gaming-edition.md), Follow-ups).
- **Publishing an edition adds** its re-chunking (about 14 minutes), its SBOM (4) and its push (about 5), so each job would need about 115 to 130 minutes, and every change to a job would wait for both its editions.
- **A job fails as a whole.** When RPM Fusion or Koji is down, the job fails for both its editions, though only one of them needs it.
- **GitHub's hosted runners are free for public repositories** and run jobs in parallel; a job may run 6 hours. A job that calls a reusable workflow can have a matrix.
- **ghcr.io gives a new package its repository's visibility**: `lumen` was public and linked to the repository from its first push (step 1.5a).
- **The boot test booted the gaming edition from its build**, not from a re-chunked image, since only `lumen` was re-chunked.

## Decision

1. **`build-image.yml` builds one edition**, given as the input `edition` (`lumen`, `gaming`, `nvidia` or `gaming-nvidia`), and `image.yml` calls it for each of the four in a matrix, with `fail-fast: false`, from both its jobs: the check for every push and pull request, and the publish for `main`.
2. **Each edition's build makes all it needs from the same commit and bases** on its own runner: the `lumen` stage, and for the NVIDIA editions `kmods` and `lumen-nvidia` with the throwaway key (ADR 0022), which a step that always runs removes before anything else is built. The gaming layer on `lumen-nvidia` starts from the image just built (ADR 0019, Follow-up).
3. **Each edition is re-chunked** against the newest build of its own `dev` and held to the same download budget, **gets its SBOM** (`<image>.spdx.json`), and **its qcow2 is made from the re-chunked image**, which is what gets pushed, then checked and booted. On `main` the build pushes it, and a sign job that needs only that edition's build signs it and moves its `dev`.
4. **One build version for all four**: the next one for which none of the four repositories has a `dev-<version>` tag (`image/build_version.py`, which now reads several tag lists). The check that a commit is published once stays per repository.
5. **The NVIDIA editions are not published yet.** Their modules carry a throwaway key's signature until Lumen's key exists (step 1.11a), and no user could enrol that key. Their builds on `main` build and test them as on any branch; step 1.12c-2 turns publishing on, with Lumen's key from the `module-signing` environment.

## Consequences

- A run takes as long as its longest edition, `gaming-nvidia`, about 95 minutes, on four runners instead of two: about 5 runner-hours a run instead of 3, which public repositories don't pay for.
- An edition that fails holds back only itself; `lumen-gaming-nvidia` also fails whenever `lumen-nvidia` does, since it builds it first (risk 7).
- The `lumen` stage is built four times a commit, and `lumen-nvidia` twice. Each image is its own, re-chunked against its own `dev`, so nothing downstream needs their common layers to be the same bytes. From Phase 2, Lumen's own RPMs (lumen-glass, lumen-shell and the services) must still be built and tested once per commit, as architecture 9.5 says: a job builds them in the `devel` stage, against `base`, and each edition's build installs those same files, which are small enough to pass as an artifact. The step that brings the first RPM does that.
- The gaming editions' boot test now boots the re-chunked image, as `lumen`'s did.
- The jobs' names change, to "Check lumen / Build the image" and so on; a branch rule that required the old names would need the new ones.
- The first push of `lumen-gaming` creates its package. If ghcr.io doesn't make it public, as it did `lumen`, the next build of `main` stops at "Make the package public", and the owner makes it public in the package's settings.

## Follow-up

- 2026-11-06: Image run 42282719947 (for `30b46bc`), the first with a runner per edition, was green in 109 minutes, as long as its longest edition: `lumen` 46 minutes (7.8 GB; an update from `dev` downloads 2 of 254 layers, 41.3 MiB; boot 10 of 10), `lumen-gaming` 89 (8.6 GB; build 42, re-chunk 17; its re-chunked image booted 11 of 11), `lumen-nvidia` 85 (9.4 GB; build 50, re-chunk 14; boot 12 of 12) and `lumen-gaming-nvidia` 109 (10.5 GB; `lumen-nvidia` 52, the gaming layer 18, re-chunk 15; boot 13 of 13). All four had build version 45.20261106, passed the checks again after re-chunking, and kept their SBOMs; the three new editions had no `dev` to measure an update from.
