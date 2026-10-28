<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contributing to Lumen OS

Thank you for helping. Lumen is in early development ([PROGRESS.md](PROGRESS.md)), so the most useful contributions today are reviews of the documents in [docs/](docs/).

## Before you start

- Read the part of [docs/spec.md](docs/spec.md) your change touches. The spec is the source of truth: if your change needs it to change, change it in the same pull request and say why.
- Use an upstream component where one exists. Patch it only when needed, and record why in an [architecture decision record](docs/decisions/).
- For a large change, open an issue first, so we can agree on the approach before you put work in.

## Rules for every change

- Every feature ships with tests, and CI stays green.
- Never weaken a security default to make something work. Never turn off SELinux, Secure Boot or signature checks.
- Every user-facing string is translatable (Qt `tr()` or gettext) and written in plain English.
- Everything respects Reduce Motion and Reduce Transparency.
- Run `just lint` and `just test` before you push. CI runs the same checks.

## Commits

- Keep commits small, each doing one thing.
- Use [Conventional Commits](https://www.conventionalcommits.org/) messages: `feat:`, `fix:`, `docs:`, `test:`, `chore:` and so on, with a scope where it helps, for example `fix(test): drop awk from the WSL check`.
- Commit with the email address you want in the public history. On GitHub, the no-reply address under Settings > Emails keeps your own address private.

## Sign off every commit (DCO)

Lumen uses the [Developer Certificate of Origin](https://developercertificate.org/) (DCO), version 1.1, instead of a contributor licence agreement. Every commit must end with a sign-off line whose name and email match the commit's author:

```text
Signed-off-by: Your Name <you@example.com>
```

`git commit -s` adds it for you. By signing off, you certify everything the DCO says. In short: you wrote the change, or otherwise have the right to submit it under the project's licence, and you understand that the contribution and your sign-off are public and kept for good. The full text at the link above is what you certify.

- You keep the copyright in your work and license it under the licence of the files you change: GPL-3.0-or-later for code and documents, ODbL 1.0 for entries in the compatibility database in `compat/` ([ADR 0003](docs/decisions/0003-licence.md)).
- Forgot to sign off? `git commit --amend -s` fixes the last commit, and `git rebase --signoff main` fixes every commit on your branch.
- **AI assistants.** Only a person can certify the DCO, so an AI assistant must never add a `Signed-off-by:` line. If one helped with a change, the person who submits it reviews it, signs off themselves and is responsible for it. Credit the assistant with a trailer such as `Co-Authored-By:`.
- **Lumen's own workflows.** The base workflow's weekly pull request ([docs/versions.md](docs/versions.md#how-the-pins-move)) holds a commit that no person wrote, so it has no sign-off. Whoever merges it reviews it and is responsible for it. If you add a commit to that pull request, sign it off as usual.

## Licence headers

Every file starts with a header that says who holds the copyright and which licence applies, following the [REUSE](https://reuse.software/) specification. In a shell script it looks like this:

<!-- REUSE-IgnoreStart -->

```sh
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
```

<!-- REUSE-IgnoreEnd -->

- "Lumen OS contributors" means everyone who wrote part of the file; the git history records who wrote what.
- A file that can't hold a comment, such as an image, gets an entry in `REUSE.toml` instead.
- Files copied from other projects keep their original copyright and licence lines.
- `just lint` runs `reuse lint`, which fails if any file is missing this information.
