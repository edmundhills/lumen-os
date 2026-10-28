#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Work out the build version of a Lumen image (docs/architecture.md, section
# 9.7): <Fedora release>.<build date>, for example 44.20261028, and then
# 44.20261028.1, .2 and so on for further builds on the same day. It goes into
# os-release, the image's version label and its dated tags.
#
# Usage: python3 image/build_version.py CONTAINERFILE [TAGS_JSON]
#
# The Fedora release is the tag of the Kinoite image that the Containerfile's
# base stage starts from, and the date is today's in UTC. TAGS_JSON is what
# `skopeo list-tags` prints for the image's repository on ghcr.io: when a build
# of this version already has its dev-<version> tag there, the next free suffix
# is used, so a dated tag never moves. Without it, the version has no suffix,
# which is what a local build needs. Prints the version and exits 0, or exits 1
# on a problem.

import datetime
import json
import re
import sys

# The base stage's FROM line: Kinoite, pinned by digest, with its release as the tag.
BASE_FROM = re.compile(
    r"^FROM quay\.io/fedora-ostree-desktops/kinoite:([0-9]+)@sha256:[0-9a-f]{64} AS base$",
    re.MULTILINE,
)


class VersionError(Exception):
    pass


def fedora_release(containerfile):
    """Return the Fedora release of the base image in CONTAINERFILE's text."""
    releases = BASE_FROM.findall(containerfile)
    if len(releases) != 1:
        raise VersionError(
            "expected one line 'FROM quay.io/fedora-ostree-desktops/kinoite:<release>@sha256:<digest> AS base',"
            f" found {len(releases)}"
        )
    return releases[0]


def build_version(release, day, tags):
    """Return the version for a build of RELEASE on DAY, given the registry's TAGS."""
    first = f"{release}.{day:%Y%m%d}"
    taken = set(tags)
    version, n = first, 0
    while f"dev-{version}" in taken:
        n += 1
        version = f"{first}.{n}"
    return version


def main(argv):
    if len(argv) not in (2, 3):
        print("Usage: build_version.py CONTAINERFILE [TAGS_JSON]", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            release = fedora_release(f.read())
        tags = []
        if len(argv) == 3:
            with open(argv[2], encoding="utf-8") as f:
                tags = json.load(f).get("Tags") or []
    except (OSError, ValueError, AttributeError, VersionError) as e:
        print(f"build_version.py: {e}", file=sys.stderr)
        return 1
    print(build_version(release, datetime.datetime.now(datetime.timezone.utc).date(), tags))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
