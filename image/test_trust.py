# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for trust.py: the overlay's trust settings pass, and each way of
# getting them wrong is caught. `just test` runs them in the lint container:
#   python3 -m unittest discover --start-directory image

import contextlib
import copy
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import trust

HERE = Path(trust.__file__).resolve().parent
OVERLAY = HERE / "overlay"
# A public key made for these tests only; nothing is signed with it.
TEST_KEY = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEoXBhjygJk1sp4zjWopTysmJ4ZYVP
urcbaUcersOOofwpvs/mCfj8QGN1gW8gGyRaO4vvaKxS55gPPJmYhie7Dw==
-----END PUBLIC KEY-----
"""


class TrustTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        for path in (trust.POLICY_PATH, trust.REGISTRIES_D):
            source, target = OVERLAY / path, self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            (shutil.copytree if source.is_dir() else shutil.copy)(source, target)
        self.key = self.root / trust.KEY_PATH.lstrip("/")
        self.key.parent.mkdir(parents=True)
        self.key.write_text(TEST_KEY, encoding="ascii")
        self.policy = json.loads((self.root / trust.POLICY_PATH).read_text(encoding="utf-8"))

    def write_policy(self, policy):
        (self.root / trust.POLICY_PATH).write_text(json.dumps(policy), encoding="utf-8")

    def assertProblem(self, text):
        problems = trust.check(self.root)
        self.assertTrue(any(text in p for p in problems), f"no problem mentions {text!r}: {problems}")

    def test_overlay_passes(self):
        self.assertEqual(trust.check(self.root), [])

    def test_overlay_key_passes(self):
        # The public half of the key CI signs with, which the owner made
        # (docs/decisions/0008-image-signing.md).
        self.assertEqual(trust.check_key(OVERLAY / trust.KEY_PATH.lstrip("/")), [])

    def test_default_must_reject(self):
        self.policy["default"] = trust.ANYTHING
        self.write_policy(self.policy)
        self.assertProblem("--enforce-container-sigpolicy")

    def test_missing_repository(self):
        del self.policy["transports"]["docker"]["ghcr.io/edmundhills/lumen-nvidia"]
        self.write_policy(self.policy)
        self.assertProblem("ghcr.io/edmundhills/lumen-nvidia is missing")

    def test_unsigned_repository(self):
        self.policy["transports"]["docker"]["ghcr.io/edmundhills/lumen"] = trust.ANYTHING
        self.write_policy(self.policy)
        self.assertProblem("ghcr.io/edmundhills/lumen needs")

    def test_other_key(self):
        signed = copy.deepcopy(trust.SIGNED)
        signed[0]["keyPath"] = "/etc/pki/containers/other.pub"
        self.policy["transports"]["docker"]["ghcr.io/edmundhills/lumen-gaming"] = signed
        self.write_policy(self.policy)
        self.assertProblem("ghcr.io/edmundhills/lumen-gaming needs")

    def test_exact_identity(self):
        # The default identity rule wants the signature to name the tag, which
        # cosign's signatures don't, so every pull by tag would fail.
        signed = copy.deepcopy(trust.SIGNED)
        del signed[0]["signedIdentity"]
        self.policy["transports"]["docker"]["ghcr.io/edmundhills/lumen"] = signed
        self.write_policy(self.policy)
        self.assertProblem("ghcr.io/edmundhills/lumen needs")

    def test_unsigned_tag(self):
        # A scope for one tag would win over the repository's.
        self.policy["transports"]["docker"]["ghcr.io/edmundhills/lumen:stable"] = trust.ANYTHING
        self.write_policy(self.policy)
        self.assertProblem("ghcr.io/edmundhills/lumen:stable needs")

    def test_signed_tag_is_fine(self):
        self.policy["transports"]["docker"]["ghcr.io/edmundhills/lumen:stable"] = trust.SIGNED
        self.write_policy(self.policy)
        self.assertEqual(trust.check(self.root), [])

    def test_lookalike_repository_is_not_lumen(self):
        # lumen-extra is not one of Lumen's images, and isn't held to Lumen's key.
        self.policy["transports"]["docker"]["ghcr.io/edmundhills/lumen-extra"] = trust.ANYTHING
        self.write_policy(self.policy)
        self.assertEqual(trust.check(self.root), [])

    def test_other_registries_unsigned(self):
        self.policy["transports"]["docker"][""] = trust.REJECT
        self.write_policy(self.policy)
        self.assertProblem("images from other registries")

    def test_missing_transport(self):
        del self.policy["transports"]["oci-archive"]
        self.write_policy(self.policy)
        self.assertProblem("the oci-archive transport is null")

    def test_unknown_transport(self):
        self.policy["transports"]["atomic"] = {"": trust.ANYTHING}
        self.write_policy(self.policy)
        self.assertProblem("the atomic transport is not one")

    def test_policy_not_json(self):
        (self.root / trust.POLICY_PATH).write_text("{", encoding="utf-8")
        self.assertProblem("cannot read")

    def test_missing_key(self):
        self.key.unlink()
        self.assertProblem("cannot read the signing key")

    def test_key_not_pem(self):
        self.key.write_text("not a key\n", encoding="ascii")
        self.assertProblem("is not a PEM public key")

    def test_key_bad_base64(self):
        self.key.write_text("-----BEGIN PUBLIC KEY-----\n!!!!\n-----END PUBLIC KEY-----\n", encoding="ascii")
        self.assertProblem("is not a PEM public key")

    def test_private_key(self):
        self.key.write_text("-----BEGIN ENCRYPTED SIGSTORE PRIVATE KEY-----\nAAAA\n"
                            "-----END ENCRYPTED SIGSTORE PRIVATE KEY-----\n", encoding="ascii")
        self.assertProblem("is not a PEM public key")

    def test_no_attachments(self):
        (self.root / trust.REGISTRIES_D / "lumen.yaml").unlink()
        self.assertProblem("use-sigstore-attachments: true for ghcr.io/edmundhills/lumen")

    def test_attachments_turned_off(self):
        (self.root / trust.REGISTRIES_D / "zz.yaml").write_text(
            "docker:\n  ghcr.io/edmundhills/lumen/x:\n    use-sigstore-attachments: false\n", encoding="utf-8")
        self.assertProblem("zz.yaml does not say use-sigstore-attachments: true")

    def test_scope_set_twice(self):
        (self.root / trust.REGISTRIES_D / "zz.yaml").write_text(
            "docker:\n  ghcr.io/edmundhills/lumen:\n    use-sigstore-attachments: true\n", encoding="utf-8")
        self.assertProblem("ghcr.io/edmundhills/lumen is set in both lumen.yaml and zz.yaml")

    def test_registry_wide_attachments(self):
        # A scope for the whole namespace covers every repository in it.
        (self.root / trust.REGISTRIES_D / "lumen.yaml").write_text(
            "docker:\n  ghcr.io/edmundhills:\n    use-sigstore-attachments: true\n", encoding="utf-8")
        self.assertEqual(trust.check(self.root), [])

    def test_default_docker_attachments(self):
        (self.root / trust.REGISTRIES_D / "lumen.yaml").write_text(
            "default-docker:\n  use-sigstore-attachments: true\n", encoding="utf-8")
        self.assertEqual(trust.check(self.root), [])

    def test_only_yaml_files_count(self):
        folder = self.root / trust.REGISTRIES_D
        (folder / "lumen.yaml").rename(folder / "lumen.yml")
        self.assertProblem("use-sigstore-attachments: true for ghcr.io/edmundhills/lumen")

    def test_main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(trust.main(["trust.py", "check", str(self.root)]), 0)
            self.assertEqual(trust.main(["trust.py", "check"]), 2)
            self.assertEqual(trust.main(["trust.py", "check", str(self.root / "missing")]), 2)
            self.key.unlink()
            self.assertEqual(trust.main(["trust.py", "check", str(self.root)]), 1)
        self.assertIn("cannot read the signing key", out.getvalue())
        self.assertIn("Usage:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
