<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0022. Build NVIDIA's open modules with akmods in a stage of their own, sign them apart, and keep nouveau as the fallback

- Status: **Accepted** (2026-11-03), at step 1.11b.
- Deciders: lead engineer (Claude). The owner reviews it at the Phase 1 acceptance (step 1.17).

## Context

The spec's `lumen-nvidia` image has NVIDIA's "proprietary driver as signed kmod, built with akmods in CI"; architecture 9.5 builds the modules in a `kmods` stage against `base`'s exact kernel and signs them with Lumen's key (ADR 0021); risk 7 asks that the desktop stays usable on the open drivers until NVIDIA's loads. Facts, read on 2026-11-01 to 2026-11-03 from the packages' sources:

- **RPM Fusion's driver is 615.78.08** (`rpmfusion/nvidia-kmod` at `628f9fd`, `rpmfusion/xorg-x11-drv-nvidia` at `91ea574`). Its `akmod-nvidia` builds NVIDIA's open modules unless `lspci` on the build machine shows a card they don't support; `--with kmod_nvidia_open` forces them. Driver 580 was the last for cards older than Turing (risk 7), so 615's modules serve Turing (GeForce 16 and 20) and newer, and the open modules are NVIDIA's own choice for those.
- **What `xorg-x11-drv-nvidia` does on other Fedora systems:** in `%posttrans` it adds `rd.driver.blacklist=nouveau,nova_core modprobe.blacklist=nouveau,nova_core` to the kernel arguments with `grubby`, which an image build can't; it keeps NVIDIA's modules out of the initramfs (`99-nvidia-dracut.conf`); and it ships `nvidia-fallback.service`, which loads nouveau before the display manager when the kernel has those arguments and NVIDIA's module didn't load, but doesn't turn it on. Its `-power` package turns on the suspend services and `nvidia-powerd`, whose start command RPM Fusion marks to ignore failures.
- **bootc applies kernel arguments from `/usr/lib/bootc/kargs.d/`** in the image when it installs or switches to it.
- **Module packages need the driver:** `kmod-nvidia` requires `nvidia-kmod-common`, which `xorg-x11-drv-nvidia` provides, and the driver requires `nvidia-kmod`, which `akmod-nvidia` provides too, with a compiler and kernel headers.
- **akmods signs only if it finds a key** in `/etc/pki/akmods/`. Universal Blue (`ublue-os/akmods` at `6d6d70c`) signs the installed modules itself and packs them again with `rpmrebuild`.

## Decision

