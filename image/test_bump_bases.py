# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for bump_bases.py. `just test` runs them in the lint container,
# which has no network, so a fake registry and fake Bodhi data stand in:
#   python3 -m unittest discover --start-directory image

import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

import bump_bases

HERE = Path(bump_bases.__file__).resolve().parent
REAL = [HERE / "Containerfile", HERE.parent / "tests" / "lint" / "Containerfile"]
OLD = "sha256:" + "1" * 64
NEW = "sha256:" + "2" * 64
OLD_KINOITE = "Kinoite 44.20261027.0, built 2026-10-27, with KWin 6.7.5, Plasma 6.7.5 and Qt 6.11.2"

IMAGE = f"""# The base.
# Pinned: {OLD_KINOITE}.
FROM quay.io/fedora-ostree-desktops/kinoite:44@{OLD} AS base

RUN true

FROM base AS lumen
"""

LINT = f"""# Pinned: Fedora 44, built 2026-10-27.
FROM registry.fedoraproject.org/fedora:44@{OLD}
RUN true
"""


def bodhi(*releases):
    """Return Bodhi release entries for (name, id_prefix, state) triples."""
    return [{"name": n, "id_prefix": p, "state": s, "version": n.lstrip("F")} for n, p, s in releases]


BODHI_44 = bodhi(
    ("F43", "FEDORA", "current"), ("F43C", "FEDORA-CONTAINER", "current"), ("F44", "FEDORA", "current"),
    ("F44F", "FEDORA-FLATPAK", "current"), ("F45", "FEDORA", "frozen"), ("F46", "FEDORA", "pending"),
)
BODHI_45 = bodhi(("F44", "FEDORA", "current"), ("F45", "FEDORA", "current"), ("F46", "FEDORA", "pending"))


class FakeRegistry:
    """Serves IMAGE:TAG as the digest in DIGESTS, with the newest builds' labels and layers."""

    def __init__(self, digests, kwin="6.7.5", plasma="6.7.5"):
        self.digests, self.kwin, self.plasma = digests, kwin, plasma

    def digest(self, image, tag):
        return self.digests[f"{image}:{tag}"]

    def info(self, image, digest):
        return {"Created": "2026-11-02T03:13:18Z", "Labels": {"org.opencontainers.image.version": "45.20261102.0"}}

    def config(self, image, digest):
        return {"history": [
            {"created_by": "ostree export of commit abc"},
            {"created_by": f"kwin-common-{self.kwin}-1.fc45.x86_64"},
            {"created_by": f"plasma-workspace-wallpapers-{self.plasma}-1.fc45.noarch"},
            {"created_by": f"plasma-workspace-{self.plasma}-1.fc45.x86_64"},
            {"created_by": "qt6-qtbase-6.11.2-3.fc45.x86_64"},
        ]}


class ParsePins(unittest.TestCase):
    def test_reads_the_pinned_bases(self):
        [pin] = bump_bases.parse_pins("Containerfile", IMAGE)
        self.assertEqual(
            (pin.line, pin.image, pin.tag, pin.digest, pin.rest, pin.build),
            (2, bump_bases.KINOITE, "44", OLD, " AS base", OLD_KINOITE),
        )

    def test_the_real_containerfiles_pin_kinoite_and_fedora(self):
        pins = bump_bases.read_pins([str(p) for p in REAL])
        self.assertEqual([p.image for p in pins], [bump_bases.KINOITE, bump_bases.FEDORA])

    def assert_rejects(self, text, message):
        with self.assertRaisesRegex(bump_bases.BumpError, message):
            bump_bases.parse_pins("Containerfile", text)

    def test_rejects_a_base_without_a_digest(self):
        self.assert_rejects("# Pinned: x\nFROM registry.fedoraproject.org/fedora:44\n", "Containerfile:2: .* by tag and digest")

    def test_rejects_a_base_without_a_tag(self):
        self.assert_rejects(f"# Pinned: x\nFROM registry.fedoraproject.org/fedora@{OLD}\n", "by tag and digest")

    def test_rejects_a_base_without_a_pinned_line(self):
        self.assert_rejects(f"# Fedora\nFROM registry.fedoraproject.org/fedora:44@{OLD}\n", "Pinned")
        self.assert_rejects(f"FROM registry.fedoraproject.org/fedora:44@{OLD}\n", "Pinned")

    def test_ignores_other_images_and_stages(self):
        text = f"FROM quay.io/fedora/fedora:44@{OLD}\nFROM base AS lumen\n"
        self.assertEqual(bump_bases.parse_pins("Containerfile", text), [])

    def test_a_file_list_without_pins_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "Containerfile")
            path.write_text("FROM base\n", encoding="utf-8")
            with self.assertRaisesRegex(bump_bases.BumpError, "no pinned base"):
                bump_bases.read_pins([str(path)])


