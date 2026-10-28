<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Lumen OS — step-by-step build plan

The spec's 10 phases (0–9), cut into session-sized steps. Do **one step per session**.

## How to resume

1. Start a **new** session with the Lumen OS project folder selected (a fresh session is cheaper than continuing a long one).
2. Send: `Do the next step in PROGRESS.md.`
3. If a session ran out mid-step, send: `Continue the current step in PROGRESS.md.`

Claude reads CLAUDE.md automatically, does that step (plus any ➕ steps right after it), commits, updates this file, and stops.

**Legend:** 👤 = needs you (an account, an admin install, real hardware or an approval). ⚠️ = big step, may get split into a/b sub-steps. ➕ = small step, done in the same session as the step above it (a batch).

## Current step

**1.3** Overlay, then ➕ **1.4** Btrfs and snapper defaults.

## Notes for the next session

- `docs/spec.md` is the source of truth (owner's decision, 2026-10-27, ADR 0001). Edit it directly; the original .docx (`C:\Users\edmun\Downloads\Perfect Linux Distro — Spec & Build Prompt.docx`) is historical and no longer kept in sync. The architecture diagram is `docs/images/architecture.png`.
- Project folder: `C:\Users\edmun\Downloads\Lumen OS`. Git for Windows is installed at `C:\Program Files\Git\cmd\git.exe` (open a new terminal if `git` isn't on PATH yet).
- A3 done 2026-10-27: repo <https://github.com/edmundhills/lumen-os> (push works); COPR account active, but not needed for now (ADR 0004). Commits must use the owner's GitHub no-reply email (set in `.git/config`), never their personal email.
- Licence decided 2026-10-27 (ADR 0003): code GPL-3.0-or-later, compatibility data ODbL 1.0. For 0.4: add `LICENSE` with the GPL-3.0 text copied unchanged from gnu.org (don't retype it), a licence section in the top-level README, and `CONTRIBUTING.md` with the DCO sign-off rule; new source files get SPDX headers. For 0.5: add `reuse lint` to `just lint`.
- A4 done 2026-10-27: Fedora 44 in WSL as `FedoraLinux-44` (on D:, user `User`), default distro. Check passes (18 pass). Nested virtualization does NOT work (`/dev/kvm` missing; maybe SVM off in BIOS), so no local VMs: run boot tests in CI. WSL has 7.7 GiB RAM. Fedora WSL has no awk; scripts must not assume it.
- ADR 0001 accepted 2026-10-27: Lumen is built to compete with Windows. Applied to the spec, this file and CLAUDE.md (new Phase 7 "Switching from Windows"; old Phases 7–8 are now 8–9). The gap list `docs/competing-with-windows.md` is a living document: update it when a gap changes. The owner deferred a Windows-style "Familiar" layout and a built-in AI assistant; don't add either without asking.
- Machine facts (2026-10-27): Ryzen 7 5800X, 16 GB RAM, virtualization on in firmware, Windows 11 Home build 26200, gh not installed on Windows. Claude reaches WSL from Windows with `wsl -d <distro> --cd "<repo>" -- <cmd>`; set `WSL_UTF8=1` (else UTF-16 output), and from Git Bash prefix `MSYS_NO_PATHCONV=1`.
- 0.1 done 2026-10-27: `docs/architecture.md` part 1. Written against the spec as amended by ADR 0001. Its section 8 listed five spec errors (Q1–Q5); with the `/usr/etc` issue they were fixed in the spec, PROGRESS.md and the architecture on the owner's instruction (ADR 0002, 2026-10-27). Q6–Q11 were accepted at 0.8 (ADR 0004).
- 0.2 done 2026-10-27: `docs/architecture.md` part 2 (sections 9 and 10): build flow, Containerfile stages, exact-version matching against the base image, variants, install media, tags and keys, CI workflows, where each test runs, and three Mermaid graphs (checked to render with Mermaid 10.9.1 and 11.4.1). It added open questions Q12–Q15, all accepted at 0.8 (ADR 0004). Q12: every Lumen package is built in a Containerfile stage, not in COPR; the spec's "Base and build chain" now says so.
- Risks for 0.3 found while writing part 2 (sections 9.4–9.9): KWin/Plasma version drift between the pinned image and Fedora's mirrors (exact `-devel` versions, Koji fallback); rebasing lumen-glass on every Plasma feature release (three a year); the ISO exceeding GitHub's 2 GiB release-file limit (Q15); runner disk, the 6-hour job limit, and KVM on hosted runners; GPU-less CI, so glass tests run on llvmpipe and frame-time budgets need real hardware; large update downloads without re-chunking; NVIDIA module signing and MOK enrolment. Part 1 already flagged Flatpak theming (section 4.3) and camera access that bypasses PipeWire (section 4.4).
- ADR 0002 follow-up (step 0.2): the spec's build chain and CLAUDE.md's fixed architecture now say the install ISO is a live ISO built from the image, not from bootc-image-builder.
- ADR 0002 (2026-10-27): the owner confirmed that remote help is same-network in v0.1, with RustDesk offered for help over the internet. Building a live ISO from a bootc image (step 1.8) is the riskiest fix; the fallback is in the ADR.
- 0.3 done 2026-10-27: `docs/risks.md`, 15 ranked risks with mitigations, a watch list, and sources checked that day. It is a living document: update a risk when it changes. It adds Q16 (what "match" means for Flatpak theming, before 2.1) and **Q17** (TPM unlock bound to PCR 7 without a PIN can be defeated by booting any Fedora-signed system, so the spec's "a stolen laptop reveals nothing" doesn't hold; owner chooses PIN by default or more PCRs via systemd-pcrlock). Both decided at 0.8 (ADR 0004): Q16 as proposed; Q17 option (b), pcrlock binding with no PIN by default, with a PIN by default as the fallback if 6.6 can't make (b) reliable.
- 0.4 done 2026-10-27: a README in every folder of the CLAUDE.md layout, plus `docs/README.md` and `docs/decisions/README.md` (ADR index and format); top-level `README.md` with the licence section; `CONTRIBUTING.md` with the DCO rule; `LICENSE` copied from gnu.org (sha256 `3972dc97…6986`, the same file Fedora ships in coreutils). `image/overlay/` doesn't exist yet: everything in it is copied into the image root, so it can't hold a README (step 1.3 creates it). Decided at 0.8 (ADR 0004): the hardware report lives in `apps/hwreport`; an AI assistant never adds a `Signed-off-by:` line (CONTRIBUTING.md), so the owner signs off Claude's commits before each push; copyright lines stay "Lumen OS contributors".
- 0.5 done 2026-10-27: `just lint` passes in WSL (8 of 8 checks, about 7 s) and `just test` passes (the self-test: each check fails on a planted fault). The tools run in a container from `tests/lint/Containerfile` (Fedora 44 pinned by digest; reuse 6.2, ShellCheck 0.11, shfmt 3.7, markdownlint-cli2 0.23, just 1.59; 452 MB, about 2 min to build the first time), with the checkout read-only and no network. `tests/lint/run.sh` lists the checks; `.editorconfig` holds the shfmt settings, `.markdownlint.yaml` the Markdown rules. `build-image`, `build-iso` and `run-vm` print which step makes them work and exit 1 until then. Every file now has an SPDX header; the architecture PNG is covered by `REUSE.toml`; `LICENSES/GPL-3.0-or-later.txt` must stay identical to `LICENSE` (lint checks it).
- Fixed after 0.5 (2026-10-27): the markdownlint crash. Fedora's Node has only English ICU data built in and loads the rest from `nodejs24-full-i18n`, a weak dependency that the lint container's `install_weak_deps=False` skipped. Without it, `Intl.Segmenter` segfaults on any text, and markdownlint calls it for table cells that aren't plain ASCII. The container now installs that package, MD060 (table column style) is back on, the self-test lints a table with an emoji, and `run.sh` reports a crashed tool as "crashed with exit status N". When the lint base moves to a new Fedora, keep the `24` in that package name equal to Node's major version.
- 0.6 done 2026-10-27: two workflows. `.github/workflows/lint.yml` runs `just lint` and `just test` on every push and pull request, in the same lint container as WSL, on `ubuntu-24.04` (Podman is preinstalled; just 1.59.0 comes from its release page, checked against a pinned SHA-256). `.github/workflows/image.yml` has the placeholder build job, which step 1.5 makes real. Both pin `actions/checkout` by commit (v7.0.1), start from `permissions: {}`, and don't keep the checkout's credentials. `just lint` now has 10 checks: yamllint 1.38 (`.yamllint.yaml`) checks every YAML file and actionlint 1.7.12 the workflows (it runs ShellCheck on their scripts). actionlint is the release binary, checked against a pinned SHA-256 in `tests/lint/Containerfile`. When you write new scripts, still mark them executable with `git add --chmod=+x`: the Windows checkout has `core.filemode=false`.
- 0.7 done 2026-10-27: `docs/versions.md`. Fedora **44** is current (Bodhi: F45 `frozen`, target release 2026-11-03). Kinoite `44.20261027.0`, index digest `sha256:9f71aa8e…5e18`, **KWin 6.7.5**, Plasma 6.7.5, Qt 6.11.2, KF 6.31.0, all read with skopeo from the image's layer names, without pulling its 2.9 GiB. Fedora 45's Kinoite has the same KWin, Plasma and Qt. **For 1.2:** read the versions again first; if Fedora 45 is out, start on 45. **Found:** dated Kinoite builds carry `quay.expires-after: 4w`, so a pinned digest stops resolving after about four weeks (the oldest dated 44 tag was four weeks old). Decided at 0.8 (ADR 0004): from step 1.5 the pin is bumped at least every two weeks (Renovate or a scheduled job), and each pinned base is copied to ghcr.io.
- From Git Bash, `wsl.exe -d FedoraLinux-44 -- cmd` passes the command line through the login shell, which expands `$variables` first; use `--exec bash -c '...'` for scripts (now in the setup guide).
- 0.8 done 2026-10-27: `just lint` 10 of 10 and `just test` 12 of 12 pass in WSL; CI green on `d211f2d` (read from the public Actions API, because gh isn't on Windows). The owner reviewed the Phase 0 docs and accepted every proposal as written; [ADR 0004](docs/decisions/0004-phase-0-review.md) records them, and they are applied to the spec, CLAUDE.md (build rule, `apps/hwreport` in the layout), the architecture and the risk register, which are now marked accepted with no **Proposed** markers left. New for Phase 1: a fourth image, `lumen-gaming-nvidia` (step 1.12); the Kinoite pin bump and ghcr.io copy (1.5); no COPR. Phase 1 starts when the owner says "continue".
- 1.1 done 2026-10-27 (Phase 1 started on the owner's "Do the next step"): `image/packages.toml`, one table per area of the spec's manifest with `keep` (Kinoite has it and Lumen relies on it), `install` and `remove` lists, read against Kinoite's own rpm database. Kinoite 44 already ships tuned-ppd instead of power-profiles-daemon, Liberation, Noto CJK and emoji, and NetworkManager-openconnect. Added: distrobox, snapper, `openrgb-udev-rules`, `libratbag-ratbagd`, Fcitx5 (Qt 6, GTK 3 and 4 modules, `kcm-fcitx5`, engines matching Kinoite's IBus ones), Inter (static `rsms-inter-fonts`: families "Inter" and "Inter Display"), JetBrains Mono, Carlito, Caladea. Removed: Discover (6 packages) and the unused font packs Adwaita Sans, Adwaita Mono and Open Sans; the other fonts cover scripts or other packages need them. Stock panels and plasmoids aren't separate packages, so 1.3 removes the default layout in the overlay. `image/packages.py` checks the file (`just lint`, now 11 checks; self-test 13) and applies it; `just test` also runs its 15 unit tests. It stops the build if a kept or removed package is missing from the base, an added one is already there, or dnf removes anything not listed. Weak dependencies are off.
- 1.2 done 2026-10-27: `image/Containerfile` with the stages `base` and `lumen`; Kinoite pinned as `kinoite:44@sha256:9f71aa8e…5e18` (Fedora 45 still frozen). `just build-image` in WSL: the first pull of Kinoite took 11 min, the build about 9 min; 41 packages added (with dependencies), 9 removed, none changed version; `bootc container lint --fatal-warnings` passes 14 checks, 1 skipped, as bare Kinoite does. dnf leaves `/run/dnf` and files in `/var`, which the lint rejects, so the `base` stage deletes them (Kinoite's own `/var` holds only `/var/tmp`); any later stage that runs dnf needs the same. `localhost/lumen:dev` is 7.63 GB, Kinoite 7.38 GB.
- [ADR 0005](docs/decisions/0005-plasma-login-manager.md) accepted 2026-10-27: Kinoite 44 has no SDDM; Fedora 44 ships KDE's Plasma Login Manager (`plasma-login-manager` 6.7.5, `plasmalogin.service` as `display-manager.service`). The owner chose to keep it. The spec, the architecture (4.4, 4.5) and steps 1.9, 4.15 and 5.6 now say "login screen" or name Plasma Login Manager, and `packages.toml` keeps it. Its greeter has no SDDM-style theme folder: it runs on its own KWin and Plasma, which step 4.15 works with.
- For later steps: os-release and the image labels (architecture 9.7) aren't named by any step; the Containerfile assigns them to 1.5. Solaar (6.4) needs `solaar-udev` on the host, which the spec's manifest doesn't list: add it at 6.4. Both IBus and Fcitx5 are installed; 1.3 should check which one starts by default on Plasma Wayland (Settings > Virtual Keyboard picks it).

---

## Stage A — Setup (once)

- [x] **A1** 👤 Move the project to a permanent folder (e.g. `Documents\lumen-os`) and `git init`. *Done when:* CLAUDE.md and PROGRESS.md are in a git repo.
- [x] **A2** Convert the .docx to `docs/spec.md` with a tool (pandoc or python-docx), not by retyping. Keep tables as Markdown tables; note the missing architecture diagram. *Done when:* every spec section and table is present.
- [x] **A3** 👤 Create an empty GitHub repo `lumen-os` (public = free Actions minutes), add the remote, push. Create a COPR account (needed from Phase 1). *Done when:* `git push` works.
- [x] **A4** 👤 Dev setup on Windows 11 Home: WSL2 + Fedora, Podman, `just`, git, gh. Claude writes `docs/dev-setup-windows.md` and a check script. Check 100 GB free disk and whether nested virtualization works. *Done when:* the check script passes in WSL.

## Phase 0 — Plan and skeleton (spec: "Claude Code prompt → Phase 0")

- [x] **0.1** `docs/architecture.md` part 1: components and how they talk (D-Bus names, files, protocols).
- [x] **0.2** `docs/architecture.md` part 2: build flow and a Mermaid dependency graph.
- [x] **0.3** `docs/risks.md`: top 15 technical risks with mitigations. Must include: the Secure Boot UEFI CA 2023 transition, hibernation under kernel lockdown, codec patents, BitLocker on Windows drives, Windows code signing for Lumen Setup, and the licences of compatibility data.
- [x] **0.4** Repo skeleton from the CLAUDE.md layout, with a README in each folder.
- [x] ➕ **0.5** `justfile` (build-image, build-iso, run-vm, test, lint) and lint tooling. *Done when:* `just lint` passes in WSL.
- [x] **0.6** GitHub Actions: lint job and a placeholder build job. *Done when:* CI is green.
- [x] ➕ **0.7** `docs/versions.md`: current Fedora release, KWin version and Kinoite image digest (read via skopeo/podman, in CI or WSL).
- [x] **0.8** 👤 Phase 0 acceptance: you review the docs; `just lint` and CI are green.

## Phase 1 — Bootable image (spec: "Spec: image build and layout", Phase 1)

- [x] **1.1** `image/packages.toml` from the package manifest table (install and remove lists).
- [x] ➕ **1.2** `image/Containerfile`: FROM Kinoite pinned by digest; install/remove packages; `bootc container lint`.
- [ ] **1.3** Overlay: enable firewalld, fwupd-refresh.timer, snapper timers, tuned-ppd; SELinux enforcing; remove the stock Plasma layout and Discover. Defaults go in `/usr/lib` and `/usr/share`, or the image's `/etc` where they can only live there; never `/usr/etc` (ADR 0002).
- [ ] ➕ **1.4** Btrfs zstd defaults and snapper config for /home (24 hourly, 7 daily, 4 weekly).
- [ ] **1.5** CI: build the default image and push to ghcr.io (free runner disk space first; Kinoite images are large). Bump the Kinoite pin at least every two weeks (Renovate or a scheduled job) and copy each pinned base to ghcr.io (ADR 0004).
- [ ] **1.6** 👤 cosign signing (you add the key as a repo secret) and SBOM with syft.
- [ ] ➕ **1.7** `/etc/containers/policy.json` and sigstore config so the system accepts only our signed images.
- [ ] **1.8** ⚠️ CI: bootc-image-builder builds the qcow2; build the install ISO as a live ISO from our image (try Titanoboa first) that runs a live session and starts Anaconda WebUI (ADR 0002). Record the tool in an ADR. If no live ISO works, fall back to `anaconda-iso` with a partial kickstart and tell the owner.
- [ ] **1.9** `tests/boot`: QEMU/KVM boot test in CI; the login screen within 60 s (`display-manager.service`, Plasma Login Manager, active and its greeter running; ADR 0005); `systemctl --failed` empty. Also boot once with Secure Boot (OVMF) and record whether kernel lockdown is on and hibernation is offered (`/sys/kernel/security/lockdown`, `/sys/power/state`) in ADR 0001's follow-up.
- [ ] **1.10** Variant `lumen-gaming`: Steam, Gamescope session, MangoHud, controller udev rules, as a layer that 1.12 also puts on `lumen-nvidia`.
- [ ] **1.11** ⚠️ Variant `lumen-nvidia`: akmods-built, signed kmods in CI.
- [ ] **1.12** NVIDIA MOK enrolment doc; variant `lumen-gaming-nvidia` (`lumen-nvidia` plus the gaming layer, ADR 0004); CI matrix builds all four images.
- [ ] **1.13** Windows-app base in the image: `ntsync` autoload, Bottles preinstalled on first boot, `.exe` and `.msi` open in Bottles until the Phase 7 dialog exists, metric-compatible fonts (Liberation, Carlito, Caladea). Boot test checks `/dev/ntsync` exists.
- [ ] **1.14** 👤 Codecs and hardware video decoding: Claude writes the options and their legal trade-offs as an ADR; you choose; Claude ships the choice.
- [ ] **1.15** Compatibility database v0 in `compat/`: JSON schema, validation test, first 20 entries, ODbL licence file.
- [ ] **1.16** ⚠️ Nightly CI compatibility job: install and launch freely downloadable Windows apps under the image's Wine, screenshot the window, update each entry's "last tested".
- [ ] **1.17** 👤 Phase 1 acceptance: install the ISO in a VM (VirtualBox 7 has a virtual TPM and Secure Boot) with encryption; `bootc status`, `bootc upgrade`, `bootc rollback`; double-clicking an `.exe` opens Bottles; the compatibility job is green. Claude writes the checklist; you run it.

## Phase 2 — Design tokens and theme (spec: "Liquid glass", "Design tokens", Phase 2)

- [ ] **2.1** `tokens.json` part 1: colours (light, dark, 8 accents), Inter type scale, radii, 4 px spacing, elevation, plus a JSON schema.
- [ ] ➕ **2.2** `tokens.json` part 2: glass presets per role (all parameters from the spec table) and spring presets; validation test.
- [ ] **2.3** Exporter framework and the QML singleton module `org.lumen.style`.
- [ ] **2.4** Exporter: KDE colour schemes.
- [ ] ➕ **2.5** Exporter: Kvantum theme.
- [ ] **2.6** Exporter: GTK 4/libadwaita CSS.
- [ ] ➕ **2.7** Exporter: GTK 3 theme.
- [ ] **2.8** KDecoration plugin scaffold, built in a Containerfile stage.
- [ ] ➕ **2.9** Decoration: rounded corners and glass titlebar role.
- [ ] **2.10** Cursor and icon theme config (open icon set with accent recolouring).
- [ ] ➕ **2.11** Global theme (look-and-feel package) `org.lumen.desktop`. It replaces the interim theme from 1.3 in `image/overlay`; keep its layout script (the interim top bar) until 4.2.
- [ ] ➕ **2.12** Run all exporters during the image build.
- [ ] **2.13** Visual test: Qt, GTK 4, GTK 3 and Flatpak apps in light and dark; store golden images.
- [ ] **2.14** 👤 Phase 2 acceptance: all four app types match in both modes (the same light or dark mode, accent, contrast and fonts; libadwaita apps keep their own shapes, ADR 0004); one accent change updates all of them.

## Phase 3 — lumen-glass (spec: "Spec: lumen-glass effect", Phase 3)

- [ ] **3.1** ⚠️ Fork KWin's blur effect (the image's exact KWin version) into `glass/` as `lumen-glass`; build as an RPM in a Containerfile stage.
- [ ] **3.2** Ship it in the image; confirm it matches stock blur in a VM.
- [ ] **3.3** Shared 1/4-resolution dual-Kawase blur, computed once per frame.
- [ ] **3.4** Damage-aware caching: idle frames do no blur work.
- [ ] **3.5** ⚠️ Shader part 1: rounded-rect SDF clip, edge refraction, RGB dispersion.
- [ ] **3.6** Shader part 2: vibrancy, rim light, blue-noise dither.
- [ ] **3.7** Shader part 3: adaptive tint from smallest-mip luminance, keeping 4.5:1 contrast.
- [ ] **3.8** Roles: the `lumen_glass_manager_v1` protocol (window type as a fallback) → presets from tokens.json; reload on token change via D-Bus.
- [ ] **3.9** Rounded corners and soft shadows for all windows; titlebar role.
- [ ] **3.10** Tiers Full / Lite / Solid in the render path.
- [ ] **3.11** First-boot benchmark oneshot → `/var/lib/lumen/glass-tier`; battery saver drops a tier; Reduce Transparency and Reduce Motion.
- [ ] **3.12** Spring open/close/morph animations (stiffness 380, damping 30).
- [ ] ➕ **3.13** Smooth-min SDF merging for dock shapes within 12 px.
- [ ] **3.14** GTK glass without a GTK module (ADR 0002): opt-in list of GTK app IDs with the tokens; lumen-glass draws whole-window glass for them; check that it shows only where the GTK themes (2.6, 2.7) left header bars and sidebars translucent.
- [ ] **3.15** ⚠️ Test harness: `kwin_wayland --virtual` in CI rendering the 12 reference scenes.
- [ ] **3.16** Golden-image compare, contrast computation, frame-time benchmark.
- [ ] **3.17** 👤 Phase 3 acceptance: contrast ≥ 4.5:1 everywhere; 60 fps with 8 surfaces on Iris Xe-class graphics (real hardware); idle GPU near zero; Solid tier samples no backdrop.

## Phase 4 — lumen-shell (spec: "Spec: lumen-shell", "Default shortcuts and gestures", Phase 4)

- [ ] **4.1** Shell package `org.lumen.desktop` skeleton; builds and loads in the image.
- [ ] **4.2** Top bar layout (left / centre / right), glass role bar, 32 px. It replaces the interim top bar from 1.3 (the layout script in Lumen's global theme).
- [ ] ➕ **4.3** Top bar indicators: tray, network, sound, battery, user; camera/mic/location indicators.
- [ ] **4.4** Dock: pinned and running apps (TaskManager), running dot.
- [ ] ➕ **4.5** Dock: progress bars, badges, recent files on right-click, auto-hide.
- [ ] **4.6** Command palette QML UI over KRunner: apps, files, settings, calculator, unit and currency conversion.
- [ ] ➕ **4.7** Palette: `>` commands, `?` web search, open windows.
- [ ] **4.8** Quick settings tiles and sliders, rearrangeable.
- [ ] **4.9** Notification centre: grouped, inline reply, actions, 7-day history.
- [ ] ➕ **4.10** Focus modes (Work, Gaming, Sleep).
- [ ] **4.11** Overview restyle.
- [ ] **4.12** Tiling: custom tiles, Super+arrows, saved layouts per monitor.
- [ ] ➕ **4.13** Auto-tile KWin script per workspace.
- [ ] **4.14** Lock screen theme.
- [ ] ➕ **4.15** Login screen: restyle Plasma Login Manager's greeter (ADR 0005). It runs on its own KWin and Plasma, so find out which Lumen styles and settings it picks up, and whether lumen-glass can draw it.
- [ ] ➕ **4.16** OSD restyle.
- [ ] **4.17** Apply every shortcut and gesture; Super+/ cheat-sheet overlay.
- [ ] **4.18** QML unit tests; session test that opens each surface and screenshots it.
- [ ] **4.19** Keyboard-only and Orca tests; startup < 1.5 s and < 250 MB check.
- [ ] **4.20** 👤 Phase 4 acceptance.

## Phase 5 — Services, CLI and Settings (spec: "Spec: lumen CLI and services", "Spec: updates, rollback and backup", "Spec: Lumen Settings and System Health", Phase 5)

- [ ] **5.1** Rust workspace (`services/`, `cli/`), shared D-Bus interface crate, hardened systemd unit and polkit templates.
- [ ] **5.2** `lumen-settingsd`: TOML store, get/set/list, change signals.
- [ ] ➕ **5.3** `lumen` CLI skeleton (clap): `--json`, completions, `lumen settings`.
- [ ] **5.4** `lumen-updated` part 1: timer, check order (bootc, Flatpak, fwupd), D-Bus API.
- [ ] **5.5** `lumen-updated` part 2: low-priority downloads, metered/battery rules, staging, one notification.
- [ ] **5.6** `lumen-updated` part 3: boot health check that needs no login (login screen up, NetworkManager running, no failed critical units) with boot-counting fallback (try greenboot first); first-login shell check that offers to go back (ADR 0002).
- [ ] **5.7** `lumen-updated` part 4: history, rollback to signed tags; `lumen update`, `lumen rollback`.
- [ ] **5.8** `lumen-health`: first 5 checks with fixes.
- [ ] ➕ **5.9** `lumen-health`: last 5 checks with fixes; `lumen health [--fix]`.
- [ ] **5.10** `lumen-hwd`: report, driver status, NVIDIA image switch; `lumen hw report`.
- [ ] **5.11** `lumen-backupd` (restic schedules) and `lumen backup`.
- [ ] ➕ **5.12** CLI: `lumen app`, `lumen dev enable`, `lumen glass tier`.
- [ ] **5.13** Settings app frame: glass sidebar, search across pages, `lumen-settings://` deep links.
- [ ] **5.14** Settings pages: Wi-Fi & Network (including OpenConnect VPN import), Bluetooth.
- [ ] **5.15** Settings pages: Displays, Sound.
- [ ] **5.16** Settings pages: Appearance, Desktop & Dock.
- [ ] **5.17** Settings pages: Notifications, Power & Battery (suspend and critical-battery action; hibernate only where Secure Boot lockdown allows it, per ADR 0001).
- [ ] **5.18** Settings pages: Privacy & Security, Users.
- [ ] **5.19** Settings pages: Apps, Updates.
- [ ] **5.20** Settings pages: Backup, Drivers & Hardware.
- [ ] **5.21** Settings pages: Keyboard & Input, Accessibility.
- [ ] **5.22** Settings pages: Developer, About & Health (including "Reset Lumen": keep files or erase everything).
- [ ] **5.22a** "Get help from a friend": Plasma remote desktop (KRdp) on the same network, behind a one-time code and a visible indicator, saying plainly that it is same-network only; for help over the internet, offer RustDesk from the Store with a note that its servers carry the connection (ADR 0002). Confirm RustDesk is on Flathub and works on Plasma Wayland.
- [ ] **5.23** Tests: GUI and CLI give identical results; update + rollback in the VM; each Health check triggered and fixed.
- [ ] **5.24** 👤 Phase 5 acceptance.

## Phase 6 — Store, Welcome, Backup, installer, hardware report (spec: "Spec: Store, first run, installer, hardware report", Phase 6)

- [ ] **6.1** Store backend (libflatpak + AppStream): list and search.
- [ ] **6.2** Store home collections and app page (screenshots, verified badge, plain-English permissions with risk colour).
- [ ] **6.3** One-button install/update/remove/open; Windows/macOS name aliases data file.
- [ ] **6.4** Essentials collection adds a OneDrive client, OpenRGB, Piper and Solaar (the `.exe` flow moved to 7.5).
- [ ] **6.5** Welcome steps 1–3: language and keyboard, Wi-Fi, account with fingerprint.
- [ ] **6.6** ⚠️ Welcome step 4: TPM2 enrolment bound to PCR 7 and Lumen's own boot measurements through systemd-pcrlock, with the volume key measured, and the recovery key. If pcrlock can't be made reliable, make a PIN the default instead, and record which shipped in ADR 0004's follow-up.
- [ ] **6.7** Welcome steps 5–9: privacy, look, import, apps, gesture tour.
- [ ] **6.8** Backup app UI: external drive, SMB, S3.
- [ ] **6.9** "Previous versions" in Files via snapper.
- [ ] **6.10** Installer theme (Anaconda WebUI in the live session from 1.8) and the three install modes; "Install alongside Windows" detects BitLocker and Fast Startup and never resizes a BitLocker volume.
- [ ] **6.11** `hardware/hardware.json` and the `lumen-hwd` compare logic, including the Microsoft UEFI CA 2023 check.
- [ ] ➕ **6.12** Hardware report app (`apps/hwreport`, green / amber / red) in the install USB's live session. If 1.8 had to fall back to `anaconda-iso`, ask the owner before dropping it (ADR 0002).
- [ ] **6.13** 👤 Phase 6 acceptance: install to usable desktop in < 15 min; a non-technical tester sets up, installs an app, restores a file and runs a backup unaided.

## Phase 7 — Switching from Windows (spec: "Spec: Windows apps and switching", Phase 7)

- [ ] **7.1** 👤 `docs/windows-apps.md`: the top 100 apps Windows users need, by category, with today's status; confirm the licences of ProtonDB, AreWeAntiCheatYet and any other source; pick the OneDrive client. You review the list.
- [ ] **7.2** Compatibility database v1: recipes, alternatives, anti-cheat status; import ProtonDB and AreWeAntiCheatYet data with attribution; cover the top 100.
- [ ] **7.3** Signed database updates through `lumen-updated`; offline lookup only; test that a lookup makes no network request.
- [ ] **7.4** `lumen-compat` Rust crate: identify an `.exe` or `.msi` (version info, installer type, file hash) and match it; `lumen app check`.
- [ ] **7.5** "Open Windows app" dialog (`apps/windows-app`): rating, reason, alternatives, Install / Try it; creates the bottle with its recipe; adds the app to the menu.
- [ ] **7.6** Sandbox defaults for Bottles; Windows apps in Settings → Apps; `lumen app list --windows`; full removal.
- [ ] **7.7** Store: ratings on Windows-name searches, Windows alternatives collection, web apps, Heroic and Lutris, anti-cheat status.
- [ ] **7.8** Welcome: "Your Windows apps" scan of the Windows drive; BitLocker unlock by recovery key for the scan and the file import.
- [ ] **7.9** ⚠️ 👤 Lumen Setup for Windows (`windows-setup/`, fork of Fedora Media Writer): hardware check, BitLocker / Fast Startup / Secure Boot checks, partition shrink, UTC clock, USB writer; built on a Windows CI runner. You provide a Windows code-signing certificate, or SmartScreen will warn users.
- [ ] **7.10** Dual-boot Health checks: Fast Startup, clock mismatch, missing boot entry, Secure Boot certificate.
- [ ] **7.11** Tests: every top-100 app has a rating and a path; dialog, Store and CLI agree; offline lookup; sandbox defaults.
- [ ] **7.12** 👤 Phase 7 acceptance: a Windows user installs Lumen with Lumen Setup, sees their apps' status, and installs five Windows apps by double-clicking, with every rating correct; at least 80% of the top-100 list is covered.

## Phase 8 — Hardening, accessibility, performance (spec: "Spec: security model", Phase 8)

- [ ] **8.1** Security review part 1 (boot, disk, image) → `docs/security.md`; fix gaps.
- [ ] **8.2** Security review part 2 (apps including Windows-app bottles and Lumen Setup, network, privilege, supply chain: SBOM, Renovate, pinned digests); fix gaps.
- [ ] **8.3** Accessibility audit: shell surfaces.
- [ ] ➕ **8.4** Accessibility audit: apps.
- [ ] **8.5** Performance: boot < 10 s on NVMe.
- [ ] ➕ **8.6** Performance: idle RAM < 1.5 GB.
- [ ] **8.7** Translations: string extraction, Weblate config, pseudo-locale.
- [ ] **8.8** 👤 Phase 8 acceptance on a real laptop.

## Phase 9 — Release v0.1 (spec: "Testing, CI and release", Phase 9)

- [ ] **9.1** Release train in CI: dev on every merge, weekly beta, stable every 2 weeks after 7 days in beta.
- [ ] **9.2** Update test job: install previous, upgrade, reboot, roll back, reboot.
- [ ] **9.3** Docs: user guide and install guide.
- [ ] ➕ **9.4** Docs: FAQ (including what won't come over from Windows), hardware notes, contributing guide.
- [ ] **9.5** 👤 Publish v0.1 (you approve): signed images, ISO, SBOM, checksums, plain-English changelog.
- [ ] **9.6** 👤 Install and run v0.1 on two real machines, one of them alongside Windows through Lumen Setup.
