#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Install packages so that every 32-bit package matches its 64-bit twin in the
# image exactly, and no package the image already has changes (docs/
# architecture.md, sections 9.4 and 9.5; step 1.10a, ADR 0019). Steam needs
# 32-bit Mesa, glibc and some forty other libraries. Fedora's mirrors carry
# only the newest build of each, which is often newer than the base image's,
# and dnf would then upgrade the 64-bit package too, so the gaming image would
# run a different Mesa from the image it derives from.
#
# packages.py calls install() for a manifest that sets exact_32bit = true:
#
# 1. dnf resolves the packages and downloads what it would install
#    (dnf download --resolve), without installing it.
# 2. Each 32-bit package whose twin the image has at another version is
#    swapped for the build at the twin's version: from the mirrors if they
#    still have it, otherwise the copy Fedora signed on Koji, its build system,
#    which keeps every build. Any upgrade of a package the image has is
#    dropped.
# 3. rpmkeys checks every file's signature against the keys of the enabled
#    repositories, which it imports first: neither dnf download nor a local
#    install checks them. Then dnf installs exactly those files, with every
#    repository turned off.
#
# If the packages can't be installed at the image's versions, the build stops
# and says which. Usage:
#   python3 image/multilib.py install PACKAGE...   as packages.py does it
#   python3 image/multilib.py check                 list every 32-bit package
#                                                   whose twin is at another
#                                                   version; exit 1 if any
#                                                   (image/gaming/check-gaming.sh)

import configparser
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DNF = ["dnf", "--assumeyes", "--setopt=install_weak_deps=False"]
KOJI = "https://kojipkgs.fedoraproject.org/packages"
QUERY = "%{NAME} %{ARCH} %{EPOCHNUM}:%{VERSION}-%{RELEASE}\n"


class MultilibError(Exception):
    """The packages can't be installed at the image's versions."""


def parse(text):
    """Turn rpm's QUERY lines into {(name, arch): epoch:version-release}."""
    found = {}
    for line in text.splitlines():
        if line.strip():
            name, arch, evr = line.split()
            found[(name, arch)] = evr
    return found


def installed():
    """{(name, arch): evr} for every installed package, gpg-pubkey's pseudo-packages left out."""
    out = subprocess.run(["rpm", "--query", "--all", "--queryformat", QUERY],
                         check=True, capture_output=True, text=True).stdout
    return {key: evr for key, evr in parse(out).items() if key[0] != "gpg-pubkey"}


def headers(paths):
    """{path: (name, arch, evr)} for RPM files."""
    found = {}
    for path in paths:
        out = subprocess.run(["rpm", "--query", "--package", "--nosignature", "--queryformat", QUERY, path],
                             check=True, capture_output=True, text=True).stdout
        (name, arch), evr = next(iter(parse(out).items()))
        found[path] = (name, arch, evr)
    return found


def plan(files, have):
    """Sort what dnf downloaded into the files to keep, the 32-bit builds to fetch and the upgrades to drop.

    FILES is {path: (name, arch, evr)}, HAVE is installed()'s answer. Returns
    (keep, fetch, dropped): the paths to install as they are; (name, evr) of
    each 32-bit package to fetch at its 64-bit twin's version; and
    "name.arch old -> new" for each upgrade of an installed package left out.
    """
    keep, fetch, dropped = [], [], []
    for path, (name, arch, evr) in sorted(files.items()):
        if (name, arch) in have:
            if have[(name, arch)] != evr:
                dropped.append(f"{name}.{arch} {have[(name, arch)]} -> {evr}")
        elif arch == "i686" and (name, "x86_64") in have and have[(name, "x86_64")] != evr:
            fetch.append((name, have[(name, "x86_64")]))
        else:
            keep.append(path)
    return keep, fetch, dropped


def mismatches(have):
    """Every 32-bit package whose 64-bit twin is at another version, as "name: i686 evr, x86_64 evr"."""
    return [f"{name}: i686 {evr}, x86_64 {have[(name, 'x86_64')]}"
            for (name, arch), evr in sorted(have.items())
            if arch == "i686" and (name, "x86_64") in have and have[(name, "x86_64")] != evr]


def version_release(evr):
    """'0:25.2.5-1.fc44' -> '25.2.5-1.fc44'."""
    return evr.split(":", 1)[-1]


def source_nvr(sourcerpm):
    """'mesa-25.2.5-1.fc44.src.rpm' -> ('mesa', '25.2.5', '1.fc44')."""
    if not sourcerpm.endswith(".src.rpm"):
        raise MultilibError(f"{sourcerpm!r} isn't a source package's file name")
    name, version, release = sourcerpm.removesuffix(".src.rpm").rsplit("-", 2)
    return name, version, release


def key_id(signature):
    """The short key ID Koji files signed copies under, from rpm's pgpsig: '…, Key ID 829b606631645531' -> '31645531'."""
    m = re.search(r"Key ID ([0-9a-fA-F]{8,40})", signature)
    if not m:
        raise MultilibError(f"no key ID in the signature {signature!r}")
    return m.group(1)[-8:].lower()