class Copies(unittest.TestCase):
    def test_lists_each_base_with_its_copy(self):
        pins = bump_bases.parse_pins("a", IMAGE) + bump_bases.parse_pins("b", LINT)
        self.assertEqual(bump_bases.list_lines("ghcr.io/owner", pins), [
            f"{bump_bases.KINOITE} {OLD} ghcr.io/owner/kinoite 44-111111111111",
            f"{bump_bases.FEDORA} {OLD} ghcr.io/owner/fedora 44-111111111111",
        ])

    def test_mirrors_pull_only_by_digest_from_the_copies(self):
        pins = bump_bases.parse_pins("a", IMAGE) + bump_bases.parse_pins("b", LINT) + bump_bases.parse_pins("c", LINT)
        conf = tomllib.loads(bump_bases.mirrors_conf("ghcr.io/owner", pins))
        self.assertEqual(conf["registry"], [
            {"prefix": bump_bases.KINOITE, "location": bump_bases.KINOITE,
             "mirror": [{"location": "ghcr.io/owner/kinoite", "pull-from-mirror": "digest-only"}]},
            {"prefix": bump_bases.FEDORA, "location": bump_bases.FEDORA,
             "mirror": [{"location": "ghcr.io/owner/fedora", "pull-from-mirror": "digest-only"}]},
        ])


class NewestFedora(unittest.TestCase):
    def test_takes_the_newest_current_release(self):
        self.assertEqual(bump_bases.newest_fedora(BODHI_44), 44)
        self.assertEqual(bump_bases.newest_fedora(BODHI_45), 45)

    def test_a_list_without_a_current_release_is_an_error(self):
        with self.assertRaises(bump_bases.BumpError):
            bump_bases.newest_fedora(bodhi(("F45", "FEDORA", "frozen"), ("EPEL-10", "FEDORA-EPEL", "current")))


class PackageVersions(unittest.TestCase):
    def test_reads_versions_from_the_layer_names(self):
        config = FakeRegistry({}).config(None, None)
        self.assertEqual(
            bump_bases.package_versions(config, ("kwin-common", "plasma-workspace", "kwin-libs")),
            {"kwin-common": "6.7.5", "plasma-workspace": "6.7.5", "kwin-libs": "unknown"},
        )


