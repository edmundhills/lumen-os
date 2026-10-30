<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0014. Install the ISO's own copy of the image with Anaconda's bootc command

- Status: **Accepted** (2026-10-30), at step 1.8c.
- Deciders: lead engineer (Claude). The owner reviews it at the Phase 1 acceptance (step 1.17), and is asked about one point now (Consequences).

## Context

The install ISO boots a Lumen live session ([ADR 0012](0012-install-iso.md)), whose installer must put Lumen on the disk with no network, so that download speed can't make the install slow (spec: under 10 minutes). The installed system must then follow `ghcr.io/edmundhills/lumen:dev` and check Lumen's signature from its first update ([ADR 0008](0008-image-signing.md)). What the tools do, read in their source on 2026-10-30:

- **Anaconda's `bootc` kickstart command** (pykickstart's `F43_Bootc`, at `1568c86`) takes `--source-imgref` with a transport, `--target-imgref` without one, and `--stateroot`, which defaults to `default`. Anaconda 44.35's `DeployBootcTask` (`pyanaconda/modules/payloads/payload/rpm_ostree/installation.py`, unchanged since 44.30 except for an unrelated fix) runs `bootc install to-filesystem --bootloader=grub --karg=… --stateroot=… --source-imgref=… --target-imgref=…` on the mounted target, after emptying it. It accepts only `/`, `/boot`, `/boot/efi`, `/home` and `/var` as mount points, which Lumen's install profile (`installer/anaconda/lumen.conf`) keeps to. Its kernel arguments include a kickstart's `bootloader --append`.
- **In a live session Anaconda reads one kickstart**, `/usr/share/anaconda/interactive-defaults.ks`: with `--liveinst`, `find_kickstart` ignores any kickstart given on the command line or on a disk labelled `OEMDRV`. A `bootc` command there picks Anaconda's `RPM_OSTREE` payload with a bootc source, ahead of copying the live system (`PayloadFactory.get_type_for_kickstart`). Anaconda's own copy of the file has no commands and is marked deprecated, with nothing in Anaconda's configuration files to replace it for this. Anaconda WebUI (releases 88 to 90) treats every payload but DNF alike: it hides the software selection.
- **bootc 1.17.1, run from the live system**, reads its install settings from the running system (`/usr/lib/bootc/install/*.toml`), which is the Lumen image, so Lumen's `enforce-container-sigpolicy = true` applies and the target is recorded as `ostree-image-signed:docker://<target>`. The source passes the trust policy because Lumen's `policy.json` accepts the `containers-storage` transport. Without `/ostree/repo`, which the live stage removes (ADR 0012), bootc reads whether the system has SELinux from `/etc/selinux/config`. When it lacks the right to write labels the policy doesn't know (`mac_admin`), it runs itself again with `/usr/bin/ostree`'s label, which gives it `install_t`.
- **image-builder 88's `--bootc-installer-payload-ref`** adds an `org.osbuild.skopeo` stage at the end of `generic-iso`'s `os-tree` pipeline, which copies an image from the build machine's container storage into the tree's `/var/lib/containers/storage`, under the name given (`pkg/manifest/os_from_container.go`, osbuild's `stages/org.osbuild.skopeo`). The SELinux stage Lumen adds after it labels those files too.
- **The live session's root is an overlay file system.** On one, Podman's storage library can use its overlay driver only through `fuse-overlayfs`, which it then picks by itself (containers/storage `drivers/overlay/overlay.go`). The Lumen image has `fuse-overlayfs`, from Kinoite (the package names in `dev`'s layers).
- **liveinst switches SELinux to permissive while Anaconda runs.** Fedora's `liveinst`, which the live desktop's installer icon starts, runs `setenforce 0` before Anaconda and sets the old mode back afterwards. It has done so since at least 2010 (`data/liveinst/liveinst` in Anaconda's history). The installed system is enforcing either way.
- **Other ways, not taken:** Bazzite's live ISO installs with `ostreecontainer --transport=containers-storage` and rewrites the origin file to the signed transport in `%post`, because Anaconda's `ostreecontainer` ignores bootc's install settings (ADR 0008). image-builder's own `bootc-installer` image type makes an Anaconda boot ISO with no live session, which ADR 0002 keeps as the fallback only.

## Decision

1. **The installer's kickstart is `installer/anaconda/interactive-defaults.ks`**, which the live stage installs in place of Anaconda's. It has one command:

   `bootc --source-imgref=containers-storage:ghcr.io/edmundhills/lumen:dev --target-imgref=ghcr.io/edmundhills/lumen:dev`

   The name in the container storage is the name the system then follows, so one name serves both, and `image/iso.py install-image` reads it from the kickstart for the workflow and the checks.
2. **The ISO carries the build its live system is made from.** The `iso` workflow pulls the build by digest, checking its signature with Lumen's trust policy (ADR 0012), names it as the kickstart does, and `image/make-iso.sh` passes it to image-builder with `--bootc-installer-payload-ref`. Its manifest is copied byte for byte, so the installed system records the digest the build has on ghcr.io, and its first update downloads only what changed.
3. **Checks:**
   - `image/live/check-live.sh`: the kickstart is installed, the parser Anaconda uses (pykickstart) reads a `bootc` command from it that installs from container storage under the name it then follows, no other source is set, `bootc install print-configuration` run in the live system says `enforce-container-sigpolicy`, and `bootc`, `skopeo` and `fuse-overlayfs` are there.
   - `image/check-iso.sh`: the squashfs has the kickstart, and its container storage holds the image the kickstart names, whose manifest has the signed build's digest and version, with all its layers (`image/iso.py payload`).
   - **The install test** (`tests/boot/install_iso.py`, in the `boot-iso` workflow after the boot test) installs from the ISO onto an empty 64 GiB disk in the VM the boot test uses, which has no network card, then starts the installed system with Secure Boot and checks it: SELinux enforcing, `bootc status` and the origin file say it follows the kickstart's name with signatures checked, it runs the ISO's copy (digest and version), and its root is Btrfs with `compress=zstd:1`. It records `bootc status`, the kernel arguments, the mounts, the home snapshots unit, kernel lockdown, the sleep states, failed units and SELinux denials, without judging them; step 1.9 judges those.
4. **How the test drives the installer.** It runs `liveinst`, as the desktop does, with Anaconda's text interface in place of WebUI (`LIVECMD='anaconda --liveinst --text'`), so it goes through the same launcher, kickstart and payload as a person does. Because Anaconda in a live session reads only the installer's kickstart, the test adds its own settings to the end of that file in the VM, after the `bootc` line, which it leaves alone: the language, the keyboard, the time zone, the VM's disk, emptied and laid out by Lumen's install profile (`autopart`, without encryption), and a root password. Anaconda then stops at its summary, where the test checks that nothing is left to fill in and presses `b`. Anaconda's logs go to the VM's second serial port, which the test keeps.

## Consequences

- Installing needs no network, and the installed system checks Lumen's signature from its first update, with no `%post` fix-up.
- The ISO carries the image twice: as the live system, and as the copy in its container storage. The squashfs stores identical files once, so it grows by less than the image's size; the first run measures it (Follow-up).
- Each release channel (step 10.1) needs its own name in the kickstart, which the `iso` workflow reads from there.
- The test covers what the install does, not WebUI's screens or encryption: the owner's install at step 1.17 covers both, and steps 6.6 and 6.10 add them to CI.
- **For the owner:** Fedora's `liveinst` runs the installer with SELinux permissive in the live session, as on every Fedora live ISO. Lumen doesn't add this, and the installed system is enforcing, but it weakens the live session's choice of enforcing (ADR 0012) while the installer runs. Options: (a) keep Fedora's behaviour; (b) once the install test passes, try the installer enforcing in CI, with a small change to `liveinst`, and keep that if it installs with no denials. Recommended: (b), as its own step, with an ADR.
