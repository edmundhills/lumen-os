#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check a disk that image-builder made from a Lumen image, such as the qcow2
# for the boot test (step 1.8a, docs/decisions/0011-disk-images.md): what bootc
# installed on it, as a system booted from it would find it.
#
# Usage:
#   python3 image/disk.py partitions LSBLK_JSON
#       The partition table, as `lsblk --json --bytes --output
#       PATH,TYPE,SIZE,PTTYPE,PARTTYPE,FSTYPE,LABEL DISK` gives it: GPT, with
#       an EFI system partition (FAT), a /boot partition and a Btrfs root.
#       Prints a line ROLE DEVICE FSTYPE for each it finds, ROLE being esp,
#       boot or root.
#   python3 image/disk.py esp DIR
#       The mounted EFI system partition: shim as the fallback boot loader,
#       and Fedora's shim, GRUB and its menu, which bootupd installs.
#   python3 image/disk.py boot DIR
#       The mounted /boot: one boot entry for an ostree deployment, with the
#       kernel and initramfs it names, and bootupd's state file with the
#       SELinux label in LABELS.
#   python3 image/disk.py root DIR IMAGE VERSION
#       The mounted root filesystem: one ostree deployment, which follows
#       IMAGE with the signed transport (docs/decisions/0008-image-signing.md),
#       and whose os-release says it is Lumen at build version VERSION; and
#       bootc's record of the install with the SELinux label in LABELS.
#   python3 image/disk.py label boot|root DIR
#       Give the files in LABELS on the mounted /boot or root filesystem their
#       labels (image/label-disk.sh mounts them read-write).
#
# image/check-disk.sh mounts the disk read-only and runs these; test_disk.py
# runs them on stand-ins. Each writes what it found to standard error, and
# exits 0 when the disk is as it should be, 1 when it isn't (saying why), and
# 2 when its input can't be read.

import errno
import json
import os
import sys
from pathlib import Path

# Partition type GUIDs (the Discoverable Partitions Specification).
ESP = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
XBOOTLDR = "bc13c2ff-59e6-4262-a352-b275fd6f7172"
ROOT_X86_64 = "4f68bce3-e8cd-4db1-96e7-fbcaf984b709"
BIOS_BOOT = "21686148-6449-6e6f-744e-656564454649"

# What bootupd puts on the EFI system partition: shim as the fallback boot
# loader, which firmware starts from a disk it has no boot entry for, and
# Fedora's signed shim and GRUB with the menu that finds /boot.
ESP_FILES = ("EFI/BOOT/BOOTX64.EFI", "EFI/fedora/shimx64.efi", "EFI/fedora/grubx64.efi", "EFI/fedora/grub.cfg")


# The SELinux labels of two files bootc and bootupd write as they install,
# relative to /boot and to the top of the root filesystem (/sysroot in the
# booted system). bootupd reads both at every boot. Neither tool labels them:
# the kernel does as they are created, where SELinux is on, as in the ISO's
# installer. image-builder runs them on a build machine where it is off, so
# image/label-disk.sh gives them these (docs/decisions/0018-disk-labels.md).
# /boot/.* is boot_t in Fedora's policy; it has no line for bootc's file, but
# gives root_t to the older /sysroot/.aleph-version.json.
LABELS = {
    "boot": {"bootupd-state.json": "system_u:object_r:boot_t:s0"},
    "root": {".bootc-aleph.json": "system_u:object_r:root_t:s0"},
}


class InputError(Exception):
    pass


def read_label(path):
    """PATH's SELinux label, or None if it has none."""
    try:
        return os.getxattr(path, "security.selinux", follow_symlinks=False).rstrip(b"\0").decode()
    except OSError as e:
        if e.errno in (errno.ENODATA, errno.ENOTSUP):
            return None
        raise


def write_label(path, label):
    # With the null at the end, as the kernel and setfiles store it.
    os.setxattr(path, "security.selinux", label.encode() + b"\0", follow_symlinks=False)


def check_labels(role, base):
    """Problems with the labels of ROLE's files in LABELS, under BASE, and a report of them."""
    problems, found = [], []
    for name, want in LABELS[role].items():
        path = Path(base) / name
        if not path.is_file():
            problems.append(f"{role} has no {name}")
            continue
        label = read_label(path)
        found.append(f"{name} {label or 'unlabeled'}")
        if label != want:
            problems.append(f"{name} is labeled {label or 'nothing'}, not {want} (image/label-disk.sh sets it)")
    return problems, [f"SELinux labels: {', '.join(found)}"] if found else []


