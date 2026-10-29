# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for rechunk.py, on manifests and configs shaped like the ones
# skopeo prints for Lumen's images, and for rechunk.sh's argument checks.
# `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory image

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import rechunk

HERE = Path(rechunk.__file__).resolve().parent
MIB = 1024 * 1024
BASE_44_1 = "quay.io/fedora-ostree-desktops/kinoite@sha256:" + "1" * 64
BASE_44_2 = "quay.io/fedora-ostree-desktops/kinoite@sha256:" + "2" * 64


def digest(name):
    return "sha256:" + name.encode().hex().ljust(64, "0")[:64]


def layer(name, size_mib, components=None):
    """A layer whose digest stands for NAME, with rpm-ostree's annotation if COMPONENTS is given."""
    entry = {"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip", "digest": digest(name),
             "size": int(size_mib * MIB)}
    if components is not None:
        entry["annotations"] = {rechunk.COMPONENTS: ",".join(components)}
    return entry


def manifest(*layers):
    return {"schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": digest("config"), "size": 1}, "layers": list(layers)}


def config(labels, **settings):
    return {"architecture": "amd64", "os": "linux",
            "config": {"Cmd": ["/sbin/init"], "Labels": labels, **settings}}


# A built image as Podman stores it: Kinoite's labels, then Lumen's.
BUILT = {
    "containers.bootc": "1", "ostree.bootable": "true", "ostree.commit": "a" * 64,
    "ostree.final-diffid": digest("kinoite-last"), "ostree.linux": "7.2.12-200.fc44.x86_64",
    "rpmostree.inputhash": "b" * 64, "org.opencontainers.image.version": "44.20261029",
    "org.opencontainers.image.title": "Lumen OS",
}
# The same image re-chunked: a new commit, and the base named.
RECHUNKED = dict(BUILT, **{"ostree.commit": "c" * 64, "ostree.final-diffid": digest("last"),
                           "org.opencontainers.image.base.name": BASE_44_1,
                           "org.opencontainers.image.base.digest": digest("kinoite-amd64")})


def rechunked_image(version, base, extra=()):
    """A re-chunked build: its commit layer, three layers of packages, the unpackaged files and an empty one."""
    layers = [
        layer(f"commit-{version}", 7),
        layer("kernel", 60, ["kernel-core"]),
        layer("kwin", 20, ["kwin-common", "kwin-libs"]),
        layer("small", 5, ["a", "b", "c", "d", "e"]),
        layer("unpackaged", 10, ["rpmostree-unpackaged-content"]),
        *extra,
        layer("empty", 0.001, []),
    ]
    labels = dict(RECHUNKED, **{"org.opencontainers.image.version": version,
                                "org.opencontainers.image.base.name": base})
    return manifest(*layers), config(labels)


class Chunked(unittest.TestCase):
    def test_a_rechunked_image(self):
        ok, why = rechunk.chunked(rechunked_image("44.20261029", BASE_44_1)[0])
        self.assertTrue(ok, why)

    def test_kinoite_and_podman_builds_are_not_rechunked(self):
        # Kinoite's own layers carry no annotations, and neither do the layers
        # of an image Podman built from it.
        ok, why = rechunk.chunked(manifest(layer("commit", 7), layer("one", 100), layer("two", 50)))
        self.assertFalse(ok)
        self.assertIn("2 of its 3 layers", why)
        self.assertIn("layer 1", why)

    def test_one_unnamed_layer_is_enough_to_refuse(self):
        m = rechunked_image("44.20261029", BASE_44_1)[0]
        m["layers"][2].pop("annotations")
        ok, why = rechunk.chunked(m)
        self.assertFalse(ok)
        self.assertIn("layer 2", why)

    def test_an_index_or_a_single_layer(self):
        self.assertFalse(rechunk.chunked({"schemaVersion": 2, "manifests": []})[0])
        self.assertFalse(rechunk.chunked(manifest(layer("commit", 7)))[0])


