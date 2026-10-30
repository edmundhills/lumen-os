<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# tests

Tests that cover more than one component, and the checks for the developer setup. Unit tests live next to the code they test (`cargo test`, Qt Test).

| Folder | What it checks | Runs | Step |
| --- | --- | --- | --- |
| [dev-env/](dev-env/) | `check-wsl.sh`: a WSL 2 + Fedora PC is ready for Lumen development ([guide](../docs/dev-setup-windows.md)) | By hand, in WSL | A4 |
| [lint/](lint/) | The lint checks (`run.sh`): licences and copyright (reuse), shell scripts (shellcheck, shfmt), Markdown style (markdownlint) and links, YAML style (yamllint), the GitHub Actions workflows (actionlint), the justfile's format, whitespace, the repository layout, and the image's package manifest and trust policy. `Containerfile` builds the container they run in, which also holds the registry, skopeo and cosign for `image/test_signatures.py`, and `selftest.sh` proves each check fails on a file that breaks its rule | `just lint`, `just test`; in CI, the `lint` workflow runs both on every push and pull request | 0.5, 0.6, 1.6 |
| [boot/](boot/) | The install ISO boots in QEMU with UEFI and Secure Boot, as a PC boots the USB, through its default entry and "Check this USB" (`boot_iso.py`); inside, `live-session.sh` checks Secure Boot, the entry's kernel arguments, SELinux enforcing with no denials, the live user's Plasma and the media check. `Containerfile` builds the VM container: QEMU and Fedora's firmware with Microsoft's keys, on the lint container's Fedora. Step 1.9 adds the image's own boot test, to the login screen within 60 seconds with no failed units | In CI, the `boot-iso` workflow after each `iso` run; `just boot-iso ISO` (slow without KVM) | 1.8b-3, 1.9 |

The other layers (session, glass visual, accessibility, performance, update and Windows compatibility tests) get their folders when their steps start.

## How the ISO's boot test works

- **The VM** is QEMU's q35 machine with 4 CPUs and 6 GiB, using KVM, with the ISO in its CD drive and no network. Its firmware is Fedora's OVMF build with Secure Boot on and Microsoft's keys enrolled, found through the firmware descriptors edk2-ovmf installs, as libvirt finds it, with SMM guarding its variables, as on a PC. Fedora's shim is signed with both Microsoft's 2011 and 2023 UEFI CAs, so either is enough. Each boot starts from fresh firmware variables.
- **The boot menu is driven over the serial port.** OVMF puts its console on the serial port as well as the screen, and GRUB's menu with it, and reads keys from there. The default entry is left to start when GRUB's 10 seconds run out, which GRUB announces ("Booting \`…'"); another entry is reached with GRUB's one-byte keys `v` and `^` and started with Enter. No entry is edited, so the kernel starts with exactly the arguments in `iso.yaml`, which the checks inside compare.
- **The way in is a systemd credential, not a change to the ISO.** QEMU puts two credentials into the VM's SMBIOS tables, which systemd reads only in a VM: `getty.ttys.serial` makes systemd start a login on the serial port, and `lumen.live-check` holds `live-session.sh`. `boot_iso.py` logs in as root, which the live session leaves without a password, retrying until livesys has unlocked it, and runs the script from `/run/credentials/@system`.
- **What it checks inside:** Secure Boot on (the firmware's `SecureBoot` variable); the kernel arguments; SELinux enforcing with the targeted policy; for "Check this USB", that dracut's `checkisomd5@` service finished; KWin and the Plasma shell running as `liveuser` in an active Wayland session, still there 30 seconds later; then no SELinux denial in the journal or the audit log since boot. It records the time Plasma took, kernel lockdown, the sleep states offered, the Secure Boot certificates and any failed units, without judging them.
- **What it keeps:** each boot's serial log, QEMU's log, and screenshots of the menu and the desktop (or of the screen when a step failed), as the `boot-iso` artifact for 7 days.

Spec: [Test layers](../docs/spec.md#test-layers). Architecture: [9.9 Where each test layer runs](../docs/architecture.md#99-where-each-test-layer-runs).