def deployments(top):
    """The origin files of the ostree deployments on the root filesystem mounted at TOP."""
    # image-builder puts the root's files in a Btrfs subvolume, so the
    # deployment may be one folder below the top of the filesystem.
    top = Path(top)
    return sorted(top.glob("ostree/deploy/*/deploy/*.origin")) + sorted(top.glob("*/ostree/deploy/*/deploy/*.origin"))


def physical_root(origin):
    """The folder holding ostree/ for the deployment whose origin file is ORIGIN: /sysroot when booted."""
    return origin.parents[4]


def label(role, base):
    """Give ROLE's files in LABELS, under BASE, their labels."""
    if role == "root":
        origins = deployments(base)
        if len(origins) != 1:
            return [f"expected one ostree deployment, found {len(origins)}"], []
        base = physical_root(origins[0])
    report = []
    for name, want in LABELS[role].items():
        path = Path(base) / name
        if path.is_file():
            write_label(path, want)
            report.append(f"Labeled {name} {want}")
    problems, found = check_labels(role, base)
    return problems, report + found


def size(n):
    return f"{n / 2**30:.1f} GiB" if n >= 2**30 else f"{n / 2**20:.0f} MiB"


def partitions(lsblk_path):
    """Return (problems, a report, {role: device}) for the disk lsblk described."""
    try:
        with open(lsblk_path, encoding="utf-8") as f:
            devices = json.load(f)["blockdevices"]
    except (OSError, ValueError, KeyError) as e:
        raise InputError(f"{lsblk_path}: {e}") from e
    # lsblk nests the partitions under the disk with --tree, and lists them
    # after it without.
    disks = [d for d in devices if d.get("type") != "part"]
    if len(disks) != 1:
        raise InputError(f"{lsblk_path}: expected one disk, found {len(disks)}")
    disk = disks[0]
    parts = [p for p in (disk.get("children") or devices) if p.get("type") == "part"]
    problems, report, roles = [], [], {}
    if disk.get("pttype") != "gpt":
        problems.append(f"the partition table is {disk.get('pttype') or 'missing'}, not GPT")
    for p in parts:
        report.append(f"{p['path']}: {size(int(p['size']))}, type {p.get('parttype')}, "
                      f"{p.get('fstype') or 'no filesystem'}, label {p.get('label') or 'none'}")

    def one(role, what, parttype):
        found = [p for p in parts if (p.get("parttype") or "").lower() == parttype]
        if len(found) != 1:
            problems.append(f"expected one {what}, found {len(found)}")
            return None
        roles[role] = f"{found[0]['path']} {found[0].get('fstype') or 'none'}"
        return found[0]

    esp = one("esp", "EFI system partition", ESP)
    if esp and esp.get("fstype") != "vfat":
        problems.append(f"the EFI system partition holds {esp.get('fstype') or 'no filesystem'}, not FAT")
    boot = one("boot", "/boot partition (XBOOTLDR)", XBOOTLDR)
    if boot and not boot.get("fstype"):
        problems.append("the /boot partition has no filesystem")
    # The spec asks for a Btrfs root; Lumen's bootc install config says so
    # (image/overlay/usr/lib/bootc/install/20-lumen.toml).
    root = one("root", "x86-64 root partition", ROOT_X86_64)
    if root and root.get("fstype") != "btrfs":
        problems.append(f"the root filesystem is {root.get('fstype') or 'missing'}, not Btrfs")
    for p in parts:
        if (p.get("parttype") or "").lower() not in {ESP, XBOOTLDR, ROOT_X86_64, BIOS_BOOT}:
            problems.append(f"{p['path']} is a partition Lumen doesn't expect")
    return problems, report, roles


def esp(root):
    root = Path(root)
    missing = [f for f in ESP_FILES if not (root / f).is_file()]
    problems = [f"the EFI system partition has no {f}" for f in missing]
    return problems, [f"EFI system partition: {', '.join(f for f in ESP_FILES if f not in missing)}"]


def read_entry(path):
    """The keys of a Boot Loader Specification entry, as {key: value}."""
    entry = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, value = line.strip().partition(" ")
        if key and not key.startswith("#"):
            entry[key] = value.strip()
    return entry


