<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0015. Run the installer with SELinux enforcing

- Status: **Accepted** (2026-10-31), at step 1.8d.
- Deciders: owner (to try it, 2026-10-31, [ADR 0014](0014-install-from-the-iso.md)), lead engineer (Claude, how). It stays only if the install test passes with no denials (Follow-up).

## Context

- The live session runs with SELinux enforcing ([ADR 0012](0012-install-iso.md)). Fedora's `liveinst`, the launcher the live desktop's installer icon starts, runs `/usr/sbin/setenforce 0` before it starts Anaconda and sets the old mode back after Anaconda ends (`data/liveinst/liveinst` in Anaconda 44.30, there since at least 2010). Every Fedora live ISO installs that way; the installed system is enforcing either way.
- Step 1.8c's install test ran through `liveinst`, as a person's install does, and logged three changes of mode (the policy's first load, `liveinst`'s switch to permissive, and its switch back) and **no** SELinux denial, on the live system or the installed one (ADR 0014, Follow-up).
- Permissive mode logs what enforcing mode would refuse, except what the policy marks `dontaudit`, which neither mode logs but enforcing refuses. So no denials while permissive makes enforcing likely to work, not certain.
- bootc, which Anaconda runs to install, tests whether it may write labels the policy doesn't know and, if it may not, runs itself again with `install_t`'s label (bootc 1.17.1, `lsm.rs`), so it is built to install from an enforcing system.

## Decision

1. The live stage of `image/Containerfile` deletes `liveinst`'s `/usr/sbin/setenforce 0` line. It stops the build if `liveinst` doesn't have that line exactly, so a change upstream is looked at rather than missed. The line that sets the old mode back stays, and does nothing now.
2. `image/live/check-live.sh` fails if `liveinst` still switches SELinux to permissive.
3. The install test (`tests/boot/install-live.sh report`) checks that SELinux stayed enforcing while the installer ran (no "enforcing=0 old_enforcing=1" in the journal since boot) and that no denial was logged in the journal or the audit log, the installer's included. Before, it recorded both without judging them.

## Consequences

- The live session is enforcing from start to end, the installer included, as the owner chose for it at step 1.8b-2.
- A future Anaconda, bootc or policy that needs more than the policy allows shows up as a failed install test, with the denials in its report, instead of passing unnoticed. The fix is then policy or labelling, never a return to permissive without the owner's say (ADR 0012's rule).
- Asking Fedora to drop the switch from `liveinst` would help every live ISO; that is the owner's call, since it means posting to their project.
- `rpm -V anaconda-live` reports `/usr/bin/liveinst` as changed in the live system. The installed system doesn't have Anaconda at all.
