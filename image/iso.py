#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The install ISO's two Lumen-specific parts (step 1.8b,
# docs/decisions/0012-install-iso.md): the SELinux labels image-builder leaves
# out, and the checks of what it made.
#
# Usage:
#   python3 image/iso.py label MANIFEST
#       Read the osbuild manifest that `image-builder manifest generic-iso`
#       made from the live system, and print it with an org.osbuild.selinux
#       stage at the end of its os-tree pipeline, the tree that becomes the
#       ISO's squashfs. The stage labels every file with the live system's own
#       policy, so the live session can run enforcing. Stops, and says why,
#       if the manifest isn't laid out as image-builder 88 lays it out, or if
#       it labels the tree already, in which case this step is no longer
#       needed.
#   python3 image/iso.py boot ISO_YAML ISO_DIR LABEL
#       The mounted ISO, whose filesystem label is LABEL: the label and the
#       boot menus are those of ISO_YAML (image/live/iso.yaml), no menu entry
#       turns SELinux off, the files UEFI and BIOS firmware start are there,
#       and the USB boots the way Fedora's do: shim, then GRUB for a CD,
#       without shim's fallback loader, which would add a boot entry to the
#       PC's firmware.
#
# image/make-iso.sh runs `label`, image/check-iso.sh runs `boot`, and
# test_iso.py runs both on stand-ins. Exits 0 when all is well, 1 when
# something isn't (saying why), and 2 when the input can't be read.

import json
import re
import shlex
import sys
from pathlib import Path

import yaml

# What the stage labels with: the policy's file contexts in the tree itself,
# which osbuild's setfiles reads relative to the tree it labels.
FILE_CONTEXTS = "etc/selinux/targeted/contexts/files/file_contexts"
SELINUX_STAGE = {"type": "org.osbuild.selinux", "options": {"file_contexts": FILE_CONTEXTS}}

# What firmware starts from the ISO. UEFI: shim as the removable-media loader,
# GRUB built for a CD (gcdx64.efi) next to it under the name shim looks for,
# and shim's MOK manager. BIOS: GRUB's El Torito image.
BOOT_FILES = (
    "EFI/BOOT/BOOTX64.EFI",
    "EFI/BOOT/grubx64.efi",
    "EFI/BOOT/mmx64.efi",
    "EFI/BOOT/grub.cfg",
    "images/efiboot.img",
    "images/eltorito.img",
    "boot/grub2/grub.cfg",
    "images/pxeboot/vmlinuz",
    "images/pxeboot/initrd.img",
    "LiveOS/squashfs.img",
)
# shim runs this instead of GRUB when it finds it next to itself, and it writes
# a boot entry for the USB into the PC's firmware.
FALLBACK = "EFI/BOOT/fbx64.efi"
# The menus: GRUB's for UEFI and for BIOS.
MENUS = ("EFI/BOOT/grub.cfg", "boot/grub2/grub.cfg")
# Kernel arguments that would turn SELinux off or make it permissive.
SELINUX_OFF = ("enforcing=0", "selinux=0")

MENUENTRY = re.compile(r"^\s*menuentry\s+'([^']*)'")
LINUX = re.compile(r"^\s*linux(?:efi)?\s+(\S.*?)\s*$")
INITRD = re.compile(r"^\s*initrd(?:efi)?\s+(\S.*?)\s*$")


class InputError(Exception):
    pass


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise InputError(f"{path}: {e}") from e


def label(manifest):
    """Return (problems, the manifest with the SELinux stage added)."""
    pipelines = manifest.get("pipelines") if isinstance(manifest, dict) else None
    if not isinstance(pipelines, list):
        return [f"The manifest has no list of pipelines; its version is {manifest.get('version')!r}"], None
    named = {}
    for p in pipelines:
        named.setdefault(p.get("name"), []).append(p)
    problems = []
    trees = named.get("os-tree", [])
    if len(trees) != 1:
        problems.append(f"The manifest has {len(trees)} pipelines named os-tree, not one: image-builder has changed "
                        "how it lays out an ISO, so check where the live system's tree is made now")
        return problems, None
    tree = trees[0]
    types = [s.get("type") for s in tree.get("stages", [])]
    if not types or types[0] != "org.osbuild.container-deploy":
        problems.append(f"The os-tree pipeline doesn't start by unpacking the live system: its stages are {types}")
    if SELINUX_STAGE["type"] in types:
        problems.append("The os-tree pipeline labels its files already: image-builder does it now, so drop this "
                        "step (docs/decisions/0012-install-iso.md)")
    # The labels must reach the squashfs, which is made from this tree.
    squashfs = [s for p in pipelines for s in p.get("stages", []) if s.get("type") == "org.osbuild.squashfs"]
    if len(squashfs) != 1:
        problems.append(f"The manifest has {len(squashfs)} squashfs stages, not one")
    else:
        refs = json.dumps(squashfs[0].get("inputs", {}))
        if "name:os-tree" not in refs:
            problems.append(f"The squashfs isn't made from the os-tree pipeline: its inputs are {refs}")
    if problems:
        return problems, None
    tree["stages"].append(json.loads(json.dumps(SELINUX_STAGE)))
    return [], manifest


