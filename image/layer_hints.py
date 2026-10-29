#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Mark files that need a layer of their own when the image is re-chunked
# (image/rechunk.sh, ADR 0007). rpm-ostree puts the files of each package in
# that package's layer, and every file no package owns in one shared layer,
# together with the initramfs. A file marked with the extended attribute
# user.component goes instead into a layer for that component alone.
#
# The initramfs can't be marked: rpm-ostree files it before it reads the
# marks. So the shared layer stays unchanged between builds on the same base
# only if the files that do change are marked and moved out of it.
#
# Usage: python3 image/layer_hints.py OVERLAY [ROOT]
#
# The lumen stage of the Containerfile runs this inside the image it is
# building, after os-release.sh, with the checkout's image/overlay as OVERLAY.
# ROOT, / by default, is where the image's files are. Exits 0 when every file
# is marked, or 1, marking none, if one is missing.

import glob
import os
import sys

ATTRIBUTE = "user.component"

# Component name: the files in it, as patterns under ROOT.
HINTS = {
    # Lumen's os-release names the build, so it changes on every build. It
    # replaces a file of a Fedora package, so it would otherwise go into that
    # package's layer and take the layer's other packages with it.
    "lumen-os-release": ["usr/lib/os-release"],
    # The package step writes these afresh on every build, even with the same
    # packages: the rpm database and dnf's state record when each package was
    # installed, and fontconfig's caches when they were made. Two builds of one
    # commit differ in nothing else (step 1.5c). Without the mark, the caches
    # would take the shared layer, initramfs and all, and the databases their
    # packages' layers.
    "lumen-build-state": [
        "usr/share/rpm/rpmdb.sqlite*",
        "usr/lib/sysimage/libdnf5/*",
        "usr/lib/fontconfig/cache/*",
    ],
}
# Every file the overlay adds. No package owns them, and they change whenever
# Lumen's defaults do.
OVERLAY = "lumen-overlay"


def is_file(path):
    # Only regular files: a link can't carry a user attribute, and a folder's
    # mark would also take the packages' files in it.
    return os.path.isfile(path) and not os.path.islink(path)


def plan(root, overlay):
    """Return (path, component) for every file to mark under ROOT, and the paths that match nothing."""
    marks, missing = [], []
    for component, patterns in HINTS.items():
        for pattern in patterns:
            paths = sorted(p for p in glob.glob(os.path.join(root, pattern)) if is_file(p))
            if not paths:
                missing.append(pattern)
            marks += [(p, component) for p in paths]
    for folder, _, names in sorted(os.walk(overlay)):
        for name in sorted(names):
            rel = os.path.relpath(os.path.join(folder, name), overlay)
            path = os.path.join(root, rel)
            if is_file(path):
                marks.append((path, OVERLAY))
            else:
                missing.append(rel)
    return marks, missing


def main(argv, setxattr=os.setxattr):
    if len(argv) not in (2, 3) or not os.path.isdir(argv[1]):
        print("Usage: layer_hints.py OVERLAY [ROOT]", file=sys.stderr)
        return 2
    marks, missing = plan(argv[2] if len(argv) == 3 else "/", argv[1])
    if missing:
        for path in missing:
            print(f"layer_hints.py: nothing matches /{path}", file=sys.stderr)
        return 1
    for path, component in marks:
        # Don't follow a link: the mark belongs on the file in the image.
        setxattr(path, ATTRIBUTE, component.encode(), follow_symlinks=False)
    counts = {}
    for _, component in marks:
        counts[component] = counts.get(component, 0) + 1
    for component, count in counts.items():
        print(f"{ATTRIBUTE}={component}: {count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
