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

**This file stays short**, because every session reads it first. What each finished step built, measured and found is in [docs/history/](docs/history/README.md), one file per phase: search it for a step's number when a step needs it. This file holds the current step, what waits for the owner, the facts every session needs, and notes for steps still to come (CLAUDE.md, "Step mode").

## Current step

**1.14c**: Steam's hardware encoding on AMD, as an opt-in download on each machine ([ADR 0025](docs/decisions/0025-codecs.md), decision 4; notes below). Then 1.15.

Where things stand (2026-11-11):

- **`main`** is at the base bump to Kinoite 45.20261102.0 (pull request #4). Its last run published and signed `lumen` (`dev` is `45.20261108`) and stopped `lumen-gaming` at its first publish, which a fix waiting on the branch repairs.
- **The branch `ccr-d3f590a0-rbcjnh`** holds everything that isn't on `main` yet: the `lumen-gaming` publish fix and steps 1.13 to 1.14b (the branch `claude/progress-next-step-cvyy8f`, which it contains, green in image run 42640758130), and the review of 2026-11-11.
- **The review of 2026-11-11** (the owner asked for a look at the work so far and at the plan; [history](docs/history/phase-1.md) has the detail under "Review, 2026-11-11"):
  - The first-boot apps, the browser among them, now install as soon as the PC is online. Before, a PC that was offline two minutes after starting got them only after a restart.
  - A change that is large to download once now says so in the image (`org.lumen.one-time-download` in `image/Containerfile`), in place of a digest in the workflow that went stale whenever `main` published.
  - Pushes that change only documents no longer start the two-hour image build on branches, or cancel the one before them; `main` builds from its own workflow, `publish`, on every merge as before.
  - This file was 147 KB; the finished steps' records moved to `docs/history/`.
  - The plan builds its tests and its translation tooling before what they check: three new steps (3.2a, 4.1a, 4.1b), and 2.13 now builds the harness they share. "Changes to the plan" below says why.
  - CI on the branch, for `9704cf7`: lint (run 43106109083) and the thumbnails test (43106109126) are green. Image run 43106109097, the first to build the label and the changed units into real images, was still building when this was written: **look at it first**, record its result here and in the history, and fix what it found before 1.14c.

## Waiting for the owner

In order. The first two publish what is already built; the rest block later steps.

1. **Merge the branch `ccr-d3f590a0-rbcjnh` into `main`** (through a pull request if you like). The first build of `main` afterwards publishes `lumen-gaming` for the first time, and `lumen` with a one-time download of about 365 MiB, which the image declares, so nothing needs editing first. It is also the first run of the new `publish` workflow: if any of its jobs fails, say so at the start of the next session.
2. **Then check that the `lumen-gaming` package on ghcr.io is public**, as `lumen`'s was from its first push; if not, make it public in the package's settings.
3. **Pull request #7**, the weekly base bump (Kinoite 45.20261109.0): press "Approve workflows to run", and merge it once its checks are green. Before or after the branch, either order works. The base workflow refreshes it every Monday until it is merged.
4. **1.11a 👤, Lumen's kernel module signing key** ([ADR 0021](docs/decisions/0021-module-signing-key.md), "How the key is made and kept"). Until it exists, the NVIDIA editions are built and tested but not published (steps 1.11c and 1.12c-2).
5. **Decide how commits get their sign-off.** CONTRIBUTING.md asks for a `Signed-off-by:` line on every commit; Claude never adds one, and pull requests #2, #3, #5 and #6 were merged without. Either sign off before merging (`git rebase --exec 'git commit --amend --no-edit --reset-author --signoff' main`), or say that the rule should change.

Your call, blocking nothing:

- Reporting upstream what Lumen works around: bootc and bootupd leaving their files' SELinux labels to the kernel, and Fedora's policy having no line for `/sysroot/.bootc-aleph.json` (ADR 0018); Anaconda's two bootc install bugs (ADR 0014, ADR 0015); image-builder's `generic-iso` not labelling its tree (ADR 0012). tuned's is already reported ([tuned#895](https://github.com/redhat-performance/tuned/issues/895)).
- The spec's "only accepts our signed images" is read as "Lumen's images only with Lumen's signature"; read for every image it would break Toolbx and distrobox (ADR 0008). Say if the spec should spell that out.
- CONTRIBUTING.md says the base workflow's own commits carry no sign-off, the DCO rule's one exception besides AI assistants. Confirm or change it.
- A merge to `main` that changes only documents still builds and publishes all four editions, because the spec's release train says every merge to `main` builds `dev`. Say if `main` should skip those too, as branches now do.

## Facts every session needs

- **Sources of truth.** `docs/spec.md` is the specification (ADR 0001): edit it directly. `docs/risks.md` and `docs/competing-with-windows.md` are living documents: update an entry when what it describes changes. The owner deferred a Windows-style "Familiar" layout and a built-in AI assistant: add neither without asking.
- **Before starting a step**, fetch, and check that `main` and this file haven't moved: two sessions once finished the same step at the same time. "Current step" says which branch holds unmerged work; start from it, not from `main`, until it is merged.
- **Commits.** Small, with conventional messages. An AI assistant never adds a `Signed-off-by:` line (CONTRIBUTING.md). On the owner's PC, commits use their GitHub no-reply email, never their personal one. Mark new scripts executable with `git add --chmod=+x`: the Windows checkout has `core.filemode=false`.
- **Checks before a push:** `just lint` and `just test`. In a cloud session, which has no Podman: install the lint tools at the versions in `tests/lint/Containerfile`, then run `bash tests/lint/run.sh`, `bash tests/lint/selftest.sh` and the two `python3 -m unittest discover` lines from the justfile.
- **CI** ([architecture 9.8](docs/architecture.md#98-ci-and-the-release-train)):
  - `lint` runs on every push. `image` builds, re-chunks and boots the four editions on every push to a branch, in about two hours, unless the push changes only documents. `publish` does the same on every push to `main`, then pushes and signs. So push code first and notes afterwards: a push of notes alone starts no image run and cancels none. To build anyway: Actions > image > Run workflow.
  - `iso` makes and boots the install ISO, on demand and when the live system changes on `main`. `thumbnails` tests the video thumbnailer against Flathub. `base` bumps the pinned bases on Mondays through a pull request, whose held checks need "Approve workflows to run".
  - A build whose update from its edition's newest `dev` downloads over 100 MiB fails. If the change is meant and happens once (any new folder that no package owns changes the 280 MiB layer that holds the initramfs), raise `org.lumen.one-time-download` in `image/Containerfile` in the same pull request and say why there (ADR 0007).
  - The runners' Podman is Ubuntu's 4.9.3; WSL's is 5.8.9. When CI and WSL disagree, suspect that first. The runners have KVM.
  - If a sign job sits at "Starting job" for hours, cancel the run, then "Re-run failed jobs".
  - A run's summary page holds 1 MB at most, and GitHub deletes runs after 90 days; the tags on ghcr.io keep the digests.
- **Image build rules**, each learned from a failed build:
  - A stage that runs dnf deletes `/run/dnf`, `/var/cache/*`, `/var/lib/dnf` and `/var/log/*` afterwards, and whatever its packages' scripts left in `/run`.
  - Build steps run Python with `PYTHONDONTWRITEBYTECODE=1`.
  - A `RUN --mount` mounts only the files it reads, or any change under `image/` runs dnf again.
  - `rm -rf /run/lumen` comes before `bootc container lint`: the runners' Podman leaves the mount points behind.
- **The owner's PC** is Windows 11 Home (Ryzen 7 5800X, 16 GB). The project folder is `C:\Users\edmun\Downloads\Lumen OS`. Linux tooling runs in WSL (`FedoraLinux-44`), which has no `/dev/kvm` and no `awk`, and is too slow to build images: build them in CI. [docs/dev-setup-windows.md](docs/dev-setup-windows.md) has the commands.
- **A cloud session** can't reach quay.io, Fedora's sites, Flathub, or the storage behind GitHub's run artifacts and ghcr.io's layers. It can read job logs through the GitHub tools, ghcr.io's manifests and github.com's release downloads. Facts about Fedora's packages therefore come from CI's output, not from the session.
- **Editing this file:** check its headings and length afterwards (a script once cut off every phase's step list). When a step is done, its record goes to `docs/history/`, and only what a later step needs stays here, under that step's number.

## Notes for steps still to come

Found while doing earlier steps. Read the lines for your step; the history and the ADRs have the detail.

- **1.11a, 1.11c, 1.12c-2** (the module signing key): [ADR 0021](docs/decisions/0021-module-signing-key.md). Until the key exists, builds sign NVIDIA's modules with a throwaway key, and `publish.yml` sets `publish: false` for the two NVIDIA editions.
- **1.14c**: ADR 0025, decision 4, has the design: RPM Fusion's `mesa-va-drivers-freeworld` at the image's exact Mesa version, kept in `/var/lib/lumen/codecs`, checked with RPM Fusion's key, VA-API pointed at it, and a service at each start that turns it off while the image's Mesa differs. RPM Fusion's Mesa can run ahead of the image's (26.2.6 against 26.2.5 on 2026-11-08), so the command must say plainly when there is no matching build yet.
- **1.17** (acceptance) must also show what CI can't:
  - the first-boot apps downloading once the PC is online, and an `.exe` opening in Bottles;
  - the interim top bar, which nobody has seen yet;
  - how much the first `bootc upgrade` after an install from the ISO downloads, most likely every layer once (ADR 0014, Consequences);
  - H.264 and HEVC video in Firefox and Haruna, and video thumbnails in Dolphin;
  - the Gamescope session, which needs real graphics hardware (ADR 0020).
  - Tell the tester that until Phase 5 an installed system updates only when someone runs `bootc upgrade`: Fedora's updaters are masked and lumen-updated doesn't exist yet.
- **Whenever Fedora 45 rebuilds it:** put `kcm-fcitx5` back in `image/packages.toml`. It was left out on 2026-11-01, when its build still needed Plasma 6.7's `libPlasma.so.7`.
- **Whenever a session can reach quay.io** (the owner's PC, or a CI job): read `docs/versions.md`'s tables again for Fedora 45. They are still the reading of 2026-10-27; the Containerfile's `# Pinned:` line is current.
- **Each August:** move `org.freedesktop.Platform` in `lumen.preinstall` to the new release.
- **When the lint container moves to a new Fedora** (by hand: the base workflow keeps it on 44): keep the number in `nodejs24-full-i18n` equal to Node's major version.
- **Pins moved by hand until Renovate (9.2):** actionlint, cosign and syft (`tests/lint/Containerfile`), just (`lint.yml`), image-builder (`build-image.yml` and `iso.yml`, kept equal by `test_iso.py`) and the actions' commits. cosign must stay on 3.x (versions.md).
- **2.1**: what "match" means for Flatpak apps is decided (ADR 0004, Q16).
- **2.11 and 4.2**: the interim global theme and its layout script are in `image/overlay/usr/share/plasma/look-and-feel/org.lumen.desktop`, and `/etc/xdg/kdeglobals` makes it the default. The interim bar has no input method widget.
- **4.15**: Plasma Login Manager's greeter has no SDDM-style theme folder; it runs on its own KWin and Plasma (ADR 0005).
- **5.4 to 5.7** (lumen-updated): pass `--enforce-container-sigpolicy` to `bootc switch` (architecture 4.4). It owns restarts. The first-boot app download (`lumen-flatpak-preinstall.service`) should follow its rule for metered connections (5.5).
- **5.8, 5.9** (Health): notice an edited `/etc/containers/policy.json`, which bootc's `/etc` merge then stops updating, and a `/root/.config/containers/policy.json`, which replaces it (ADR 0008).
- **5.21**: choose the default input method. Neither IBus nor Fcitx5 starts on Plasma Wayland by default; Fedora sets KWin's to Plasma's on-screen keyboard (history, step 1.3).
- **6.1 to 6.3** (Store): take `x-scheme-handler/appstream`. `kde-mimeapps.list` still sends `appstream://` links and `.rpm` files to Discover, which is gone, and Fedora's app-menu favourites still list it. Whether Fedora's own Flatpak remote shows is the Store's decision (ADR 0024).
- **6.4**: Solaar needs `solaar-udev` on the host: add it to `image/packages.toml`.
- **6.5** (Welcome): Kinoite's `plasma-setup.service` creates the first user today. Welcome must replace it or build on it, and stay off in the live session as it does (`ConditionKernelCommandLine=!rd.live.image`). The boot test finishes Plasma Setup by hand (ADR 0017), so it changes with it.
- **6.6**: TPM unlock through systemd-pcrlock with no PIN by default, and a PIN as the fallback (ADR 0004, Q17).
- **6.10**: the firmware's boot entry is labelled "Fedora" (bootupd's EFI vendor folder). The installer's kickstart installs only `lumen`; the other editions are reached by switching afterwards (5.10), so decide here whether the installer offers them.
- **9.1, 9.2**: decide on a second, offline signing key in `keyPaths`, and on checking Fedora's own signature on each new Kinoite base before the base workflow pins it (ADR 0008).
- **9.5**: stale Python bytecode in the installed image costs start-up time; recompiling it as the live stage does is worth asking Fedora about first (ADR 0012, Follow-up). On a first boot `fedora-atomic-desktop-mandb-update.service` takes 22 s and `ldconfig.service` 12 s, after the screen is up.
- **10.1**: deleting old `dev` builds must delete their `sha256-<digest>.sig` and `.att` tags too. A signature holds for a repository, not a tag, so decide whether channels need their own identity (ADR 0008). The ISO, at 3.6 GiB, is over GitHub's 2 GiB limit for a release file: choose a host (Q15). A re-run of one edition's failed publish job works out its version again and can get the next suffix, so one commit's editions could differ in version.
- **Not scheduled:** reusing the `base` stage between CI runs when neither the pin nor `packages.toml` changed would cut a rebuild's download from 41 MiB to about 8 (ADR 0007).

## Changes to the plan

- 2026-11-11, a review of the work so far. CLAUDE.md asks that every feature ships with tests and that every string is translatable, but the plan built the test harnesses at the end of Phases 3 and 4 and the translation tooling in Phase 9, after everything they would have checked. That work now comes earlier ([ADR 0026](docs/decisions/0026-short-plan-early-tests.md)); no step was dropped, and no step number changed:
  - **2.13** is also where the headless session harness is built, which 3.2a and 4.1a reuse.
  - **3.2a** (new): the glass test harness, before the shader work instead of after it. 3.15 and 3.16 keep the full set of 12 scenes, the contrast figures and the frame-time benchmark.
  - **4.1a** (new): the shell's test scaffold, before its first surface. 4.18 keeps full coverage.
  - **4.1b** (new): string extraction and a pseudo-locale check, before the first screen with text. 9.7 keeps Weblate and the full pass.
  - **5.1** says that the Rust checks join `just lint` and `just test` from the first service.

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
- [x] **1.8a** CI: bootc-image-builder, now part of osbuild's image-builder (ADR 0011), makes a qcow2 of every build for the boot test. Check the disk it makes: the partitions, a Btrfs root, Lumen's os-release, and that the install records `ghcr.io/edmundhills/lumen:dev` with the signed transport (ADR 0008).
- [x] **1.8b-1** The `live` stage: a Lumen live session that follows the container-native ISO contract (dracut-live with `dmsquash-live`, livesys-scripts, Anaconda WebUI with `installer/anaconda/lumen.conf`, Welcome kept from running, shim and GRUB where the contract wants them, `iso.yaml`), with checks, built in WSL.
- [x] **1.8b-2** ⚠️ 👤 Pack the live stage into an ISO, on demand in CI, with the SELinux labels the owner chose (1.8b-1 notes). Try Titanoboa first, then image-builder's `generic-iso`, and record the tool in an ADR. CI keeps the ISO as a short-lived workflow artifact (Q15).
- [x] **1.8b-3a** Boot the ISO in QEMU in CI, with UEFI and Secure Boot (OVMF), and check the live session: SELinux enforcing and no denials, the live user reaches Plasma, "Check this USB" passes. This is CI's first VM, so it also finds out whether the runners have KVM (1.9). *Done:* the test runs after every ISO; everything passes but the denial check.
- [x] **1.8b-3b** 👤 Fix the SELinux denials the boot test found (tuned running bootc, tuned-ppd rewriting stale bytecode), with the owner's choice of fix for tuned, until the `boot-iso` job passes.
- [x] **1.8c** The installer installs the ISO's own copy of the image, with no network, through Anaconda's `bootc` kickstart command (`--source-imgref containers-storage:…`, `--target-imgref ghcr.io/edmundhills/lumen:dev`), so the installed system records the signed transport (ADR 0008). Check it with an unattended install in a VM in CI. If no live ISO works, fall back as ADR 0002 says and tell the owner.
- [x] **1.8d** Run the installer with SELinux enforcing in the live session (owner's choice, 2026-10-31, ADR 0014): Fedora's `liveinst` runs `setenforce 0` while Anaconda runs. Change that in the live stage, with an ADR, and keep it if the install test still installs with no SELinux denials; otherwise record the denials and what fixing them would take, and ask the owner.
- [x] **1.8e** Installed systems run Btrfs with the zstd compression the spec asks for, and `systemd-remount-fs.service` doesn't fail (1.8c notes). The installer mounts the disk with `compress=zstd:1` while it installs, but bootc's kernel arguments give only `rootflags=subvol=/root`, and the `/` line Anaconda writes in `/etc/fstab` can't be applied to a composefs root, so remount-fs fails. Find the way that holds for installs and for image-builder's disks (kernel arguments, an fstab without `/`, or a remount of `/sysroot`), and turn the install test's record of the compression back into a check.
- [x] **1.9** `tests/boot`: QEMU/KVM boot test in CI; the login screen within 60 s (`display-manager.service`, Plasma Login Manager, active and its greeter running; ADR 0005); `systemctl --failed` empty. Also boot once with Secure Boot (OVMF) and record whether kernel lockdown is on and hibernation is offered (`/sys/kernel/security/lockdown`, `/sys/power/state`) in ADR 0001's follow-up.
- [x] **1.10** Variant `lumen-gaming`: Steam, Gamescope session, MangoHud, controller udev rules, as a layer that 1.12 also puts on `lumen-nvidia`.
  - [x] **1.10a** The `lumen-gaming` stage builds: RPM Fusion's Steam repository with its signing key pinned in the repository, `image/gaming/packages.toml` (Steam, Gamescope, MangoHud, GameMode, Fedora's `steam-devices` controller rules), the 32-bit packages Steam needs at exactly `base`'s versions (architecture 9.4 and 9.5) with Koji as the fallback, os-release and labels for the edition, its own checks and `bootc container lint`. CI builds it after `lumen` in the image job, from the same build, and runs the checks. ADR 0019.
  - [x] **1.10b** The Gamescope session: Steam's Big Picture mode as a session in Plasma Login Manager, from ChimeraOS's `gamescope-session` (MIT), built in a stage of the image, without SteamOS's update and BIOS helpers and their polkit rules; returning to the desktop works. Checks.
  - [x] **1.10c** The gaming image's qcow2 boots in CI as `lumen`'s does (1.9's test, which takes any qcow2), and its login screen offers the Gamescope session.
- [ ] **1.11** ⚠️ Variant `lumen-nvidia`: akmods-built, signed kmods in CI.
  - [ ] **1.11a** 👤 Lumen's kernel module signing key: Claude writes the key's profile and procedure (ADR 0021, `image/nvidia/make-module-key.sh`, `module_key.py` and its tests); the owner makes the key in WSL with no network, puts it in a `module-signing` environment for `main`, commits the certificate as `image/nvidia/module-signing.der` and keeps an offline backup. *Done when:* the certificate is in the repository and passes `test_module_key.py`, and the environment's two secrets exist.
  - [x] **1.11b** The `lumen-nvidia` stage: RPM Fusion's `akmod-nvidia` built with akmods against `base`'s exact kernel, NVIDIA's open kernel modules (Turing and newer; driver 580 was the last for older cards, risk 7), signed in a step of its own with `sign-file` (a throwaway key on branches), NVIDIA's user-space packages, os-release and labels for the variant, checks and `bootc container lint`; CI builds it after `lumen`. Decide how nouveau stays usable until the NVIDIA modules load (risk 7). ADR 0022.
  - [ ] **1.11c** CI signs with the real key on `main` (the `module-signing` environment, the key as a build secret), and the NVIDIA image's qcow2 boots in CI, with no NVIDIA card and no MOK enrolled, to the login screen with no failed units (risk 7's session test).
- [ ] **1.12** NVIDIA MOK enrolment doc; variant `lumen-gaming-nvidia` (`lumen-nvidia` plus the gaming layer, ADR 0004); CI matrix builds all four images.
  - [x] **1.12a** The NVIDIA MOK enrolment doc: `docs/nvidia-secure-boot.md` (enrol with `mokutil --import`, the blue MokManager screen, check, remove, fingerprint), and `check-nvidia.sh` checks that `mokutil` and `openssl` are in the image.
  - [x] **1.12b** `lumen-gaming-nvidia`: the gaming layer on `lumen-nvidia` (`LUMEN_GAMING_FROM=localhost/lumen-nvidia:ci`), with os-release naming both (`VARIANT_ID=gaming-nvidia`, `IMAGE_ID=lumen-gaming-nvidia`), NVIDIA's 32-bit libraries for Steam's games (`xorg-x11-drv-nvidia-libs.i686`, which the driver requires with Steam's 32-bit Mesa), both editions' checks, built and booted in the `nvidia` job.
  - [ ] **1.12c** CI publishes all four images: each re-chunked, its SBOM made, pushed to `ghcr.io/<owner>/lumen`, `lumen-gaming`, `lumen-nvidia` and `lumen-gaming-nvidia`, and signed (ADR 0008), its `dev` tag moved; a failed NVIDIA build holds only its own two images back (risk 7). Split:
    - [x] **1.12c-1** Each edition on a runner of its own (ADR 0023): `image.yml` calls `build-image.yml` for each of the four in a matrix; each is built, re-chunked, measured against its own `dev`, given its SBOM, its qcow2 made from the re-chunked image and booted; one build version for all four. Builds of `main` publish `lumen` and `lumen-gaming`; the NVIDIA editions are built and tested but not published.
    - [ ] **1.12c-2** Publish `lumen-nvidia` and `lumen-gaming-nvidia` from `main`, their modules signed with Lumen's key from the `module-signing` environment. Needs 1.11a; finishes 1.11c.
- [x] **1.13** Windows-app base in the image: `ntsync` autoload, Bottles preinstalled on first boot, `.exe` and `.msi` open in Bottles until the Phase 7 dialog exists, metric-compatible fonts (Liberation, Carlito, Caladea). Boot test checks `/dev/ntsync` exists.
- [ ] **1.14** 👤 Codecs and hardware video decoding: Claude writes the options and their legal trade-offs as an ADR; you choose; Claude ships the choice.
  - [x] **1.14a** The owner's choice (ADR 0025, option A): Fedora's codecs in the image; Flathub's Firefox and KDE's Haruna in the preinstall list; Kinoite's Firefox RPM removed, with nothing left naming it.
  - [x] **1.14b** H.264 and HEVC video thumbnails from Flathub's codecs: `ffmpegthumbs` removed; Lumen's `.thumbnailer` runs the newest freedesktop runtime's `ffmpeg` in `flatpak run --sandbox` with only the file readable; the runtime preinstalled; a CI test with H.264 and HEVC clips.
  - [ ] **1.14c** Steam's hardware encoding on AMD, opt-in on each machine: a command that downloads RPM Fusion's `mesa-va-drivers-freeworld` at the image's exact Mesa version into `/var/lib/lumen/codecs`, checked with RPM Fusion's key, and points VA-API at it; a service at each start that turns it off while the image's Mesa differs.
- [ ] **1.15** Compatibility database v0 in `compat/`: JSON schema, validation test, first 20 entries, ODbL licence file.
- [ ] **1.16** ⚠️ Nightly CI compatibility job: install and launch freely downloadable Windows apps under the image's Wine, screenshot the window, update each entry's "last tested".
- [ ] **1.17** 👤 Phase 1 acceptance: install the ISO in a VM (VirtualBox 7 has a virtual TPM and Secure Boot) with encryption; `bootc status`, `bootc upgrade`, `bootc rollback`; double-clicking an `.exe` opens Bottles; the compatibility job is green. Claude writes the checklist, which also covers what CI can't see ("Notes for steps still to come"); you run it.

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
- [ ] **2.13** ⚠️ Visual test, and the harness that Phases 3 and 4 reuse (3.2a, 4.1a): a headless Plasma session in CI (`kwin_wayland --virtual`, software rendering) that opens an app, takes a screenshot and compares it with a golden image within a tolerance. First use: Qt, GTK 4, GTK 3 and Flatpak apps in light and dark; store the golden images.
- [ ] **2.14** 👤 Phase 2 acceptance: all four app types match in both modes (the same light or dark mode, accent, contrast and fonts; libadwaita apps keep their own shapes, ADR 0004); one accent change updates all of them.

## Phase 3 — lumen-glass (spec: "Spec: lumen-glass effect", Phase 3)

- [ ] **3.0** 👤 Design session: what the glass looks like on screen. The values come from 2.0; here, show the owner the refraction, dispersion, rim light and tint on real backgrounds, as renders or a page, and agree on them before the shader work. *Done when:* the owner has agreed.
- [ ] **3.1** ⚠️ Fork KWin's blur effect (the image's exact KWin version) into `glass/` as `lumen-glass`; build as an RPM in a Containerfile stage.
- [ ] **3.2** Ship it in the image; confirm it matches stock blur in a VM.
- [ ] **3.2a** ⚠️ Glass test harness, moved up from 3.15 so that each shader step ships with its test: the session harness of 2.13 renders reference scenes through lumen-glass on software rendering, compares them with golden images within a tolerance, and computes text contrast. It starts with the scenes stock blur can draw; each step from 3.3 to 3.14 adds the scenes for what it draws, with their golden images.
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
- [ ] **3.15** All 12 reference scenes of the spec's glass visual test in the harness of 3.2a, each with its golden image.
- [ ] **3.16** Contrast of at least 4.5:1 computed on every scene, and the frame-time benchmark (the golden-image compare is the harness's, from 3.2a).
- [ ] **3.17** 👤 Phase 3 acceptance: contrast ≥ 4.5:1 everywhere; 60 fps with 8 surfaces on Iris Xe-class graphics (real hardware); idle GPU near zero; Solid tier samples no backdrop.

## Phase 4 — lumen-shell (spec: "Spec: lumen-shell", "Default shortcuts and gestures", Phase 4)

- [ ] **4.0** 👤 Design session: the exact layout of every shell surface. Cover the top bar's three islands, the dock, the command palette, quick settings, notifications, the overview, the lock and login screens, the OSDs and the shortcut overlay. Show sizes, spacing, what each holds and how it moves, as a clickable page, and record what the owner agrees to before 4.1. *Done when:* the owner has agreed.
- [ ] **4.1** Shell package `org.lumen.desktop` skeleton; builds and loads in the image.
- [ ] **4.1a** Shell test scaffold, moved up from 4.18 so that each surface ships with its test: the QML unit-test runner in CI, and a session test on the harness of 2.13 that opens a surface by D-Bus call or shortcut and takes a screenshot. Each step from 4.2 on adds its surface.
- [ ] **4.1b** Translation plumbing, moved up from 9.7, before the first screen with text: the build extracts every Lumen component's strings (Qt's `lupdate`, gettext elsewhere), and a pseudo-locale run of the session test shows any text that isn't translatable. Every later step with user-facing text passes it.
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
- [ ] **4.18** The QML unit tests and the session test cover every surface (the scaffold is 4.1a's).
- [ ] **4.19** Keyboard-only and Orca tests; startup < 1.5 s and < 250 MB check.
- [ ] **4.20** 👤 Phase 4 acceptance.

## Phase 5 — Services, CLI and Settings (spec: "Spec: lumen CLI and services", "Spec: updates, rollback and backup", "Spec: Lumen Settings and System Health", Phase 5)

- [ ] **5.1** Rust workspace (`services/`, `cli/`), shared D-Bus interface crate, hardened systemd unit and polkit templates. `cargo fmt`, `clippy` and `cargo test` join `just lint` and `just test`, so each service ships with its tests; 5.23 is the end-to-end pass.
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
- [ ] **9.7** Translations: Weblate config, and a full pass with the pseudo-locale over every app and surface (string extraction and the pseudo-locale check exist since 4.1b).
- [ ] **9.8** 👤 Phase 9 acceptance on a real laptop.

## Phase 10 — Release v0.1 (spec: "Testing, CI and release", Phase 10)

- [ ] **10.1** Release train in CI: dev on every merge, weekly beta, stable every 2 weeks after 7 days in beta.
- [ ] **10.2** Update test job: install previous, upgrade, reboot, roll back, reboot.
- [ ] **10.3** Docs: user guide and install guide.
- [ ] ➕ **10.4** Docs: FAQ (including what won't come over from Windows), hardware notes, contributing guide.
- [ ] **10.5** 👤 Publish v0.1 (you approve): signed images, ISO, SBOM, checksums, plain-English changelog.
- [ ] **10.6** 👤 Install and run v0.1 on two real machines, one of them alongside Windows through Lumen Setup.