def koji_url(sourcerpm, key, name, evr, arch="i686"):
    """Where Koji keeps the copy of a build signed with KEY."""
    source, version, release = source_nvr(sourcerpm)
    return f"{KOJI}/{source}/{version}/{release}/data/signed/{key}/{arch}/{name}-{version_release(evr)}.{arch}.rpm"


def fetch(name, evr, dest):
    """Download the 32-bit NAME at EVR into DEST, from the mirrors or Koji; return the file's path."""
    spec = f"{name}-{version_release(evr)}.i686"
    before = set(glob.glob(f"{dest}/*.rpm"))
    if subprocess.run(DNF + ["download", f"--destdir={dest}", spec]).returncode == 0:
        new = set(glob.glob(f"{dest}/*.rpm")) - before
        if len(new) == 1:
            return new.pop()
    twin = f"{name}.x86_64"
    sourcerpm, signature = subprocess.run(
        ["rpm", "--query", "--queryformat", "%{SOURCERPM}\n%{RSAHEADER:pgpsig}\n", twin],
        check=True, capture_output=True, text=True).stdout.splitlines()[:2]
    url = koji_url(sourcerpm, key_id(signature), name, evr)
    path = os.path.join(dest, url.rsplit("/", 1)[1])
    print(f"The mirrors don't have {spec}; downloading it from Koji: {url}", flush=True)
    if subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location", "--retry", "3",
                       "--output", path, url]).returncode != 0:
        raise MultilibError(f"{spec}, at the version of {twin} in the image, is neither in the mirrors "
                            f"nor on Koji ({url})")
    return path


def import_keys():
    """Import the signing keys of the enabled repositories' file:// gpgkey entries into rpm's keyring."""
    fedora = subprocess.run(["rpm", "--eval", "%{fedora}"], check=True, capture_output=True, text=True).stdout.strip()
    keys = []
    for path in sorted(glob.glob("/etc/yum.repos.d/*.repo")):
        repos = configparser.ConfigParser(interpolation=None, strict=False)
        repos.read(path)
        for name in repos.sections():
            section = repos[name]
            if section.get("enabled", "1").strip() not in ("1", "true", "True"):
                continue
            for key in section.get("gpgkey", "").split():
                if key.startswith("file://"):
                    key = (key.removeprefix("file://").replace("$releasever_major", fedora)
                           .replace("$releasever", fedora).replace("$basearch", "x86_64"))
                    if os.path.isfile(key) and key not in keys:
                        keys.append(key)
    for key in keys:
        subprocess.run(["rpmkeys", "--import", key], check=True)
    return keys


def verify(path):
    """Stop unless PATH carries a signature by a key rpm trusts: rpm passes an unsigned package on its digests alone."""
    check = subprocess.run(["rpmkeys", "--checksig", path], capture_output=True, text=True)
    if check.returncode != 0 or "signatures ok" not in check.stdout.lower():
        raise MultilibError(f"{os.path.basename(path)} fails its signature check: {check.stdout.strip()}")


def downloaded(dest):
    """The RPM files dnf download --resolve left in DEST."""
    return glob.glob(f"{dest}/*.rpm")


def install(names):
    """Install NAMES, every 32-bit package at its 64-bit twin's version and nothing the image has changed."""
    have = installed()
    work = tempfile.mkdtemp(prefix="lumen-multilib-")
    try:
        resolved, exact = Path(work, "resolved"), Path(work, "exact")
        resolved.mkdir()
        exact.mkdir()
        subprocess.run(DNF + ["download", "--resolve", f"--destdir={resolved}", *names], check=True)
        keep, wanted, dropped = plan(headers(downloaded(resolved)), have)
        for line in dropped:
            print(f"Left out, to keep the image's version: {line}", flush=True)
        for name, evr in wanted:
            print(f"Fetching {name}.i686 at the image's {version_release(evr)}", flush=True)
            keep.append(fetch(name, evr, str(exact)))
        if not keep:
            return
        print(f"Checking the signatures of {len(keep)} packages", flush=True)
        import_keys()
        for path in keep:
            verify(path)
        # With every repository off, dnf installs these files and nothing else,
        # and stops if they need something the image doesn't have.
        result = subprocess.run(DNF + ["install", "--disablerepo=*", *keep])
        if result.returncode != 0:
            raise MultilibError("dnf could not install the packages at the image's versions (above). If it left "
                                "out an upgrade they need, wait for the base image to have it (the weekly bump)")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    after = installed()
    problems = [f"{name}.{arch} changed from {evr} to {after[(name, arch)]}"
                for (name, arch), evr in sorted(have.items()) if after.get((name, arch), evr) != evr]
    problems += [f"32-bit and 64-bit builds differ: {m}" for m in mismatches(after)]
    if problems:
        raise MultilibError("\n".join(problems))


def main(argv):
    if argv[1:] == ["check"]:
        found = mismatches(installed())
        for line in found:
            print(f"32-bit and 64-bit builds differ: {line}")
        return 1 if found else 0
    if len(argv) < 3 or argv[1] != "install":
        print("Usage: multilib.py install PACKAGE... | check", file=sys.stderr)
        return 2
    try:
        install(argv[2:])
    except MultilibError as e:
        print(e, file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"{' '.join(e.cmd)} failed with exit status {e.returncode}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
