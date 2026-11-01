# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for disk.py, on stand-ins for a disk image-builder made: the
# partition table as lsblk describes it, and folders laid out like the
# mounted partitions. `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory image

import contextlib
import copy
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import disk

IMAGE = "ghcr.io/edmundhills/lumen:dev"
VERSION = "44.20261029.1"
# image-builder puts the root's files in a Btrfs subvolume named root.
DEPLOYMENT = "root/ostree/deploy/default/deploy/0123abcd.0"


def part(path, size, parttype, fstype=None, label=None):
    return {"path": path, "type": "part", "size": size, "pttype": "gpt", "parttype": parttype,
            "fstype": fstype, "label": label}


# The disk image-builder 88.0.0 made of dev 44.20261029.1 in WSL, as
# `lsblk --json --bytes --tree` showed it.
LSBLK = {"blockdevices": [{
    "path": "/dev/loop0", "type": "loop", "size": 16639852544, "pttype": "gpt", "parttype": None,
    "fstype": None, "label": None, "children": [
        part("/dev/loop0p1", 1048576, "21686148-6449-6e6f-744e-656564454649"),
        part("/dev/loop0p2", 525336576, "c12a7328-f81f-11d2-ba4b-00a0c93ec93b", "vfat", "EFI-SYSTEM"),
        part("/dev/loop0p3", 1073741824, "bc13c2ff-59e6-4262-a352-b275fd6f7172", "ext4", "boot"),
        part("/dev/loop0p4", 15037628416, "4f68bce3-e8cd-4db1-96e7-fbcaf984b709", "btrfs", "root"),
    ]}]}

ORIGIN = f"""[origin]
container-image-reference=ostree-image-signed:docker://{IMAGE}
"""

OS_RELEASE = f"""NAME="Lumen OS"
ID=lumen
ID_LIKE=fedora
VERSION_ID=0.1
PRETTY_NAME="Lumen OS 0.1"
IMAGE_VERSION={VERSION}
"""

# On a /boot partition of its own, an entry names its files from the top of
# that partition. bootc writes the subvolume's rootflags, image/disk.toml the
# compression's.
ENTRY = """title Lumen OS 0.1 (ostree:0)
version 1
options root=UUID=1234 rootflags=subvol=/root rw console=tty0 console=ttyS0 rootflags=compress=zstd:1 ostree=/ostree/boot.1/default/abcd/0
linux /ostree/default-abcd/vmlinuz-6.17.5-300.fc44.x86_64
initrd /ostree/default-abcd/initramfs-6.17.5-300.fc44.x86_64.img
"""


BOOT_T = "system_u:object_r:boot_t:s0"
ROOT_T = "system_u:object_r:root_t:s0"


