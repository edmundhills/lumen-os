<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0012. Pack the install ISO with image-builder's generic-iso, and label its files for SELinux

- Status: **Accepted** (2026-10-29), at step 1.8b-2. The owner chose that the live session runs with SELinux enforcing; the lead engineer chose the tool.
- Deciders: owner (SELinux in the live session), lead engineer (Claude). The owner reviews the rest at the Phase 1 acceptance (step 1.17).

## Context

The install ISO is a live ISO made from the Lumen image (ADR 0002). Step 1.8b-1 built the `live` stage of `image/Containerfile` to the "container-native ISO contract v0.1.0", which two tools pack into an ISO: Universal Blue's Titanoboa, which the spec says to try first, and osbuild's image-builder, with its `generic-iso` type ([ADR 0011](0011-disk-images.md)). What each does, checked on 2026-10-29 in their source and by running image-builder:

- **Neither labels the files for SELinux.** A system reads each file's SELinux label from an extended attribute. Labels never travel in a container image's layers, so the files of an unpacked image have none, and the policy refuses an enforcing system almost everything on unlabelled files. Titanoboa packs the image straight from container storage. image-builder unpacks it into a tree of its own and labels only its build environment: in the manifest it made of the live system, the `os-tree` pipeline that becomes the squashfs is the unpacking stage alone. Its source on 2026-10-29 (`osbuild/images`, `pkg/manifest/os_from_container.go`) has no SELinux stage there either. So every upstream example boots its live session with `enforcing=0`, which image-builder also writes into its default menu.
- **The owner's choice (2026-10-29):** Lumen labels the live system's files itself before packing, so the live session runs enforcing, as Fedora's own live ISOs do. Booting the live session permissive was the other option. Either way the installed system is enforcing.
- **Labelling works without SELinux on the build machine**, which matters because GitHub's Ubuntu runners use AppArmor and WSL has no SELinux. Checked in WSL with the live system's own `setfiles` (policycoreutils 3.11) and policy (version 35): `setfiles -F -m -r` wrote the labels the policy gives, such as `shell_exec_t` on `/usr/bin/bash` and `shadow_t` on `/etc/shadow`, and kept file capabilities (`cap_setuid` on `newuidmap`). `mksquashfs` kept both. Asked to change nothing, `setfiles -n -v` listed no file on the labelled squashfs, and 4,305 of the same files on an unlabelled one. osbuild's own SELinux stage says it is meant to run where SELinux is off.
- **Titanoboa** (`ublue-os/titanoboa`, newest commit `5c457c3` of 2026-05-19, no releases) is two short scripts. `main.sh` mounts the image into an unpinned `quay.io/fedora/fedora:latest` container, where `build_iso.sh` installs its tools from Fedora's mirrors, runs `mksquashfs` on the mounted image and builds the ISO with `xorriso`. For Lumen:
  - It packs the image as mounted, so its files have no labels, and it takes no other input. Lumen would run `build_iso.sh` alone, with a labelled copy of the tree mounted in its place.
  - It copies the image's `/boot/efi/EFI` folder as it is. Fedora's shim puts only itself (`BOOTX64.EFI`) and its fallback loader (`fbx64.efi`) in `EFI/BOOT`, with no GRUB. shim started from a USB runs the fallback loader when it finds one, which writes a boot entry for the USB into the PC's firmware and boots that, so every PC the USB starts would keep an entry. GRUB for a CD (`gcdx64.efi`), which the contract asks for, isn't used.
  - It makes ISOs that boot on UEFI only. Its check for GRUB's BIOS files tests a folder as if it were a file, so it never copies them.
  - It writes no checksum into the ISO, so a "check this USB" entry can't work.