def boot(root):
    root = Path(root)
    entries = sorted((root / "loader" / "entries").glob("*.conf"))
    if len(entries) != 1:
        return [f"expected one boot entry in /boot/loader/entries, found {len(entries)}"], []
    entry = read_entry(entries[0])
    problems = []
    for key in ("linux", "initrd"):
        name = entry.get(key, "")
        if not name:
            problems.append(f"the boot entry {entries[0].name} names no {key}")
        elif not (root / name.lstrip("/")).is_file():
            problems.append(f"the boot entry's {key}, {name}, isn't on /boot")
    options = entry.get("options", "").split()
    if not any(o.startswith("ostree=") for o in options):
        problems.append("the boot entry doesn't start an ostree deployment (no ostree= option)")
    # The Btrfs root is mounted with zstd compression (image/disk.toml, ADR
    # 0016): systemd joins every rootflags= into one list of mount options.
    rootflags = ",".join(o.split("=", 1)[1] for o in options if o.startswith("rootflags="))
    if "compress=zstd:1" not in rootflags.split(","):
        problems.append(f"the kernel arguments mount the root without compress=zstd:1 (rootflags: {rootflags or 'none'})")
    labels, found = check_labels("boot", root)
    return problems + labels, [f"Boot entry {entries[0].name}: {entry.get('title', 'no title')}",
                               f"Kernel arguments: {' '.join(options)}", *found]


def read_keyfile(path):
    """The values of an ostree origin file, as {(group, key): value}."""
    values, group = {}, ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            group = line[1:-1]
        elif "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            values[(group, key.strip())] = value.strip()
    return values


def read_os_release(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.startswith("#"):
            values[key.strip()] = value.strip().strip('"')
    return values


def mount_options(deployment):
    """The options of the root's mount unit, which image-builder writes in the deployment's /etc, or None."""
    unit = deployment / "etc/systemd/system/-.mount"
    if not unit.is_file():
        return None
    for line in unit.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "Options":
            return value.strip()
    return ""


def root(top, image, version):
    top = Path(top)
    origins = deployments(top)
    if len(origins) != 1:
        return [f"expected one ostree deployment, found {len(origins)}"], []
    origin = origins[0]
    deployment = origin.with_suffix("")
    problems, report = check_labels("root", physical_root(origin))
    report.insert(0, f"Deployment: {deployment.relative_to(top)}")
    options = mount_options(deployment)
    if options is not None:
        report.append(f"Root mount options: {options}")
    reference = read_keyfile(origin).get(("origin", "container-image-reference"), "")
    report.append(f"Follows: {reference or 'nothing'}")
    want = f"ostree-image-signed:docker://{image}"
    if reference != want:
        problems.append(f"the deployment follows {reference or 'nothing'}, not {want}")
    os_release = deployment / "usr/lib/os-release"
    if not os_release.is_file():
        return problems + ["the deployment has no /usr/lib/os-release"], report
    fields = read_os_release(os_release)
    report.append(f"os-release: {fields.get('PRETTY_NAME', '?')}, build {fields.get('IMAGE_VERSION', '?')}")
    for key, value in (("ID", "lumen"), ("IMAGE_VERSION", version)):
        if fields.get(key) != value:
            problems.append(f"the deployment's os-release says {key}={fields.get(key, '')}, not {value}")
    return problems, report


def main(argv):
    commands = {"partitions": 1, "esp": 1, "boot": 1, "root": 3, "label": 2}
    if (len(argv) < 2 or argv[1] not in commands or len(argv) != 2 + commands[argv[1]]
            or (argv[1] == "label" and argv[2] not in LABELS)):
        print("Usage: disk.py partitions LSBLK_JSON | esp DIR | boot DIR | root DIR IMAGE VERSION"
              " | label boot|root DIR", file=sys.stderr)
        return 2
    command, args = argv[1], argv[2:]
    try:
        if command == "partitions":
            problems, report, roles = partitions(*args)
        elif command == "label":
            if not Path(args[1]).is_dir():
                raise InputError(f"{args[1]} is not a folder")
            problems, report = label(*args)
            roles = {}
        else:
            if not Path(args[0]).is_dir():
                raise InputError(f"{args[0]} is not a folder")
            problems, report = {"esp": esp, "boot": boot, "root": root}[command](*args)
            roles = {}
    except (InputError, OSError, UnicodeDecodeError) as e:
        print(f"disk.py: {e}", file=sys.stderr)
        return 2
    for line in report:
        print(line, file=sys.stderr)
    for problem in problems:
        print(f"Problem: {problem}", file=sys.stderr)
    for role, device in roles.items():
        print(role, device)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
