<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# image

The Lumen OS image: an OCI container image built `FROM` Fedora Kinoite and managed by bootc. It is the whole operating system, and it updates as one piece.

| Path | What it is | Step |
| --- | --- | --- |
| `packages.toml` | The package manifest: the Fedora packages Lumen keeps from Kinoite, adds and removes, by the areas of the spec's manifest | 1.1 |
| `packages.py` | Checks the manifest (`just lint`) and applies it in the `base` stage. It stops the build if the manifest doesn't match Kinoite, or if dnf removes a package the manifest doesn't list. `test_packages.py` holds its unit tests (`just test`) | 1.1 |
| `Containerfile` | The multi-stage build. Phase 1 has `base` (Kinoite plus the manifest) and `lumen` (the image users get, ending with `bootc container lint`); `devel`, the build stages, the variants and `live` come with their steps | 1.2 |
| `overlay/` | Files copied into the image as they are: vendor defaults in `/usr/lib` and `/usr/share`, and the image's `/etc` only where a setting can live nowhere else. Never `/usr/etc` (ADR 0002) | 1.3 |

- Kinoite is pinned by digest. Every Lumen package that links KWin or Plasma is built in a stage of this Containerfile against that exact base (CLAUDE.md, "Critical build rule").
- Everything in `overlay/` lands in the image's root folder, so `overlay/` holds only files meant for the image, and no README.
- Variants: `lumen` (the default), `lumen-gaming` (step 1.10), `lumen-nvidia` (step 1.11) and `lumen-gaming-nvidia` (step 1.12, ADR 0004).

Spec: [image build and layout](../docs/spec.md#spec-image-build-and-layout). Architecture: [4.1 Base image](../docs/architecture.md#41-base-image), [9.3 Inside the image build](../docs/architecture.md#93-inside-the-image-build), [9.5 Variants](../docs/architecture.md#95-variants).
