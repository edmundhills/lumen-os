#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Keep the base images that Lumen's Containerfiles pin current, and say where
# their copies on ghcr.io live (step 1.5b, ADR 0004). quay.io deletes a dated
# Kinoite build four weeks after it is made, and Fedora's registry drops old
# digests too, so the base workflow (.github/workflows/base.yml) moves every
# pin each week and copies each pinned base to ghcr.io with its digest intact.
#
# Usage:
#   python3 image/bump_bases.py list REGISTRY CONTAINERFILE...
#       Print each pinned base as "IMAGE DIGEST COPY TAG": the base is
#       IMAGE@DIGEST, and its copy is COPY:TAG, for example
#       ghcr.io/edmundhills/kinoite:44-9f71aa8ed152.
#   python3 image/bump_bases.py mirrors REGISTRY CONTAINERFILE...
#       Print a registries.conf drop-in that makes Podman pull each pinned base
#       from its copy in REGISTRY first, and only by digest.
#   python3 image/bump_bases.py bump CONTAINERFILE...
#       Move each pin to the newest build of its tag, and Kinoite's to the
#       newest Fedora release that Bodhi lists as current. Rewrite each moved
#       pin and its "# Pinned:" line, and print a commit message that says what
#       moved, or nothing if every pin is current. Needs skopeo and the network.
#
# A pinned base is a FROM line that names one of the images in BASES by tag and
# digest, below a "# Pinned:" line that says which build it is. Exits 0, 1 on a
# problem, or 2 on a usage error.

import dataclasses
import hashlib
import json
import re
import subprocess
import sys
import urllib.request

KINOITE = "quay.io/fedora-ostree-desktops/kinoite"
FEDORA = "registry.fedoraproject.org/fedora"
# The images Lumen builds from. Kinoite's tag is the Fedora release, which
# moves to each new one; the lint container's Fedora tag stays where it is,
# because moving it can change the Node version its nodejs package names.
BASES = (KINOITE, FEDORA)

BODHI_RELEASES = "https://bodhi.fedoraproject.org/releases/?exclude_archived=1&rows_per_page=100"

FROM_LINE = re.compile(r"FROM (?P<image>[^\s:@]+)(?::(?P<tag>[^\s@]+))?(?:@(?P<digest>sha256:[0-9a-f]{64}))?(?P<rest>\s.*)?")
PINNED_LINE = re.compile(r"# Pinned: (?P<build>.+)")
# A layer that rpm-ostree named after the one package in it: name-version-release.arch.
NEVRA = re.compile(r"(?P<name>.+)-(?P<version>[^-]+)-(?P<release>[^-]+)\.(?P<arch>[^.-]+)")


class BumpError(Exception):
    pass


@dataclasses.dataclass
class Pin:
    """A pinned base: the FROM line at index LINE of PATH's lines."""

    path: str
    line: int
    image: str
    tag: str
    digest: str
    rest: str
    build: str

    def copy(self, registry):
        """Return the name and tag of this base's copy in REGISTRY."""
        return f"{registry}/{self.image.rsplit('/', 1)[1]}", f"{self.tag}-{self.digest[7:19]}"


def parse_pins(path, text):
    """Return the pinned bases in the Containerfile PATH, whose text is TEXT."""
    lines = text.split("\n")
    pins = []
    for i, line in enumerate(lines):
        m = FROM_LINE.fullmatch(line)
        if not m or m["image"] not in BASES:
            continue
        if not m["tag"] or not m["digest"]:
            raise BumpError(f"{path}:{i + 1}: {m['image']} must be pinned by tag and digest, as IMAGE:TAG@sha256:DIGEST")
        pinned = PINNED_LINE.fullmatch(lines[i - 1]) if i > 0 else None
        if not pinned:
            raise BumpError(f"{path}:{i + 1}: the line above a pinned base must say which build it is: '# Pinned: ...'")
        pins.append(Pin(path, i, m["image"], m["tag"], m["digest"], m["rest"] or "", pinned["build"].rstrip(".")))
    return pins


