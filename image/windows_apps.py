#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Make Windows programs and installers open in Bottles (step 1.13, spec,
# "Windows apps", docs/decisions/0024-windows-app-base.md), until Lumen's own
# dialog takes over in Phase 7, and check that they do.
#
# Usage:
#   python3 image/windows_apps.py apply LIST
#   python3 image/windows_apps.py check ROOT
#
# apply   Puts Bottles first, as the default and as an added app, for every
#         type in TYPES in LIST, Plasma's vendor list of default apps
#         (/usr/share/applications/kde-mimeapps.list, which Plasma reads before
#         Fedora's mimeapps.list there). It keeps whatever else LIST holds, or
#         makes it. The lumen stage of image/Containerfile runs it.
# check   In the image at ROOT (/ for image/check-image.sh): for every type the
#         image's shared-mime-info gives *.exe and *.msi files, LIST makes
#         Bottles the default and adds it, and no list Plasma reads before it
#         sets another default or removes Bottles.
#
# Exits 0 when done or when every check holds, 1 when one doesn't (saying
# why), and 2 on a usage error.

import configparser
import io
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BOTTLES = "com.usebottles.bottles.desktop"
LIST = Path("usr/share/applications/kde-mimeapps.list")
MIME_PACKAGES = Path("usr/share/mime/packages")
SECTIONS = ("Added Associations", "Default Applications")
# The files Windows programs and installers come in.
PATTERNS = ("*.exe", "*.msi")
# Every type shared-mime-info gives those files. Bottles' desktop file declares
# the first and the last (bottlesdevs/Bottles at fdeaff1); the rest are other
# names, or older formats, an .exe file can have (Fedora 45's shared-mime-info,
# 2026-11-06).
TYPES = (
    "application/x-ms-dos-executable",
    "application/x-msdownload",
    "application/vnd.microsoft.portable-executable",
    "application/x-dosexec",
    "application/x-ms-ne-executable",
    "application/x-lx-executable",
    "application/x-msi",
)
# The lists Plasma reads before LIST: the system's config folders
# (XDG_CONFIG_DIRS, with Fedora's KDE profile) and /usr/local's data folder.
# Fedora's /usr/share/applications/mimeapps.list comes after it.
EARLIER = (Path("etc/xdg"), Path("usr/share/kde-settings"), Path("usr/local/share/applications"))
NS = "{http://www.freedesktop.org/standards/shared-mime-info}"
HEADER = """\
# Plasma's default apps for file types (XDG MIME Applications). Lumen's image
# build puts Bottles first for Windows programs and installers
# (image/windows_apps.py), until Lumen's "Open Windows app" dialog takes over
# in Phase 7. A user's own choice, in Settings or "Open With", goes in
# ~/.config/mimeapps.list and wins.
"""


def types_for(xml_texts, pattern):
    """The MIME types whose glob is PATTERN in shared-mime-info's XML_TEXTS, in the order found."""
    found = []
    for text in xml_texts:
        root = ET.fromstring(text)
        for mime in root.iter(f"{NS}mime-type"):
            for glob in mime.iter(f"{NS}glob"):
                if glob.get("pattern") == pattern and mime.get("type") not in found:
                    found.append(mime.get("type"))
    return found


def parser():
    p = configparser.ConfigParser(interpolation=None, strict=False, delimiters=("=",), comment_prefixes=("#",))
    p.optionxform = str
    return p


def read_list(text):
    """{section: {MIME type: [desktop file IDs]}} of a mimeapps.list."""
    p = parser()
    p.read_string(text)
    return {section: {key: [app for app in value.split(";") if app] for key, value in p[section].items()}
            for section in p.sections()}


def with_bottles(text):
    """TEXT, a mimeapps.list or "", with Bottles first for every type in TYPES."""
    p = parser()
    p.read_string(text)
    for section in SECTIONS:
        if not p.has_section(section):
            p.add_section(section)
        for mime in TYPES:
            apps = [app for app in p[section].get(mime, "").split(";") if app and app != BOTTLES]
            p[section][mime] = ";".join([BOTTLES, *apps]) + ";"
    out = io.StringIO()
    p.write(out, space_around_delimiters=False)
    return HEADER + "\n" + out.getvalue()


def apply(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(with_bottles(text), encoding="utf-8")


def earlier_lists(root):
    """Every mimeapps.list under ROOT that Plasma reads before LIST."""
    found = []
    for folder in EARLIER:
        if (root / folder).is_dir():
            found += sorted((root / folder).rglob("*mimeapps.list"))
    return found


def check(root):
    """List what keeps .exe and .msi files from opening in Bottles in the image at ROOT."""
    root = Path(root)
    problems = []
    xml_texts = [path.read_text(encoding="utf-8") for path in sorted((root / MIME_PACKAGES).glob("*.xml"))]
    if not xml_texts:
        return [f"{root / MIME_PACKAGES} has no shared-mime-info XML"]
    path = root / LIST
    if not path.is_file():
        return [f"{path} is missing"]
    sections = read_list(path.read_text(encoding="utf-8"))
    types = []
    for pattern in PATTERNS:
        found = types_for(xml_texts, pattern)
        if not found:
            problems.append(f"shared-mime-info gives {pattern} no type")
        for mime in found:
            types.append(mime)
            if sections.get("Default Applications", {}).get(mime, [None])[0] != BOTTLES:
                problems.append(f"{LIST} doesn't make Bottles the default for {mime}, a type of {pattern}")
            if BOTTLES not in sections.get("Added Associations", {}).get(mime, []):
                problems.append(f"{LIST} doesn't add Bottles for {mime}, a type of {pattern}")
    for other in earlier_lists(root):
        earlier = read_list(other.read_text(encoding="utf-8"))
        for mime in types:
            apps = earlier.get("Default Applications", {}).get(mime)
            if apps and apps[0] != BOTTLES:
                problems.append(f"{other}, which Plasma reads first, sets {';'.join(apps)} as the default for {mime}")
            if BOTTLES in earlier.get("Removed Associations", {}).get(mime, []):
                problems.append(f"{other}, which Plasma reads first, removes Bottles from {mime}")
    return problems


def main(argv):
    if len(argv) == 3 and argv[1] == "apply":
        apply(argv[2])
        return 0
    if len(argv) == 3 and argv[1] == "check":
        problems = check(argv[2])
        for problem in problems:
            print(problem)
        return 1 if problems else 0
    print("Usage: windows_apps.py apply LIST | check ROOT", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
