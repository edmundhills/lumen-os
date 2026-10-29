<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Lumen OS — step-by-step build plan

The spec's 11 phases (0–10), cut into session-sized steps. Do **one step per session**.

## How to resume

1. Start a **new** session with the Lumen OS project folder selected (a fresh session is cheaper than continuing a long one).
2. Send: `Do the next step in PROGRESS.md.`
3. If a session ran out mid-step, send: `Continue the current step in PROGRESS.md.`

Claude reads CLAUDE.md automatically, does that step (plus any ➕ steps right after it), commits, updates this file, and stops.

**Legend:** 👤 = needs you (an account, an admin install, real hardware or an approval). ⚠️ = big step, may get split into a/b sub-steps. ➕ = small step, done in the same session as the step above it (a batch).

**The look is decided with the owner** (owner's request, 2026-10-29). Before any step that fixes how Lumen looks, Claude goes through the exact design with the owner and waits for their agreement: colours, type, sizes, spacing, glass, motion, icons, and the layout of each surface. Steps 2.0, 3.0 and 4.0 are those design sessions. For a step in a later phase that designs a screen of its own, such as a Settings page, the Store or Welcome, show the design first too.

## Current step

**1.8b** ⚠️ The `live` stage and the ISO. Read ADR 0011 first, then architecture 4.8 and 9.6, the spec's "Installer", and the 1.8a notes below, which list what the stage must hold and the SELinux question to ask the owner.

Left over from 1.8a, 1.6, 1.5c and 1.5b:

- **First, 1.8a's first run in CI.** It was checked in WSL, not yet in CI. In main's image run for the 1.8a commits, "Make the qcow2" and "Check the qcow2" must pass. Then tick 1.8a and add to ADR 0011's Consequences how long the steps took and how much disk was left (`df` in their logs). If they fail, fix that before 1.8b.
- How the next bump pull request got its checks, on Monday 2026-11-02 or by hand before then. Did GitHub run its `pull_request` checks straight away, hold them for approval, or make none, so that the job started them itself? Record the answer in versions.md, "How the pins move". Its image run is also the first to report the download for a new base.
- Offered, not decided: skip the hour-long image build for commits that change only documentation (the lint workflow still checks them). Most of 2026-10-29's pushes were docs only.

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
- [ADR 0006](docs/decisions/0006-lumen-look.md) accepted 2026-10-28: the owner found a spec-faithful mockup "way too much like macOS", so Lumen gets its own look.
  - The top bar is three floating islands, and app menus move into the window's title bar.
  - App icons are round lenses, and the eight accents are named for kinds of light, with gold Sunbeam as the default.
  - The focused window gets a line of accent light, and the dock gets a "Search or run" field.
  - Fonts: the owner first chose the Red Hat family, but Fedora's Red Hat fonts cover Latin-script languages only (no Cyrillic, Greek or Vietnamese; checked with `fc-query`). So it is Red Hat Display for display text only, Source Sans 3 (`adobe-source-sans-pro-fonts`) for interface text, and JetBrains Mono for code. Inter is gone from `packages.toml`.
  - Applied to the spec ("Lumen's look", shell, manifest, Phase 2–4 prompts), `design/README.md` and steps 2.1, 2.9, 2.10, 2.11, 3.9, 4.2, 4.4 and 4.5.
  - The clickable mockup is an artifact in the owner's claude.ai account, not in the repo.
- For later steps: os-release and the image labels (architecture 9.7) aren't named by any step; the Containerfile assigns them to 1.5. Solaar (6.4) needs `solaar-udev` on the host, which the spec's manifest doesn't list: add it at 6.4.
- 1.3 done 2026-10-28: `image/overlay/` and `image/check-image.sh`, which the `lumen` stage runs before `bootc container lint` (8 checks with 1.4's; each was seen to fail on a planted fault). The image is 7.62 GB.
  - Kinoite already had firewalld, tuned and tuned-ppd on and SELinux enforcing. `fwupd-refresh.timer` and snapper's timers were off, and `rpm-ostree-countme.timer` was on. The Containerfile now masks it, with Fedora's two updaters.
  - `40-lumen.preset` lists what Lumen turns on. The build runs `systemctl preset-all --preset-mode=enable-only`, which is what systemd does on a first boot (the image's `/etc/machine-id` is empty); on Kinoite it changes nothing else. Masks are `systemctl mask` in the Containerfile: a preset can't mask, and the Windows checkout can't hold the symlinks.
  - The stock layout: the owner chose an interim top bar over a bare desktop (2026-10-27). Lumen's global theme `org.lumen.desktop` copies Fedora's theme settings and has its own layout script: one 32 px top bar with the app menu, open windows, system tray and clock. `/etc/xdg/kdeglobals` makes it the default; Fedora's `XDG_CONFIG_DIRS` is `/etc/xdg`, then its kde-settings profile in `/usr/share`, whose kdeglobals names Fedora's theme. Nobody has seen the bar yet: the boot test (1.9) stops at the login screen, so the first look is at 1.17. The bar has no input method widget (the stock panel adds one for some languages only).
  - WSL shows the Windows checkout's files as 0777, so the overlay is copied with modes the build sets (0644, and 0755 for folders and `/usr/libexec/lumen-*`).
  - The `base` stage now mounts only `packages.py` and `packages.toml`: Podman reruns a step when anything it mounts changes, so mounting all of `image/` reran dnf (about 9 min) after every overlay edit.
  - Input methods: neither IBus nor Fcitx5 starts on Plasma Wayland by default. Fedora's kde-settings sets KWin's input method to Plasma's on-screen keyboard (`kwinrc`, `[Wayland] InputMethod=org.kde.plasma.keyboard.desktop`); users pick Fcitx5 or IBus in Settings > Keyboard > Virtual Keyboard. Installing Fcitx5 moved the `xinputrc` alternative to it, which only X11 sessions read. Step 5.21 should pick the default.
  - Discover leftovers: `kde-mimeapps.list` still sends `appstream://` links and `.rpm` files to Discover, and Fedora's app-menu favourites list it; Plasma skips missing apps. The Store (Phase 6) should take `x-scheme-handler/appstream`.
  - Kinoite 44 turns on `plasma-setup.service`, KDE's first-run setup that creates the first user. Welcome (6.5) must replace it or build on it.
- 1.4 done 2026-10-28: Btrfs and snapper defaults.
  - Compression is a mount option, which the installer sets, not the image. Anaconda picks its profile by os-release `ID`. Fedora's profiles give Btrfs with `zstd:1`, but once `ID=lumen` (step 1.5) none match, and Anaconda falls back to LVM with no compression. `installer/anaconda/lumen.conf` builds on Kinoite's profile and repeats Btrfs, `zstd:1` and the `/home` subvolume; Anaconda 44.30's own loader detects it for `ID=lumen` and gives those values. **1.8:** install it in the live stage's `/etc/anaconda/profile.d/`.
  - `/usr/lib/bootc/install/20-lumen.toml` makes `bootc install` default to a Btrfs root, so bootc-image-builder's qcow2 gets one too, without compression (bootc has no mount-option setting). Whether that qcow2 makes `/var/home` a subvolume isn't known yet.
  - `lumen-home-snapshots.service` runs `snapper --no-dbus create-config --template lumen-home /var/home` on the first boot, then `restorecon` (Fedora's policy labels `/var/home/.snapshots` `snapperd_data_t`). If `/var/home` isn't a Btrfs subvolume, it says so and exits 0. Unit tests use stand-ins; nothing has run it on a real disk yet. **1.9:** check that the unit succeeded, and start `snapper-timeline.service` and `snapper-cleanup.service` once before reading `systemctl --failed`: their timers first fire on the hour and after 10 min, outside the 60 s window.
  - Snapshot limits and disk space: as snapper's documentation describes its cleanup (not tested here, and the Fedora man page doesn't spell it out), fixed limits (24 hourly, 7 daily, 4 weekly) stop the free-space limit from deleting snapshots below those counts. Space freed by deleting a big file in `/home` would then come back only when the last snapshot holding it expires, up to 4 weeks later. Ranges such as `2-24` would let snapper drop older snapshots when free space falls below 20%. The owner chose to keep the spec's 24/7/4 for now (2026-10-28) and revisit it at 6.9.
- 1.5 split into 1.5a, 1.5b and 1.5c on 2026-10-28: building and pushing, the pin bump, and re-chunking are each a session's work, and nothing in CI can be checked until the owner pushes.
- 1.5a done 2026-10-28 (commits `f079677`, `d7aff0d`; fixes `96b0ce8`, `457c9d5`, `9d42a74`). CI is green on main at `1f89d93` (lint and image runs #5).
  - On ghcr.io, `dev`, `dev-44.20261028` and `sha-1f89d93…` are one image, digest `sha256:d0afd0cb52de606e687b6fd76ef0a5de5626ed4fcd869a65d929e093d054934e`: 7.62 GB, 262 layers, with the right labels.
  - The package `lumen` was public from its first push and is linked to the repository, so the owner had nothing to change. Without a login, `skopeo inspect` works, and a layer fetched with ghcr.io's anonymous pull token matched its digest.
  - The publish job took 23 min: 2.5 to free disk, 19 to build (Kinoite is pulled afresh each run), 1.7 to push.
  - The first run (`c0832a4`) failed. What failed and how it was fixed:
  - **lint** failed: quay.io had deleted the lint container's pinned `fedora:44` image, about a day after a newer build took the tag (podman exit 125, "manifest unknown"). WSL passed only because the lint image was cached. `registry.fedoraproject.org` still serves the same digest, so `tests/lint/Containerfile` now pulls it from there. How long Fedora's registry keeps an old digest isn't known; the 1.5b job should bump this pin with Kinoite's.
  - **image** failed only at `bootc container lint`: `nonempty-run-tmp` found `/run/lumen`. Ubuntu 24.04's Podman 4.9.3 on the runner leaves the `RUN --mount` mount points in the image; Podman 5.8.9 in WSL doesn't, rootless or rootful. Reproduced with Podman 4.9.3 in an Ubuntu 24.04 container in WSL. The lint step now runs `rm -rf /run/lumen` first. Everything else passed in CI: dnf with that day's repositories, the 9 image checks, and 13 of bootc's 14 lint checks.
  - "Work out the build version" gave `44.20261028` on both runs. The second printed "has no tags yet", so ghcr.io answers a repository that doesn't exist with one of the messages the step matches.
  - The runner had one 145 GB disk (`/mnt` wasn't a separate disk), 122 GB free after the cleanup.
  - CI logs: the owner signed in to GitHub in the desktop app's built-in browser (2026-10-28). Claude reads a job's raw log there at `https://github.com/edmundhills/lumen-os/commit/<sha>/checks/<job id>/logs`; the API and the website show logs only to signed-in users.
  - The `lumen` stage writes `/usr/lib/os-release` (`image/os-release.sh`: `ID=lumen`, `ID_LIKE=fedora`, `VERSION_ID=0.1`, `IMAGE_ID=lumen`, `IMAGE_VERSION=<build version>`, `DEFAULT_HOSTNAME=lumen`) and the OCI labels (title, description, version, revision, source, url). `image/build_version.py` works out the version from the base stage's `FROM` tag and today's UTC date, plus the tags on ghcr.io in CI; 9 unit tests. `check-image.sh` now has 9 checks; the new one was seen to fail on a planted fault.
  - In WSL: `just build-image` took 6 min with the base stage cached; `just lint` 11 of 11, `just test` passes (32 unit tests).
  - CI: `image.yml` calls `build-image.yml` from a read-only `check` job (pull requests, other branches) and a `publish` job (pushes to main, `packages: write`). It frees disk, moves rootful Podman's storage to `/mnt` when that disk has more room, builds, and on main pushes `dev-<version>`, `sha-<commit>` and `dev` to `ghcr.io/edmundhills/lumen`. Signing and the SBOM are 1.6.
  - The workflow takes "name unknown" or "not known to registry" from `skopeo list-tags` to mean ghcr.io has no `lumen` yet (before the first push, anonymous requests got 403 instead). It worked (see above).
  - The runner's Podman is Ubuntu's 4.9.3, older than WSL's 5.8.9 (Buildah 1.43.5). If CI builds differently from WSL, suspect that first: it caused the `/run/lumen` failure above. To test with it locally: `sudo podman run --rm --privileged docker.io/library/ubuntu:24.04`, `apt-get install podman`, then build with `--storage-driver=vfs --isolation=chroot`.
  - Side effects of `ID=lumen`: Fedora's Toolbx welcome text in `/etc/profile.d/toolbox.sh` (Kinoite only) no longer shows, and Toolbx falls back to `fedora` with its built-in release (checked in its source), which is what Lumen wants. Kinoite's initramfs still says Fedora. The image inherits Kinoite's `quay.expires-after: 4w` label, which ghcr.io ignores.
  - **1.5b design idea:** keep the `FROM` line on quay.io (CLAUDE.md's fixed architecture names it) and copy each pinned base with `skopeo copy --all --preserve-digests` to `ghcr.io/edmundhills/kinoite:<build>`, so the digest stays the same. CI then lists the copy as a digest-only mirror in `/etc/containers/registries.conf.d/` (`pull-from-mirror = "digest-only"`), which also makes pulls faster. Renovate can't copy the base before it bumps the pin, so a scheduled job fits better. It should bump the lint container's `fedora:44` pin too (see above).
  - **1.5c:** Fedora's documented tool is `rpm-ostree compose build-chunked-oci --bootc --from=<image> --output containers-storage:<image>`, run as root with `/var/lib/containers` mounted (the image has rpm-ostree 2026.3). A CentOS Stream bug report about a missing `org.opencontainers.image.version` label suspects it, so check the labels after re-chunking. Fedora's `bootc-base-imagectl rechunk --chunkah` keeps them, but Kinoite doesn't ship it.
  - **1.8:** bootc-image-builder picks its distro definitions from the image's os-release. Check that it builds a qcow2 with `ID=lumen` and `VERSION_ID=0.1`. Its source couldn't be read this session. If it can't, record the fix in an ADR, for example keeping `VERSION_ID` at the Fedora release.
- 1.5b done 2026-10-28 (pushed as `c13fe48`..`ddeca3c`, plus a fix for the bump pull request's checks). [versions, "How the pins move"](docs/versions.md#how-the-pins-move) describes the whole flow.
  - The owner ticked "Allow GitHub Actions to create and approve pull requests" (Settings > Actions > General, in the Workflow permissions section; that page has four Save buttons, and only the one under that section saves it).
  - First runs (2026-10-28), all green:
    - The push's lint, image (22 min) and `copy` runs.
    - `copy` made `ghcr.io/edmundhills/kinoite:44-9f71aa8ed152` and `fedora:44-e34bf2671371`. Both packages were public and linked to the repository from their first push, so the owner had nothing to change.
    - The bump, run by hand, took 1.5 min and opened [#1](https://github.com/edmundhills/lumen-os/pull/1) (Kinoite 44.20261028.0, `fedora:44` of 10-28) as `github-actions[bot]`. Copying the new Kinoite took under a minute, because most of its layers were already on ghcr.io.
    - The lint and image runs on the bump commit, started with workflow_dispatch, were green.
  - **Found with #1:** GitHub did make `pull_request` runs for the pull request the workflow's token opened, but held them for approval, because the repository's policy is "Require approval for first-time contributors" and `github-actions[bot]` had no merged contribution. It made no runs for the push to `bump-bases`. The runs the job started with workflow_dispatch didn't show on the pull request at all. The fix: the job now starts lint and image only when GitHub made no pull request runs, and the pull request says to press "Approve workflows to run" if its checks are held.
  - **CI pulls from the copies:** checked with Ubuntu 24.04's Podman 4.9.3 and skopeo 1.13.3 and the drop-in written as CI writes it. A copied digest is read from ghcr.io with no request to quay.io, the lint base's layers download from ghcr.io, and an uncopied digest falls back to quay.io. The same holds in WSL with the file in `/etc/containers/registries.conf.d/`. Setting `CONTAINERS_REGISTRIES_CONF` to a test file didn't apply the mirror in WSL's skopeo; the drop-in path did.
  - Pulling Kinoite took 83 s from the copy and 83 s from quay.io (the push build started its pull about 30 s before `copy` finished, so it came from quay.io). The copies keep old commits buildable but don't make CI faster. ghcr.io's download counter still showed 0 afterwards, so it can't confirm pulls.
  - The anonymous Actions API allows 60 requests an hour; polling three runs a minute ran into it. Read job details in the signed-in browser instead.
  - A scheduled job, not Renovate, because Renovate can't copy a base before it bumps the pin. `.github/workflows/base.yml` has two jobs. `copy` runs on main: on pushes that change a pin, on Mondays and by hand. `bump` runs on Mondays at 05:17 UTC and by hand. `image/bump_bases.py` reads and rewrites the pins (`list`, `mirrors`, `bump`), and `image/copy-bases.sh` copies them. 26 new unit tests; `just lint` 11 of 11, `just test` passes (58 unit tests).
  - The lint container's base is bumped and copied too, but stays on Fedora 44: moving it to 45 by hand also means checking the `nodejs24-full-i18n` name.
  - Each Containerfile pin now has a `# Pinned:` line above its `FROM` line, which the job rewrites. It names the build and, for Kinoite, its KWin, Plasma and Qt, read from the names rpm-ostree gives the layers (for example `kwin-common-6.7.5-1.fc44.x86_64`).
  - The bump copies its new bases at once, not only on merge. A bump that waits more than four weeks, for example while lumen-glass is rebased onto a new KWin, would otherwise lose its base before anyone copied it.
  - Once a person adds a commit to the open pull request (`gh pr view --json commits`, author emails), runs leave it alone.
  - CI pulls from the copies first: `bump_bases.py mirrors` writes `/etc/containers/registries.conf.d/50-lumen-bases.conf` with `pull-from-mirror = "digest-only"`.
  - Checked before the first push, in WSL with Ubuntu 24.04's Podman 4.9.3 and skopeo 1.13.3:
    - The drop-in parses. Ubuntu has no `registries.conf` at all, only `registries.conf.d/shortnames.conf`.
    - A `FROM name:tag@digest` build tries the mirror first.
    - A digest the mirror lacks falls back to the original registry, and a tag pull never uses the mirror.
    - `copy --all --preserve-digests` keeps the index digest.
    - `--no-creds`, `--no-tags` and `--retry-times` exist.
  - A live `bump` on scratch copies (2026-10-28) would move Kinoite to 44.20261028.0 (`93139a85…`) and `fedora:44` to `a3299035…`, with KWin and Plasma 6.7.5 and Qt 6.11.2 unchanged. Bodhi listed F43 and F44 as current and F45 as frozen. The Kinoite index holds amd64 and arm64 with zstd layers, about 2.9 GiB each, so a copy is about 5.8 GiB.
  - **Owner to confirm:** CONTRIBUTING.md now says the workflow's own commits carry no sign-off, and whoever merges the pull request reviews it. That is the DCO rule's first exception besides AI assistants.
  - GitHub turns off scheduled workflows in a public repository after 60 days with no activity (in versions.md and the risk register's watch list).
- 1.5c done 2026-10-28, in a claude.ai cloud session rather than on the owner's PC, on the branch `claude/next-step-zfy63s`. [ADR 0007](docs/decisions/0007-rechunking.md) (accepted) holds the decision and the measurements; `image/rechunk.sh`, `image/rechunk.py` and `image/layer_hints.py` do the work, and CI runs them after every build.
  - Left over from 1.5b: the owner merged [#1](https://github.com/edmundhills/lumen-os/pull/1) at 18:03 UTC without approving its held runs. GitHub ended them as failed, with no jobs. The merge's own lint, image and copy runs on main were green: the image job built in 19 min and pushed `dev-44.20261028.3` in 31 s. No later bump has run yet.
  - Before re-chunking, measured from the manifests of the four `dev` builds: a rebuild with no change downloaded 113 MiB, a daily base bump 487 MiB, and a change in how Podman compressed the base's layers all 3 GiB. `skopeo inspect --raw` on ghcr.io works without logging in, from anywhere.
  - The tool is `rpm-ostree compose build-chunked-oci`, run from the built image (rpm-ostree 2026.3). Its `--previous-build` keeps the newest `dev`'s packing, but stops with an error if that build isn't re-chunked, so `rechunk.py chunked` checks first. It keeps the labels and settings: checked in its source and by every CI run.
  - CI, image runs #11 to #13 on the branch, with a temporary experiment step since removed:
    - The nested Podman worked: rpm-ostree inside the image used the runner's Podman 4.9.3 storage with no trouble.
    - Re-chunking changed no file among 470,000. `check-image.sh` and `bootc container lint` pass on the result.
    - rpm-ostree files the initramfs before it reads `user.component` marks, so the first try's mark on it did nothing. A rebuild then downloaded 338 MiB, mostly the 275 MiB layer it shares with the files no package owns.
    - Two from-scratch builds of one commit differ in 11 files: fontconfig caches, the rpm database, dnf's state and os-release. With those marked `lumen-build-state`, a rebuild downloads 40.8 MiB in 3 layers. The overlay's files are marked `lumen-overlay`, so an edit to them doesn't take the shared layer along either.
    - The budget is 100 MiB (`DOWNLOAD_BUDGET_MIB` in `build-image.yml`) for builds on the same base. A new base is reported, not held to it.
    - Re-chunking and its checks add about 13 minutes: the check job takes about 40.
  - Possible later saving: reuse the `base` stage between CI runs when neither the pin nor `packages.toml` changed. That would keep the rpm database the same and cut a rebuild's download from 41 MiB to about 8. Not scheduled: it needs a cache that pull requests can read and only main writes.
  - GitHub refused the cloud session's push at first (403); the owner installed the Claude GitHub App on the repository, and pushes then worked. The commits' author is Claude (`noreply@anthropic.com`), as the cloud session requires. Before they reach main, the owner signs them off, as for every Claude commit. CONTRIBUTING.md wants the sign-off to match the author, so make yourself the author at the same time: `git rebase --exec 'git commit --amend --no-edit --reset-author --signoff' main`. The `Co-Authored-By:` trailers stay.
  - Checked in the cloud session, with Ubuntu 24.04's Podman 4.9.3 and skopeo 1.13.3 (the runners' versions): Podman records the base image annotations, and a `user.component` attribute set in a `RUN` step survives into the layer. The linters ran there with locally installed tools, and in CI's lint container (lint runs #11 to #13 green).
- 1.5c's leftovers, checked 2026-10-29: the owner merged the branch, rebased with their sign-off, and main's image run for `02d400d` was green in 52 min. `dev` (`dev-44.20261029`, `sha256:101c706b…181c`) has 257 layers whose annotations name their packages, and its update from `dev-44.20261028.3` downloads 3,183.6 MiB once (ADR 0007's Follow-up).
- 1.6 and 1.7 done 2026-10-29 ([ADR 0008](docs/decisions/0008-image-signing.md) has the facts and sources). The first signed build is `44.20261029.1` (`sha256:f3b2f05d…54de3`), from main's run for `5ca3439`. The owner asked Claude to make the key; Claude made it in WSL with no network, and the owner set up the `image-signing` environment and its two secrets. Main's first two runs failed before pushing anything and were fixed (ADR 0007 and 0008, Follow-ups). The facts:
  - **What CI does:** every build makes an SPDX SBOM with syft 1.55.0 from the re-chunked layout, packages only, and `image/sbom.py` checks that it lists exactly the image's RPMs. Builds of main push `dev-<version>` and `sha-<commit>`. A separate `sign` job then opens the environment `image-signing` and runs these checks and steps in order:
    - checks that the image's trust policy refuses the unsigned digest;
    - signs it and attaches the SBOM with `image/sign.sh` (cosign 3.1.4);
    - checks both with the image's public key, and that the policy now accepts the image;
    - moves `dev`.
  - **Signature format:** cosign 3 writes a format that Fedora 44's containers/image, and so bootc, can't read. `sign.sh` therefore passes `--new-bundle-format=false --use-signing-config=false --tlog-upload=false`, as Universal Blue does, and nothing goes to Sigstore's public log. cosign must stay on 3.x (versions.md).
  - **The trust policy:** `/etc/containers/policy.json` rejects by default. Lumen's four repositories need Lumen's signature (`matchRepository`, key `/usr/share/pki/containers/lumen.pub`). Other registries and local transports are open, as on Fedora, so Toolbx, distrobox, `bootc install` and the installers keep working. `registries.d/lumen.yaml` points containers/image at the `.sig` tags. `20-lumen.toml` adds `enforce-container-sigpolicy = true`, so installs record `ostree-image-signed`.
  - **Owner to confirm:** the spec's "only accepts our signed images" is read as "Lumen's images only with Lumen's signature". Read for every image, it would break Toolbx and distrobox. The spec is unchanged; say if it should spell this out.
  - **Tests:** `image/trust.py` (lint, `check-image.sh`, 25 unit tests); `check-image.sh` also checks the install setting; `image/sbom.py` (10 unit tests); `image/test_signatures.py` (10 tests). That last one runs a registry inside the lint container that answers for ghcr.io (the justfile maps the name), signs with `sign.sh` and the pinned cosign, and pulls with Fedora 44's skopeo and the overlay's settings. The lint container gained `docker-distribution`, `openssl`, `skopeo` and cosign, by checksum. In WSL with a stand-in key: `just lint` 12 of 12, `just test` passes (127 unit tests). The runner's skopeo 1.13.3 parses the policy and refuses today's unsigned `dev` with the message the `sign` job looks for.
  - **For 1.8:** Anaconda's `ostreecontainer` ignores the install setting and records the unverified transport. Use Anaconda's `bootc` kickstart command, or `%post bootc switch --mutate-in-place --enforce-container-sigpolicy --transport registry …` as Bazzite does. Whether bootc-image-builder reads the image's install config is inferred from bootc's source, not tested.
  - **For Phase 5:** `lumen-updated` must pass `--enforce-container-sigpolicy` to `bootc switch` (architecture 4.4). A Health check should notice an edited `/etc/containers/policy.json`, which bootc's `/etc` merge then stops updating, or a `/root/.config/containers/policy.json`, which replaces it.
  - **For 9.2:** whether to keep a second, offline key in `keyPaths` from the start, and whether CI should check Fedora's own cosign signature on each new Kinoite base before the base workflow pins it.
  - **For 10.1:** deleting old `dev` builds must delete their `sha256-<digest>.sig` and `.att` tags too. A signature holds for a repository, not a tag, so decide whether channels need their own identity.
  - Since 2026-10-01, GitHub deletes workflow runs, and their summaries, after the retention period, at most 90 days for a public repository. The tags on ghcr.io keep the digests.
  - The research workflow's agents left test files in WSL's `/tmp` (`cosigntest`, `cosignsrc`, `cosignres`, `lr`, `cs`, `dl`) and the images `ghcr.io/sigstore/cosign/cosign:v3.1.4`, `registry:3` and `quay.io/libpod/alpine` in rootless Podman. None of it is needed.
- 2026-10-29: a cloud session and a session on the owner's PC both finished 1.6 at the same time. The owner pushed the PC's commits; the cloud session's branch `ccr-aa9986c4-vir9s7` was rebuilt on them with only its extra findings: check run #19's budget result (ADR 0007), the SBOM's format checked with the pinned syft, and an openssl check of the signature (ADR 0008). Before starting a step, fetch and check that main and PROGRESS.md haven't moved. From a cloud session, GitHub's log and artifact storage (`*.blob.core.windows.net`) and ghcr.io's blob host (`pkg-containers.githubusercontent.com`) are blocked; the GitHub tools' job logs, ghcr.io manifests and github.com release downloads work, and the lint tools can be installed at the lint container's versions.
- 1.8 split into 1.8a, 1.8b and 1.8c on 2026-10-29: the qcow2, the live ISO, and installing from it are each a session's work.
- 1.8a, 2026-10-29: [ADR 0011](docs/decisions/0011-disk-images.md) has the facts and sources.
  - **bootc-image-builder is now osbuild's image-builder.** Its sources moved into `osbuild/image-builder` on 2026-10-01, and upstream asks new workflows to call `image-builder build --bootc-ref <image> <type>`. CI uses the container `ghcr.io/osbuild/image-builder-cli:v88.0.0` (Fedora 44), pinned by digest in `build-image.yml`. The old `quay.io/centos-bootc/bootc-image-builder` is CentOS Stream 10 running image-builder 85 under the old name.
  - **CI:** the build job makes a qcow2 of every build from the re-chunked image, named `ghcr.io/<owner>/lumen:dev` so the system on it follows `dev`, after the SBOM and before the push. `image/check-disk.sh` converts it to raw and checks it read-only with `image/disk.py`. The disk isn't uploaded: the boot test (1.9) runs in the same job. The job's time limit went from 90 to 120 minutes.
  - **The 1.5a question is answered:** image-builder takes `ID=lumen` and `VERSION_ID=0.1` ("Unknown distro", so a generic runner, which changes nothing for a disk). It reads `VERSION_ID` as a version with at most one dot, so `os-release.sh` now stops the build if the product version has more (`test_os_release.py`).
  - **Checked in WSL** on `dev` `44.20261029.1`: the qcow2 follows `ostree-image-signed:docker://ghcr.io/edmundhills/lumen:dev`, which settles ADR 0008's open inference. `check-disk.sh` passed on it, and caught a planted wrong image and version. The deployment is in a Btrfs subvolume `root`, installed with `compress=zstd:1`; the kernel command line has `rootflags=subvol=/root`, `console=ttyS0` and `rw`. The qcow2 is 3.6 GiB.
  - **The 1.4 question is answered:** the qcow2's `/var/home` isn't a subvolume (the first boot makes it), so the boot test's VM will log that `lumen-home-snapshots` found no subvolume. **For 1.9:** also read `/proc/mounts` to see whether `/` runs with `compress=zstd:1`, which image-builder's mount unit names but the kernel command line doesn't.
  - In WSL the build took 48 minutes, 29 of them osbuild copying the image's files through its 257 layers into its build root. WSL's kernel loads Btrfs only by hand (`sudo modprobe btrfs`); CI's step does it too. A first try with the old command line in the CentOS container got as far as the manifest and was stopped, so it wasn't compared. `just lint` 12 of 12, `just test` passes (160 unit tests).
  - The experiment's disks and images are deleted from WSL.
  - **For 1.8b, what the live stage must hold:** since 2026-05-19 Titanoboa only packs a container into an ISO, by the "container-native ISO contract" that image-builder's `generic-iso` packs too (ADR 0011). The container holds the kernel and an `initramfs.img` next to it built with `dmsquash-live`; shim, GRUB and `gcdx64.efi` (`grub2-efi-x64-cdboot`) copied to `/boot/efi/EFI/fedora` (`cp -a /usr/lib/efi/*/*/EFI /boot/efi/`); `/usr/lib/grub/i386-pc`; `xorriso`, `isomd5sum` and `squashfs-tools`; and `iso.yaml` (image-builder reads `/usr/lib/image-builder/bootc/`, Titanoboa `/usr/lib/bootc-image-builder/`) with the label and the GRUB entries (`root=live:CDLABEL=<label> rd.live.image`). Start from two examples: the `kinoite` folder of github.com/ondrejbudai/bootc-isos (dracut with `dmsquash-live dmsquash-live-autooverlay`, livesys-scripts with `livesys_session=kde`), and Titanoboa's `examples/bazzite` (`anaconda-live`, `libblockdev-{btrfs,lvm,dm}`, `/var/lib/rpm-state` for WebUI, a larger tmpfs on `/var/tmp` for ostree, hidden WebUI pages, a BitLocker check in `%pre`).
  - **For 1.8b, ask before weakening SELinux:** the contract's squashfs isn't SELinux-labelled (v0.1.0), and every example boots its live session with `enforcing=0`. CLAUDE.md never weakens SELinux, so check whether image-builder labels it now; if the live session can only run permissive, ask the owner. The installed system is enforcing either way.
  - **For 1.8c:** image-builder's `--bootc-installer-payload-ref <image>` copies the image into the live system's container storage (Titanoboa can't, so its live stage would `podman pull` it in its own build, as Bazzite's does). The kickstart is then `bootc --source-imgref containers-storage:<image> --target-imgref <image>`. Bazzite instead uses `ostreecontainer --transport=containers-storage` and rewrites the origin file to `ostree-image-signed` in `%post`. image-builder's documentation warns that a bootc system installed by Anaconda fails `systemd-remount-fs.service`.

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
- [x] **1.3** Overlay: enable firewalld, fwupd-refresh.timer, snapper timers, tuned-ppd; SELinux enforcing; remove the stock Plasma layout and Discover. Defaults go in `/usr/lib` and `/usr/share`, or the image's `/etc` where they can only live there; never `/usr/etc` (ADR 0002).
- [x] ➕ **1.4** Btrfs zstd defaults and snapper config for /home (24 hourly, 7 daily, 4 weekly).
- [x] **1.5a** 👤 CI: build the default image on every push and pull request (free runner disk space first; Kinoite images are large) and push builds of main to ghcr.io; os-release and the image labels (architecture 9.7). You make the `lumen` package on ghcr.io public after its first push. *Done when:* CI is green on main and `ghcr.io/edmundhills/lumen:dev` can be pulled without logging in.
- [x] **1.5b** Bump the Kinoite pin at least every two weeks (Renovate or a scheduled job that opens a pull request) and copy each pinned base to ghcr.io, so older commits stay buildable (ADR 0004). Must land before the pinned build expires from quay.io (about 2026-11-24), and handle Fedora 45 (due 2026-11-03).
- [x] **1.5c** Re-chunk the image before the push (architecture 9.3, risk 14): pick the tool, check that bootc's labels survive it, and measure each build's download from the previous `dev` build against a budget.
- [x] **1.6** 👤 cosign signing (you add the key as a repo secret) and SBOM with syft.
- [x] ➕ **1.7** `/etc/containers/policy.json` and sigstore config so the system accepts only our signed images.
- [ ] **1.8a** CI: bootc-image-builder, now part of osbuild's image-builder (ADR 0011), makes a qcow2 of every build for the boot test. Check the disk it makes: the partitions, a Btrfs root, Lumen's os-release, and that the install records `ghcr.io/edmundhills/lumen:dev` with the signed transport (ADR 0008).
- [ ] **1.8b** ⚠️ The `live` stage and the ISO: a Lumen live session that follows the container-native ISO contract (dracut-live with `dmsquash-live`, livesys-scripts, Anaconda WebUI with `installer/anaconda/lumen.conf`, Welcome kept from running, shim and GRUB where the contract wants them, `iso.yaml`), built into an ISO on demand in CI. Try Titanoboa first, then image-builder's `generic-iso`, and record the tool in an ADR. CI keeps the ISO as a short-lived workflow artifact (Q15).
- [ ] **1.8c** The installer installs the ISO's own copy of the image, with no network, through Anaconda's `bootc` kickstart command (`--source-imgref containers-storage:…`, `--target-imgref ghcr.io/edmundhills/lumen:dev`), so the installed system records the signed transport (ADR 0008). Check it with an unattended install in a VM in CI. If no live ISO works, fall back as ADR 0002 says and tell the owner.
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

- [ ] **2.0** 👤 Design session: Lumen's exact visual language, before any token is written. Start from ADR 0006 and its clickable mockup (an artifact in the owner's claude.ai account). Propose and show, with a page the owner can click through, the light and dark colours, the eight accents, the type scale, radii, spacing, elevation, the glass presets per role, the springs and the icon style. Then record what the owner agrees to in an ADR, and 2.1 to 2.11 build exactly that. *Done when:* the owner has agreed to every value.
- [ ] **2.1** `tokens.json` part 1: colours (light, dark, 8 accents named for kinds of light with Sunbeam as the default; each with a fill, a text colour on the fill and an ink shade, all at 4.5:1), type scale (Source Sans 3 for interface text, Red Hat Display for display text with a Source Sans 3 fallback in other scripts, JetBrains Mono; ADR 0006), radii, 4 px spacing, elevation, plus a JSON schema.
- [ ] ➕ **2.2** `tokens.json` part 2: glass presets per role (all parameters from the spec table) and spring presets; validation test.
- [ ] **2.3** Exporter framework and the QML singleton module `org.lumen.style`.
- [ ] **2.4** Exporter: KDE colour schemes.
- [ ] ➕ **2.5** Exporter: Kvantum theme.
- [ ] **2.6** Exporter: GTK 4/libadwaita CSS.
- [ ] ➕ **2.7** Exporter: GTK 3 theme.
- [ ] **2.8** KDecoration plugin scaffold, built in a Containerfile stage.
- [ ] ➕ **2.9** Decoration: rounded corners, glass titlebar role, left-aligned title with the app's icon, an app menu button (⋯) for apps that publish their menu, and a line of accent light on the focused window (ADR 0006). Record which kinds of app publish their menu.
- [ ] ⚠️ **2.10** Cursor and icon theme config (open symbolic icon set with accent recolouring), and lens icons for Lumen's apps and the apps in the image (ADR 0006).
- [ ] ➕ **2.11** Global theme (look-and-feel package) `org.lumen.desktop`. It replaces the interim theme from 1.3 in `image/overlay`; keep its layout script (the interim top bar) until 4.2. It sets the fonts (Source Sans 3, JetBrains Mono) and a fontconfig fallback from Red Hat Display to Source Sans 3 (ADR 0006).
- [ ] ➕ **2.12** Run all exporters during the image build.
- [ ] **2.13** Visual test: Qt, GTK 4, GTK 3 and Flatpak apps in light and dark; store golden images.
- [ ] **2.14** 👤 Phase 2 acceptance: all four app types match in both modes (the same light or dark mode, accent, contrast and fonts; libadwaita apps keep their own shapes, ADR 0004); one accent change updates all of them.

## Phase 3 — lumen-glass (spec: "Spec: lumen-glass effect", Phase 3)

- [ ] **3.0** 👤 Design session: what the glass looks like on screen. The values come from 2.0; here, show the owner the refraction, dispersion, rim light and tint on real backgrounds, as renders or a page, and agree on them before the shader work. *Done when:* the owner has agreed.
- [ ] **3.1** ⚠️ Fork KWin's blur effect (the image's exact KWin version) into `glass/` as `lumen-glass`; build as an RPM in a Containerfile stage.
- [ ] **3.2** Ship it in the image; confirm it matches stock blur in a VM.
- [ ] **3.3** Shared 1/4-resolution dual-Kawase blur, computed once per frame.
- [ ] **3.4** Damage-aware caching: idle frames do no blur work.
- [ ] **3.5** ⚠️ Shader part 1: rounded-rect SDF clip, edge refraction, RGB dispersion.
- [ ] **3.6** Shader part 2: vibrancy, rim light, blue-noise dither.
- [ ] **3.7** Shader part 3: adaptive tint from smallest-mip luminance, keeping 4.5:1 contrast.
- [ ] **3.8** Roles: the `lumen_glass_manager_v1` protocol (window type as a fallback) → presets from tokens.json; reload on token change via D-Bus.
- [ ] **3.9** Rounded corners and soft shadows for all windows; titlebar role; the focused window's line of accent light for apps that draw their own title bars (ADR 0006).
- [ ] **3.10** Tiers Full / Lite / Solid in the render path.
- [ ] **3.11** First-boot benchmark oneshot → `/var/lib/lumen/glass-tier`; battery saver drops a tier; Reduce Transparency and Reduce Motion.
- [ ] **3.12** Spring open/close/morph animations (stiffness 380, damping 30).
- [ ] ➕ **3.13** Smooth-min SDF merging for dock shapes within 12 px.
- [ ] **3.14** GTK glass without a GTK module (ADR 0002): opt-in list of GTK app IDs with the tokens; lumen-glass draws whole-window glass for them; check that it shows only where the GTK themes (2.6, 2.7) left header bars and sidebars translucent.
- [ ] **3.15** ⚠️ Test harness: `kwin_wayland --virtual` in CI rendering the 12 reference scenes.
- [ ] **3.16** Golden-image compare, contrast computation, frame-time benchmark.
- [ ] **3.17** 👤 Phase 3 acceptance: contrast ≥ 4.5:1 everywhere; 60 fps with 8 surfaces on Iris Xe-class graphics (real hardware); idle GPU near zero; Solid tier samples no backdrop.

## Phase 4 — lumen-shell (spec: "Spec: lumen-shell", "Default shortcuts and gestures", Phase 4)

- [ ] **4.0** 👤 Design session: the exact layout of every shell surface. Cover the top bar's three islands, the dock, the command palette, quick settings, notifications, the overview, the lock and login screens, the OSDs and the shortcut overlay. Show sizes, spacing, what each holds and how it moves, as a clickable page, and record what the owner agrees to before 4.1. *Done when:* the owner has agreed.
- [ ] **4.1** Shell package `org.lumen.desktop` skeleton; builds and loads in the image.
- [ ] **4.2** Top bar as three floating islands (left / centre / right), each a floating Plasma panel sized to its content, glass role bar, 32 px (ADR 0006). First check that Plasma can put three such panels on one edge; if it can't, draw the islands in one containment and tell the owner, because lumen-glass then has to clip several rounded rectangles in one surface. It replaces the interim top bar from 1.3 (the layout script in Lumen's global theme).
- [ ] ➕ **4.3** Top bar indicators: tray, network, sound, battery, user; camera/mic/location indicators.
- [ ] **4.4** Dock: "Search or run" field that opens the palette; pinned and running apps (TaskManager) as lens icons, other apps' icons in a lens frame; a line of light in the app's colour under running apps, longer for the focused one (ADR 0006).
- [ ] ➕ **4.5** Dock: progress rings, badges, recent files on right-click, auto-hide.
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
- [ ] **6.9** "Previous versions" in Files via snapper. Revisit the snapshot limits first: test whether fixed limits (24/7/4) keep snapper from freeing space when the disk fills, and if so propose ranges to the owner (1.4 note).
- [ ] **6.10** Installer theme (Anaconda WebUI in the live session from 1.8) and the three install modes; "Install alongside Windows" detects BitLocker and Fast Startup and never resizes a BitLocker volume.
- [ ] **6.11** `hardware/hardware.json` and the `lumen-hwd` compare logic, including the Microsoft UEFI CA 2023 check.
- [ ] ➕ **6.12** Hardware report app (`apps/hwreport`, green / amber / red) in the install USB's live session. If 1.8 had to fall back to `anaconda-iso`, ask the owner before dropping it (ADR 0002).
- [ ] **6.13** 👤 Phase 6 acceptance: install to usable desktop in < 15 min; a non-technical tester sets up, installs an app, restores a file and runs a backup unaided.

## Phase 7 — Switching from Windows (spec: "Spec: Windows apps and switching", Phase 7)

- [ ] **7.1** 👤 `docs/windows-apps.md`: the top 100 apps Windows users need, by category, with today's status; confirm the licences of ProtonDB, AreWeAntiCheatYet and any other source, including where the cloud-gaming alternatives come from and whether their terms allow Lumen to use them (ADR 0009); pick the OneDrive client. You review the list.
- [ ] **7.2** Compatibility database v1: recipes, alternatives, anti-cheat status; import ProtonDB and AreWeAntiCheatYet data with attribution; cover the top 100. For games that anti-cheat blocks, list the cloud-gaming services that carry them as alternatives. Where AreWeAntiCheatYet says broken and recent ProtonDB reports say it runs, rate the game "May work, not yet confirmed" (ADR 0009: only 32 of its 636 broken entries changed after 2025-01-01).
- [ ] **7.3** Signed database updates through `lumen-updated`; offline lookup only; test that a lookup makes no network request.
- [ ] **7.4** `lumen-compat` Rust crate: identify an `.exe` or `.msi` (version info, installer type, file hash) and match it; `lumen app check`.
- [ ] **7.5** "Open Windows app" dialog (`apps/windows-app`): rating, reason, alternatives, Install / Try it; creates the bottle with its recipe; adds the app to the menu.
- [ ] **7.6** Sandbox defaults for Bottles; Windows apps in Settings → Apps; `lumen app list --windows`; full removal.
- [ ] **7.7** Store: ratings on Windows-name searches, Windows alternatives collection, web apps, Heroic and Lutris, anti-cheat status, and on a blocked game's page its cloud-gaming alternatives.
- [ ] **7.8** Welcome: "Your Windows apps" scan of the Windows drive; BitLocker unlock by recovery key for the scan and the file import.
- [ ] **7.9** ⚠️ 👤 Lumen Setup for Windows (`windows-setup/`, fork of Fedora Media Writer): hardware check, BitLocker / Fast Startup / Secure Boot checks, partition shrink, UTC clock, USB writer; built on a Windows CI runner. You provide a Windows code-signing certificate, or SmartScreen will warn users.
- [ ] **7.10** Dual-boot Health checks: Fast Startup, clock mismatch, missing boot entry, Secure Boot certificate.
- [ ] ➕ **7.10a** "Play in Windows" (ADR 0009): on a blocked game's Store page, in its dialog and in the app menu, a button that asks first, then restarts once into Windows through the firmware's one-time boot (UEFI `BootNext` to Windows Boot Manager, never Lumen's boot menu, so BitLocker isn't disturbed). Shown only when that firmware entry exists. Decide which service sets `BootNext` under polkit (lumen-updated owns restarts), and check that BitLocker stays quiet on a real dual-boot machine.
- [ ] **7.11** Tests: every top-100 app has a rating and a path; dialog, Store and CLI agree; offline lookup; sandbox defaults; a blocked game offers its cloud alternatives and, with a Windows entry, "Play in Windows".
- [ ] **7.12** 👤 Phase 7 acceptance: a Windows user installs Lumen with Lumen Setup, sees their apps' status, and installs five Windows apps by double-clicking, with every rating correct; at least 80% of the top-100 list is covered.

## Phase 8 — Hardware: full use of each device (spec: "Spec: hardware", Phase 8; ADR 0010)

Every step here needs real hardware to finish. CI can only test what it can emulate, so these steps prepare everything in the image and leave the check on each reference laptop to the owner or a tester who has it.

- [ ] **8.1** 👤 `docs/hardware.md`: the device features Windows users rely on, class by class, with how well Linux supports each today and what Lumen must add: built-in and USB cameras (including the MIPI cameras of recent Intel and AMD laptops), speakers and microphones, fingerprint readers, touchpads, pens and touchscreens, 2-in-1 sensors, displays (HDR, refresh rates, ambient light), keyboard backlights and vendor keys, batteries, performance modes and fans, Wi-Fi and Bluetooth, docks and USB4, and GPUs' video engines and NPUs. Choose the reference laptops for the hardware lab (the spec names six kinds). You review the list.
- [ ] **8.2** Device profiles: `hardware/hardware.json` (step 6.11) gains the best settings per model (kernel arguments, firmware, quirks, audio tuning, power settings). lumen-hwd applies them on the first boot and when hardware changes, and records what it did for Settings.
- [ ] **8.3** ⚠️ Cameras: built-in MIPI cameras (Intel IPU6 and IPU7, AMD's camera processor) through libcamera and PipeWire, so browsers and call apps reach them through the camera portal; image tuning per sensor where libcamera has it; USB webcam controls in Settings. *Done when:* the reference laptops' cameras work in a browser video call with a picture that compares well with Windows.
- [ ] **8.4** Sound: speaker and microphone tuning per laptop model (PipeWire filter chains, like the processing makers ship for Windows), noise suppression for calls, headset buttons, Bluetooth LE Audio.
- [ ] **8.5** Displays: HDR, variable and high refresh rates on where they work, colour profiles, automatic brightness from the ambient light sensor, scaling per screen.
- [ ] **8.6** Input: pens (pressure, tilt, buttons), touchscreens, 2-in-1 rotation and tablet mode, keyboard backlights, and vendor keys such as camera and microphone mute and performance mode.
- [ ] **8.7** Power and heat: battery charge limits, the performance modes the firmware offers (and vendor tools where needed, each through the package manifest), reliable sleep, battery-life tuning per model.
- [ ] **8.8** Graphics and accelerators: hardware video decode and encode in browsers and apps (with the codec choice of 1.14), GPU compute for creative apps, and NPUs where their drivers allow.
- [ ] **8.9** Connections: fingerprint readers (enrolled in Welcome and Settings), Wi-Fi 7, Thunderbolt and USB4 docks and displays, printers and scanners without drivers (IPP Everywhere, eSCL).
- [ ] **8.10** Settings > Drivers & Hardware: each device with what it can do, whether Lumen uses it, and a plain-English fix or reason when it can't; the hardware report (6.12) says the same before install.
- [ ] **8.11** Tests: the profiles' schema; emulated devices in the VM (a virtual camera, touchpad and pen) for what can be emulated; the hardware report covers every device class in `docs/hardware.md`.
- [ ] **8.12** 👤 Phase 8 acceptance on the reference laptops: every feature in `docs/hardware.md` works, or the hardware report says plainly why not; the cameras and sound compare well with Windows on the same laptop, and battery life is within 10% of Windows'.

## Phase 9 — Hardening, accessibility, performance (spec: "Spec: security model", Phase 9)

- [ ] **9.1** Security review part 1 (boot, disk, image) → `docs/security.md`; fix gaps.
- [ ] **9.2** Security review part 2 (apps including Windows-app bottles and Lumen Setup, network, privilege, supply chain: SBOM, Renovate, pinned digests); fix gaps.
- [ ] **9.3** Accessibility audit: shell surfaces.
- [ ] ➕ **9.4** Accessibility audit: apps.
- [ ] **9.5** Performance: boot < 10 s on NVMe.
- [ ] ➕ **9.6** Performance: idle RAM < 1.5 GB.
- [ ] **9.7** Translations: string extraction, Weblate config, pseudo-locale.
- [ ] **9.8** 👤 Phase 9 acceptance on a real laptop.

## Phase 10 — Release v0.1 (spec: "Testing, CI and release", Phase 10)

- [ ] **10.1** Release train in CI: dev on every merge, weekly beta, stable every 2 weeks after 7 days in beta.
- [ ] **10.2** Update test job: install previous, upgrade, reboot, roll back, reboot.
- [ ] **10.3** Docs: user guide and install guide.
- [ ] ➕ **10.4** Docs: FAQ (including what won't come over from Windows), hardware notes, contributing guide.
- [ ] **10.5** 👤 Publish v0.1 (you approve): signed images, ISO, SBOM, checksums, plain-English changelog.
- [ ] **10.6** 👤 Install and run v0.1 on two real machines, one of them alongside Windows through Lumen Setup.
