<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Lumen OS

Lumen OS is a desktop Linux distribution built to be a real alternative to Windows: easy by default, powerful underneath, never breaks, with a liquid-glass design. A new user never needs a terminal; a power user is never blocked by the GUI.

It is built on Fedora Kinoite as a bootc image. The system is a signed, read-only image that updates as one piece and can go back to the previous version. Apps come from Flathub. Windows programs run on Wine through Bottles, and Lumen shows how well each one works before it is installed; games run through Steam and Proton.

## Status

Early development: there is nothing to install yet. [PROGRESS.md](PROGRESS.md) lists every step and shows where work stands.

## Documents

| Document | What it says |
| --- | --- |
| [docs/spec.md](docs/spec.md) | The specification, and the source of truth |
| [docs/architecture.md](docs/architecture.md) | The components, how they talk to each other, and how they are built |
| [docs/risks.md](docs/risks.md) | The top technical risks and what we do about each |
| [docs/competing-with-windows.md](docs/competing-with-windows.md) | What stops people switching from Windows, and what Lumen does about each item |
| [docs/decisions/](docs/decisions/) | Architecture decision records |

## Repository layout

| Folder | Holds | Phase |
| --- | --- | --- |
| [image/](image/) | The OS image: Containerfile, package list and overlay | 1 |
| [design/](design/) | The design tokens and their exporters, the window decoration and the global theme | 2 |
| [glass/](glass/) | lumen-glass, the KWin effect that draws the glass | 3 |
| [shell/](shell/) | lumen-shell: the top bar, dock, command palette and the rest of the desktop | 4 |
| [services/](services/) | The system and session services | 5 |
| [cli/](cli/) | The `lumen` command | 5 |
| [apps/](apps/) | Settings, Store, Welcome, Backup and the "Open Windows app" dialog | 5 to 7 |
| [installer/](installer/) | The installer's kickstart and theme | 1, 6 |
| [hardware/](hardware/) | The hardware database | 6 |
| [compat/](compat/) | The Windows app compatibility database and the `lumen-compat` crate | 1, 7 |
| [windows-setup/](windows-setup/) | Lumen Setup for Windows | 7 |
| [tests/](tests/) | Tests that cover more than one component | All |
| [docs/](docs/) | The documents above, and the developer setup guide | All |

Each folder's README says what goes in it and which step builds it.

## Building

Development needs Linux, or Windows 11 with WSL 2 and Fedora: see the [Windows setup guide](docs/dev-setup-windows.md). The image and the install media are built in GitHub Actions. With [just](https://just.systems/) and Podman installed:

```sh
just        # list the recipes
just lint   # check licences, formatting and the links between documents
just test   # run the tests that work on this machine
```

The lint tools run in a container, so nothing else needs installing.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Every commit needs a `Signed-off-by:` line, which certifies the Developer Certificate of Origin.

## Licence

- Lumen's code is licensed under the GNU General Public License, version 3 or (at your option) any later version: GPL-3.0-or-later. The full text is in [LICENSE](LICENSE).
- The Windows app compatibility database in `compat/` will be published under the Open Database License 1.0 (ODbL-1.0); its licence file arrives with the database at step 1.15. The `lumen-compat` crate in the same folder is code, so it is GPL-3.0-or-later.
- Files that come from other projects, such as the KWin code that lumen-glass forks, keep their own copyright and licence notices.
- Every file states its licence with an SPDX header, following the [REUSE](https://reuse.software/) specification.

[ADR 0003](docs/decisions/0003-licence.md) explains the choice.
