<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0013. Lumen's own tuned profiles, so tuned never runs bootc

- Status: **Accepted** (2026-10-30), at step 1.8b-3b. The owner chose this fix over turning tuned off in the live session or having the boot test accept the denial.
- Deciders: owner, lead engineer (Claude).
- Upstream: [tuned#895](https://github.com/redhat-performance/tuned/issues/895). Remove this when a fixed tuned reaches the image (Follow-up says how to tell).

## Context

Lumen's power modes (Power Saver, Balanced, Performance in Plasma) come from tuned through tuned-ppd, as on Fedora's desktops (architecture, Q2). The ISO's boot test (step 1.8b-3) found SELinux denials on every boot, from tuned, and the same code runs on installed systems:

- **tuned 2.28 runs bootc on every profile it applies.** On a system where `bootc loader-entries set-options-for-source --help` works, its daemon adds a bootloader unit to every profile that has none, so that it can clear kernel arguments an earlier profile set. Applying the profile then runs `bootc loader-entries set-options-for-source --source tuned`, and leaving it runs that again.
- **bootc 1.17 first checks whether it may write any SELinux label.** Before a command that writes, `prepare_for_write` runs `chcon -t invalid_bootcinstall_testlabel_t` on a temporary file. That needs `mac_admin`, which the policy gives `install_t` and not `tuned_t`, so the kernel logs an AVC denial and a `SELINUX_ERR` each time: 7 a boot in the boot test's VM. `--help` stops before that check, so only the commands that write cause it.
- **Upstream:** [tuned#895](https://github.com/redhat-performance/tuned/issues/895), opened 2026-09-26, reports the same on Fedora 44, with no reply or fix by 2026-10-30. Its workaround is `skip_grub_config=True` in a profile's `[bootloader]` section.
- **What `skip_grub_config` does in tuned 2.28's code:** applying the profile only writes the kernel arguments it would have set to `/etc/tuned/bootcmdline`, and leaving it removes nothing, so neither runs bootc. A profile that has its own `[bootloader]` section also keeps the daemon from adding one.
- **Nothing is lost.** Fedora's profiles behind the power modes (`powersave`, `balanced`, `balanced-battery`, `throughput-performance`) set no kernel arguments, and Lumen doesn't use tuned for kernel arguments.
- **The first profile matters too.** Before tuned-ppd starts, tuned applies the profile Fedora's recommendation picks, such as `virtual-guest` in a VM or `balanced`, which would run bootc on applying and again on leaving it.

The other choices were turning tuned off in the live session only, which leaves installed systems with the denials, or having the boot test accept exactly this denial until upstream fixes it.

## Decision

1. **Lumen ships four tuned profiles** in `/usr/lib/tuned/profiles`: `lumen-powersave`, `lumen-balanced`, `lumen-balanced-battery` and `lumen-performance`. Each includes the Fedora profile it stands for, unchanged, and adds `[bootloader] skip_grub_config=True`.
2. **tuned-ppd maps the power modes to them** in `/etc/tuned/ppd.conf`, Fedora's file with Lumen's profile names. It lives in `/etc` because tuned-ppd reads it only there.
3. **tuned starts with `lumen-balanced`.** `/usr/lib/tuned/recommend.d/40-lumen.conf` recommends it with no conditions. tuned reads the recommendation files in name order and takes the first section that matches, so it comes before Fedora's `50-tuned.conf`.
4. **`image/check-image.sh` checks all three** at every build: each power mode maps to a Lumen profile that sets `skip_grub_config=True` and includes a profile that exists, nothing in `/etc/tuned/profiles` takes its place, and no recommendation comes before Lumen's. The ISO's boot test checks the result: no denials.

## Consequences

- No denial from tuned, in the live session or on installed systems. Checked before the first CI run in the published `dev` image: tuned's own loader merges each Lumen profile with Fedora's, plus the bootloader setting, and its own recommender picks `lumen-balanced`.
- Plasma still shows the three power modes, and on battery Balanced still means Fedora's `balanced-battery`.
- `tuned-adm list` shows the four Lumen profiles next to Fedora's. Someone who picks a Fedora profile with `tuned-adm` gets the denials again, until upstream fixes tuned.
- A tuned profile that should set kernel arguments, which Lumen has none of, would need this undone first.
- Removal, once tuned#895 is fixed: delete the profiles, `ppd.conf` and the recommendation, and the check in `check-image.sh`. Systems that remember a `lumen-*` profile as their active one would then lack it, so the removal keeps a migration in mind: tuned-ppd sets the mode again at its next start, but plain tuned would not.

## Follow-up

- Watch [tuned#895](https://github.com/redhat-performance/tuned/issues/895) and Fedora's tuned updates. When a fixed tuned is in the image, rerun the ISO's boot test with Fedora's profiles in `ppd.conf` before removing these.
