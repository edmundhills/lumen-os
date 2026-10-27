<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# tests

Tests that cover more than one component, and the checks for the developer setup. Unit tests live next to the code they test (`cargo test`, Qt Test).

| Folder | What it checks | Runs | Step |
| --- | --- | --- | --- |
| [dev-env/](dev-env/) | `check-wsl.sh`: a WSL 2 + Fedora PC is ready for Lumen development ([guide](../docs/dev-setup-windows.md)) | By hand, in WSL | A4 |
| [lint/](lint/) | The lint checks (`run.sh`): licences and copyright (reuse), shell scripts (shellcheck, shfmt), Markdown style (markdownlint) and links, the justfile's format, whitespace, and the repository layout. `Containerfile` builds the container they run in, and `selftest.sh` proves each check fails on a file that breaks its rule | `just lint`, `just test`; CI from step 0.6 | 0.5 |
| `boot/` | The image boots in QEMU to the login screen within 60 seconds, with no failed units | CI | 1.9 |

The other layers (session, glass visual, accessibility, performance, update and Windows compatibility tests) get their folders when their steps start.

Spec: [Test layers](../docs/spec.md#test-layers). Architecture: [9.9 Where each test layer runs](../docs/architecture.md#99-where-each-test-layer-runs).