def read_pins(paths):
    pins = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            pins += parse_pins(path, f.read())
    if not pins:
        raise BumpError(f"no pinned base in {', '.join(paths)}")
    return pins


def list_lines(registry, pins):
    """Return the lines `list` prints: IMAGE DIGEST COPY TAG for each pin."""
    return [" ".join((pin.image, pin.digest, *pin.copy(registry))) for pin in pins]


def mirrors_conf(registry, pins):
    """Return a registries.conf drop-in that pulls each base from its copy in REGISTRY first."""
    out = [
        "# Pull Lumen's pinned base images from their copies on ghcr.io first, and only",
        "# by digest, so a tag can never resolve there. Podman falls back to the",
        "# image's own registry when a copy is missing. Written by image/bump_bases.py.",
    ]
    seen = set()
    for pin in pins:
        if pin.image in seen:
            continue
        seen.add(pin.image)
        out += [
            "",
            "[[registry]]",
            f'prefix = "{pin.image}"',
            f'location = "{pin.image}"',
            "",
            "[[registry.mirror]]",
            f'location = "{pin.copy(registry)[0]}"',
            'pull-from-mirror = "digest-only"',
        ]
    return "\n".join(out) + "\n"


def newest_fedora(releases):
    """Return the newest Fedora release that Bodhi's RELEASES list as current."""
    current = [
        int(r["version"])
        for r in releases
        if r.get("id_prefix") == "FEDORA" and r.get("state") == "current" and re.fullmatch(r"F[0-9]+", r.get("name", ""))
    ]
    if not current:
        raise BumpError("Bodhi lists no current Fedora release")
    return max(current)


def bodhi_releases():
    """Return the releases Bodhi lists, archived ones left out."""
    with urllib.request.urlopen(BODHI_RELEASES, timeout=60) as response:
        data = json.load(response)
    if data.get("pages", 1) != 1:
        raise BumpError(f"Bodhi's release list has {data.get('pages')} pages; read them all")
    return data["releases"]


def package_versions(config, names):
    """Return the version of each package in NAMES, read from the layer names in an image's CONFIG.

    rpm-ostree names a layer that holds one package after it, for example
    kwin-common-6.7.5-1.fc44.x86_64. A package that shares a layer has no
    version here, and gets "unknown".
    """
    found = {}
    for entry in config.get("history", []):
        m = NEVRA.fullmatch(entry.get("created_by", ""))
        if m and m["name"] in names:
            found[m["name"]] = m["version"]
    return {name: found.get(name, "unknown") for name in names}


def describe(image, tag, info, config):
    """Return the text of the "# Pinned:" line for a build of IMAGE:TAG."""
    built = (info.get("Created") or "")[:10] or "on an unknown date"
    if image == KINOITE:
        version = (info.get("Labels") or {}).get("org.opencontainers.image.version", f"{tag} (no version label)")
        v = package_versions(config, ("kwin-common", "plasma-workspace", "qt6-qtbase"))
        return (
            f"Kinoite {version}, built {built}, with KWin {v['kwin-common']},"
            f" Plasma {v['plasma-workspace']} and Qt {v['qt6-qtbase']}"
        )
    return f"Fedora {tag}, built {built}"


class Skopeo:
    """Reads images from their registries with skopeo."""

    def run(self, *args):
        result = subprocess.run(["skopeo", "inspect", "--retry-times", "3", *args], capture_output=True, check=False)
        if result.returncode != 0:
            raise BumpError(f"skopeo inspect {' '.join(args)}: {result.stderr.decode(errors='replace').strip()}")
        return result.stdout

    def digest(self, image, tag):
        """Return the digest IMAGE:TAG points at; for a multi-architecture image, its index's."""
        return "sha256:" + hashlib.sha256(self.run("--raw", f"docker://{image}:{tag}")).hexdigest()

    def info(self, image, digest):
        return json.loads(self.run("--no-tags", f"docker://{image}@{digest}"))

    def config(self, image, digest):
        return json.loads(self.run("--config", f"docker://{image}@{digest}"))


