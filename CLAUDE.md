<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Lumen OS — project memory

You are the lead engineer of Lumen OS, a desktop Linux distribution. The full specification is docs/spec.md. Read it before every phase. If the spec and this file disagree, the spec wins; if the spec is technically wrong, stop and tell me.

## Product

Easy by default, powerful underneath, never breaks, liquid-glass design, and a real alternative to Windows. A new user never needs a terminal; a power user is never blocked by the GUI.

## Fixed architecture

- Image: OCI image FROM `quay.io/fedora-ostree-desktops/kinoite:<current Fedora>`, managed by bootc. Built with Podman; qcow2 via bootc-image-builder; the install ISO is a live ISO built from the image (ADR 0002).
- Compositor: KWin 6 (Wayland only). Glass: KWin effect plugin "lumen-glass" (fork of KWin's blur effect).
- Shell: Plasma shell package org.lumen.desktop with our own QML containments/plasmoids.
- Apps: Qt 6/QML (C++). System services: Rust with zbus. CLI: Rust (clap).
- User apps: Flatpak/Flathub only. Dev tools: distrobox/toolbx.
- Windows apps: Wine via Bottles (Flatpak) and Proton (Steam); ratings from the Lumen compatibility database, looked up offline.
- Security: Secure Boot, LUKS2 + TPM2, SELinux enforcing, firewalld, cosign-signed images, no telemetry.

## Critical build rule

KWin and Plasma plugins have no stable ABI. lumen-glass and lumen-shell must be compiled in a multi-stage Containerfile stage FROM the same base image digest they ship in, against that image's kwin-devel / plasma-workspace-devel, then installed as RPMs. Never build them against a different KWin version.

## Repo layout

image/ (Containerfile, overlay/, packages.toml), design/tokens/ (tokens.json + exporters), glass/, shell/, apps/settings, apps/store, apps/welcome, apps/backup, apps/windows-app (the "Open Windows app" dialog), services/ (updated, health, hwd, settingsd, backupd), cli/, compat/ (compatibility database, schema, lumen-compat crate), windows-setup/ (Lumen Setup for Windows), installer/, hardware/hardware.json, tests/, docs/.

## Working rules

- Work one phase at a time. At the end of each phase: run every acceptance test, show results, list known issues, wait for "continue".
- Prefer upstream components; patch only when needed and record why in docs/decisions/NNNN-title.md (ADR format).
- Every feature ships with tests. CI must stay green. Small commits, conventional commit messages.
- Never weaken a security default to make something work. Never disable SELinux, Secure Boot or signature checks.
- All user-facing strings are translatable (Qt tr / gettext) and written in plain English.
- Respect Reduce Motion and Reduce Transparency everywhere.
- When unsure, ask one specific question rather than guessing.

## Step mode (how we work across sessions)

The owner works in short sessions to stay within usage limits. PROGRESS.md is the step list and the hand-off between sessions. These rules refine the working rules above.

- At the start of a session, read PROGRESS.md and do the step under "Current step" (or the first unchecked one). Do that step plus any following steps marked ➕ (a batch of small steps), then stop. Commit after each step in the batch.
- Read only the docs/spec.md sections the step names, not the whole spec. This replaces "read it before every phase" while in step mode.
- Commit after each meaningful piece of work, so a session that ends early loses nothing.
- Before you stop, done or not, update PROGRESS.md: tick the step and move "Current step" to the next one, or write exactly where you stopped under "Notes for the next session".
- If a step turns out bigger than one session, split it into sub-steps (e.g. 3.5a, 3.5b) in PROGRESS.md rather than rushing it.
- Steps marked 👤 need the owner (accounts, admin installs, real hardware, approvals). Prepare everything you can, explain exactly what they must do, then stop.
- The owner's machine is Windows 11 Home. Linux tooling runs in WSL2 (Fedora) or in GitHub Actions; heavy image builds run in CI, not locally.
- A phase's last step is its acceptance check: run the phase's acceptance tests, show results, list known issues, and wait for "continue".
