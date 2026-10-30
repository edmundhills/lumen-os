# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for iso.py, on stand-ins: a manifest laid out as the one
# `image-builder manifest generic-iso` 88.0.0 made of the live system, and a
# folder laid out like the ISO osbuild built from it. `just test` runs them in
# the lint container:
#   python3 -m unittest discover --start-directory image

import contextlib
import copy
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

import iso

REPO = Path(__file__).resolve().parent.parent
ISO_YAML = REPO / "image/live/iso.yaml"


def tree_input(pipeline):
    return {"type": "org.osbuild.tree", "origin": "org.osbuild.pipeline", "references": [f"name:{pipeline}"]}


def deploy():
    return {"type": "org.osbuild.container-deploy", "inputs": {"images": {
        "type": "org.osbuild.containers-storage", "origin": "org.osbuild.source",
        "references": {"sha256:d3f4a1ef": {"name": "localhost/lumen-live:ci"}}}},
        "options": {"remove-signatures": True}}


# The pipelines and the stages that matter here, as image-builder 88.0.0 made
# them on 2026-10-29; the boot stages' options are left out.
MANIFEST = {"version": "2", "pipelines": [
    {"name": "build", "stages": [deploy(), {"type": "org.osbuild.selinux", "options": {
        "file_contexts": "etc/selinux/targeted/contexts/files/file_contexts", "exclude_paths": ["/sysroot"]}}]},
    {"name": "os-tree", "build": "name:build", "stages": [deploy()]},
    {"name": "efiboot-tree", "build": "name:build", "stages": [{"type": "org.osbuild.grub2.iso"}]},
    {"name": "bootiso-tree", "build": "name:build", "stages": [
        {"type": "org.osbuild.copy", "inputs": {"tree": tree_input("os-tree")}},
        {"type": "org.osbuild.squashfs", "inputs": {"tree": tree_input("os-tree")},
         "options": {"filename": "LiveOS/squashfs.img", "compression": {"method": "zstd"}}},
        {"type": "org.osbuild.grub2.iso.legacy"}]},
    {"name": "bootiso", "build": "name:build", "stages": [
        {"type": "org.osbuild.xorrisofs", "options": {"filename": "install.iso", "volid": "Lumen-Live"}},
        {"type": "org.osbuild.implantisomd5", "options": {"filename": "install.iso"}}]},
], "sources": {"org.osbuild.containers-storage": {"items": {"sha256:d3f4a1ef": {}}}}}


def pipeline(manifest, name):
    return next(p for p in manifest["pipelines"] if p["name"] == name)


class LabelTest(unittest.TestCase):
    def test_adds_the_stage_to_the_live_tree(self):
        problems, labelled = iso.label(copy.deepcopy(MANIFEST))
        self.assertEqual(problems, [])
        stages = pipeline(labelled, "os-tree")["stages"]
        self.assertEqual([s["type"] for s in stages], ["org.osbuild.container-deploy", "org.osbuild.selinux"])
        self.assertEqual(stages[1]["options"], {"file_contexts": "etc/selinux/targeted/contexts/files/file_contexts"})
        # Nothing else changes.
        for p in labelled["pipelines"]:
            if p["name"] != "os-tree":
                self.assertEqual(p, pipeline(MANIFEST, p["name"]))
        self.assertEqual(labelled["sources"], MANIFEST["sources"])

    def test_stops_when_the_tree_is_labelled_already(self):
        problems, _ = iso.label(iso.label(copy.deepcopy(MANIFEST))[1])
        self.assertEqual(len(problems), 1)
        self.assertIn("image-builder does it now", problems[0])

    def test_stops_when_the_layout_changes(self):
        cases = {}
        m = copy.deepcopy(MANIFEST)
        pipeline(m, "os-tree")["name"] = "rootfs"
        cases["no os-tree"] = (m, "0 pipelines named os-tree")
        m = copy.deepcopy(MANIFEST)
        m["pipelines"].append(copy.deepcopy(pipeline(m, "os-tree")))
        cases["two os-trees"] = (m, "2 pipelines named os-tree")
        m = copy.deepcopy(MANIFEST)
        pipeline(m, "os-tree")["stages"].insert(0, {"type": "org.osbuild.mkdir"})
        cases["another first stage"] = (m, "doesn't start by unpacking")
        m = copy.deepcopy(MANIFEST)
        pipeline(m, "bootiso-tree")["stages"][1]["inputs"]["tree"] = tree_input("rootfs-tree")
        cases["squashfs of another tree"] = (m, "isn't made from the os-tree pipeline")
        m = copy.deepcopy(MANIFEST)
        del pipeline(m, "bootiso-tree")["stages"][1]
        cases["no squashfs"] = (m, "0 squashfs stages")
        cases["no pipelines"] = ({"version": "3"}, "no list of pipelines")
        for name, (manifest, message) in cases.items():
            with self.subTest(name):
                problems, labelled = iso.label(manifest)
                self.assertIsNone(labelled)
                self.assertTrue(any(message in p for p in problems), problems)