- **image-builder 88.0.0's `generic-iso`**, from the container Lumen already pins for the qcow2:
  - The manifest it makes of the live system has five pipelines: `build` (the live system as the build environment, labelled), `os-tree` (the live system unpacked), `efiboot-tree`, `bootiso-tree` (squashfs, kernel, BIOS boot) and `bootiso` (`xorrisofs`, then `implantisomd5`).
  - It makes the squashfs from `os-tree` with `mksquashfs`, which stores extended attributes, and so labels, by default.
  - It lays out `EFI/BOOT` as Fedora's ISOs do: shim as `BOOTX64.EFI`, `gcdx64.efi` as the `grubx64.efi` shim starts, and the MOK manager, with no fallback loader. It also builds GRUB's BIOS boot image and writes the checksum.
  - Lumen's own menu entries from `iso.yaml` replace its default ones, so its `enforcing=0` isn't used.
  - With `--bootc-installer-payload-ref` it copies an image into the live system's container storage, which step 1.8c needs to install with no network.

## Decision

1. **image-builder's `generic-iso` packs the install ISO**, from the container that makes the qcow2, pinned by release and digest: `.github/workflows/iso.yml` pins the same one as `build-image.yml`, and `image/test_iso.py` checks that they agree. Titanoboa isn't used: the spec's "try Titanoboa first" is answered by the points above, of which the firmware boot entries and the lack of labels matter most.
2. **Lumen labels the files with osbuild's own SELinux stage.** `image/make-iso.sh` asks image-builder for its manifest (`image-builder manifest --bootc-ref <live system> generic-iso`), `image/iso.py label` adds an `org.osbuild.selinux` stage at the end of the `os-tree` pipeline, which labels every file with the live system's own `file_contexts`, and the script runs osbuild from the same container. `iso.py` stops with a message if the manifest is no longer laid out this way, or if image-builder labels the tree itself, which would make the step unnecessary.

   Before that, the `live` stage removes the ostree repository that every build carries (`/sysroot/ostree`, and `/ostree`, which points to it). The live system runs from the squashfs, not from an ostree deployment, and step 1.8c installs from container storage, so nothing uses it. Its files are hard links to those in `/usr`, and the policy labels the two paths differently, so each such file would get whichever label `setfiles` met first. Titanoboa leaves both folders out of its squashfs too. The second run in CI found this (Follow-up).
3. **`image/check-iso.sh` checks every ISO**, inside the live system it was made from, so that it reads the labels with that system's `setfiles` and policy:
   - The label and boot menus are those of `iso.yaml`, and no entry turns SELinux off.
   - The files UEFI and BIOS firmware start are there, with no fallback loader, and the EFI system partition holds the same boot files as the ISO.
   - `checkisomd5` accepts the checksum.
   - The kernel and initramfs are the live system's own.
   - The squashfs holds the build named, with `SELINUX=enforcing`.
   - Every file in the squashfs has the label the policy gives it, and `setfiles` gives no warning, such as one about a file with two paths the policy labels differently.
4. **The `iso` workflow makes the ISO** on demand, and on pushes to main that change the live system or how the ISO is made. It builds only the `live` stage, on a published build whose signature it checks first with the trust policy Lumen ships, and keeps the ISO for 7 days as a workflow artifact (Q15).
5. **`iso.yaml` gets a "Check this USB, then try or install Lumen OS" entry** (`rd.live.check`), now that the ISO carries a checksum. The initramfs has `checkisomd5`, because the live stage installs `isomd5sum` before it runs dracut.

## Consequences

- The live session runs with SELinux enforcing. Whether it reaches the desktop without denials is the boot test's to find out (step 1.8b-3). A denial is fixed by labelling or policy, never by booting permissive, unless the owner decides otherwise.
- `make-iso.sh` runs osbuild itself rather than `image-builder build`, so a new image-builder release can break the edit. `iso.py` then stops and says what changed, and the pin moves only in a pull request that passes the `iso` workflow. Once image-builder labels the tree itself, `iso.py` says so, and the edit goes. Asking osbuild to label `generic-iso` trees upstream would help every bootc ISO; that is the owner's call, since it means posting to their project.
- The ISO is larger than GitHub's 2 GiB limit for release files, so releases need another host (Q15, step 9.5).
- Step 1.8c adds `--bootc-installer-payload-ref` to the manifest `make-iso.sh` asks for. image-builder copies the payload into `os-tree` before the SELinux stage, so its files are labelled too.
- The spec, the architecture and the risk register now name image-builder as the ISO's packer, and Titanoboa is no longer one of the tool images Renovate will move.

## Follow-up