class DiskTest(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work)
        # SELinux labels, which a test can't write without privileges: by path.
        self.labels = {}
        for name, fake in (("read_label", lambda path: self.labels.get(str(path))),
                           ("write_label", lambda path, label: self.labels.__setitem__(str(path), label))):
            patcher = mock.patch.object(disk, name, fake)
            patcher.start()
            self.addCleanup(patcher.stop)

    def labeled(self, relative, label):
        """Write the file RELATIVE with the SELinux label LABEL, or none if LABEL is None."""
        path = self.write(relative, "{}")
        self.labels.pop(str(path), None)
        if label:
            self.labels[str(path)] = label
        return path

    def write(self, relative, text=""):
        path = self.work / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = disk.main(["disk.py", *args])
        return status, out.getvalue(), err.getvalue()

    # The partition table

    def partitions(self, lsblk):
        return self.run_main("partitions", str(self.write("lsblk.json", json.dumps(lsblk))))

    def test_partitions_of_a_good_disk(self):
        status, out, err = self.partitions(LSBLK)
        self.assertEqual(status, 0, err)
        self.assertEqual(out.split("\n"),
                         ["esp /dev/loop0p2 vfat", "boot /dev/loop0p3 ext4", "root /dev/loop0p4 btrfs", ""])
        self.assertIn("/dev/loop0p4: 14.0 GiB", err)

    def test_partitions_listed_flat(self):
        # Without --tree, lsblk lists the partitions after the disk.
        disk = copy.deepcopy(LSBLK["blockdevices"][0])
        parts = disk.pop("children")
        status, out, err = self.partitions({"blockdevices": [disk, *parts]})
        self.assertEqual(status, 0, err)
        self.assertIn("root /dev/loop0p4 btrfs", out)

    def test_partitions_need_gpt(self):
        lsblk = copy.deepcopy(LSBLK)
        lsblk["blockdevices"][0]["pttype"] = "dos"
        status, _, err = self.partitions(lsblk)
        self.assertEqual(status, 1)
        self.assertIn("the partition table is dos, not GPT", err)

    def test_partitions_need_a_btrfs_root(self):
        lsblk = copy.deepcopy(LSBLK)
        lsblk["blockdevices"][0]["children"][3]["fstype"] = "xfs"
        status, out, err = self.partitions(lsblk)
        self.assertEqual(status, 1)
        self.assertIn("the root filesystem is xfs, not Btrfs", err)
        # The partitions are still named, so the other checks can run.
        self.assertIn("root /dev/loop0p4 xfs", out)

    def test_partitions_need_a_fat_esp(self):
        lsblk = copy.deepcopy(LSBLK)
        lsblk["blockdevices"][0]["children"][1]["fstype"] = None
        status, _, err = self.partitions(lsblk)
        self.assertEqual(status, 1)
        self.assertIn("the EFI system partition holds no filesystem, not FAT", err)

    def test_partitions_need_one_boot(self):
        lsblk = copy.deepcopy(LSBLK)
        del lsblk["blockdevices"][0]["children"][2]
        status, out, err = self.partitions(lsblk)
        self.assertEqual(status, 1)
        self.assertIn("expected one /boot partition (XBOOTLDR), found 0", err)
        self.assertNotIn("boot ", out)

    def test_partitions_need_a_root_of_the_right_type(self):
        # A generic Linux data partition isn't the root of the Discoverable
        # Partitions Specification, which image-builder marks.
        lsblk = copy.deepcopy(LSBLK)
        lsblk["blockdevices"][0]["children"][3]["parttype"] = "0fc63daf-8483-4772-8e79-3d69d8477de4"
        status, _, err = self.partitions(lsblk)
        self.assertEqual(status, 1)
        self.assertIn("expected one x86-64 root partition, found 0", err)
        self.assertIn("/dev/loop0p4 is a partition Lumen doesn't expect", err)

    def test_partitions_refuse_one_lumen_does_not_expect(self):
        lsblk = copy.deepcopy(LSBLK)
        lsblk["blockdevices"][0]["children"].append(
            part("/dev/loop0p5", 2**30, "0657fd6d-a4ab-43c4-84e5-0933c84b4f4f", "swap"))
        status, _, err = self.partitions(lsblk)
        self.assertEqual(status, 1)
        self.assertIn("/dev/loop0p5 is a partition Lumen doesn't expect", err)

    def test_partitions_of_unreadable_input(self):
        status, _, err = self.run_main("partitions", str(self.write("lsblk.json", "not json")))
        self.assertEqual(status, 2)
        self.assertIn("disk.py:", err)

    # The EFI system partition

    def make_esp(self, skip=()):
        for f in disk.ESP_FILES:
            if f not in skip:
                self.write(f"esp/{f}")
        return str(self.work / "esp")

    def test_esp_with_shim_and_grub(self):
        status, _, err = self.run_main("esp", self.make_esp())
        self.assertEqual(status, 0, err)

    def test_esp_needs_the_fallback_loader(self):
        status, _, err = self.run_main("esp", self.make_esp(skip=("EFI/BOOT/BOOTX64.EFI",)))
        self.assertEqual(status, 1)
        self.assertIn("has no EFI/BOOT/BOOTX64.EFI", err)

    # /boot

    def make_boot(self, entry=ENTRY, state_label=BOOT_T):
        self.labeled("boot/bootupd-state.json", state_label)
        self.write("boot/loader/entries/ostree-1.conf", entry)
        self.write("boot/ostree/default-abcd/vmlinuz-6.17.5-300.fc44.x86_64")
        self.write("boot/ostree/default-abcd/initramfs-6.17.5-300.fc44.x86_64.img")
        return str(self.work / "boot")

    def test_boot_with_one_entry(self):
        status, _, err = self.run_main("boot", self.make_boot())
        self.assertEqual(status, 0, err)
        self.assertIn("console=ttyS0", err)

    def test_boot_needs_the_kernel_it_names(self):
        boot = self.make_boot(ENTRY.replace("vmlinuz-6.17.5", "vmlinuz-6.18.0"))
        status, _, err = self.run_main("boot", boot)
        self.assertEqual(status, 1)
        self.assertIn("the boot entry's linux, /ostree/default-abcd/vmlinuz-6.18.0", err)

    def test_boot_mounts_the_root_compressed(self):
        for options, ok in (("rootflags=subvol=/root rootflags=compress=zstd:1", True),
                            ("rootflags=subvol=/root,compress=zstd:1", True),
                            ("rootflags=subvol=/root", False),
                            ("rootflags=subvol=/root rootflags=compress=zstd:3", False)):
            with self.subTest(options):
                entry = ENTRY.replace("rootflags=subvol=/root", "ROOT", 1).replace(" rootflags=compress=zstd:1", "")
                status, _, err = self.run_main("boot", self.make_boot(entry.replace("ROOT", options)))
                self.assertEqual(status, 0 if ok else 1, err)
                if not ok:
                    self.assertIn("without compress=zstd:1", err)

    def test_boot_needs_an_ostree_entry(self):
        status, _, err = self.run_main("boot", self.make_boot(ENTRY.replace(" ostree=", " root2=")))
        self.assertEqual(status, 1)
        self.assertIn("no ostree= option", err)

    def test_boot_needs_bootupds_state_labeled(self):
        status, _, err = self.run_main("boot", self.make_boot())
        self.assertIn(f"SELinux labels: bootupd-state.json {BOOT_T}", err)
        for label in (None, "system_u:object_r:unlabeled_t:s0"):
            with self.subTest(label):
                status, _, err = self.run_main("boot", self.make_boot(state_label=label))
                self.assertEqual(status, 1)
                self.assertIn(f"bootupd-state.json is labeled {label or 'nothing'}, not {BOOT_T}", err)
        (self.work / "boot/bootupd-state.json").unlink()
        status, _, err = self.run_main("boot", str(self.work / "boot"))
        self.assertEqual(status, 1)
        self.assertIn("boot has no bootupd-state.json", err)

    def test_boot_needs_exactly_one_entry(self):
        boot = self.make_boot()
        self.write("boot/loader/entries/ostree-2.conf", ENTRY)
        status, _, err = self.run_main("boot", boot)
        self.assertEqual(status, 1)
        self.assertIn("expected one boot entry in /boot/loader/entries, found 2", err)

    # The root filesystem

    def make_root(self, origin=ORIGIN, os_release=OS_RELEASE, aleph_label=ROOT_T):
        # bootc's record of the install, at the top of the subvolume.
        self.labeled("root/root/.bootc-aleph.json", aleph_label)
        self.write(f"root/{DEPLOYMENT}.origin", origin)
        if os_release is not None:
            self.write(f"root/{DEPLOYMENT}/usr/lib/os-release", os_release)
        return str(self.work / "root")

    def test_root_follows_the_image_signed(self):
        root = self.make_root()
        self.write(f"root/{DEPLOYMENT}/etc/systemd/system/-.mount",
                   "[Mount]\nWhat=/dev/disk/by-uuid/0845\nWhere=/\nType=btrfs\nOptions=subvol=root,compress=zstd:1,ro\n")
        status, _, err = self.run_main("root", root, IMAGE, VERSION)
        self.assertEqual(status, 0, err)
        self.assertIn(f"Follows: ostree-image-signed:docker://{IMAGE}", err)
        self.assertIn("Root mount options: subvol=root,compress=zstd:1,ro", err)

    def test_root_without_a_subvolume(self):
        self.labeled("root/.bootc-aleph.json", ROOT_T)
        self.write("root/ostree/deploy/default/deploy/0123abcd.0.origin", ORIGIN)
        self.write("root/ostree/deploy/default/deploy/0123abcd.0/usr/lib/os-release", OS_RELEASE)
        status, _, err = self.run_main("root", str(self.work / "root"), IMAGE, VERSION)
        self.assertEqual(status, 0, err)
        self.assertIn("Deployment: ostree/deploy/default/deploy/0123abcd.0", err)

    def test_root_refuses_the_unverified_transport(self):
        # What Anaconda's ostreecontainer command records (ADR 0008).
        origin = ORIGIN.replace("ostree-image-signed:", "ostree-unverified-registry:")
        status, _, err = self.run_main("root", self.make_root(origin), IMAGE, VERSION)
        self.assertEqual(status, 1)
        self.assertIn(f"follows ostree-unverified-registry:docker://{IMAGE}, not ostree-image-signed:", err)

    def test_root_refuses_another_image(self):
        origin = ORIGIN.replace(IMAGE, "localhost/lumen:ci-rechunked")
        status, _, err = self.run_main("root", self.make_root(origin), IMAGE, VERSION)
        self.assertEqual(status, 1)
        self.assertIn("follows ostree-image-signed:docker://localhost/lumen:ci-rechunked", err)

    def test_root_needs_the_build_version(self):
        status, _, err = self.run_main("root", self.make_root(), IMAGE, "44.20261030")
        self.assertEqual(status, 1)
        self.assertIn(f"IMAGE_VERSION={VERSION}, not 44.20261030", err)

    def test_root_needs_lumen(self):
        status, _, err = self.run_main("root", self.make_root(os_release=OS_RELEASE.replace("ID=lumen", "ID=fedora")),
                                       IMAGE, VERSION)
        self.assertEqual(status, 1)
        self.assertIn("os-release says ID=fedora, not lumen", err)

    def test_root_needs_os_release(self):
        status, _, err = self.run_main("root", self.make_root(os_release=None), IMAGE, VERSION)
        self.assertEqual(status, 1)
        self.assertIn("the deployment has no /usr/lib/os-release", err)

    def test_root_needs_bootcs_record_labeled(self):
        # What a relabel by Fedora's policy gives it: default_t.
        default_t = "system_u:object_r:default_t:s0"
        status, _, err = self.run_main("root", self.make_root(aleph_label=default_t), IMAGE, VERSION)
        self.assertEqual(status, 1)
        self.assertIn(f".bootc-aleph.json is labeled {default_t}, not {ROOT_T}", err)

    # Labeling

    def test_label_both_files(self):
        boot = self.make_boot(state_label=None)
        root = self.make_root(aleph_label="system_u:object_r:default_t:s0")
        for role, folder in (("boot", boot), ("root", root)):
            with self.subTest(role):
                status, _, err = self.run_main("label", role, folder)
                self.assertEqual(status, 0, err)
                self.assertIn("Labeled ", err)
        self.assertEqual(self.labels, {str(self.work / "boot/bootupd-state.json"): BOOT_T,
                                       str(self.work / "root/root/.bootc-aleph.json"): ROOT_T})
        self.assertEqual(self.run_main("boot", boot)[0], 0)
        self.assertEqual(self.run_main("root", root, IMAGE, VERSION)[0], 0)

    def test_label_needs_the_files(self):
        root = self.make_root()
        (self.work / "root/root/.bootc-aleph.json").unlink()
        status, _, err = self.run_main("label", "root", root)
        self.assertEqual(status, 1)
        self.assertIn("root has no .bootc-aleph.json", err)
        self.assertEqual(self.run_main("label", "esp", root)[0], 2)

    def test_a_file_without_a_label(self):
        with mock.patch.object(disk, "read_label", DiskTest.real_read_label):
            self.assertIsNone(disk.read_label(self.write("plain")))

    def test_root_needs_one_deployment(self):
        root = self.make_root()
        self.write("root/root/ostree/deploy/default/deploy/4567cdef.0.origin", ORIGIN)
        status, _, err = self.run_main("root", root, IMAGE, VERSION)
        self.assertEqual(status, 1)
        self.assertIn("expected one ostree deployment, found 2", err)

    def test_a_missing_folder(self):
        status, _, err = self.run_main("esp", str(self.work / "nothing"))
        self.assertEqual(status, 2)
        self.assertIn("is not a folder", err)

    def test_usage(self):
        status, _, err = self.run_main("root", "only-one-argument")
        self.assertEqual(status, 2)
        self.assertIn("Usage:", err)


DiskTest.real_read_label = staticmethod(disk.read_label)

if __name__ == "__main__":
    unittest.main()
