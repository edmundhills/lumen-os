# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for copy-bases.sh, with a stand-in for skopeo that logs its calls
# and answers from a list of what exists and what is public. `just test` runs
# them in the lint container:
#   python3 -m unittest discover --start-directory image

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
KINOITE = "sha256:" + "1" * 64
FEDORA = "sha256:" + "2" * 64
COPY_KINOITE = f"docker://ghcr.io/owner/kinoite@{KINOITE}"
COPY_FEDORA = f"docker://ghcr.io/owner/fedora@{FEDORA}"

CONTAINERFILE = f"""# Pinned: Kinoite 44.20261027.0.
FROM quay.io/fedora-ostree-desktops/kinoite:44@{KINOITE} AS base
FROM base AS lumen

# Pinned: Fedora 44, built 2026-10-27.
FROM registry.fedoraproject.org/fedora:44@{FEDORA} AS tools
"""

# Lines of the state file: "exists REF" and "public REF". The last argument
# of every call is an image reference.
FAKE_SKOPEO = """#!/usr/bin/env bash
printf '%s\\n' "$*" >>"$FAKE_LOG"
ref=${!#}
case $1 in
  inspect)
    if [[ " $* " == *" --no-creds "* ]]; then grep -qxF "public $ref" "$FAKE_STATE"; else grep -qxF "exists $ref" "$FAKE_STATE"; fi
    ;;
  copy) exit 0 ;;
  *) exit 99 ;;
esac
"""


class CopyBases(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)
        (self.dir / "bin").mkdir()
        skopeo = self.dir / "bin" / "skopeo"
        skopeo.write_text(FAKE_SKOPEO, encoding="utf-8")
        skopeo.chmod(0o755)
        self.containerfile = self.dir / "Containerfile"
        self.containerfile.write_text(CONTAINERFILE, encoding="utf-8")
        self.log, self.state = self.dir / "log", self.dir / "state"
        self.log.touch()

    def run_script(self, *state):
        self.state.write_text("".join(f"{line}\n" for line in state), encoding="utf-8")
        env = dict(os.environ, PATH=f"{self.dir / 'bin'}:{os.environ['PATH']}",
                   FAKE_LOG=str(self.log), FAKE_STATE=str(self.state))
        env.pop("GITHUB_STEP_SUMMARY", None)
        result = subprocess.run(
            ["bash", str(HERE / "copy-bases.sh"), "ghcr.io/owner", str(self.containerfile)],
            capture_output=True, text=True, check=False, env=env,
        )
        return result, self.log.read_text(encoding="utf-8").splitlines()

    def copies(self, calls):
        return [c for c in calls if c.startswith("copy ")]

    def test_copies_each_missing_base_with_its_digest(self):
        result, calls = self.run_script(f"public {COPY_KINOITE}", f"public {COPY_FEDORA}")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.copies(calls), [
            "copy --all --preserve-digests --retry-times 3 "
            f"docker://quay.io/fedora-ostree-desktops/kinoite@{KINOITE} docker://ghcr.io/owner/kinoite:44-111111111111",
            "copy --all --preserve-digests --retry-times 3 "
            f"docker://registry.fedoraproject.org/fedora@{FEDORA} docker://ghcr.io/owner/fedora:44-222222222222",
        ])

    def test_skips_a_base_that_is_already_copied(self):
        result, calls = self.run_script(
            f"exists {COPY_KINOITE}", f"public {COPY_KINOITE}", f"public {COPY_FEDORA}")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("is already copied to ghcr.io/owner/kinoite", result.stdout)
        self.assertEqual(len(self.copies(calls)), 1)
        self.assertIn("ghcr.io/owner/fedora:44-", self.copies(calls)[0])

    def test_fails_when_a_copy_is_not_public(self):
        result, calls = self.run_script(f"public {COPY_KINOITE}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ghcr.io/owner/fedora needs a login to pull", result.stdout)
        self.assertIn("https://github.com/users/owner/packages/container/fedora/settings", result.stdout)
        self.assertNotIn("kinoite needs a login", result.stdout)
        # It still copies and checks every base.
        self.assertEqual(len(self.copies(calls)), 2)

    def test_usage_error(self):
        result = subprocess.run(["bash", str(HERE / "copy-bases.sh"), "ghcr.io/owner"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
