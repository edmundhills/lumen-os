<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# image

The Lumen OS image: an OCI container image built `FROM` Fedora Kinoite and managed by bootc. It is the whole operating system, and it updates as one piece.

| Path | What it is | Step |
| --- | --- | --- |
| `packages.toml` | The packages Lumen adds to Kinoite and the ones it removes | 1.1 |
| `Containerfile` | The multi-stage build: `base`, `devel`, the build stages, `lumen`, the variants and `live` | 1.2 |
| `overlay/` | Files copied into the image as they are: vendor defaults in `/usr/lib` and `/usr/share`, and the image's `/etc` only where a setting can live nowhere else. Never `/usr/etc` (ADR 0002) | 1.3 |

- Kinoite is pinned by digest. Every Lumen package that links KWin or Plasma is built in a stage of this Containerfile against that exact base (CLAUDE.md, "Critical build rule").
- Everything in `overlay/` lands in the image's root folder, so `overlay/` holds only files meant for the image, and no README.
- Variants: `lumen` (the default), `lumen-gaming` (step 1.10) and `lumen-nvidia` (step 1.11).

Spec: [image build and layout](../docs/spec.md#spec-image-build-and-layout). Architecture: [4.1 Base image](../docs/architecture.md#41-base-image), [9.3 Inside the image build](../docs/architecture.md#93-inside-the-image-build), [9.5 Variants](../docs/architecture.md#95-variants).