@dataclasses.dataclass
class Move:
    pin: Pin
    tag: str
    digest: str
    build: str


def bump(paths, registry, releases):
    """Move every pin in PATHS to the newest build, and return the moves.

    REGISTRY reads images (Skopeo), and RELEASES returns Bodhi's releases.
    """
    moves, newest = [], None
    for path in paths:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        lines = text.split("\n")
        for pin in parse_pins(path, text):
            tag = pin.tag
            if pin.image == KINOITE:
                if newest is None:
                    newest = newest_fedora(releases())
                # A pin on a newer release than Bodhi's newest stays on it.
                tag = str(max(int(pin.tag), newest))
            digest = registry.digest(pin.image, tag)
            if (tag, digest) == (pin.tag, pin.digest):
                continue
            build = describe(pin.image, tag, registry.info(pin.image, digest), registry.config(pin.image, digest))
            lines[pin.line - 1] = f"# Pinned: {build}."
            lines[pin.line] = f"FROM {pin.image}:{tag}@{digest}{pin.rest}"
            moves.append(Move(pin, tag, digest, build))
        new_text = "\n".join(lines)
        if new_text != text:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new_text)
    return moves


def kwin_and_plasma(build):
    return re.findall(r"(?:KWin|Plasma) [^,\s]+", build)


def message(moves):
    """Return the commit message for MOVES, or "" when nothing moved."""
    if not moves:
        return ""
    kinoite = next((m for m in moves if m.pin.image == KINOITE), None)
    if kinoite and kinoite.tag != kinoite.pin.tag:
        title = f"build(image): move the base to Fedora {kinoite.tag}"
    elif kinoite:
        title = f"build(image): bump the base to {kinoite.build.split(',')[0]}"
    else:
        title = "build(lint): bump the lint container's Fedora base"
    out = [title, "", "Moves the pinned base images to their newest builds (.github/workflows/base.yml).", ""]
    for m in moves:
        out += [
            f"- {m.pin.path}, {m.pin.image}:",
            f"  - was {m.pin.tag}@{m.pin.digest[:19]}…: {m.pin.build}",
            f"  - now {m.tag}@{m.digest[:19]}…: {m.build}",
        ]
    if kinoite and kinoite.tag != kinoite.pin.tag:
        out += [
            "",
            f"Bodhi lists Fedora {kinoite.tag} as current, so the image moves to it. If the base stage",
            f"fails, image/packages.toml doesn't match Kinoite {kinoite.tag} yet: fix it on this branch.",
        ]
    if kinoite and kwin_and_plasma(kinoite.build) != kwin_and_plasma(kinoite.pin.build):
        out += [
            "",
            "KWin or Plasma changed. Every Lumen package that links them is rebuilt against the new",
            "versions in this build (CLAUDE.md, \"Critical build rule\"), and a Plasma feature release",
            "usually needs lumen-glass rebased onto KWin's new blur effect (docs/risks.md, risk 1).",
        ]
    return "\n".join(out) + "\n"


def main(argv):
    command, args = (argv[1], argv[2:]) if len(argv) > 1 else ("", [])
    if not ((command in ("list", "mirrors") and len(args) >= 2) or (command == "bump" and args)):
        print(
            "Usage: bump_bases.py list REGISTRY CONTAINERFILE...\n"
            "       bump_bases.py mirrors REGISTRY CONTAINERFILE...\n"
            "       bump_bases.py bump CONTAINERFILE...",
            file=sys.stderr,
        )
        return 2
    try:
        if command == "list":
            print("\n".join(list_lines(args[0].rstrip("/"), read_pins(args[1:]))))
        elif command == "mirrors":
            print(mirrors_conf(args[0].rstrip("/"), read_pins(args[1:])), end="")
        else:
            read_pins(args)  # Check every file before changing any.
            print(message(bump(args, Skopeo(), bodhi_releases)), end="")
    except (OSError, ValueError, KeyError, BumpError) as e:
        print(f"bump_bases.py: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
