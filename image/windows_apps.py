#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check that Windows programs and installers open in Bottles (step 1.13, spec,
# "Windows apps"), until Lumen's own dialog takes over in Phase 7.
#
# Usage: python3 image/windows_apps.py check ROOT
#
# ROOT is the image's root: / inside the image, for image/check-image.sh. The
# check reads the types the image's shared-mime-info gives *.exe and *.msi
# files, and requires that:
#
#   - Lumen's /usr/share/applications/mimeapps.list makes Bottles the default
#     for each of them, and adds it as an app for them;
#   - no other mimeapps.list that Plasma reads sets a default for them, or
#     removes Bottles from them;
#   - no package owns Lumen's list, which would mean the image replaced a file
#     of Fedora's.
#
# Exits 0 when all hold, 1 when one doesn't (saying why), and 2 on a usage error.

import configparser
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BOTTLES = "com.usebottles.bottles.desktop"
LUMEN_LIST = Path("usr/share/applications/mimeapps.list")
MIME_PACKAGES = Path("usr/share/mime/packages")
# The files Windows programs and installers come in.
PATTERNS = ("*.exe", "*.msi")
# Where the other lists Plasma reads can be: the system's config folders
# (XDG_CONFIG_DIRS) and data folders (XDG_DATA_DIRS), each as <desktop>-mimeapps.list
# or mimeapps.list. Fedora's KDE settings keep a profile of their own.
LIST_FOLDERS = (Path("etc/xdg"), Path("usr/share/applications"), Path("usr/local/share/applications"),
                Path("usr/share/kde-settings"))
NS = "{http://www.freedesktop.org/standards/shared-mime-info}"


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


def read_list(text):
    """{section: {MIME type: [desktop file IDs]}} of a mimeapps.list."""
    parser = configparser.ConfigParser(interpolation=None, strict=False, delimiters=("=",),
                                       comment_prefixes=("#",))
    parser.optionxform = str
    parser.read_string(text)
    return {section: {key: [app for app in value.split(";") if app] for key, value in parser[section].items()}
            for section in parser.sections()}


def rpm_owner(path):
    """The package that owns PATH, or None."""
    result = subprocess.run(["rpm", "--query", "--file", "--queryformat", "%{NAME}\n", str(path)],
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def other_lists(root):
    """Every mimeapps.list under ROOT that Plasma may read, but Lumen's."""
    lumen = root / LUMEN_LIST
    found = []
    for folder in LIST_FOLDERS:
        if (root / folder).is_dir():
            found += [path for path in sorted((root / folder).rglob("*mimeapps.list")) if path != lumen]
    return found


def check(root, owner=rpm_owner):
    """List what keeps .exe and .msi files from opening in Bottles in the image at ROOT."""
    root = Path(root)
    problems = []
    xml_texts = [path.read_text(encoding="utf-8") for path in sorted((root / MIME_PACKAGES).glob("*.xml"))]
    if not xml_texts:
        return [f"{root / MIME_PACKAGES} has no shared-mime-info XML"]
    lumen_path = root / LUMEN_LIST
    if not lumen_path.is_file():
        return [f"{lumen_path} is missing"]
    lumen = read_list(lumen_path.read_text(encoding="utf-8"))
    defaults = lumen.get("Default Applications", {})
    added = lumen.get("Added Associations", {})
    types = []
    for pattern in PATTERNS:
        found = types_for(xml_texts, pattern)
        if not found:
            problems.append(f"shared-mime-info gives {pattern} no type")
        for mime in found:
            types.append(mime)
            if defaults.get(mime, [None])[0] != BOTTLES:
                problems.append(f"Lumen's mimeapps.list doesn't make Bottles the default for {mime}, the type of {pattern}")
            if BOTTLES not in added.get(mime, []):
                problems.append(f"Lumen's mimeapps.list doesn't add Bottles for {mime}, the type of {pattern}")
    for path in other_lists(root):
        sections = read_list(path.read_text(encoding="utf-8"))
        for mime in types:
            if mime in sections.get("Default Applications", {}):
                problems.append(f"{path} sets a default app for {mime}: "
                                f"{';'.join(sections['Default Applications'][mime])}")
            if BOTTLES in sections.get("Removed Associations", {}).get(mime, []):
                problems.append(f"{path} removes Bottles from {mime}")
    package = owner(lumen_path)
    if package:
        problems.append(f"{lumen_path} belongs to the package {package}, whose file Lumen's replaced")
    return problems


def main(argv):
    if len(argv) != 3 or argv[1] != "check":
        print("Usage: windows_apps.py check ROOT", file=sys.stderr)
        return 2
    problems = check(argv[2])
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
