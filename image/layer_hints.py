#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Mark files that need a layer of their own when the image is re-chunked
# (image/rechunk.sh, ADR 0007). rpm-ostree puts the files of each package in
# that package's layer, and every file no package owns, with the initramfs, in
# one shared layer. A file marked with the extended attribute user.component
# goes instead into a layer for that component alone.
#
# Usage: python3 image/layer_hints.py [ROOT]
#
# The lumen stage of the Containerfile runs this inside the image it is
# building, after os-release.sh. ROOT, / by default, is where the image's files
# are. Exits 0 when every file in HINTS is marked, 1 if one is missing.

import glob
import os
import sys

ATTRIBUTE = "user.component"

# Component name: the files in it, as patterns under ROOT.
HINTS = {
    # The initramfs changes only with Kinoite's, but the files no package owns
    # change on every build. Sharing their layer, it would be downloaded again
    # with each update.
    "initramfs": ["usr/lib/modules/*/initramfs.img"],
    # Lumen's os-release names the build, so it changes on every build. It
    # replaces a file of a Fedora package, so it would otherwise go into that
    # package's layer and take the layer's other packages with it.
    "lumen-os-release": ["usr/lib/os-release"],
}


def plan(root):
    """Return (path, component) for every file in HINTS under ROOT, and the patterns that match nothing.

    Only regular files count: a link can't carry a user attribute.
    """
    marks, missing = [], []
    for component, patterns in HINTS.items():
        for pattern in patterns:
            paths = sorted(p for p in glob.glob(os.path.join(root, pattern))
                           if os.path.isfile(p) and not os.path.islink(p))
            if not paths:
                missing.append(pattern)
            marks += [(p, component) for p in paths]
    return marks, missing


def main(argv, setxattr=os.setxattr):
    if len(argv) > 2:
        print("Usage: layer_hints.py [ROOT]", file=sys.stderr)
        return 2
    marks, missing = plan(argv[1] if len(argv) == 2 else "/")
    for pattern in missing:
        print(f"layer_hints.py: nothing matches /{pattern}", file=sys.stderr)
    for path, component in marks:
        # Don't follow a link: the mark belongs on the file in the image.
        setxattr(path, ATTRIBUTE, component.encode(), follow_symlinks=False)
        print(f"{path}: {ATTRIBUTE}={component}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
