<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0015. Run the installer with SELinux enforcing

- Status: **Accepted** (2026-10-31), at step 1.8d.
- Deciders: owner (to try it, and to patch Anaconda for `chage`, both 2026-10-31, [ADR 0014](0014-install-from-the-iso.md)), lead engineer (Claude, how). It stays only if the install test passes with no denials (Follow-up).

## Context

- The live session runs with SELinux enforcing ([ADR 0012](0012-install-iso.md)). Fedora's `liveinst`, the launcher the live desktop's installer icon starts, runs `/usr/sbin/setenforce 0` before it starts Anaconda and sets the old mode back after Anaconda ends (`data/liveinst/liveinst` in Anaconda 44.30, there since at least 2010). Every Fedora live ISO installs that way; the installed system is enforcing either way.
- Step 1.8c's install test ran through `liveinst`, as a person's install does, and logged three changes of mode (the policy's first load, `liveinst`'s switch to permissive, and its switch back) and **no** SELinux denial, on the live system or the installed one (ADR 0014, Follow-up).
- Permissive mode logs what enforcing mode would refuse, except what the policy marks `dontaudit`, which neither mode logs but enforcing refuses. So no denials while permissive makes enforcing likely to work, not certain.
- After it sets any password, Anaconda runs `chage -R <new system> -d "" <user>` (`pyanaconda/core/users.py`). Its bootc install binds only `/proc` and `/sys` into the new system, without recursion (`PrepareBootcMountTargetsTask._handle_api_mount_points`, the same in 44.30 and 44.35), so `/sys/fs/selinux` is empty there, and libselinux in `chage` logs a `USER_SELINUX_ERR`, "avc: could not determine enforcing mode: No such file or directory". It isn't an access the policy refused: the password is set. Anaconda's other installs mount SELinux's file system into the new system (`fsset.py`). The install test found it in the audit log on 2026-10-31, enforcing and permissive alike (Follow-up).
- bootc, which Anaconda runs to install, tests whether it may write labels the policy doesn't know and, if it may not, runs itself again with `install_t`'s label (bootc 1.17.1, `lsm.rs`), so it is built to install from an enforcing system.

## Decision

1. The live stage of `image/Containerfile` deletes `liveinst`'s `/usr/sbin/setenforce 0` line. It stops the build if `liveinst` doesn't have that line exactly, so a change upstream is looked at rather than missed. The line that sets the old mode back stays, and does nothing now.
2. `image/live/check-live.sh` fails if `liveinst` still switches SELinux to permissive.
3. **The owner chose to patch Anaconda** for `chage` (2026-10-31): the live stage changes that one line to `for path in ("/proc", "/sys", "/sys/fs/selinux"):`, so the new system has SELinux's file system while Anaconda works in it. Anaconda unmounts its internal mounts in reverse order, so it comes off before `/sys`. The build stops if the line isn't there exactly once, and the patch comes before the live stage's bytecode step, which compiles the file again. `check-live.sh` checks both changes.
4. The install test (`tests/boot/install-live.sh report`) checks that SELinux stayed enforcing while the installer ran (no "enforcing=0 old_enforcing=1" in the journal since boot) and that no denial was logged in the journal or the audit log, the installer's included. Before, it recorded both without judging them.

## Consequences

- The live session is enforcing from start to end, the installer included, as the owner chose for it at step 1.8b-2.
- A future Anaconda, bootc or policy that needs more than the policy allows shows up as a failed install test, with the denials in its report, instead of passing unnoticed. The fix is then policy or labelling, never a return to permissive without the owner's say (ADR 0012's rule).
- Asking Fedora to drop the switch from `liveinst` would help every live ISO; that is the owner's call, since it means posting to their project.
- `rpm -V` reports `/usr/bin/liveinst` (anaconda-live) and Anaconda's `installation.py` (anaconda-core) as changed in the live system. The installed system doesn't have Anaconda at all.
- Lumen carries a one-line Anaconda patch until Anaconda mounts SELinux's file system in its bootc install itself. Reporting it, and the `/var` bind failure of ADR 0014, to Anaconda would let Lumen drop both workarounds; that is the owner's call, since it means posting to their project.

## Follow-up

- 2026-10-31, `iso` run 41203281496 (`liveinst` changed, no Anaconda patch yet): the installer installed Lumen with SELinux enforcing in the same 511 seconds as before, and the installed system passed all its checks. SELinux changed mode once since boot, the policy's first load. The test found one `USER_SELINUX_ERR` from `chage` (Context), and boot-iso run 41207984383, the same test on step 1.8c's ISO with `liveinst`'s switch still in place, found the same line and the switch (`MAC_STATUS enforcing=0 old_enforcing=1`), so the line doesn't come from running enforcing. Decision 3 fixes it.
