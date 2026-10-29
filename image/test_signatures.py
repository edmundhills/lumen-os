# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test the trust settings in image/overlay the way bootc meets them: skopeo
# pulls images with them from a registry that answers for ghcr.io, and must
# accept Lumen's images only with Lumen's signature (step 1.7,
# docs/decisions/0008-image-signing.md).
#
# `just test` runs it in the lint container, which has the registry, skopeo
# and openssl, maps ghcr.io to the container itself, and sets
# LUMEN_SIGNATURE_TEST=1. Without that variable the tests are skipped: they
# start a registry on port 443, which needs a container of its own.
#
# The policy is the overlay's, with its key path pointing to a key made here.
# The images are signed the way CI signs (image/sign.sh), with cosign.

import json
import os
import shutil
import socket
import ssl
import subprocess
import tarfile
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path
from hashlib import sha256
from io import BytesIO

import trust

HERE = Path(trust.__file__).resolve().parent
OVERLAY = HERE / "overlay"
REGISTRY = trust.REGISTRY
LUMEN = f"{REGISTRY}/lumen"
PASSPHRASE = "test passphrase, for keys made by this test only"


def run(*args, env=None, check=True):
    return subprocess.run(args, capture_output=True, text=True, env=env, check=check)


def blob(folder, data):
    """Store DATA in the OCI layout FOLDER, and return its descriptor's digest and size."""
    digest = sha256(data).hexdigest()
    (folder / "blobs" / "sha256" / digest).write_bytes(data)
    return {"digest": f"sha256:{digest}", "size": len(data)}