class Labels(unittest.TestCase):
    def test_rechunking_may_replace_the_commit_and_add_the_base(self):
        self.assertEqual(rechunk.compare_labels(config(BUILT), config(RECHUNKED)), [])

    def test_a_changed_or_lost_label(self):
        changed = dict(RECHUNKED, **{"org.opencontainers.image.version": "44.20261028"})
        lost = {k: v for k, v in RECHUNKED.items() if k != "ostree.linux"}
        self.assertIn("the label org.opencontainers.image.version changed from '44.20261029' to '44.20261028'",
                      rechunk.compare_labels(config(BUILT), config(changed)))
        self.assertIn("the label ostree.linux is gone (it was '7.2.12-200.fc44.x86_64')",
                      rechunk.compare_labels(config(BUILT), config(lost)))

    def test_bootc_labels_and_a_new_commit_are_required(self):
        before = {k: v for k, v in BUILT.items() if k != "containers.bootc"}
        after = {k: v for k, v in RECHUNKED.items() if k not in ("containers.bootc", "ostree.commit")}
        problems = rechunk.compare_labels(config(before), config(after))
        self.assertIn("the label containers.bootc is None, not '1', so bootc won't take the image", problems)
        self.assertIn("the label ostree.commit is missing", problems)

    def test_an_unexpected_new_label(self):
        problems = rechunk.compare_labels(config(BUILT), config(dict(RECHUNKED, surprise="yes")))
        self.assertEqual(len(problems), 1)
        self.assertIn("a new label surprise='yes' appeared", problems[0])

    def test_settings_and_platform_must_not_change(self):
        problems = rechunk.compare_labels(config(BUILT, Env=["A=1"]), config(RECHUNKED, Env=["A=2"]))
        self.assertEqual(problems, ["the setting Env changed from ['A=1'] to ['A=2']"])
        arm = dict(config(RECHUNKED), architecture="arm64")
        self.assertIn("the platform changed from linux/amd64 to linux/arm64",
                      rechunk.compare_labels(config(BUILT), arm))


class Download(unittest.TestCase):
    def report(self, new, old, budget=50):
        m, c = new
        previous = None if old is None else (old[0], old[1], digest("old-manifest"))
        return rechunk.download(budget, m, c, digest("new-manifest"), previous)

    def test_no_previous_build(self):
        report, within = self.report(rechunked_image("44.20261029", BASE_44_1), None)
        self.assertTrue(within)
        self.assertIn("6 layers, 102.0 MiB compressed", report)
        self.assertIn("downloads all of it", report)

    def test_a_rebuild_downloads_only_its_changed_layers(self):
        old = rechunked_image("44.20261029", BASE_44_1)
        new = rechunked_image("44.20261029.1", BASE_44_1, [layer("rpm-new", 30, ["rpm", "rpm-libs"])])
        report, within = self.report(new, old)
        self.assertTrue(within, report)
        self.assertIn("**2 of 7 layers, 37.0 MiB**", report)
        self.assertIn("Within the budget of 50 MiB", report)
        self.assertIn("| 5 | 30.0 MiB | rpm, rpm-libs |", report)
        self.assertIn("| 0 | 7.0 MiB | the ostree commit", report)
        self.assertIn("Previous build: 44.20261029 (`sha256:", report)

    def test_over_the_budget_on_the_same_base(self):
        old = rechunked_image("44.20261029", BASE_44_1)
        new = rechunked_image("44.20261029.1", BASE_44_1, [layer("big", 80, ["rpmostree-unpackaged-content"])])
        report, within = self.report(new, old)
        self.assertFalse(within)
        self.assertIn("**Over the budget** of 50 MiB", report)
        self.assertIn("| 5 | 80.0 MiB | files no package owns |", report)

    def test_a_new_base_is_reported_but_not_held_to_the_budget(self):
        old = rechunked_image("44.20261029", BASE_44_1)
        new = rechunked_image("44.20261030", BASE_44_2, [layer("big", 80, ["mesa-dri-drivers"])])
        report, within = self.report(new, old)
        self.assertTrue(within)
        self.assertIn("The base image changed", report)

    def test_the_first_rechunked_build_is_not_held_to_the_budget(self):
        old = (manifest(layer("commit-old", 7), layer("one", 100), layer("two", 50)), config(BUILT))
        report, within = self.report(rechunked_image("44.20261029", BASE_44_1), old)
        self.assertTrue(within)
        self.assertIn("isn't re-chunked", report)
        self.assertIn("**6 of 6 layers", report)

    def test_long_lists_are_shortened(self):
        extra = [layer(f"pkg{i}", 1 + i / 10, [f"p{i}"]) for i in range(25)]
        new = rechunked_image("44.20261029.1", BASE_44_2, extra)
        report, _ = self.report(new, rechunked_image("44.20261029", BASE_44_1))
        self.assertIn("and 6 smaller layers", report)
        self.assertIn("a, b, c and 2 more", rechunk.describe(layer("small", 5, list("abcde")), 3))
        self.assertIn("kept empty", rechunk.describe(layer("empty", 0, []), 9))