1. **A `kmods` stage, `FROM base`, never shipped** (`image/nvidia/build-kmods.sh`): `kernel-devel` at exactly `kernel-core`'s version, from the mirrors or Fedora's signed copy on Koji (`multilib.py fetch`); RPM Fusion's nonfree repositories for this step, limited to NVIDIA's driver (`image/nvidia/rpmfusion-nonfree.repo`, the gaming edition's key and pin); `%_with_kmod_nvidia_open 1`, so the open modules don't depend on the build machine; then `akmods --kernels <kernel> --kmod nvidia`, unsigned.
2. **Signing apart** (`image/nvidia/sign-kmods.sh`): a step of its own gets the key, its certificate and its pass phrase as build secrets, which no layer keeps; NVIDIA's build scripts run in the step before and never see them. The kernel's `sign-file` signs each module (xz again with the CRC32 check the kernel needs), its signer is checked, and `rpmrebuild` packs the installed package with the signed modules. Every build signs: CI makes a throwaway key named "Lumen OS kernel module signing (throwaway)", and builds of `main` use Lumen's key from step 1.11c.
3. **The `lumen-nvidia` stage**, `FROM ${LUMEN_NVIDIA_FROM}` (default `lumen`; step 1.12 puts the gaming layer on it): the signed `kmod-nvidia` first, with `rpm --nodeps`, so nothing pulls in `akmod-nvidia`; then `xorg-x11-drv-nvidia`, `-power` and `-cuda-libs` (NVENC and NVDEC) through `packages.py` with nothing the image has changed (`image/nvidia/packages.toml`); then `rpm --verify` of the module package's dependencies, `depmod`, and the certificate in `/usr/share/pki/lumen/module-signing.der` for MOK enrolment.
4. **Nouveau as the fallback:** the edition's overlay puts RPM Fusion's kernel arguments in `/usr/lib/bootc/kargs.d/00-lumen-nvidia.toml` and turns on `nvidia-fallback.service` with a preset. NVIDIA's module loads when the user has enrolled Lumen's key; until then, or on a machine with no NVIDIA card, nouveau loads before the login screen and the desktop works.
5. **os-release** says `VARIANT="NVIDIA"`, `VARIANT_ID=nvidia`, `IMAGE_ID=lumen-nvidia`.
6. **Checks in the stage:** `check-image.sh` again, and `image/nvidia/check-nvidia.sh`: the driver installed and nothing that built it; every module built for the image's kernel, open (a GPL-compatible licence: `Dual MIT/GPL`, or `Dual BSD/GPL` for `nvidia-peermem`, where the proprietary modules say `NVIDIA`), signed by the certificate the image carries and indexed by `depmod`; the kernel arguments, the fallback service turned on with a condition that matches them, NVIDIA's modules kept out of the initramfs; no RPM Fusion repository left; os-release. Then `bootc container lint`.
7. **CI builds it in a job of its own**, `nvidia` in `build-image.yml`, which builds `lumen` again from the same commit and bases: the build job, at 92 minutes, would pass its 120-minute limit. The job then makes, checks and boots its qcow2 with `image/ci-disks.sh`, as the build job does its own (step 1.11c): in a VM with no NVIDIA card and no MOK enrolled, nouveau must take over and the kernel must refuse NVIDIA's module. Step 1.11c also adds the real key; step 1.12b builds and boots `lumen-gaming-nvidia` in the same job, from the same `lumen-nvidia` (ADR 0019, Follow-up); step 1.12c publishes the editions.

## Consequences

- The NVIDIA edition supports Turing and newer cards; older ones run on nouveau and `hardware.json` marks them amber (risk 7).
- Users enrol Lumen's key once, with `mokutil` and the blue MokManager screen at the next start ([nvidia-secure-boot.md](../nvidia-secure-boot.md), step 1.12a); Settings does the first part for them from Phase 5.
- Without the key enrolled, the NVIDIA edition still starts to a working desktop on nouveau, which step 1.11c tests on a machine with no NVIDIA card.
- The build depends on RPM Fusion's mirrors and, when the mirrors have moved past the base's kernel, Koji; either being down fails the NVIDIA job, not `lumen`'s.
- Each build of a branch runs a second runner for about an hour.
- `kmod-nvidia` is installed before its dependency; `rpm --verify` stops the build if it ends up without one.

## Follow-up

- 2026-11-03: written in a cloud session, which can't reach Fedora's mirrors, RPM Fusion or Koji; CI's `nvidia` job is the first build.
- 2026-11-03, what the first builds found, each fixed in its own commit: the mirrors had `kernel-devel` and `kernel-devel-matched` only for 7.2.11 and 7.2.15, so both come from Koji at the image's 7.2.13 (akmods requires the second); RPM Fusion's `akmod-nvidia` starts a build in its `%post`, as root, which `akmodsbuild` refuses and dnf then counts as a failed transaction, so it is installed with `tsflags=noscripts` after `kernel-devel`, `akmods` and `rpmrebuild`; `rpmrebuild` works in root's home, a link to `/var/roothome`, which the signing step makes; Fedora 45's rpm refuses a package without a signature, so this build's `kmod-nvidia` is installed with `_pkgverify_level digest`; and NVIDIA's open `nvidia-peermem` is under Dual BSD/GPL, so the check wants a GPL-compatible licence.
- 2026-11-04: image run 41736790496 (for `bc9e062`) green. The `nvidia` job took 52 minutes: akmods built the five open modules (`nvidia`, `-drm`, `-modeset`, `-uvm`, `-peermem`, `.ko.xz`) for 7.2.13 in about 90 seconds, the signing step signed them with the throwaway key from the build secrets, and the edition passed the lumen checks (14), its own (5) and bootc's lint. The image is 9.4 GB. The build job passed in the same run, 94 minutes.
- 2026-11-04, step 1.11c: image run 41845862445 (for `0638b8e`) booted the NVIDIA edition's qcow2, which follows `ghcr.io/edmundhills/lumen-nvidia:dev`, in a VM with no NVIDIA card and no MOK enrolled, and passed 12 of 12: the kernel had `rd.driver.blacklist=nouveau,nova_core modprobe.blacklist=nouveau,nova_core` from `kargs.d`, `nvidia-fallback.service` loaded nouveau, NVIDIA's module wasn't loaded, `modprobe nvidia` was refused with "Key was rejected by service", Plasma Setup came 32 s after the kernel and the greeter 15 s, with no failed units or SELinux denials on either boot. The display ran on QEMU's `bochs-drm`. The `nvidia` job took 69 minutes, the build job 94, in parallel.
