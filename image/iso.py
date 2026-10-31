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
#   python3 image/iso.py install-image KICKSTART
#       Print the name of the image the installer's kickstart
#       (installer/anaconda/interactive-defaults.ks) installs from the live
#       system's container storage, which is also the image the installed
#       system follows. Stops if its bootc command says otherwise (step 1.8c).
#   python3 image/iso.py payload STORAGE NAME IMAGE_ID VERSION
#       The container storage STORAGE, the live system's
#       /var/lib/containers/storage in the ISO's squashfs, holds the image
#       NAME with all its layers, and it is the signed build the ISO was made
#       from: its image ID, the digest of its configuration, is IMAGE_ID, and
#       its build version VERSION. The installer installs it (step 1.8c). Its
#       manifest isn't the build's own: copying an image out of container
#       storage rewrites the manifest with uncompressed layers (ADR 0014).
#
# image/make-iso.sh runs `label`, iso.yml runs `install-image`,
# image/check-iso.sh runs `boot` and `payload`, and test_iso.py runs them all
# on stand-ins. Exits 0 when all is well, 1 when something isn't (saying why),
# and 2 when the input can't be read.

import base64
import hashlib
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

# The installer's source: Anaconda's bootc command installs from this
# transport, the live system's container storage.
LOCAL_STORAGE = "containers-storage:"
# The label that carries a build's version (image/Containerfile).
VERSION_LABEL = "org.opencontainers.image.version"

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


def kickstart_commands(text, name):
    """Return the arguments of each command NAME in the kickstart TEXT, outside its %pre, %post and other sections."""
    commands, section = [], False
    for line in text.splitlines():
        if section:
            # A script's lines are shell, not kickstart.
            section = line.split()[:1] != ["%end"]
            continue
        words = shlex.split(line, comments=True)
        if not words:
            continue
        if words[0].startswith("%") and words[0] not in ("%include", "%ksappend"):
            section = words[0] != "%end"
        elif words[0] == name:
            commands.append(words[1:])
    return commands


def options(args):
    """Return the --name=value and --name value options in ARGS as {name: value}."""
    found, words = {}, iter(args)
    for word in words:
        if not word.startswith("--"):
            raise ValueError(f"{word!r} isn't an option")
        name, equals, value = word.partition("=")
        found[name] = value if equals else next(words, "")
    return found


def install_image(text):
    """Return (problems, the image name) for the kickstart TEXT's bootc command."""
    try:
        commands = kickstart_commands(text, "bootc")
        if len(commands) != 1:
            return [f"The kickstart has {len(commands)} bootc commands, not one"], None
        found = options(commands[0])
    except ValueError as e:
        return [f"The kickstart's bootc command can't be read: {e}"], None
    source, target = found.get("--source-imgref", ""), found.get("--target-imgref", "")
    if not source.startswith(LOCAL_STORAGE):
        return [f"bootc installs from {source!r}, not from the live system's {LOCAL_STORAGE}"], None
    name = source.removeprefix(LOCAL_STORAGE)
    if not name or name != target:
        return [f"bootc installs {name!r} from container storage, but the system then follows {target!r}"], None
    return [], name


def big_data_name(key):
    """Return the file name containers/storage keeps the data KEY of an image under (makeBigDataBaseName)."""
    if re.fullmatch(r"[.0-9a-z]+", key):
        return key
    return "=" + base64.b64encode(key.encode()).decode()


def payload(storage, name, image_id, version):
    """Return (problems, a report) for the image NAME in the container storage STORAGE."""
    root = Path(storage)
    images = load_json(root / "overlay-images/images.json")
    layers = {layer.get("id"): layer for layer in load_json(root / "overlay-layers/layers.json")}
    found = [i for i in images if name in (i.get("names") or [])]
    if len(found) != 1:
        held = sorted(n for i in images for n in i.get("names") or [])
        return [f"The container storage has {len(found)} images named {name}, not one; it has {held}"], []
    image = found[0]
    problems = []
    # The build, by its configuration: containers/storage names an image by
    # its configuration's digest, its manifest gives that digest, and the
    # configuration kept has it.
    if f"sha256:{image.get('id')}" != image_id:
        problems.append(f"{name} has the image ID sha256:{image.get('id')}, not {image_id}, the build's")
    folder = root / "overlay-images" / image.get("id", "")
    try:
        manifest = json.loads((folder / big_data_name("manifest")).read_bytes())
        raw = (folder / big_data_name(image_id)).read_bytes()
        config = json.loads(raw)
    except (OSError, ValueError) as e:
        return problems + [f"{name}'s manifest or configuration can't be read: {e}"], []
    if (manifest.get("config") or {}).get("digest") != image_id:
        problems.append(f"{name}'s manifest names the configuration {(manifest.get('config') or {}).get('digest')}, "
                        f"not {image_id}")
    if f"sha256:{hashlib.sha256(raw).hexdigest()}" != image_id:
        problems.append(f"{name}'s configuration doesn't have the digest {image_id}")
    have = ((config.get("config") or {}).get("Labels") or {}).get(VERSION_LABEL)
    if have != version:
        problems.append(f"{name} is build {have}, not {version}")
    # Its layers, from the top one down, each with its files.
    chain, layer = [], image.get("layer")
    while layer and len(chain) <= len(layers):
        chain.append(layer)
        if layer not in layers:
            problems.append(f"Layer {layer} of {name} isn't in the container storage")
            break
        if not (root / "overlay" / layer / "diff").is_dir():
            problems.append(f"Layer {layer} of {name} has no files (overlay/{layer}/diff)")
        layer = layers[layer].get("parent")
    if len(chain) != len(manifest.get("layers", [])):
        problems.append(f"{name} has {len(chain)} layers in the container storage, but its manifest lists "
                        f"{len(manifest.get('layers', []))}")
    return problems, [f"{name}: build {have}, image ID {image_id}, manifest {image.get('digest')}, {len(chain)} layers"]


def main(argv):
    commands = {"label": 1, "boot": 3, "install-image": 1, "payload": 4}
    if len(argv) < 2 or argv[1] not in commands or len(argv) != 2 + commands[argv[1]]:
        print("Usage: iso.py label MANIFEST | boot ISO_YAML ISO_DIR LABEL | install-image KICKSTART"
              " | payload STORAGE NAME IMAGE_ID VERSION", file=sys.stderr)
        return 2
    command, args = argv[1], argv[2:]
    manifest, report = None, []
    try:
        if command == "label":
            problems, manifest = label(load_json(args[0]))
        elif command == "install-image":
            problems, name = install_image(Path(args[0]).read_text(encoding="utf-8"))
            if name:
                print(name)
        elif command == "payload":
            if not Path(args[0]).is_dir():
                raise InputError(f"{args[0]} is not a folder")
            problems, report = payload(*args)
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
