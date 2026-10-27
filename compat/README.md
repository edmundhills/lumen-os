<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# compat

The Windows app compatibility database, and the code that reads it.

| Part | What it is | Steps |
| --- | --- | --- |
| `windows-apps.json` and the data files beside it | One entry per Windows program: how to recognise it, its rating and the reason, known issues, the recipe for Bottles, alternatives, anti-cheat status, and when and how it was last tested | 1.15 (v0, 20 entries), 7.2 (the top 100) |
| The JSON schema | Checks every entry in CI | 1.15 |
| `lumen-compat` | A Rust crate that identifies a `.exe` or `.msi` (version info, installer type, file hash) and looks it up. The Store, the "Open Windows app" dialog, Welcome and `lumen app check` all use it, so they can't disagree | 7.4 |

- Lookups never touch the network. lumen-updated keeps a newer signed copy of the database between image updates (step 7.3).
- A nightly CI job installs and launches freely downloadable Windows apps under the image's Wine and updates each entry's "last tested" (step 1.16).
- **Licences** ([ADR 0003](../docs/decisions/0003-licence.md)): the database is published under the Open Database License 1.0, because it includes ProtonDB data; its licence file arrives with the database at step 1.15. The `lumen-compat` crate is code, so it is GPL-3.0-or-later. Contributions to the database are offered under ODbL 1.0 ([CONTRIBUTING.md](../CONTRIBUTING.md)).

Spec: [Compatibility ratings](../docs/spec.md#compatibility-ratings), [Compatibility database](../docs/spec.md#compatibility-database). Architecture: [4.9 Windows apps and switching](../docs/architecture.md#49-windows-apps-and-switching). Risks: [12](../docs/risks.md#12-licences-of-compatibility-data).