class CommandLine(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)

    def write(self, name, data):
        path = self.dir / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def run_main(self, *args):
        return subprocess.run(["python3", str(HERE / "rechunk.py"), *args],
                              capture_output=True, text=True, check=False)

    def test_chunked(self):
        yes = self.write("yes.json", rechunked_image("44.20261029", BASE_44_1)[0])
        no = self.write("no.json", manifest(layer("commit", 7), layer("one", 100)))
        self.assertEqual(self.run_main("chunked", yes).returncode, 0)
        result = self.run_main("chunked", no)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not re-chunked", result.stdout)

    def test_labels(self):
        before, after = self.write("b.json", config(BUILT)), self.write("a.json", config(RECHUNKED))
        self.assertEqual(self.run_main("labels", before, after).returncode, 0)
        result = self.run_main("labels", after, before)
        self.assertEqual(result.returncode, 1)
        self.assertIn("After re-chunking, the label", result.stderr)

    def test_download_and_its_digest(self):
        old_m, old_c = rechunked_image("44.20261029", BASE_44_1)
        new_m, new_c = rechunked_image("44.20261029.1", BASE_44_1, [layer("big", 80, ["x"])])
        paths = [self.write(n, d) for n, d in
                 (("m.json", new_m), ("c.json", new_c), ("om.json", old_m), ("oc.json", old_c))]
        result = self.run_main("download", "50", *paths)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("over the download budget", result.stderr)
        # The digest shown is that of the manifest's bytes, as the registry names it.
        self.assertIn(rechunk.read_json(paths[0])[1], result.stdout)
        self.assertEqual(self.run_main("download", "100", *paths).returncode, 0)

    def test_usage_and_unreadable_files(self):
        self.assertEqual(self.run_main().returncode, 2)
        self.assertEqual(self.run_main("download", "lots", "m", "c").returncode, 2)
        result = self.run_main("chunked", str(self.dir / "missing.json"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing.json", result.stderr)


class Script(unittest.TestCase):
    """rechunk.sh refuses bad arguments before it touches Podman."""

    def run_script(self, *args):
        env = dict(os.environ, PATH="/nonexistent:/usr/bin:/bin")
        return subprocess.run(["bash", str(HERE / "rechunk.sh"), *args],
                              capture_output=True, text=True, check=False, env=env)

    def test_usage(self):
        self.assertEqual(self.run_script().returncode, 2)
        self.assertEqual(self.run_script("a", "b", "c", "d").returncode, 2)

    def test_output_must_be_new(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.run_script("localhost/lumen:ci", d)
        self.assertEqual(result.returncode, 2)
        self.assertIn("already exists", result.stderr)

    def test_previous_must_name_a_transport(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.run_script("localhost/lumen:ci", f"{d}/out", "ghcr.io/owner/lumen:dev")
        self.assertEqual(result.returncode, 2)
        self.assertIn("must start with docker:// or oci:", result.stderr)


if __name__ == "__main__":
    unittest.main()