def load_iso_yaml(path):
    try:
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config["label"], [(e["name"], e["linux"], e["initrd"]) for e in config["grub2"]["entries"]]
    except (OSError, yaml.YAMLError, KeyError, TypeError) as e:
        raise InputError(f"{path}: {e}") from e


def menu_entries(text):
    """Return [(name, linux line, initrd line)] for each menuentry in a grub.cfg."""
    entries, current = [], None
    for line in text.splitlines():
        if m := MENUENTRY.match(line):
            current = [m.group(1), None, None]
            entries.append(current)
        elif current is not None and (m := LINUX.match(line)):
            current[1] = m.group(1)
        elif current is not None and (m := INITRD.match(line)):
            current[2] = m.group(1)
    return [tuple(e) for e in entries]


def boot(iso_yaml, iso_dir, iso_label):
    """Return (problems, a report) for the ISO mounted at iso_dir."""
    want_label, want_entries = load_iso_yaml(iso_yaml)
    root = Path(iso_dir)
    problems, report = [], []
    if iso_label != want_label:
        problems.append(f"The ISO's label is {iso_label!r}, not {want_label!r} as iso.yaml says: the initramfs "
                        "finds the USB by it")
    for name in BOOT_FILES:
        f = root / name
        if not f.is_file() or f.stat().st_size == 0:
            problems.append(f"{name} is missing or empty")
    if (root / FALLBACK).exists():
        problems.append(f"{FALLBACK} is there: shim would run it from a USB and add a boot entry to the firmware")
    for name in MENUS:
        f = root / name
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for word in SELINUX_OFF:
            if re.search(rf"(^|\s){re.escape(word)}(\s|$)", text, re.MULTILINE):
                problems.append(f"{name} has {word}, which turns SELinux off")
        entries = menu_entries(text)
        if len(entries) != len(want_entries):
            problems.append(f"{name} has {len(entries)} entries, not the {len(want_entries)} of iso.yaml")
        elif entries != want_entries:
            for n, (have, want) in enumerate(zip(entries, want_entries), 1):
                if have != want:
                    problems.append(f"Entry {n} of {name} is {have}, not {want} as in iso.yaml")
        else:
            report.append(f"{name}: {len(entries)} entries, as iso.yaml says")
        for _, linux, _ in entries:
            args = shlex.split(linux or "")
            if f"root=live:CDLABEL={iso_label}" not in args:
                problems.append(f"An entry in {name} doesn't find the USB by its label {iso_label!r}: {linux}")
    return problems, report


def main(argv):
    commands = {"label": 1, "boot": 3}
    if len(argv) < 2 or argv[1] not in commands or len(argv) != 2 + commands[argv[1]]:
        print("Usage: iso.py label MANIFEST | boot ISO_YAML ISO_DIR LABEL", file=sys.stderr)
        return 2
    command, args = argv[1], argv[2:]
    manifest, report = None, []
    try:
        if command == "label":
            problems, manifest = label(load_json(args[0]))
        else:
            if not Path(args[1]).is_dir():
                raise InputError(f"{args[1]} is not a folder")
            problems, report = boot(*args)
    except (InputError, OSError, UnicodeDecodeError) as e:
        print(f"iso.py: {e}", file=sys.stderr)
        return 2
    for line in report:
        print(line, file=sys.stderr)
    for problem in problems:
        print(f"Problem: {problem}", file=sys.stderr)
    if manifest is not None:
        json.dump(manifest, sys.stdout, indent=1)
        print()
        print("Added an SELinux stage to the os-tree pipeline.", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
