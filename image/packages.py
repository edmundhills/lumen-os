#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Read image/packages.toml, the Fedora packages Lumen keeps from Kinoite, adds
# and removes, and apply it to the image.
#
# Usage:
#   python3 image/packages.py check [FILE]   check the file's format (just lint)
#   python3 image/packages.py apply [FILE]   change the packages (the base stage
#                                             of image/Containerfile)
#
# `apply` checks the file against the base image first: everything under keep
# and remove is installed, and nothing under install is. It then installs and
# removes with dnf, and checks the result: everything under install is
# installed, everything under remove is gone, and no other package was removed.
# Any mismatch stops the build and names the package, so the manifest always
# says exactly what Lumen changes. FILE defaults to packages.toml next to this
# script. Exits 0 on success, 1 on a problem.

import re
import subprocess
import sys
import tomllib
from pathlib import Path

LISTS = ("keep", "install", "remove")
# An RPM package name: letters, digits and . _ + -, starting with a letter or digit.
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")
# Weak dependencies stay out, so every package Lumen wants is in the manifest.
DNF = ["dnf", "--assumeyes", "--setopt=install_weak_deps=False"]


class ManifestError(Exception):
    """The manifest is malformed, or doesn't match the image."""


def load(path):
    """Read the manifest and return its keep, install and remove lists.

    The file has one table per area of the spec's package manifest, such as
    [desktop], each with any of the lists keep, install and remove. The lists
    come back merged across areas, in file order.
    """
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ManifestError(f"{path}: {e}") from None

    lists = {key: [] for key in LISTS}
    where = {}  # package name -> the list it was first seen in
    problems = []
    for area, table in data.items():
        if not isinstance(table, dict):
            problems.append(f"{area}: expected a table, [{area}], holding keep, install or remove lists")
            continue
        for key, names in table.items():
            here = f"[{area}] {key}"
            if key not in LISTS:
                problems.append(f"{here}: unknown list; the lists are keep, install and remove")
            elif not isinstance(names, list) or not all(isinstance(n, str) for n in names):
                problems.append(f"{here}: expected a list of package names")
            else:
                for name in names:
                    if not NAME.fullmatch(name):
                        problems.append(f"{here}: {name!r} isn't a package name")
                    elif name in where:
                        problems.append(f"{here}: {name} is already listed in {where[name]}")
                    else:
                        where[name] = here
                        lists[key].append(name)
    if problems:
        raise ManifestError("\n".join(f"{path}: {p}" for p in problems))
    return lists


def check_before(lists, have):
    """List what in the manifest doesn't match the base image's packages."""
    problems = []
    for name in lists["keep"]:
        if name not in have:
            problems.append(f"{name} is listed under keep, but the base image doesn't have it")
    for name in lists["remove"]:
        if name not in have:
            problems.append(f"{name} is listed under remove, but the base image doesn't have it")
    for name in lists["install"]:
        if name in have:
            problems.append(f"{name} is listed under install, but the base image already has it: move it to keep")
    return problems


def check_after(lists, before, after):
    """List where the packages after dnf ran differ from what the manifest says."""
    problems = []
    for name in lists["install"]:
        if name not in after:
            problems.append(f"{name} is listed under install, but isn't installed")
    for name in lists["remove"]:
        if name in after:
            problems.append(f"{name} is listed under remove, but is still installed")
    for name in sorted(set(before) - set(after) - set(lists["remove"])):
        problems.append(f"{name} was removed, but isn't listed under remove. dnf removes a package when it "
                        "depends on one that goes, or conflicts with one that comes. List it under remove, "
                        "or keep what it needs")
    return problems


def installed():
    """Return {name: version-release} for every installed package."""
    out = subprocess.run(["rpm", "--query", "--all", "--queryformat", "%{NAME} %{EVR}\n"],
                         check=True, capture_output=True, text=True).stdout
    return dict(line.split(" ", 1) for line in out.splitlines())


def report(before, after):
    """Print every package that came, went or changed version, for the build log."""
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(n for n in set(before) & set(after) if before[n] != after[n])
    print(f"\nPackages added: {len(added)}, removed: {len(removed)}, changed version: {len(changed)}")
    for name in added:
        print(f"  + {name} {after[name]}")
    for name in removed:
        print(f"  - {name} {before[name]}")
    for name in changed:
        print(f"  ~ {name} {before[name]} -> {after[name]}")


def fail_on(problems):
    if problems:
        raise ManifestError("\n".join(problems))


def apply(path):
    lists = load(path)
    before = installed()
    fail_on(check_before(lists, before))
    if lists["install"]:
        # --allowerasing lets a package replace one it conflicts with (tuned-ppd
        # replaces power-profiles-daemon). check_after stops the build if that
        # erases anything not listed under remove.
        subprocess.run(DNF + ["install", "--allowerasing", *lists["install"]], check=True)
    remaining = [name for name in lists["remove"] if name in installed()]
    if remaining:
        subprocess.run(DNF + ["remove", *remaining], check=True)
    after = installed()
    report(before, after)
    fail_on(check_after(lists, before, after))
    subprocess.run(["dnf", "clean", "all"], check=True)


def main(argv):
    if len(argv) not in (2, 3) or argv[1] not in ("check", "apply"):
        print("Usage: packages.py check|apply [FILE]", file=sys.stderr)
        return 2
    path = Path(argv[2]) if len(argv) == 3 else Path(__file__).with_name("packages.toml")
    try:
        if argv[1] == "check":
            lists = load(path)
            print(f"{path}: keeps {len(lists['keep'])}, installs {len(lists['install'])} "
                  f"and removes {len(lists['remove'])} packages")
        else:
            apply(path)
    except ManifestError as e:
        print(e, file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"{' '.join(e.cmd)} failed with exit status {e.returncode}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