def grub_cfg(entries):
    """A menu as osbuild's grub2.iso stages write it, for the entries given."""
    lines = ["set default=\"0\"", "set timeout=10", "search --no-floppy --set=root -l 'Lumen-Live'", ""]
    for name, linux, initrd in entries:
        lines += [f"menuentry '{name}' --class fedora --class gnu-linux --class gnu --class os {{",
                  f"\tlinux {linux}", f"\tinitrd {initrd}", "}"]
    return "\n".join(lines) + "\n"


class BootTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.label, self.entries = iso.load_iso_yaml(ISO_YAML)
        for name in iso.BOOT_FILES:
            f = self.dir / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(grub_cfg(self.entries) if name in iso.MENUS else "x", encoding="utf-8")

    def problems(self):
        return iso.boot(ISO_YAML, self.dir, self.label)[0]

    def assertProblem(self, text):
        problems = self.problems()
        self.assertTrue(any(text in p for p in problems), problems)

    def test_an_iso_as_it_should_be(self):
        problems, report = iso.boot(ISO_YAML, self.dir, self.label)
        self.assertEqual(problems, [])
        self.assertEqual(len(report), 2)

    def test_the_label(self):
        self.assertTrue(any("not 'Lumen-Live'" in p for p in iso.boot(ISO_YAML, self.dir, "Fedora")[0]))

    def test_each_boot_file(self):
        for name in iso.BOOT_FILES:
            with self.subTest(name):
                f = self.dir / name
                data = f.read_bytes()
                f.unlink()
                self.assertProblem(f"{name} is missing")
                f.write_bytes(b"")
                self.assertProblem(f"{name} is missing or empty")
                f.write_bytes(data)

    def test_no_fallback_loader(self):
        (self.dir / iso.FALLBACK).write_text("x", encoding="utf-8")
        self.assertProblem("add a boot entry to the firmware")

    def test_selinux_stays_on(self):
        for word in iso.SELINUX_OFF:
            with self.subTest(word):
                name, linux, initrd = self.entries[0]
                entries = [(name, f"{linux} {word}", initrd)] + self.entries[1:]
                (self.dir / "boot/grub2/grub.cfg").write_text(grub_cfg(entries), encoding="utf-8")
                self.assertProblem(f"boot/grub2/grub.cfg has {word}")

    def test_the_menu_is_iso_yaml_s(self):
        (self.dir / "EFI/BOOT/grub.cfg").write_text(grub_cfg(self.entries[:1]), encoding="utf-8")
        self.assertProblem(f"EFI/BOOT/grub.cfg has 1 entries, not the {len(self.entries)} of iso.yaml")
        name, linux, initrd = self.entries[1]
        entries = self.entries[:1] + [(name.upper(), linux, initrd)] + self.entries[2:]
        (self.dir / "EFI/BOOT/grub.cfg").write_text(grub_cfg(entries), encoding="utf-8")
        self.assertProblem("Entry 2 of EFI/BOOT/grub.cfg is")

    def test_each_entry_finds_the_usb(self):
        entries = [(n, linux.replace("CDLABEL=Lumen-Live", "CDLABEL=Other"), i) for n, linux, i in self.entries]
        yaml_file = self.dir / "iso.yaml"
        yaml_file.write_text(yaml.safe_dump({"label": self.label, "grub2": {"entries": [
            {"name": n, "linux": linux, "initrd": i} for n, linux, i in entries]}}), encoding="utf-8")
        for name in iso.MENUS:
            (self.dir / name).write_text(grub_cfg(entries), encoding="utf-8")
        problems = iso.boot(yaml_file, self.dir, self.label)[0]
        self.assertEqual(len([p for p in problems if "doesn't find the USB" in p]), 2 * len(entries))

    def test_main(self):
        manifest = self.dir / "manifest.json"
        manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(iso.main(["iso.py", "label", str(manifest)]), 0)
            self.assertEqual(iso.main(["iso.py", "boot", str(ISO_YAML), str(self.dir), self.label]), 0)
        labelled = json.loads(out.getvalue())
        self.assertEqual(labelled, iso.label(copy.deepcopy(MANIFEST))[1])
        # A manifest it can't label prints nothing to standard output.
        manifest.write_text(json.dumps(labelled), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(iso.main(["iso.py", "label", str(manifest)]), 1)
            self.assertEqual(iso.main(["iso.py", "label", str(self.dir / "missing.json")]), 2)
            self.assertEqual(iso.main(["iso.py", "boot", str(ISO_YAML), str(self.dir / "missing"), "x"]), 2)
            self.assertEqual(iso.main(["iso.py", "label"]), 2)
        self.assertEqual(out.getvalue(), "")


KICKSTART = REPO / "installer/anaconda/interactive-defaults.ks"
NAME = "ghcr.io/edmundhills/lumen:dev"


class InstallImageTest(unittest.TestCase):
    def test_the_installer_s_kickstart(self):
        self.assertEqual(iso.install_image(KICKSTART.read_text(encoding="utf-8")), ([], NAME))

    def test_forms_of_the_bootc_command(self):
        ks = ("bootc --source-imgref containers-storage:x/y:z --target-imgref=x/y:z\n"
              "%post\nbootc --source-imgref=registry:elsewhere\n%end\n# bootc --source-imgref=oci:a\n")
        self.assertEqual(iso.install_image(ks), ([], "x/y:z"))

    def test_what_it_refuses(self):
        cases = {
            "no bootc": "ostreecontainer --url=x --transport=containers-storage\n",
            "two": "bootc --source-imgref=containers-storage:a --target-imgref=a\n" * 2,
            "from a registry": "bootc --source-imgref=registry:ghcr.io/a:b --target-imgref=ghcr.io/a:b\n",
            "another target": "bootc --source-imgref=containers-storage:a:b --target-imgref=c:d\n",
            "no target": "bootc --source-imgref=containers-storage:a:b\n",
            "not an option": "bootc containers-storage:a:b\n",
        }
        for case, ks in cases.items():
            with self.subTest(case):
                problems, name = iso.install_image(ks)
                self.assertEqual(len(problems), 1)
                self.assertIsNone(name)


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())


