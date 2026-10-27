# Lumen OS — step-by-step build plan

The spec's 9 phases, cut into session-sized steps. Do **one step per session**.

## How to resume

1. Start a **new** session with the Lumen OS project folder selected (a fresh session is cheaper than continuing a long one).
2. Send: `Do the next step in PROGRESS.md.`
3. If a session ran out mid-step, send: `Continue the current step in PROGRESS.md.`

Claude reads CLAUDE.md automatically, does that one step, commits, updates this file, and stops.

**Legend:** 👤 = needs you (an account, an admin install, real hardware or an approval). ⚠️ = big step, may get split into a/b sub-steps.

## Current step

**A4**

## Notes for the next session

- `docs/spec.md` was generated from the .docx by a converter script; the architecture diagram is `docs/images/architecture.png`. If the .docx changes, regenerate it with a converter (e.g. pandoc) rather than hand-editing.
- Project folder: `C:\Users\edmun\Downloads\Lumen OS`. Git for Windows is installed at `C:\Program Files\Git\cmd\git.exe` (open a new terminal if `git` isn't on PATH yet).
- Spec source: `C:\Users\edmun\Downloads\Perfect Linux Distro — Spec & Build Prompt.docx`.
- A3 done 2026-10-27: repo https://github.com/edmundhills/lumen-os (push works); COPR account active. Commits must use the owner's GitHub no-reply email (set in `.git/config`), never their personal email.
- No licence is chosen yet (the spec doesn't name one). lumen-glass forks KWin code (GPL-2.0-or-later), so the licence must be GPL-compatible. Ask the owner before 0.4.
- Spec issue to raise at step 1.3: the spec puts image defaults in `/usr/etc`, but `bootc container lint` rejects images that contain `/usr/etc`. The likely fix is to write defaults to `/etc` in the Containerfile (bootc 3-way merges it) or to `/usr/lib` / `/usr/share`. Verify, ask the owner, record an ADR.

---

## Stage A — Setup (once)

- [x] **A1** 👤 Move the project to a permanent folder (e.g. `Documents\lumen-os`) and `git init`. *Done when:* CLAUDE.md and PROGRESS.md are in a git repo.
- [x] **A2** Convert the .docx to `docs/spec.md` with a tool (pandoc or python-docx), not by retyping. Keep tables as Markdown tables; note the missing architecture diagram. *Done when:* every spec section and table is present.
- [x] **A3** 👤 Create an empty GitHub repo `lumen-os` (public = free Actions minutes), add the remote, push. Create a COPR account (needed from Phase 1). *Done when:* `git push` works.
- [ ] **A4** 👤 Dev setup on Windows 11 Home: WSL2 + Fedora, Podman, `just`, git, gh. Claude writes `docs/dev-setup-windows.md` and a check script. Check 100 GB free disk and whether nested virtualization works. *Done when:* the check script passes in WSL.

## Phase 0 — Plan and skeleton (spec: "Claude Code prompt → Phase 0")

- [ ] **0.1** `docs/architecture.md` part 1: components and how they talk (D-Bus names, files, protocols).
- [ ] **0.2** `docs/architecture.md` part 2: build flow and a Mermaid dependency graph.
- [ ] **0.3** `docs/risks.md`: top 15 technical risks with mitigations.
- [ ] **0.4** Repo skeleton from the CLAUDE.md layout, with a README in each folder.
- [ ] **0.5** `justfile` (build-image, build-iso, run-vm, test, lint) and lint tooling. *Done when:* `just lint` passes in WSL.
- [ ] **0.6** GitHub Actions: lint job and a placeholder build job. *Done when:* CI is green.
- [ ] **0.7** `docs/versions.md`: current Fedora release, KWin version and Kinoite image digest (read via skopeo/podman, in CI or WSL).
- [ ] **0.8** 👤 Phase 0 acceptance: you review the docs; `just lint` and CI are green.

## Phase 1 — Bootable image (spec: "Spec: image build and layout", Phase 1)

- [ ] **1.1** `image/packages.toml` from the package manifest table (install and remove lists).
- [ ] **1.2** `image/Containerfile`: FROM Kinoite pinned by digest; install/remove packages; `bootc container lint`.
- [ ] **1.3** Overlay: enable firewalld, fwupd-refresh.timer, snapper timers, power-profiles-daemon; SELinux enforcing; remove the stock Plasma layout and Discover. Raise the `/usr/etc` issue first.
- [ ] **1.4** Btrfs zstd defaults and snapper config for /home (24 hourly, 7 daily, 4 weekly).
- [ ] **1.5** CI: build the default image and push to ghcr.io (free runner disk space first; Kinoite images are large).
- [ ] **1.6** 👤 cosign signing (you add the key as a repo secret) and SBOM with syft.
- [ ] **1.7** `/etc/containers/policy.json` and sigstore config so the system accepts only our signed images.
- [ ] **1.8** CI: bootc-image-builder builds qcow2 and anaconda-iso artifacts.
- [ ] **1.9** `tests/boot`: QEMU/KVM boot test in CI; SDDM within 60 s; `systemctl --failed` empty.
- [ ] **1.10** Variant `lumen-gaming`: Steam, Gamescope session, MangoHud, controller udev rules.
- [ ] **1.11** ⚠️ Variant `lumen-nvidia`: akmods-built, signed kmods in CI.
- [ ] **1.12** NVIDIA MOK enrolment doc; CI matrix builds all variants.
- [ ] **1.13** 👤 Phase 1 acceptance: install the ISO in a VM (VirtualBox 7 has a virtual TPM and Secure Boot) with encryption; `bootc status`, `bootc upgrade`, `bootc rollback`. Claude writes the checklist; you run it.

## Phase 2 — Design tokens and theme (spec: "Liquid glass", "Design tokens", Phase 2)

- [ ] **2.1** `tokens.json` part 1: colours (light, dark, 8 accents), Inter type scale, radii, 4 px spacing, elevation, plus a JSON schema.
- [ ] **2.2** `tokens.json` part 2: glass presets per role (all parameters from the spec table) and spring presets; validation test.
- [ ] **2.3** Exporter framework and the QML singleton module `org.lumen.style`.
- [ ] **2.4** Exporter: KDE colour schemes.
- [ ] **2.5** Exporter: Kvantum theme.
- [ ] **2.6** Exporter: GTK 4/libadwaita CSS.
- [ ] **2.7** Exporter: GTK 3 theme.
- [ ] **2.8** KDecoration plugin scaffold, built in a Containerfile stage.
- [ ] **2.9** Decoration: rounded corners and glass titlebar role.
- [ ] **2.10** Cursor and icon theme config (open icon set with accent recolouring).
- [ ] **2.11** Global theme (look-and-feel package) `org.lumen.desktop`.
- [ ] **2.12** Run all exporters during the image build.
- [ ] **2.13** Visual test: Qt, GTK 4, GTK 3 and Flatpak apps in light and dark; store golden images.
- [ ] **2.14** 👤 Phase 2 acceptance: all four app types match in both modes; one accent change updates all of them.

## Phase 3 — lumen-glass (spec: "Spec: lumen-glass effect", Phase 3)

- [ ] **3.1** ⚠️ Fork KWin's blur effect (the image's exact KWin version) into `glass/` as `lumen-glass`; build as an RPM in a Containerfile stage.
- [ ] **3.2** Ship it in the image; confirm it matches stock blur in a VM.
- [ ] **3.3** Shared 1/4-resolution dual-Kawase blur, computed once per frame.
- [ ] **3.4** Damage-aware caching: idle frames do no blur work.
- [ ] **3.5** ⚠️ Shader part 1: rounded-rect SDF clip, edge refraction, RGB dispersion.
- [ ] **3.6** Shader part 2: vibrancy, rim light, blue-noise dither.
- [ ] **3.7** Shader part 3: adaptive tint from smallest-mip luminance, keeping 4.5:1 contrast.
- [ ] **3.8** Roles: window property → presets from tokens.json; reload on token change via D-Bus.
- [ ] **3.9** Rounded corners and soft shadows for all windows; titlebar role.
- [ ] **3.10** Tiers Full / Lite / Solid in the render path.
- [ ] **3.11** First-boot benchmark oneshot → `/var/lib/lumen/glass-tier`; battery saver drops a tier; Reduce Transparency and Reduce Motion.
- [ ] **3.12** Spring open/close/morph animations (stiffness 380, damping 30).
- [ ] **3.13** Smooth-min SDF merging for dock shapes within 12 px.
- [ ] **3.14** GTK module that requests the blur region for GTK 4/3 windows that declare glass.
- [ ] **3.15** ⚠️ Test harness: `kwin_wayland --virtual` in CI rendering the 12 reference scenes.
- [ ] **3.16** Golden-image compare, contrast computation, frame-time benchmark.
- [ ] **3.17** 👤 Phase 3 acceptance: contrast ≥ 4.5:1 everywhere; 60 fps with 8 surfaces on Iris Xe-class graphics (real hardware); idle GPU near zero; Solid tier samples no backdrop.

## Phase 4 — lumen-shell (spec: "Spec: lumen-shell", "Default shortcuts and gestures", Phase 4)

- [ ] **4.1** Shell package `org.lumen.desktop` skeleton; builds and loads in the image.
- [ ] **4.2** Top bar layout (left / centre / right), glass role bar, 32 px.
- [ ] **4.3** Top bar indicators: tray, network, sound, battery, user; camera/mic/location indicators.
- [ ] **4.4** Dock: pinned and running apps (TaskManager), running dot.
- [ ] **4.5** Dock: progress bars, badges, recent files on right-click, auto-hide.
- [ ] **4.6** Command palette QML UI over KRunner: apps, files, settings, calculator, unit and currency conversion.
- [ ] **4.7** Palette: `>` commands, `?` web search, open windows.
- [ ] **4.8** Quick settings tiles and sliders, rearrangeable.
- [ ] **4.9** Notification centre: grouped, inline reply, actions, 7-day history.
- [ ] **4.10** Focus modes (Work, Gaming, Sleep).
- [ ] **4.11** Overview restyle.
- [ ] **4.12** Tiling: custom tiles, Super+arrows, saved layouts per monitor.
- [ ] **4.13** Auto-tile KWin script per workspace.
- [ ] **4.14** Lock screen theme.
- [ ] **4.15** SDDM theme (Wayland greeter).
- [ ] **4.16** OSD restyle.
- [ ] **4.17** Apply every shortcut and gesture; Super+/ cheat-sheet overlay.
- [ ] **4.18** QML unit tests; session test that opens each surface and screenshots it.
- [ ] **4.19** Keyboard-only and Orca tests; startup < 1.5 s and < 250 MB check.
- [ ] **4.20** 👤 Phase 4 acceptance.

## Phase 5 — Services, CLI and Settings (spec: "Spec: lumen CLI and services", "Spec: updates, rollback and backup", "Spec: Lumen Settings and System Health", Phase 5)

- [ ] **5.1** Rust workspace (`services/`, `cli/`), shared D-Bus interface crate, hardened systemd unit and polkit templates.
- [ ] **5.2** `lumen-settingsd`: TOML store, get/set/list, change signals.
- [ ] **5.3** `lumen` CLI skeleton (clap): `--json`, completions, `lumen settings`.
- [ ] **5.4** `lumen-updated` part 1: timer, check order (bootc, Flatpak, fwupd), D-Bus API.
- [ ] **5.5** `lumen-updated` part 2: low-priority downloads, metered/battery rules, staging, one notification.
- [ ] **5.6** `lumen-updated` part 3: post-boot health check with boot-counting fallback.
- [ ] **5.7** `lumen-updated` part 4: history, rollback to signed tags; `lumen update`, `lumen rollback`.
- [ ] **5.8** `lumen-health`: first 5 checks with fixes.
- [ ] **5.9** `lumen-health`: last 5 checks with fixes; `lumen health [--fix]`.
- [ ] **5.10** `lumen-hwd`: report, driver status, NVIDIA image switch; `lumen hw report`.
- [ ] **5.11** `lumen-backupd` (restic schedules) and `lumen backup`.
- [ ] **5.12** CLI: `lumen app`, `lumen dev enable`, `lumen glass tier`.
- [ ] **5.13** Settings app frame: glass sidebar, search across pages, `lumen-settings://` deep links.
- [ ] **5.14** Settings pages: Wi-Fi & Network, Bluetooth.
- [ ] **5.15** Settings pages: Displays, Sound.
- [ ] **5.16** Settings pages: Appearance, Desktop & Dock.
- [ ] **5.17** Settings pages: Notifications, Power & Battery.
- [ ] **5.18** Settings pages: Privacy & Security, Users.
- [ ] **5.19** Settings pages: Apps, Updates.
- [ ] **5.20** Settings pages: Backup, Drivers & Hardware.
- [ ] **5.21** Settings pages: Keyboard & Input, Accessibility.
- [ ] **5.22** Settings pages: Developer, About & Health.
- [ ] **5.23** Tests: GUI and CLI give identical results; update + rollback in the VM; each Health check triggered and fixed.
- [ ] **5.24** 👤 Phase 5 acceptance.

## Phase 6 — Store, Welcome, Backup, installer, hardware report (spec: "Spec: Store, first run, installer, hardware report", Phase 6)

- [ ] **6.1** Store backend (libflatpak + AppStream): list and search.
- [ ] **6.2** Store home collections and app page (screenshots, verified badge, plain-English permissions with risk colour).
- [ ] **6.3** One-button install/update/remove/open; Windows/macOS name aliases data file.
- [ ] **6.4** Bottles flow for `.exe` files.
- [ ] **6.5** Welcome steps 1–3: language and keyboard, Wi-Fi, account with fingerprint.
- [ ] **6.6** Welcome step 4: TPM2 enrolment and recovery key.
- [ ] **6.7** Welcome steps 5–9: privacy, look, import, apps, gesture tour.
- [ ] **6.8** Backup app UI: external drive, SMB, S3.
- [ ] **6.9** "Previous versions" in Files via snapper.
- [ ] **6.10** Installer theme and the three install modes.
- [ ] **6.11** `hardware/hardware.json` and the `lumen-hwd` compare logic.
- [ ] **6.12** Live-session hardware report app (green / amber / red).
- [ ] **6.13** 👤 Phase 6 acceptance: install to usable desktop in < 15 min; a non-technical tester sets up, installs an app, restores a file and runs a backup unaided.

## Phase 7 — Hardening, accessibility, performance (spec: "Spec: security model", Phase 7)

- [ ] **7.1** Security review part 1 (boot, disk, image) → `docs/security.md`; fix gaps.
- [ ] **7.2** Security review part 2 (apps, network, privilege, supply chain: SBOM, Renovate, pinned digests); fix gaps.
- [ ] **7.3** Accessibility audit: shell surfaces.
- [ ] **7.4** Accessibility audit: apps.
- [ ] **7.5** Performance: boot < 10 s on NVMe.
- [ ] **7.6** Performance: idle RAM < 1.5 GB.
- [ ] **7.7** Translations: string extraction, Weblate config, pseudo-locale.
- [ ] **7.8** 👤 Phase 7 acceptance on a real laptop.

## Phase 8 — Release v0.1 (spec: "Testing, CI and release", Phase 8)

- [ ] **8.1** Release train in CI: dev on every merge, weekly beta, stable every 2 weeks after 7 days in beta.
- [ ] **8.2** Update test job: install previous, upgrade, reboot, roll back, reboot.
- [ ] **8.3** Docs: user guide and install guide.
- [ ] **8.4** Docs: FAQ, hardware notes, contributing guide.
- [ ] **8.5** 👤 Publish v0.1 (you approve): signed images, ISO, SBOM, checksums, plain-English changelog.
- [ ] **8.6** 👤 Install and run v0.1 on two real machines.
