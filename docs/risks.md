<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Lumen OS technical risks

Status: accepted by the owner at step 0.8 (2026-10-27, [ADR 0004](decisions/0004-phase-0-review.md)). Written at step 0.3 against [docs/spec.md](spec.md) as amended by [ADR 0001](decisions/0001-compete-with-windows.md) and [ADR 0002](decisions/0002-fix-spec-errors-from-architecture-review.md), and against [docs/architecture.md](architecture.md).

This is a living document, like the [gap list](competing-with-windows.md). Update a risk when it changes, and close it when its mitigation has shipped and been tested. Facts that move (dates, upstream patches, rules for certificates) were checked on 2026-10-27; the sources are at the end.

**How to read it.** *Likelihood* is how likely the risk is to hurt Lumen before v0.1 if we do nothing beyond the plan. *Impact* is how bad it is when it happens: **High** means users lose data or can't boot or install, or a promise in the spec fails; **Medium** means a feature degrades or work is delayed. Each risk says what can go wrong, what we do about it, how we'll notice early, and which steps in [PROGRESS.md](../PROGRESS.md) act on it. The owner accepted every proposed mitigation at step 0.8; the step named builds it, or checks it first where the mitigation says so.

## Summary

| # | Risk | Likelihood | Impact | Main steps |
| --- | --- | --- | --- | --- |
| 1 | [KWin and Plasma change their internals every release](#1-kwin-and-plasma-change-their-internals-every-release) | High | High | 1.2, 3.1, 3.2, 4.1, 8.2 |
| 2 | [Secure Boot's move to the Microsoft UEFI CA 2023](#2-secure-boots-move-to-the-microsoft-uefi-ca-2023) | High | High | 1.3, 1.9, 6.11, 7.9, 7.10 |
| 3 | [BitLocker on Windows drives](#3-bitlocker-on-windows-drives) | High | High | 6.10, 7.8, 7.9, 9.6 |
| 4 | [TPM2 automatic unlock: recovery, enrolment and strength](#4-tpm2-automatic-unlock-recovery-enrolment-and-strength) | High | High | 5.5, 6.6, 8.1 |
| 5 | [Building the install ISO as a live ISO from a bootc image](#5-building-the-install-iso-as-a-live-iso-from-a-bootc-image) | Medium | High | 1.8, 6.10, 6.12, 9.5 |
| 6 | [Rollback doesn't roll back state](#6-rollback-doesnt-roll-back-state) | Medium | High | 5.1, 5.6, 5.7, 9.2 |
| 7 | [NVIDIA drivers under Secure Boot](#7-nvidia-drivers-under-secure-boot) | High | Medium | 1.11, 1.12, 5.10 |
| 8 | [Glass misses its frame-time and contrast budgets](#8-glass-misses-its-frame-time-and-contrast-budgets) | Medium | High | 3.3 to 3.11, 3.16, 3.17 |
| 9 | [Windows code signing for Lumen Setup](#9-windows-code-signing-for-lumen-setup) | High | Medium | 0.4, 7.9, 9.5 |
| 10 | [Codec patents and hardware video decoding](#10-codec-patents-and-hardware-video-decoding) | High | Medium | 1.14 |
| 11 | [Hibernation under kernel lockdown](#11-hibernation-under-kernel-lockdown) | High | Medium | 1.9, 5.17, 6.11 |
| 12 | [Licences of compatibility data](#12-licences-of-compatibility-data) | Medium | Medium | 1.15, 7.1, 7.2 |
| 13 | [CI capacity: disk, time, KVM and no GPU](#13-ci-capacity-disk-time-kvm-and-no-gpu) | High | Medium | 0.6, 1.5, 1.8, 1.9 |
| 14 | [Updates download too much](#14-updates-download-too-much) | Medium | Medium | 1.5, 5.5, 9.2 |
| 15 | [Flatpak apps don't match the Lumen look](#15-flatpak-apps-dont-match-the-lumen-look) | High | Medium | 2.4 to 2.7, 2.13, 2.14 |

Risks 2, 3 and 4 are linked: installing the 2023 Secure Boot certificates changes what the TPM measures, which makes both BitLocker and Lumen's disk unlock ask for their recovery keys.

## 1. KWin and Plasma change their internals every release

Likelihood **High** (it happens every release). Impact **High**.

**What can go wrong**

- lumen-glass (a fork of KWin's blur effect), the window decoration and lumen-shell link KWin, KDecoration and libplasma. None of them keep a stable ABI or API. A plugin built against another version fails to load or crashes KWin, and a KWin crash ends the session.
- Plasma has three feature releases a year, and Fedora ships each one as an update to its current release. A feature release usually changes the blur effect, so the fork needs rebasing three times a year, plus at each Fedora rebase. Interfaces do move: Plasma 6.3 replaced KDecoration2 with KDecoration3.
- Fedora's mirrors keep only the release-day build and the newest update. A plain `dnf install kwin-devel` in the `devel` stage can fetch a newer KWin than `base` ships, and the build still passes ([architecture 9.4](architecture.md#94-matching-the-base-image-exactly)).

**Mitigation**

- Exact-version `-devel` packages, with Koji as the fallback, and the guard check at the end of `devel` (architecture 9.4). Each plugin is built in a stage derived from the stage it ships in.
- **Step 3.1:** keep the fork easy to rebase. lumen-glass keeps the upstream effect's file layout, puts Lumen's own work in separate files, and records the KWin commit it forked from in `glass/UPSTREAM`. A rebase then means re-applying one known diff.
- **Step 3.1:** a weekly canary job builds lumen-glass, the decoration and lumen-shell against the KWin and Plasma in Fedora's `updates-testing` and Rawhide. Breakage then shows up weeks before Renovate's pull request for the new base digest. The canary is never shipped, so the build rule still holds for what users get.
- The Renovate pull request for a new Kinoite digest stays red until the rebase is done, so users stay on the previous base and untested code can't reach them. That also delays the rest of the base's updates, so each Plasma release month has rebase time planned in.
- If lumen-glass fails to load, KWin runs without it. A session test (step 3.15) checks that the shell is still usable with the effect turned off.
- Upstream what we can. Generic hooks, such as support for `ext_background_effect_manager_v1`, belong in KWin, so the fork shrinks over time.

**Early warning:** the canary job turns red; KDE's beta of each Plasma release, a few weeks before it ships.

**Steps:** 1.2, 2.8, 3.1, 3.2, 3.15, 4.1, 8.2.

## 2. Secure Boot's move to the Microsoft UEFI CA 2023

Likelihood **High** (it's happening now). Impact **High**.

**What can go wrong**

- Microsoft's 2011 UEFI CA, which signs shim (the first stage of every Secure Boot Linux boot), and its 2011 KEK expired in June 2026. New shims carry the 2023 CA's signature. Firmware without the 2023 CA in its `db` won't boot a shim signed only with it, and that includes the Lumen install USB. The user then can't even reach the live hardware report that was meant to warn them.
- Some new PCs ship with only the 2023 CA, so a shim signed only with the 2011 CA won't boot on them. A shim signed with both helps, but not all firmware reads more than one signature.
- Installing the 2023 certificates changes the Secure Boot variables, and so TPM PCR 7. Lumen's TPM unlock ([risk 4](#4-tpm2-automatic-unlock-recovery-enrolment-and-strength)) and Windows' BitLocker ([risk 3](#3-bitlocker-on-windows-drives)) then ask for their recovery keys.
- Firmware without the 2023 KEK can't accept new revocations (`dbx` updates), which are now signed with it.
- On an image-based system, shim and GRUB live in the EFI system partition, outside the image. Fedora's atomic desktops update them with bootupd at boot (since Fedora 41). If that doesn't run on our image, users keep an old shim.
- Graphics cards whose option ROMs are signed with the 2011 CA show a picture at boot only while the 2011 CA stays in `db`.

**Mitigation**

- Check before anything changes. Lumen Setup for Windows reads the firmware's `db`. If the 2023 CA is missing, it tells the user to install Windows Update's Secure Boot certificate update, or the PC maker's firmware update, *before* going further (step 7.9). The install guide says the same for people who don't use Setup (9.3).
- On installed systems, lumen-hwd reads `db` and `KEK` from the EFI variables, and a Health check reports a missing 2023 CA (6.11, 7.10). fwupd 2.0 and the LVFS deliver the KEK and `db` updates on Linux; lumen-updated offers them like any firmware update, with consent, and first warns about the recovery-key prompt (risk 4).
- At step 1.9, and at every Fedora rebase, record which signatures the shim on our image and ISO carries (for example with `sbverify --list`). The boot test runs OVMF with three key sets: 2011 only, both, and 2023 only (variable stores made with virt-firmware's `virt-fw-vars`).
- Confirm that bootupd's automatic update runs on our image (step 1.3), and show the installed shim version in `lumen hw report` (5.10).
- Lumen never removes the 2011 CA from `db` and never revokes it.

**Early warning:** a new Fedora shim build; boot-test failures with the 2011-only or 2023-only key set; a hardware-lab PC that won't boot the ISO.

**Steps:** 1.3, 1.8, 1.9, 5.4, 5.10, 6.11, 7.9, 7.10, 9.3.

## 3. BitLocker on Windows drives

Likelihood **High**. Impact **High** (the user can lose Windows and its files).

**What can go wrong**

- Windows 11 24H2 turns on device encryption (BitLocker) by default on clean installs set up with a Microsoft account, Home edition included. Many users don't know their drive is encrypted. The recovery key is saved to their Microsoft account; with a local account it may not be saved anywhere.
- Linux can't resize a BitLocker volume (ADR 0001), so the space for Lumen must be made from inside Windows. Windows can only shrink a volume as far as its unmovable files (page file, restore points) allow.
- Installing Lumen alongside Windows can change what the PC measures at boot: a new first entry in the boot order, the Windows boot manager started from GRUB (chainloading), or the certificate update of [risk 2](#2-secure-boots-move-to-the-microsoft-uefi-ca-2023). BitLocker then asks for the recovery key. Without it, Windows and everything on it is gone.
- Welcome's import has to read the Windows drive. That needs the recovery key or a BitLocker password, because the TPM only unlocks the drive for Windows itself. `cryptsetup` can open a BitLocker volume but not change it, and writing to a Windows drive that Fast Startup left hibernated corrupts it.

**Mitigation**

- Lumen Setup for Windows detects BitLocker, shows where the recovery key is (the Microsoft account's recovery key page, or `manage-bde -protectors -get`), and doesn't continue with "alongside Windows" until the user confirms the key is saved somewhere off the PC (step 7.9).
- **Step 7.9:** Setup offers to suspend BitLocker for the next two Windows restarts (`Suspend-BitLocker -RebootCount 2`), as Microsoft advises before firmware updates. This lowers protection for a short time, so it gets its own confirm button and a plain explanation, and is never done silently.
- Setup shrinks Windows with Windows' own tools, and says how much space it could free before the user commits.
- **Step 6.10:** Lumen's boot menu starts Windows by asking the firmware to boot the Windows boot manager next (the EFI `BootNext` variable), not by chainloading it from GRUB. The dual-boot tests check on a real BitLocker PC that this avoids the recovery prompt.
- The installer never resizes, formats or writes a BitLocker volume; "Install alongside Windows" uses only free space (6.10). Welcome's import opens the Windows drive read-only with the recovery key the user types, and refuses a hibernated drive with the Fast Startup explanation (7.8).
- Test on a real Windows 11 install with device encryption on, not only in a VM (6.13, 7.12, 9.6).

**Early warning:** any recovery-key prompt during a hardware-lab dual-boot test.

**Steps:** 6.10, 6.13, 7.8, 7.9, 7.10, 7.12, 9.6.

## 4. TPM2 automatic unlock: recovery, enrolment and strength

Likelihood **High**. Impact **High** (lost keys mean lost data).

**What can go wrong**

- The spec binds the LUKS2 unlock to PCR 7, the Secure Boot state. PCR 7 changes when the Secure Boot certificates or revocation list change (risk 2, and the `dbx` updates fwupd delivers), when Secure Boot is turned off or on, and after some firmware updates. The TPM then won't release the key, and the user must type the disk passphrase or the recovery key they saw once at setup. Many won't have either to hand.
- A user who has lost both loses everything on the disk, and nobody can help them.
- Enrolment needs root before any user account exists ([Q8](architecture.md#8-spec-problems-and-open-questions)).
- PCR 7 records who signed the boot chain, not which system is booting. Lumen boots Fedora's signed shim, GRUB and kernel, so any other Fedora-signed system, such as a Fedora live USB, produces the same PCR 7 and can ask the TPM for the key. Without a PIN, someone who knows this can unlock a stolen laptop. The spec's promise that "a stolen laptop reveals nothing" doesn't hold in that case ([Q17](#questions-for-the-owner)).

**Mitigation**

- Welcome makes the recovery key hard to lose: it shows the key, lets the user save it to a USB drive, print it or scan it as a QR code, and asks them to type back part of it (step 6.6).
- Before lumen-updated applies a Secure Boot or firmware update that changes PCR 7, it says plainly that the next start will ask for the recovery key once. After that start, the TPM is enrolled again (`systemd-cryptenroll`), so later starts are automatic again (5.5, 6.6).
- **Step 6.6:** systemd-pcrlock predicts the new PCR values before the restart, so the prompt isn't needed at all ([Q17](#questions-for-the-owner)). The warning above stays for changes pcrlock can't predict.
- A Health check notices when unlock has fallen back to the passphrase and offers to enrol again (5.8).
- Strength ([Q17](#questions-for-the-owner), decided at step 0.8): no PIN by default, but the unlock is also bound to Lumen's own boot measurements, predicted with systemd-pcrlock. If step 6.6 can't make that reliable, a PIN becomes the default instead. Either way, measure the volume key into a PCR (systemd's `tpm2-measure-pcr=`), which blocks attacks that swap in a fake root partition.

**Early warning:** recovery prompts in the update test after a `db` update (OVMF with swtpm in CI).

**Steps:** 5.5, 5.8, 6.6, 8.1.

## 5. Building the install ISO as a live ISO from a bootc image

Likelihood **Medium**. Impact **High** (no way to install).

**What can go wrong**

- ADR 0002 relies on a newer path: Titanoboa turns the Lumen image into a live ISO, which then starts Anaconda WebUI. Universal Blue uses it, but one of its own ISO builds (Bluefin LTS) broke because Anaconda didn't work on that base image. Handing the image to Anaconda from the ISO, offline, is unproven for us.
- Anaconda WebUI's partitioning must offer "alongside Windows" using free space only ([risk 3](#3-bitlocker-on-windows-drives)), plus erase-disk with LUKS2. Its modes may not match the spec's three install modes.
- The ISO holds a live system and a copy of the image, so it will exceed GitHub's 2 GiB limit per release file ([Q15](architecture.md#8-spec-problems-and-open-questions)). CI has to build it within the runner's disk and time limits ([risk 13](#13-ci-capacity-disk-time-kvm-and-no-gpu)).
- The ISO's shim has to boot on old and new firmware ([risk 2](#2-secure-boots-move-to-the-microsoft-uefi-ca-2023)).

**Mitigation**

- Step 1.8 builds it early, before Phase 2 builds on it, and records the tool in an ADR. Titanoboa is pinned by digest and updated through Renovate.
- The fallback stays ready: bootc-image-builder's `anaconda-iso` with a partial kickstart. Dropping the live hardware report then needs the owner's approval (ADR 0002).
- From step 1.8 on, CI installs from the ISO in a VM in each install mode, rather than waiting for Phase 6.
- The download host is chosen at step 9.5 (Q15). Until then CI keeps test ISOs as short-lived workflow artifacts.

**Early warning:** the first build at step 1.8; issues in Universal Blue's ISO repositories.

**Steps:** 1.8, 1.9, 6.10, 6.12, 9.5.

## 6. Rollback doesn't roll back state

Likelihood **Medium**. Impact **High** (the "never breaks" promise depends on rollback).

**What can go wrong**

- `bootc rollback` brings back the previous `/usr` and the image's `/etc` defaults, but not `/var`, `/home` or local changes in `/etc`. A newer Plasma or KDE Frameworks migrates the user's config files forward, and the older one may not read them. A newer Lumen service may rewrite its state in `/var/lib/lumen/` in a format the older one doesn't know.
- A Fedora rebase, twice a year, is the biggest jump: new Plasma, Qt, Mesa and kernel at once.
- The `/etc` 3-way merge keeps a local copy of a file even when the new image needs it changed.
- greenboot was written for rpm-ostree systems; whether it works with bootc is checked at step 5.6.

**Mitigation**

- **Step 5.1:** Lumen's state files carry a format version. Each release reads the previous release's format, and a service never deletes data it doesn't understand. Each service has a unit test for this.
- The update test (step 9.2) logs into a real session on the new version before rolling back, so the config migrations actually run. It then logs into the old version and runs the session test, not just a boot check.
- Keep image changes out of `/etc` wherever possible (ADR 0002); the image lint lists every file the image ships in `/etc`.
- Snapper's hourly `/home` snapshots give users a way back for config files ("Previous versions", step 6.9).
- A Fedora rebase spends 4 weeks in beta first ([Q14](architecture.md#8-spec-problems-and-open-questions)).

**Steps:** 5.1, 5.6, 5.7, 6.9, 9.1, 9.2.

## 7. NVIDIA drivers under Secure Boot

Likelihood **High**. Impact **Medium**.

**What can go wrong**

- NVIDIA's driver is outside the kernel, so CI builds its modules with akmods against `base`'s exact kernel and signs them with Lumen's key. A new kernel can break that build, which holds the NVIDIA image back.
- With Secure Boot on, the kernel only loads the modules once the user has enrolled Lumen's key as a MOK: a one-time blue MokManager screen at the next start, with a password. It's easy to miss or get wrong. The driver then doesn't load, and the user sees a slow desktop or none.
- A leaked module key lets anyone sign kernel modules that every enrolled machine will load. Changing the key means every user enrols again.
- NVIDIA's 580 driver branch is the last for Maxwell, Pascal and Volta cards, so older cards need a legacy driver or the open nouveau driver.
- A gamer with an NVIDIA card has no image with both ([Q13](architecture.md#8-spec-problems-and-open-questions)).

**Mitigation**

- lumen-hwd explains enrolment before the switch, with a picture of the screen and the password to type (steps 1.12, 5.10). After the restart it checks that the key is enrolled (`mokutil`) and the driver loaded. If not, it explains what happened and offers to try again.
- The desktop stays usable on the open drivers (nouveau and NVK) until the NVIDIA driver loads, never a black screen. A session test boots the NVIDIA image with no MOK enrolled and checks that it reaches the desktop.
- The NVIDIA variant can fail on its own: its tag stays on the last good build while the other images move on, and CI opens an issue. That build misses security updates, so a failure lasting more than a week goes to the owner (step 9.1).
- The module key lives only in a protected GitHub environment for `main`, with an offline backup kept by the owner and a written procedure for replacing it (step 1.11).
- Universal Blue's signed-akmods pipeline is prior art; reuse its approach where it fits.
- `hardware.json` marks cards older than Turing amber.

**Steps:** 1.11, 1.12, 5.10, 6.11, 9.1.

## 8. Glass misses its frame-time and contrast budgets

Likelihood **Medium**. Impact **High** (glass is the design's centrepiece).

**What can go wrong**

- The spec asks for 60 fps with 8 glass surfaces on Iris Xe-class graphics, an idle GPU near zero, and 4.5:1 text contrast on any backdrop. Refraction, dispersion and adaptive tint cost GPU time per pixel, and high-resolution, high-refresh laptop panels multiply that cost.
- Text over glass can fall below 4.5:1 over busy, bright or moving backdrops such as video.
- CI has no GPU. The glass tests render on llvmpipe, which says nothing about speed, so real numbers only arrive at step 3.17, late in Phase 3. The owner's PC is a desktop; Iris Xe class means testing on a laptop.

**Mitigation**

- Measure early: time each pass on real Intel laptop graphics right after the shared blur exists (step 3.3), before the shader work, so each later step knows its share of the budget.
- The shared quarter-resolution blur, computed once per frame, and damage-aware caching (3.3, 3.4) are the main savings. The Lite and Solid tiers and the first-boot benchmark (3.10, 3.11) cover weaker GPUs.
- Contrast is computed, not judged by eye. Adaptive tint raises the tint until 4.5:1 is met, and the reference scenes (3.15, 3.16) include video and busy backdrops.
- Reduce Transparency and the Solid tier always give an opaque look that meets the contrast rule.
- 👤 The real-hardware check needs a laptop with Iris Xe-class graphics, borrowed or bought, before step 3.17.

**Steps:** 3.3 to 3.11, 3.15 to 3.17.

## 9. Windows code signing for Lumen Setup

Likelihood **High**. Impact **Medium** (a switcher's first impression).

**What can go wrong**

- An unsigned Lumen Setup gets SmartScreen's "Windows protected your PC" warning. With Smart App Control on, Windows blocks unsigned programs without a good reputation outright.
- Code-signing keys must now be kept in hardware (a token or an HSM), so CI can't hold a plain key file and has to sign through a cloud signing service.
- Certificates issued since March 2026 last at most 460 days, so renewal and identity checks come every year.
- Reputation is earned over time and tied to the signing identity; Microsoft says changing certificates affects it. A new project starts with none.
- A program that shrinks partitions and changes boot settings can trip antivirus heuristics.

**Mitigation**

The owner chooses the route at step 7.9. The licence chosen at step 0.4 decides whether the first one is open to us.

| Route | Cost | Conditions |
| --- | --- | --- |
| SignPath Foundation | Free for open-source projects | Every component under an OSI-approved licence, no commercial dual licensing; builds fully automated from the public repository; a code-signing policy published on the project's site. The certificate names SignPath Foundation as the publisher |
| Microsoft Artifact Signing (formerly Trusted Signing) | Monthly fee | Cloud signing that suits GitHub Actions. Onboarding for individuals has been limited by country; check eligibility at 7.9 |
| Commercial certificate in a cloud HSM | Yearly fee | Works for anyone; yearly renewal |

- Keep one signing identity once chosen, and sign every published build, betas included, so reputation builds before v0.1.
- Submit each release to Microsoft's malware analysis portal to clear false positives.
- Setup asks for administrator rights only for the steps that change Windows, each with its own confirm button (spec).
- Never publish an unsigned build. CI builds unsigned ones for tests only.

**Steps:** 0.4, 7.9, 9.5.

## 10. Codec patents and hardware video decoding

Likelihood **High**. Impact **Medium** for users; the legal exposure is for the owner to judge with advice.

**What can go wrong**

- Fedora leaves out patent-encumbered codecs (H.264, HEVC and others) and builds Mesa without H.264 and HEVC hardware decoding for AMD. RPM Fusion's `mesa-va-drivers-freeworld` puts it back. Without it, AMD laptops decode video on the CPU, which costs battery, and some files won't play in host apps.
- Fedora can't ship Cisco's OpenH264 inside its atomic images, because Cisco's patent cover applies to copies downloaded from Cisco. Kinoite carries a `noopenh264` placeholder instead, and Lumen inherits the same limit.
- Shipping RPM Fusion's codecs in the image makes Lumen the distributor of patent-encumbered software. Whether that is acceptable depends on where and how the project is run. That is a legal question, not an engineering one (step 1.14, 👤).
- If the image uses freeworld Mesa, it must match `base`'s Mesa exactly (architecture 9.4). RPM Fusion's build can trail a Fedora Mesa update, which would hold the image until it catches up.

**Mitigation**

- Flatpak apps (browsers, video players, editors) get codecs from Flathub's runtime extensions whatever the image does, and the Store installs Flatpaks, so most video plays either way. Step 1.14 also checks whether Flatpak apps get hardware decoding through Flathub's graphics drivers.
- Step 1.14 writes the options and their legal trade-offs as an ADR, and the owner chooses: Fedora's codecs only; RPM Fusion's codecs in the image, as several Fedora-based images do; or a separate codecs variant.
- If freeworld Mesa is chosen, the exact-version guard covers it, and CI holds a Mesa update until the matching freeworld build exists.
- The hardware report and the FAQ say what plays out of the box (6.12, 9.4).

**Steps:** 1.14, 6.12, 9.4.

## 11. Hibernation under kernel lockdown

Likelihood **High** (it's how lockdown works). Impact **Medium**.

**What can go wrong**

- With Secure Boot on, kernel lockdown blocks hibernation, because the kernel can't verify the resume image. Lumen keeps lockdown on (ADR 0001), so there's no hibernation and no suspend-then-hibernate. Laptops whose sleep drains the battery overnight have no fallback, and Windows users expect hibernate.
- No upstream fix is close. A July 2026 patch to allow hibernation under lockdown was withdrawn by its author the same day, and a lockdown reviewer replied that its threat model includes root, so a plain bypass won't be accepted. Two other designs (encrypted snapshots, July 2026; a TPM-backed one, October 2026) are early requests for comment.
- Fedora kernels from 6.12 shipped with lockdown off under Secure Boot (CVE-2025-1272). If ours does, that's a security gap, and it would also make hibernation look as if it works.
- Even where lockdown allows it, hibernation needs disk swap at least as large as RAM. Fedora uses only zram.

**Mitigation**

- The spec already promises suspend, tuned power profiles and a safe shutdown at critical battery, and offers hibernation only where lockdown allows it (5.17).
- Step 1.9 records the lockdown state and `/sys/power/state` on our image under Secure Boot. If lockdown is off, step 8.1 fixes it.
- `hardware.json` records how much battery each model loses asleep, and the hardware report warns about laptops that drain badly (6.11).
- Track the upstream designs. When a verified method reaches Fedora's kernel, an ADR adds a swap file and turns hibernation on.

**Steps:** 1.9, 5.17, 6.11, 8.1.

## 12. Licences of compatibility data

Likelihood **Medium**. Impact **Medium** (data we can't publish has to be removed).

**What can go wrong**

- ProtonDB's report exports are ODbL 1.0, with DbCL for the contents. ODbL is share-alike, so the Lumen database that includes them must be published under ODbL, with attribution wherever its ratings are shown. The spec already plans this, but every other source then has to be compatible with ODbL.
- Some sources can't be mixed in. PCGamingWiki's content is CC BY-NC-SA 3.0, and its non-commercial term clashes with ODbL. WineHQ AppDB's terms haven't been checked. AreWeAntiCheatYet is listed as MIT, but its LICENSE file hasn't been confirmed. Copying install scripts from Bottles' or Lutris' installer collections would bring their licences in.
- Icons, screenshots and descriptions on store pages belong to their publishers.
- Contributed entries need clear terms, or the database can't be published.
- If ProtonDB's exports stop being updated, game ratings go stale.

**Mitigation**

- Every entry lists its sources (spec). **Step 1.15:** `compat/SOURCES.md` lists each source with its confirmed licence, and a CI check rejects an entry that cites a source not on that list.
- Write our own recipes. Never copy another project's scripts or text, and never scrape (spec).
- Confirm at step 7.1: that ProtonDB's export is still updated, AreWeAntiCheatYet's LICENSE file, and WineHQ AppDB's terms (ask WineHQ if they're unclear).
- Take only facts from stores (names, Steam App IDs). Icons and descriptions for alternatives come from Flathub's AppStream data under its own metadata licences.
- Contributions to `compat/` carry a sign-off (DCO) offering them under ODbL; set up with the licence at step 0.4.
- The Store and the "Open Windows app" dialog show an attribution screen (7.5, 7.7).

**Steps:** 0.4, 1.15, 7.1, 7.2, 7.5, 7.7.

## 13. CI capacity: disk, time, KVM and no GPU

Likelihood **High**. Impact **Medium** (slow or blocked work).

**What can go wrong**

- A standard runner for public repositories has 4 CPUs, 16 GB of RAM and 14 GB of guaranteed disk; about 20 GB is free in practice. Kinoite is several gigabytes compressed and far larger unpacked. The build stages, the variants, a qcow2 and a live ISO won't fit in one job.
- A job stops after 6 hours.
- The boot tests need KVM. GitHub offers it on its Linux runners (a udev rule makes `/dev/kvm` usable), but documents it for Android emulators; step 1.9 confirms it works for QEMU. The owner's PC has no `/dev/kvm` in WSL, so there is no local fallback.
- No GPU ([risk 8](#8-glass-misses-its-frame-time-and-contrast-budgets)).

**Mitigation**

- Free disk first by removing preinstalled toolchains, and put container storage on the runner's second disk (step 1.5).
- One job per image and per disk image. Jobs pass images through the registry under short-lived CI tags, never channel tags.
- Cache Podman layers so unchanged stages aren't rebuilt.
- Session and glass tests run as containers, not VMs (architecture 9.9).
- If hosted runners can't cope, a self-hosted runner needs a Linux machine with KVM. That costs money, so it's the owner's call.

**Steps:** 0.6, 1.5, 1.8, 1.9.

## 14. Updates download too much

Likelihood **Medium**. Impact **Medium**.

**What can go wrong**

- bootc downloads the image layers that changed. One Containerfile step that installs all of Lumen's packages makes one large layer that changes on every build, so every update downloads all of it even if one file changed. On slow or metered connections that breaks the promise of updates you don't notice.
- A Fedora rebase or a new base digest changes many packages at once.

**Mitigation**

- Re-chunk the image after the build, so each layer holds a stable group of packages (rpm-ostree's chunked image build, or the re-chunker Universal Blue uses). Step 1.5c picks the tool.
- **Step 1.5c:** CI measures the download from the current `stable` (until there is one, from the previous `dev`) to each candidate and fails above a budget set at that step.
- lumen-updated's metered-network and battery rules (step 5.5).

**Steps:** 1.5, 5.5, 9.2.

## 15. Flatpak apps don't match the Lumen look

Likelihood **High**. Impact **Medium**.

**What can go wrong**

- Flatpak apps can't see the host's theme files. They get light or dark, accent and contrast through the Settings portal, and nothing more (architecture 4.3).
- GTK 4 apps that use libadwaita don't load themes, by design. They read only `~/.config/gtk-4.0/gtk.css`, which a Flatpak can't see without a filesystem override.
- GTK 3 Flatpaks need the theme published on Flathub as an extension (`org.gtk.Gtk3theme.Lumen`), which Lumen then maintains there.
- Qt Flatpaks use the KDE runtime's style. Kvantum needs its own Flatpak extension plus the theme.
- So Phase 2's acceptance, "all four app types match in both modes", may be out of reach for Flatpak apps without overrides Lumen mustn't set behind the user's back.

**Mitigation**

- Phase 2's acceptance defines "match" as a baseline every app gets: light or dark, accent, contrast and fonts. Lumen's apps and host apps get the full style; GTK 3 Flatpaks get it through a Flathub theme extension; libadwaita apps keep their own shapes ([Q16](#questions-for-the-owner)).
- Never add filesystem overrides to Flatpak apps silently (sandbox rule).
- The visual test at step 2.13 includes a Flatpak app of each toolkit.

**Steps:** 2.4 to 2.7, 2.13, 2.14.

## Watch list

Smaller risks, or ones already covered by a step. They move into the top 15 if they grow.

| Risk | What we do | Steps |
| --- | --- | --- |
| Camera and microphone indicators miss programs that open the devices directly, bypassing PipeWire: host programs, and Flatpaks with `--device=all` (common for browsers and Steam) | Watch open handles on the video and audio devices as well as PipeWire streams; the Store flags `--device=all` as a risky permission | 4.3, 6.2 |
| Ratings go stale as Wine and Proton change. Bottles is a small project, and `bottles-cli` may not apply every recipe field | The nightly compatibility job and the spec's 6-month rule; check `bottles-cli` before building on it | 1.16, 7.5 |
| Fedora drops 32-bit packages, which Steam and parts of Wine need on the host. A 2025 proposal to drop them was withdrawn | Fall back to Steam's Flatpak and Wine's WoW64 mode | 1.10 |
| Losing a signing key or the GitHub account: one person holds every key | Protected environment for `main`, hardware-key 2FA, offline key backups, a written procedure to replace each key (architecture 9.7); consider keyless Sigstore signing for images at step 1.6 | 1.6, 8.2 |
| Fedora's six-month cycle: each rebase moves KWin, Plasma, Qt, Mesa and the kernel at once, and each release is supported for about 13 months | Covered by risks 1 and 6, and Q14 | 9.1 |
| Kinoite's dated builds expire from quay.io four weeks after they are built (label `quay.expires-after: 4w`, found at step 0.7), so a pinned base digest stops resolving and CI can no longer build an older commit | Bump the pin at least every two weeks (decided at step 0.8), by Renovate or a scheduled job, from step 1.5 instead of 8.2; and copy each pinned base into Lumen's own registry on ghcr.io, so old builds stay reproducible ([versions](versions.md#things-to-know)) | 1.2, 1.5, 8.2 |

Not ranked, because they aren't technical: one owner's time across about 170 steps, and the business gaps in the gap list (for example no shop preinstalls).

## Questions for the owner

Decided at step 0.8: the owner accepted both proposals, with option (b) for Q17 and (a) as its fallback ([ADR 0004](decisions/0004-phase-0-review.md)). They continue the numbering of [architecture section 8](architecture.md#8-spec-problems-and-open-questions).

| # | Question | Decision | Steps |
| --- | --- | --- | --- |
| Q16 | Phase 2's acceptance says all four app types "match in both modes". Flatpak apps, libadwaita ones above all, can't take the full theme without overrides ([risk 15](#15-flatpak-apps-dont-match-the-lumen-look)). What does "match" mean? | Every app gets the same light or dark, accent, contrast and fonts. Lumen's apps and host apps get the full style, GTK 3 Flatpaks get it through a Flathub theme extension, and libadwaita apps keep their own shapes. The Phase 2 acceptance line in the spec now says so | 2.1 to 2.14 |
| Q17 | The spec unlocks the disk with the TPM bound to PCR 7, with an optional PIN, and promises that "a stolen laptop reveals nothing". Without a PIN, any Fedora-signed system booted on the stolen laptop gets the same PCR 7 and can ask the TPM for the key ([risk 4](#4-tpm2-automatic-unlock-recovery-enrolment-and-strength)). Which do you want? | (b): no PIN, but also bind to measurements of Lumen's own boot files, predicted with systemd-pcrlock so updates don't prompt for the key. This is closer to how Windows behaves. If step 6.6 can't make it reliable, (a): a PIN by default, with automatic unlock as the opt-in. Measure the volume key in both cases. The spec's security table and Welcome step now say so | 6.6 |

## Sources

Checked on 2026-10-27.

- Secure Boot certificates: [Red Hat on the 2026 expiry](https://www.redhat.com/en/blog/expiration-secure-boot-signing-certificates-2026); [Rocky Linux on the CA and KEK change](https://rockylinux.org/news/2026-06-02-secure-boot-ca-kek-transition); [fwupd's `uefi-db` documentation](https://sources.debian.org/src/fwupd/2.0.20-1/docs/uefi-db.md); [Ubuntu on the CA rotation](https://discourse.ubuntu.com/t/microsoft-uefi-ca-rotation-what-it-means-for-ubuntu-users-and-vendors/82652); [Google Cloud on KEK and `db` updates](https://docs.cloud.google.com/compute/docs/security/ms-secure-boot-certificates-update); [bootupd on Fedora 41 atomic desktops](https://fedoramagazine.org/whats-new-for-fedora-atomic-desktops-in-fedora-41/).
- Hibernation: [the July 2026 opt-in patch](https://kernsec.org/pipermail/linux-security-module-archive/2026-July/058515.html); [Phoronix on the later designs](https://phoronix.com/news/Linux-Hibernation-With-Lockdown).
- BitLocker: [Windows Latest on device encryption by default in 24H2](https://windowslatest.com/2024/05/08/microsoft-confirms-windows-11-24h2-turns-on-device-encryption-by-default); [Elcomsoft on BitLocker by default](https://blog.elcomsoft.com/2025/05/forensic-implications-of-bitlocker-by-default-in-windows-11-24h2).
- TPM and PCR 7: [Fedora discussion of PCR choices on atomic desktops](https://discussion.fedoraproject.org/t/silverblue-tpm-luks-and-higher-pcrs/160617); [systemd-devel on measuring the volume key](https://lists.freedesktop.org/archives/systemd-devel/2025-March/051256.html).
- Code signing: [DigiCert on the 460-day limit](https://knowledge.digicert.com/alerts/code-signing-certificates-459-day-validity); [Microsoft on SmartScreen reputation](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation); [Smart App Control](https://textslashplain.com/2026/04/28/smart-app-control/); [SignPath Foundation's terms](https://signpath.org/terms); [Artifact Signing pricing](https://azure.microsoft.com/pricing/details/artifact-signing/).
- Codecs: [Fedora's OpenH264 page](https://fedoraproject.org/wiki/OpenH264); [RPM Fusion's `mesa-va-drivers-freeworld` for Fedora 44](https://centos.ruhr-uni-bochum.de/rpmfusion/free/fedora/updates/44/x86_64/repoview/mesa-va-drivers-freeworld.html) (mirror).
- Compatibility data: [ProtonDB's ODbL exports](https://protondb.com/news/report-exports-odbl); [AreWeAntiCheatYet](https://github.com/AreWeAntiCheatYet/AreWeAntiCheatYet); [PCGamingWiki's licence](https://en.wikipedia.org/wiki/PCGamingWiki).
- CI: [GitHub-hosted runner hardware](https://docs.github.com/en/actions/reference/runners/github-hosted-runners); [KVM on GitHub's Linux runners](https://github.blog/changelog/2023-02-23-hardware-accelerated-android-virtualization-on-actions-windows-and-linux-larger-hosted-runners).
- Live ISO: [Titanoboa](https://github.com/ublue-os/titanoboa).
