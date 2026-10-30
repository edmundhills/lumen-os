# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# What the installer installs (step 1.8c, docs/decisions/0014-install-from-the-iso.md).
# The live stage of image/Containerfile installs this file as
# /usr/share/anaconda/interactive-defaults.ks, in place of Anaconda's own,
# which has no commands. Anaconda reads it whenever it runs from the live
# session (liveinst), and only it: there, Anaconda ignores any other
# kickstart.
#
# bootc installs the Lumen build that the ISO carries in its own container
# storage, under this name (image/make-iso.sh puts it there), so the install
# needs no network. The installed system then follows the same name on
# ghcr.io for its updates. bootc reads Lumen's install settings from the live
# system (/usr/lib/bootc/install/20-lumen.toml), which make it record the image
# as ostree-image-signed: every update must carry Lumen's signature (ADR 0008).
# The name in --source-imgref must stay the same as --target-imgref:
# image/iso.py reads it from here.
bootc --source-imgref=containers-storage:ghcr.io/edmundhills/lumen:dev --target-imgref=ghcr.io/edmundhills/lumen:dev
