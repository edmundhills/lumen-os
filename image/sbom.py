#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check the SBOM that syft makes of a Lumen image (step 1.6,
# docs/decisions/0008-image-signing.md): it must list exactly the RPM packages
# the image has, so that what CI attaches to the image says truly what is in it.
#
# Usage: python3 image/sbom.py check SBOM PACKAGES
#
#   SBOM      syft's SPDX JSON document for the image.
#   PACKAGES  The image's packages, one per line, as rpm prints them with
#             --queryformat '%{NAME} %{EPOCHNUM}:%{VERSION}-%{RELEASE} %{ARCH}\n'.
#
# Writes, in Markdown, what the SBOM holds. Exits 0 when its RPM packages are
# the image's, 1 when they aren't (listing the differences), and 2 when a file
# can't be read.

import json
import sys
from collections import Counter
from urllib.parse import parse_qs, unquote, urlsplit

# rpm lists the keys it trusts as packages named gpg-pubkey, which syft skips.
NOT_PACKAGES = {"gpg-pubkey"}
# How many differences to list before saying how many more there are.
SHOWN = 20


class InputError(Exception):
    pass


def rpm_from_purl(purl):
    """Return (name, "epoch:version-release", arch) for an RPM package URL, or None for another kind."""
    if not purl.startswith("pkg:rpm/"):
        return None
    parts = urlsplit(purl)
    path, _, version = parts.path.partition("@")
    name = unquote(path.rsplit("/", 1)[-1])
    query = parse_qs(parts.query)
    epoch = query.get("epoch", ["0"])[0]
    arch = query.get("arch", [""])[0]
    return name, f"{epoch}:{unquote(version)}", arch


def purl(package):
    for ref in package.get("externalRefs") or []:
        if ref.get("referenceType") == "purl":
            return ref.get("referenceLocator", "")
    return ""


def kind(locator):
    """The ecosystem of a package URL, such as rpm or pypi, or "other"."""
    return locator[4:].split("/", 1)[0] if locator.startswith("pkg:") else "other"


def read_sbom(path):
    """Return (the SBOM's RPM packages as a Counter, the other packages by kind as a Counter)."""
    try:
        with open(path, encoding="utf-8") as f:
            sbom = json.load(f)
    except (OSError, ValueError) as e:
        raise InputError(f"{path}: {e}") from e
    if not str(sbom.get("spdxVersion", "")).startswith("SPDX-"):
        raise InputError(f"{path}: not an SPDX JSON document")
    rpms, others = Counter(), Counter()
    for package in sbom.get("packages") or []:
        locator = purl(package)
        rpm = rpm_from_purl(locator)
        if rpm:
            rpms[rpm] += 1
        elif not str(package.get("SPDXID", "")).startswith("SPDXRef-DocumentRoot"):
            # The document's root package is the image itself.
            others[kind(locator)] += 1
    return rpms, others


def read_packages(path):
    """Return the image's packages, from rpm's output, as a Counter of (name, epoch:version-release, arch)."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as e:
        raise InputError(f"{path}: {e}") from e
    packages = Counter()
    for number, line in enumerate(lines, 1):
        fields = line.split()
        if not fields:
            continue
        if len(fields) != 3:
            raise InputError(f"{path}, line {number}: expected NAME EPOCH:VERSION-RELEASE ARCH, found {line!r}")
        if fields[0] not in NOT_PACKAGES:
            packages[tuple(fields)] += 1
    return packages


def show(title, packages):
    lines = [f"{title}:"]
    names = sorted(" ".join(p) for p in packages.elements())
    lines += [f"- `{name}`" for name in names[:SHOWN]]
    if len(names) > SHOWN:
        lines.append(f"- and {len(names) - SHOWN} more")
    return lines


def check(sbom_path, packages_path):
    """Return (True if the SBOM's RPM packages are the image's, a Markdown report)."""
    rpms, others = read_sbom(sbom_path)
    packages = read_packages(packages_path)
    lines = ["### SBOM", ""]
    missing, extra = packages - rpms, rpms - packages
    if not missing and not extra:
        lines.append(f"The SBOM lists the image's {sum(packages.values()):,} RPM packages.")
    else:
        lines.append(f"The SBOM lists {sum(rpms.values()):,} RPM packages, and the image has {sum(packages.values()):,}.")
        if missing:
            lines += [""] + show("In the image but not in the SBOM", missing)
        if extra:
            lines += [""] + show("In the SBOM but not in the image", extra)
    if others:
        found = ", ".join(f"{n:,} {k}" for k, n in sorted(others.items(), key=lambda kv: (-kv[1], kv[0])))
        lines += ["", f"syft also found packages of other kinds in the image's files: {found}."]
    return not missing and not extra, "\n".join(lines)


def main(argv):
    if len(argv) != 4 or argv[1] != "check":
        print("Usage: sbom.py check SBOM PACKAGES", file=sys.stderr)
        return 2
    try:
        ok, report = check(argv[2], argv[3])
    except InputError as e:
        print(f"sbom.py: {e}", file=sys.stderr)
        return 2
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