class Bump(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.image, self.lint = Path(d.name, "image"), Path(d.name, "lint")
        self.image.write_text(IMAGE, encoding="utf-8")
        self.lint.write_text(LINT, encoding="utf-8")

    def bump(self, registry, releases=BODHI_44):
        moves = bump_bases.bump([str(self.image), str(self.lint)], registry, lambda: releases)
        return bump_bases.message(moves)

    def test_nothing_moves_when_every_pin_is_current(self):
        registry = FakeRegistry({f"{bump_bases.KINOITE}:44": OLD, f"{bump_bases.FEDORA}:44": OLD})
        self.assertEqual(self.bump(registry), "")
        self.assertEqual(self.image.read_text(encoding="utf-8"), IMAGE)
        self.assertEqual(self.lint.read_text(encoding="utf-8"), LINT)

    def test_moves_each_pin_to_its_tags_newest_build(self):
        registry = FakeRegistry({f"{bump_bases.KINOITE}:44": NEW, f"{bump_bases.FEDORA}:44": NEW})
        message = self.bump(registry)
        self.assertEqual(self.image.read_text(encoding="utf-8"), IMAGE.replace(OLD, NEW).replace(
            OLD_KINOITE, "Kinoite 45.20261102.0, built 2026-11-02, with KWin 6.7.5, Plasma 6.7.5 and Qt 6.11.2"))
        self.assertEqual(self.lint.read_text(encoding="utf-8"), LINT.replace(OLD, NEW).replace("10-27", "11-02"))
        self.assertTrue(message.startswith("build(image): bump the base to Kinoite 45.20261102.0\n\n"), message)
        self.assertIn(f"  - was 44@sha256:111111111111…: {OLD_KINOITE}\n", message)
        self.assertIn("  - now 44@sha256:222222222222…: Fedora 44, built 2026-11-02\n", message)
        self.assertNotIn("KWin or Plasma changed", message)
        self.assertNotIn("Bodhi", message)

    def test_moves_kinoite_to_a_new_fedora_release_but_not_the_lint_base(self):
        registry = FakeRegistry({f"{bump_bases.KINOITE}:45": NEW, f"{bump_bases.FEDORA}:44": OLD})
        message = self.bump(registry, BODHI_45)
        self.assertIn(f"FROM quay.io/fedora-ostree-desktops/kinoite:45@{NEW} AS base\n", self.image.read_text(encoding="utf-8"))
        self.assertEqual(self.lint.read_text(encoding="utf-8"), LINT)
        self.assertTrue(message.startswith("build(image): move the base to Fedora 45\n"), message)
        self.assertIn("Bodhi lists Fedora 45 as current", message)

    def test_never_moves_kinoite_to_an_older_release(self):
        self.image.write_text(IMAGE.replace("kinoite:44", "kinoite:45"), encoding="utf-8")
        registry = FakeRegistry({f"{bump_bases.KINOITE}:45": OLD, f"{bump_bases.FEDORA}:44": OLD})
        self.assertEqual(self.bump(registry, BODHI_44), "")

    def test_says_when_kwin_or_plasma_changed(self):
        registry = FakeRegistry({f"{bump_bases.KINOITE}:44": NEW, f"{bump_bases.FEDORA}:44": OLD}, plasma="6.8.0")
        self.assertIn("KWin or Plasma changed", self.bump(registry))

    def test_a_lint_only_bump_says_so(self):
        registry = FakeRegistry({f"{bump_bases.KINOITE}:44": OLD, f"{bump_bases.FEDORA}:44": NEW})
        self.assertTrue(self.bump(registry).startswith("build(lint): "))


class Main(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(HERE / "bump_bases.py"), *args],
            capture_output=True, text=True, check=False,
        )

    def test_lists_the_real_pins(self):
        result = self.run_script("list", "ghcr.io/owner/", *map(str, REAL))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(
            result.stdout,
            r"^quay\.io/fedora-ostree-desktops/kinoite sha256:[0-9a-f]{64} ghcr\.io/owner/kinoite [0-9]+-[0-9a-f]{12}\n"
            r"registry\.fedoraproject\.org/fedora sha256:[0-9a-f]{64} ghcr\.io/owner/fedora [0-9]+-[0-9a-f]{12}\n$",
        )

    def test_writes_the_real_mirrors(self):
        result = self.run_script("mirrors", "ghcr.io/owner", *map(str, REAL))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(tomllib.loads(result.stdout)["registry"]), 2)

    def test_usage_errors(self):
        for args in ([], ["list", "ghcr.io/owner"], ["bump"], ["copy", "x", "y"]):
            self.assertEqual(self.run_script(*args).returncode, 2, args)

    def test_a_bad_file_is_an_error(self):
        result = self.run_script("list", "ghcr.io/owner", str(HERE / "no-such-file"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("bump_bases.py: ", result.stderr)


if __name__ == "__main__":
    unittest.main()
