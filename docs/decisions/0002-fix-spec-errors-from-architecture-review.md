# 0002. Fix the spec errors found while writing the architecture

- Status: **Accepted** (2026-10-27). The owner asked for the issues to be fixed; applied to `docs/spec.md`, `PROGRESS.md` and `docs/architecture.md`.
- Deciders: owner (Edmund), lead engineer (Claude)

## Context

Writing `docs/architecture.md` part 1 (step 0.1) turned up five places where the spec was technically wrong (its section 8, Q1 to Q5). A sixth, the spec's use of `/usr/etc`, was already noted for step 1.3. The owner asked for them to be fixed now, before any phase builds on them.

## Decisions

### 1. GTK apps get glass without a GTK module

**Problem.** The spec said GTK apps request glass "via our small GTK module". GTK 4 dropped general-purpose loadable modules, so the module can't load into GTK 4 apps. Flatpak apps can't load modules from the host either, and Flatpak is the only way users install apps. The module would only have reached GTK 3 apps shipped in the image.

**Decision.** The compositor does it instead. The GTK 4 and GTK 3 themes make header bars and sidebars translucent. For GTK apps on an opt-in list of app IDs (kept with the tokens), lumen-glass draws glass behind the whole window; it shows only where the theme left the window translucent. Content stays opaque, as the spec requires. A GTK 3 module for host apps is not built unless a real need appears.

**Cost.** Glass is sampled over the whole window area for opted-in GTK apps, not just the sidebar. The shared blur texture is computed once per frame anyway, so the extra work is one shader pass over those pixels; the Lite and Solid tiers cover weak GPUs. GTK apps in Flatpaks only get the translucent theme if they can see it, which Phase 2 already has to solve for theming in general.

### 2. Keep tuned-ppd, drop power-profiles-daemon

**Problem.** The package manifest listed both `power-profiles-daemon` and `tuned-ppd`. In the Fedora 44 repositories both provide `ppd-service` and conflict on it, so they can't be installed together.

**Decision.** Ship `tuned-ppd` only. It serves the same power-profiles D-Bus API, so the shell, Settings and lumen-glass don't change. Step 1.1 confirms which one Kinoite already ships.

### 3. The post-update health check doesn't wait for a login

**Problem.** The spec's check after an update needed "shell started" within 2 minutes, and two failures rolled the machine back. The shell only starts when someone logs in. After a "Tonight" restart nobody does, so every good update would roll back. "Network up" had the same flaw: a laptop that boots with no network would fail it.

**Decision.**

- The boot check needs no login: the login screen is up, NetworkManager is running (not "connected"), and no critical units failed, all within 2 minutes of boot. Two failed boots in a row fall back to the previous deployment, as before.
- At the first login after an update, a session check confirms the shell started. If it didn't, the user is offered "Go back to the previous version". This isn't automatic, because one user's broken session shouldn't roll back the whole machine.
- Try greenboot (Fedora's boot health checks with GRUB boot counting) before writing our own.

### 4. The install media is a live ISO built from the Lumen image

**Problem.** The spec has the hardware report run on the live USB and the installer be Anaconda WebUI from bootc-image-builder's `anaconda-iso`. That ISO boots straight into Anaconda with no live desktop, so the hardware report app has nowhere to run. By default it is also unattended and installs to the first disk it finds; interactive choices need a partial kickstart.

**Decision.**

- The install ISO is a live ISO built from the Lumen image itself (try Universal Blue's Titanoboa first). It boots into a Lumen live session that runs the hardware report, then starts the Anaconda installer. Anaconda WebUI normally runs inside a live session, so this keeps the spec's installer. The qcow2 for tests still comes from bootc-image-builder.
- Step 1.8 builds it and records the tool chosen in an ADR.
- Fallback, if no live ISO works by Phase 6: `anaconda-iso` with a partial kickstart, so the user picks the disk and install mode. The hardware report then runs only in Lumen Setup for Windows and as `lumen hw report` after install. That drops the spec's "Live USB runs a hardware compatibility report" requirement, so the owner must approve it before it happens.

### 5. "Get help from a friend" works on the same network in v0.1

**Problem.** The spec puts remote help on Plasma's remote desktop (KRdp) behind a one-time code. KRdp is a plain RDP server with no relay. A friend on another network can't reach it unless the user forwards a port on their router. Windows' Quick Assist works across the internet because Microsoft runs a relay.

**Decision.** This one was a product choice; the lead engineer made it on the owner's instruction to fix the issues, and the owner can change it.

- v0.1: KRdp on the same network, behind a one-time code and a visible indicator. The page says plainly that the friend must be on the same network.
- For help over the internet, the same page offers RustDesk from the Store, with a plain note that RustDesk's own servers carry the connection. Confirm at step 5.22a that RustDesk is on Flathub and works on Plasma Wayland.
- After v0.1: a Lumen relay, so help over the internet needs no third-party app. It has running costs and privacy questions, so it needs the owner's approval.

### 6. Image defaults never go in `/usr/etc`

**Problem.** The spec put config defaults in `/usr/etc`. `bootc container lint` rejects that: bootc 1.17.1 in Fedora 44 reports "Found /usr/etc - this is a bootc implementation detail and not supported to use in containers" (lint `etc-usretc`).

**Decision.** Vendor defaults go in `/usr/lib` and `/usr/share` wherever the software reads them there (systemd, polkit, sysctl, udev, XDG data directories). Config that only exists in `/etc` goes in the image's `/etc`, which bootc treats as the default and 3-way merges with local changes on every update. Nothing creates `/usr/etc`. `bootc container lint` (step 1.2) enforces this.

## Changes made to docs/spec.md

- Problems table and package manifest: tuned-ppd instead of power-profiles-daemon.
- Base and build chain: the new rule for defaults (decision 6).
- Update flow: the boot check and the first-login check (decision 3).
- How surfaces ask for glass: GTK apps through the theme and the opt-in list (decision 1).
- Power & Battery and About & Health rows of the Settings table (decisions 2 and 5).
- Installer: install media and Anaconda (decision 4).
- Windows section, "After v0.1": the Lumen relay (decision 5).
- Phase 1, 3, 5 and 6 prompts: matching wording.

## Changes made to PROGRESS.md

Steps 1.3, 1.8, 3.14, 5.6, 5.22a, 6.10 and 6.12 reworded to match. No steps added or removed; step 1.8 is marked as a big step (⚠️).

## Consequences

- Phase 1 takes on the riskiest of these: building a live ISO from a bootc image is newer and less proven than `anaconda-iso`. If it fails, the fallback keeps Phase 1 moving and the owner decides about the live report.
- GTK apps get glass in more places than the module would have reached (every Flatpak GTK app on the list), at some extra GPU cost.
- Remote help is honest about its limit in v0.1 instead of failing silently across the internet.
