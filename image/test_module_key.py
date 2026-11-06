# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unit tests for nvidia/module_key.py (step 1.11a, ADR 0021): certificates made
# with openssl the way make-module-key.sh makes one, and with one thing wrong
# each. `just test` runs them in the lint container, which has openssl:
#   python3 -m unittest discover --start-directory image

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "nvidia"))
import module_key  # noqa: E402

GOOD = {"bits": "4096", "subject": "/O=Lumen OS/CN=Lumen OS kernel module signing",
        "constraints": "critical,CA:FALSE", "usage": "digitalSignature"}


@unittest.skipUnless(shutil.which("openssl"), "needs openssl")
class Check(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = Path(tempfile.mkdtemp())
        cls.certs = {}
        variants = {
            "good": {},
            "2048 bits": {"bits": "2048"},
            "a CA": {"constraints": "critical,CA:TRUE"},
            "not critical": {"constraints": "CA:FALSE"},
            "another name": {"subject": "/O=Someone/CN=Someone's modules"},
            "only for key encipherment": {"usage": "keyEncipherment"},
        }
        for name, change in variants.items():
            v = {**GOOD, **change}
            path = cls.work / f"{name}.der"
            subprocess.run(["openssl", "req", "-new", "-x509", "-newkey", f"rsa:{v['bits']}", "-sha256", "-days", "36500",
                            "-subj", v["subject"], "-addext", f"basicConstraints={v['constraints']}",
                            "-addext", f"keyUsage={v['usage']}", "-noenc", "-keyout", str(cls.work / f"{name}.key"),
                            "-outform", "DER", "-out", str(path)], check=True, capture_output=True)
            cls.certs[name] = path

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work)

    def found(self, name):
        return module_key.problems(module_key.describe(str(self.certs[name])))

    def test_the_profile_make_module_key_uses_passes(self):
        self.assertEqual(self.found("good"), [])
        text = module_key.describe(str(self.certs["good"]))
        self.assertRegex(module_key.fingerprint(text), r"^([0-9A-F]{2}:){31}[0-9A-F]{2}$")

    def test_each_fault_is_named(self):
        for name, words in (("2048 bits", "isn't RSA with 4096 bits"),
                            ("a CA", "not critical CA:FALSE"),
                            ("not critical", "not critical CA:FALSE"),
                            ("another name", "not O=Lumen OS, CN=Lumen OS kernel module signing"),
                            ("only for key encipherment", "not Digital Signature")):
            with self.subTest(name):
                self.assertTrue(any(words in p for p in self.found(name)), self.found(name))

    def test_what_isnt_a_certificate(self):
        junk = self.work / "junk.der"
        junk.write_bytes(b"not a certificate")
        with self.assertRaises(ValueError):
            module_key.describe(str(junk))
        self.assertEqual(module_key.main(["module_key.py", "check", str(junk)]), 1)
        self.assertEqual(module_key.main(["module_key.py"]), 2)

    def test_the_committed_certificate(self):
        cert = HERE / "nvidia" / "module-signing.der"
        if not cert.exists():
            self.skipTest("the owner hasn't committed the certificate yet (step 1.11a)")
        self.assertEqual(module_key.problems(module_key.describe(str(cert))), [])

    def test_the_script_makes_this_profile(self):
        script = (HERE / "nvidia" / "make-module-key.sh").read_text()
        for part in ("rsa:4096", "-sha256", '-subj "/O=Lumen OS/CN=Lumen OS kernel module signing"',
                     '"basicConstraints=critical,CA:FALSE"', '"keyUsage=digitalSignature"', "--network=none"):
            self.assertIn(part, script)
        self.assertNotIn("-noenc", script)  # The real key is encrypted with a password.


if __name__ == "__main__":
    unittest.main()