class PayloadTest(unittest.TestCase):
    """A stand-in for the live system's container storage, laid out as containers/storage lays it out."""

    VERSION = "44.20261030.4"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        config = json.dumps({"config": {"Labels": {iso.VERSION_LABEL: self.VERSION}}}).encode()
        self.image_id = "sha256:" + hashlib.sha256(config).hexdigest()
        # As copied out of container storage: the layers uncompressed, so not the build's own manifest.
        manifest = json.dumps({"schemaVersion": 2, "config": {"digest": self.image_id},
                               "layers": [{"digest": f"sha256:{n}"} for n in "abc"]}).encode()
        self.layers = [{"id": "l1"}, {"id": "l2", "parent": "l1"}, {"id": "l3", "parent": "l2"}]
        for layer in self.layers:
            (self.root / "overlay" / layer["id"] / "diff").mkdir(parents=True)
        self.image = {"id": self.image_id.removeprefix("sha256:"), "digest": "sha256:" + "d" * 64,
                      "names": [NAME], "layer": "l3"}
        self.folder = self.root / "overlay-images" / self.image["id"]
        put(self.folder / "manifest", manifest)
        put(self.folder / iso.big_data_name(self.image_id), config)
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        put(self.root / "overlay-images/images.json", [{"id": "other", "names": ["localhost/x:y"]}, self.image])
        put(self.root / "overlay-layers/layers.json", self.layers)

    def check(self, image_id=None, version=VERSION):
        return iso.payload(self.root, NAME, image_id or self.image_id, version)

    def test_the_build_with_its_layers(self):
        problems, report = self.check()
        self.assertEqual(problems, [])
        self.assertEqual(report, [f"{NAME}: build {self.VERSION}, image ID {self.image_id}, "
                                  f"manifest sha256:{'d' * 64}, 3 layers"])

    def test_big_data_names(self):
        self.assertEqual(iso.big_data_name("manifest"), "manifest")
        self.assertEqual(iso.big_data_name("sha256:ab"), "=c2hhMjU2OmFi")

    def test_another_build(self):
        self.assertIn(f"is build {self.VERSION}, not 44.1", " ".join(self.check(version="44.1")[0]))
        problems = self.check(image_id="sha256:" + "0" * 64)[0]
        self.assertTrue(any("has the image ID" in p for p in problems), problems)

    def test_a_changed_configuration(self):
        put(self.folder / iso.big_data_name(self.image_id), b"{}")
        problems = self.check()[0]
        self.assertTrue(any("doesn't have the digest" in p for p in problems), problems)

    def test_no_such_image(self):
        self.image["names"] = ["ghcr.io/edmundhills/lumen:other"]
        self.write()
        problems, _ = self.check()
        self.assertEqual(len(problems), 1)
        self.assertIn("0 images named", problems[0])

    def test_missing_layers(self):
        shutil.rmtree(self.root / "overlay/l2")
        self.assertIn("Layer l2 of", " ".join(self.check()[0]))
        self.layers = self.layers[1:]
        self.write()
        problems = self.check()[0]
        self.assertTrue(any("Layer l1 of" in p and "isn't in" in p for p in problems), problems)

    def test_main(self):
        args = ["iso.py", "payload", str(self.root), NAME, self.image_id, self.VERSION]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(iso.main(args), 0)
            self.assertEqual(iso.main(args[:-1] + ["44.1"]), 1)
            self.assertEqual(iso.main(["iso.py", "payload", str(self.root / "none"), NAME, self.image_id, "1"]), 2)
        self.assertIn("3 layers", err.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(iso.main(["iso.py", "install-image", str(KICKSTART)]), 0)
        self.assertEqual(out.getvalue(), NAME + "\n")


class PinTest(unittest.TestCase):
    def test_the_iso_and_the_qcow2_use_one_image_builder(self):
        """iso.yml pins the image-builder build-image.yml pins: one release to move."""
        pins = {}
        for workflow, job in (("build-image.yml", "build"), ("iso.yml", "iso")):
            with open(REPO / ".github/workflows" / workflow, encoding="utf-8") as f:
                pins[workflow] = yaml.safe_load(f)["jobs"][job]["env"]["IMAGE_BUILDER"]
        self.assertRegex(pins["iso.yml"], r"^ghcr\.io/osbuild/image-builder-cli:v[0-9.]+@sha256:[0-9a-f]{64}$")
        self.assertEqual(pins["iso.yml"], pins["build-image.yml"])


if __name__ == "__main__":
    unittest.main()