- 2026-10-30: the first two runs in CI, on `dev` `44.20261029.4`, both made the ISO, which is 3.53 GiB. The first (`iso` run 40974893727) stopped before the check, because `make-iso.sh` runs as root and made the output folder the runner then had to write the checksum into. The second (run 41022162696) passed 5 of the 6 checks and failed on the labels:
  - `setfiles` warned about 131,591 files that have a second path in `/sysroot/ostree/repo/objects`, the build's ostree repository, which the policy labels `default_t`.
  - osbuild's `setfiles` met the `/usr` paths first, so the files had their `/usr` labels, which is what the live system needs. The check reads the squashfs, which lists `sysroot` before `usr`, so it met the repository's paths first and found every one of those files mislabelled. Which label a file ends up with depended on the order osbuild's file system happened to list the folders in.
  - The check also wrote all of `setfiles`'s warnings into the run's summary, 48.6 MB, which GitHub refused (it takes 1 MB). It now shows at most 40 lines of a failing check, and fails on any warning from `setfiles`.
  - The fix is Decision 2's second paragraph: the `live` stage removes the repository, and `check-live.sh` checks that it is gone.
- 2026-10-30: the third run (`iso` run 41045231975, for `bc95770`, on `dev` `44.20261030`) passed 6 of 6 in 34 minutes 46 seconds, and the live stage's check passed 11 of 11, "The build's ostree repository is gone" among them.
  - Without the repository, the squashfs holds 126,685 files and 156,532 inodes, against 274,881 and 305,134, and is 2,939.5 MB against 3,286.3 MB. The ISO is 1,671,498 sectors, 3.19 GiB, against 3.53 GiB.
  - The job's log is 123 KB, against 40 MB for the first run, which most likely held the same warnings from osbuild's `setfiles`.
  - Step times: freeing disk 3 minutes, the pull with its signature check 1 minute 45 seconds, the live stage 16 minutes 51 seconds, "Make the ISO" 12 minutes 8 seconds, the check 24 seconds and the upload 31 seconds. In osbuild, unpacking the live system took 127 seconds for the build environment and 121 for `os-tree`, labelling 6.5 and 5.0 seconds, the squashfs 276 seconds, `xorrisofs` 41 and `implantisomd5` 15.
  - `df` showed 123 GB free after the cleanup, 115 GB after the live stage and 110 GB after the ISO, so disk is no concern.
  - `actions/upload-artifact` with `archive: false` kept the 3.19 GiB file as it is, for 7 days.
- 2026-10-30, step 1.8b-3: the boot test (`tests/boot/`, the `boot-iso` workflow) booted the ISO of `iso` run 41068574134 (`44.20261030.2`, for `d1fd4a3`) in QEMU/KVM with Secure Boot. Both entries it boots passed 8 of 9 checks: GRUB's menu, the login, Secure Boot on, the kernel arguments of `iso.yaml`, SELinux enforcing, the live user's Plasma, and for "Check this USB" the media check. Plasma ran 17 seconds after the kernel started (25 with the media check). The ninth check found SELinux denials, from two sources:
  - **tuned runs bootc.** tuned 2.28 runs `bootc loader-entries set-options-for-source` on every profile it applies, to clear kernel arguments it may have set. bootc 1.17 first runs `chcon` on a temporary file to test whether it may write labels the policy doesn't know (`mac_admin`), which `tuned_t` may not, so each profile switch logs a `mac_admin` denial and a `SELINUX_ERR`. Installed systems run the same code, so they log it too. It is reported upstream as [tuned#895](https://github.com/redhat-performance/tuned/issues/895), still open with no fix.
  - **Stale Python bytecode.** 3,778 of the image's 3,986 `.pyc` files record a source time other than the 0 that the image gives every file, so Python compiles those modules again whenever it imports them. Kinoite's own files are the same, before Lumen re-chunks them. In the live session `/usr` is writable, so `tuned-ppd` writes the new bytecode next to the old, which its policy (`tuned_ppd_t`, a permissive domain) logs. On an installed system `/usr` is read-only, so nothing is written and nothing logged, but Python programs start more slowly.
  - The step is split: 1.8b-3a is the boot test, done; 1.8b-3b fixes the denials until it passes.