def make_image(folder, content):
    """Write a one-layer image holding a file with CONTENT as an OCI layout in FOLDER, tagged latest."""
    (folder / "blobs" / "sha256").mkdir(parents=True)
    (folder / "oci-layout").write_text('{"imageLayoutVersion": "1.0.0"}', encoding="utf-8")
    data = content.encode()
    tar = BytesIO()
    with tarfile.open(fileobj=tar, mode="w") as t:
        info = tarfile.TarInfo("hello.txt")
        info.size = len(data)
        t.addfile(info, BytesIO(data))
    layer = tar.getvalue()
    config = json.dumps({
        "architecture": "amd64", "os": "linux", "config": {},
        "rootfs": {"type": "layers", "diff_ids": [f"sha256:{sha256(layer).hexdigest()}"]},
    }).encode()
    manifest = json.dumps({
        "schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {"mediaType": "application/vnd.oci.image.config.v1+json", **blob(folder, config)},
        "layers": [{"mediaType": "application/vnd.oci.image.layer.v1.tar", **blob(folder, layer)}],
    }).encode()
    index = {"schemaVersion": 2, "manifests": [{
        "mediaType": "application/vnd.oci.image.manifest.v1+json", **blob(folder, manifest),
        "annotations": {"org.opencontainers.image.ref.name": "latest"},
    }]}
    (folder / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return f"oci:{folder}:latest"


@unittest.skipUnless(os.environ.get("LUMEN_SIGNATURE_TEST") == "1",
                     "needs the lint container: run `just test`")
class SignatureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for tool in ("registry", "skopeo", "openssl", "cosign"):
            if not shutil.which(tool):
                raise AssertionError(f"{tool} is missing from the lint container (tests/lint/Containerfile)")
        if socket.gethostbyname("ghcr.io") != "127.0.0.1":
            raise AssertionError("ghcr.io must point to 127.0.0.1 in the test container (the justfile maps it)")
        cls.work = Path(tempfile.mkdtemp())
        cls.count = 0
        work = cls.work

        # A certificate for ghcr.io, which skopeo and cosign trust for this test only.
        certs = work / "certs"
        certs.mkdir()
        run("openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
            "-days", "1", "-subj", "/CN=ghcr.io", "-addext", "subjectAltName=DNS:ghcr.io",
            "-keyout", str(work / "registry.key"), "-out", str(certs / "ghcr.io.crt"))
        cls.certs = certs
        cls.env = dict(os.environ, SSL_CERT_FILE=str(certs / "ghcr.io.crt"), COSIGN_PASSWORD=PASSPHRASE)

        config = work / "registry.yaml"
        config.write_text(json.dumps({
            "version": 0.1, "log": {"level": "error"},
            "storage": {"filesystem": {"rootdirectory": str(work / "storage")}},
            "http": {"addr": "127.0.0.1:443", "tls": {
                "certificate": str(certs / "ghcr.io.crt"), "key": str(work / "registry.key")}},
        }), encoding="utf-8")
        # The registry logs every request that fails, such as cosign looking
        # for a tag that isn't there, so its log goes to a file: a pipe that
        # nobody reads fills up and stops the registry.
        log = work / "registry.log"
        with open(log, "wb") as out:
            cls.registry = subprocess.Popen(["registry", "serve", str(config)],
                                            stdout=subprocess.DEVNULL, stderr=out)
        context = ssl.create_default_context(cafile=str(certs / "ghcr.io.crt"))
        for _ in range(100):
            try:
                urllib.request.urlopen("https://ghcr.io/v2/", context=context, timeout=1)
                break
            except OSError:
                if cls.registry.poll() is not None:
                    raise AssertionError(f"the registry stopped: {log.read_text(errors='replace')}")
                time.sleep(0.1)
        else:
            raise AssertionError("the registry didn't start")

        # Lumen's key and another, both made here, in cosign's format.
        for name in ("lumen", "other"):
            (work / name).mkdir()
            run("cosign", "generate-key-pair", "--output-key-prefix", str(work / name / "cosign"), env=cls.env)

        # The overlay's policy, with the key path pointing to this test's key.
        text = (OVERLAY / trust.POLICY_PATH).read_text(encoding="utf-8")
        cls.policy = work / "policy.json"
        cls.policy.write_text(text.replace(trust.KEY_PATH, str(work / "lumen" / "cosign.pub")), encoding="utf-8")
        cls.registries_d = OVERLAY / trust.REGISTRIES_D

    @classmethod
    def tearDownClass(cls):
        cls.registry.terminate()
        cls.registry.wait()
        shutil.rmtree(cls.work)

    def skopeo(self, *args, check=False):
        return run("skopeo", "--policy", str(self.policy), "--registries.d", str(self.registries_d), *args,
                   env=self.env, check=check)

    def new_image(self):
        """Return a new image, different from every other, as an OCI layout."""
        type(self).count += 1
        return make_image(self.work / f"image-{self.count}", f"image {self.count}\n")

    def push(self, image, reference, key=None, sbom=None):
        """Push IMAGE to REFERENCE, then sign it, and attach SBOM, with KEY ("lumen" or "other") as CI does.

        Returns the image's digest.
        """
        out = self.work / "digest"
        self.skopeo("copy", "--quiet", "--dest-cert-dir", str(self.certs), "--digestfile", str(out),
                    image, f"docker://{reference}", check=True)
        digest = out.read_text(encoding="utf-8").strip()
        if key:
            repository = reference.rsplit(":", 1)[0]
            args = [f"{repository}@{digest}", str(self.work / key / "cosign.key")] + ([str(sbom)] if sbom else [])
            sign = self.sign("sign", *args)
            self.assertEqual(sign.returncode, 0, sign.stdout + sign.stderr)
        return digest

    def sign(self, *args):
        return run("bash", str(HERE / "sign.sh"), *args, env=self.env, check=False)

    def pull(self, reference):
        # skopeo checks the signatures against the policy before it copies
        # anything. An OCI layout can't hold them, so it doesn't copy them.
        type(self).count += 1
        return self.skopeo("copy", "--quiet", "--remove-signatures", "--src-cert-dir", str(self.certs),
                           f"docker://{reference}", f"oci:{self.work / 'pulled'}:{self.count}")

    def assertAccepted(self, reference):
        result = self.pull(reference)
        self.assertEqual(result.returncode, 0, f"{reference} was refused: {result.stderr}")

    def assertRefused(self, reference, why):
        result = self.pull(reference)
        self.assertNotEqual(result.returncode, 0, f"{reference} was accepted")
        self.assertIn(why, result.stderr)

    def test_signed_images_are_accepted(self):
        for repository in trust.REPOSITORIES:
            with self.subTest(repository):
                self.push(self.new_image(), f"{repository}:dev", key="lumen")
                self.assertAccepted(f"{repository}:dev")

    def test_a_signed_image_is_accepted_by_digest(self):
        digest = self.push(self.new_image(), f"{LUMEN}:by-digest", key="lumen")
        self.assertAccepted(f"{LUMEN}@{digest}")

    def test_an_unsigned_image_is_refused(self):
        self.push(self.new_image(), f"{LUMEN}:unsigned")
        self.assertRefused(f"{LUMEN}:unsigned", "A signature was required, but no signature exists")

    def test_another_key_is_refused(self):
        self.push(self.new_image(), f"{LUMEN}:other-key", key="other")
        self.assertRefused(f"{LUMEN}:other-key", "cryptographic signature verification failed")

    def test_a_moved_tag_is_accepted(self):
        # CI signs the digest, then moves dev to it: the signature follows.
        digest = self.push(self.new_image(), f"{LUMEN}:dev-44.20261029", key="lumen")
        self.skopeo("copy", "--quiet", "--src-cert-dir", str(self.certs), "--dest-cert-dir", str(self.certs),
                    f"docker://{LUMEN}@{digest}", f"docker://{LUMEN}:stable", check=True)
        self.assertAccepted(f"{LUMEN}:stable")

    def test_a_signature_for_another_variant_is_refused(self):
        # An image signed as lumen-gaming, offered under lumen's name.
        image = self.new_image()
        digest = self.push(image, f"{REGISTRY}/lumen-gaming:dev", key="lumen")
        self.skopeo("copy", "--quiet", "--src-cert-dir", str(self.certs), "--dest-cert-dir", str(self.certs),
                    "--insecure-policy", f"docker://{REGISTRY}/lumen-gaming:sha256-{digest[7:]}.sig",
                    f"docker://{LUMEN}:sha256-{digest[7:]}.sig", check=True)
        self.push(image, f"{LUMEN}:from-gaming")
        self.assertRefused(f"{LUMEN}:from-gaming", f'Signature for identity \\"{REGISTRY}/lumen-gaming\\" is not accepted')

    def test_the_sbom_is_attached_and_signed(self):
        # What the sign job checks after signing, with the key in the image.
        sbom = self.work / "sbom.spdx.json"
        sbom.write_text(json.dumps({"spdxVersion": "SPDX-2.3", "SPDXID": "SPDXRef-DOCUMENT", "name": "test",
                                    "dataLicense": "CC0-1.0", "packages": []}), encoding="utf-8")
        digest = self.push(self.new_image(), f"{LUMEN}:with-sbom", key="lumen", sbom=sbom)
        image = f"{LUMEN}@{digest}"
        result = self.sign("verify", image, str(self.work / "lumen" / "cosign.pub"), "--sbom")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.sign("verify", image, str(self.work / "other" / "cosign.pub"))
        self.assertNotEqual(result.returncode, 0, "cosign accepted a signature by another key")
        self.assertAccepted(image)

    def test_verify_needs_the_sbom_when_asked(self):
        digest = self.push(self.new_image(), f"{LUMEN}:no-sbom", key="lumen")
        result = self.sign("verify", f"{LUMEN}@{digest}", str(self.work / "lumen" / "cosign.pub"), "--sbom")
        self.assertNotEqual(result.returncode, 0, "cosign found an SBOM attestation that was never made")

    def test_other_registries_are_unchanged(self):
        # Toolbx, distrobox and Podman pull other images unsigned, as on Fedora.
        self.push(self.new_image(), "ghcr.io/someone-else/toolbox:latest")
        self.assertAccepted("ghcr.io/someone-else/toolbox:latest")

    def test_local_transports_are_unchanged(self):
        image = self.new_image()
        for destination in (f"dir:{self.work / 'dir'}", f"oci-archive:{self.work / 'image.tar'}",
                            f"docker-archive:{self.work / 'docker.tar'}"):
            with self.subTest(destination):
                result = self.skopeo("copy", "--quiet", image, destination)
                self.assertEqual(result.returncode, 0, result.stderr)
                again = self.skopeo("copy", "--quiet", destination, f"oci:{self.work / 'again'}:x")
                self.assertEqual(again.returncode, 0, again.stderr)


if __name__ == "__main__":
    unittest.main()
