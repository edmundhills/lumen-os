#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check Lumen's kernel module signing certificate (step 1.11a,
# docs/decisions/0021-module-signing-key.md): the certificate users enrol as a
# MOK, so that the kernel loads the NVIDIA modules Lumen signs.
#
# Usage: python3 module_key.py check CERTIFICATE
#
# CERTIFICATE is DER, as make-module-key.sh writes it. The check: a
# self-signed X.509 v3 certificate for "Lumen OS kernel module signing", an
# RSA key of 4096 bits signed with SHA-256, marked critical as not a CA, for
# digital signatures. Prints its SHA-256 fingerprint. Exits 0 when it passes,
# 1 when it doesn't (saying why), 2 on a usage error. Needs openssl.

import re
import subprocess
import sys

SUBJECT = "O=Lumen OS, CN=Lumen OS kernel module signing"


def describe(path):
    """openssl's text description of the DER certificate at PATH."""
    result = subprocess.run(["openssl", "x509", "-inform", "DER", "-in", path, "-noout", "-text",
                             "-nameopt", "RFC2253", "-fingerprint", "-sha256"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(f"{path} isn't a DER certificate: {result.stderr.strip()}")
    return result.stdout


def field(text, name):
    m = re.search(rf"^\s*{re.escape(name)}:\s*(.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def extension(text, name):
    """The first line after an extension's heading, and whether it is critical."""
    m = re.search(rf"^\s*X509v3 {re.escape(name)}:( critical)?\s*\n\s*(.*)$", text, re.MULTILINE)
    return (m.group(2).strip(), bool(m.group(1))) if m else (None, False)


def problems(text):
    found = []
    # -nameopt RFC2253 prints the most significant part last.
    subject = ", ".join(reversed([p.strip() for p in field(text, "Subject").split(",")]))
    issuer = ", ".join(reversed([p.strip() for p in field(text, "Issuer").split(",")]))
    if subject != SUBJECT:
        found.append(f"the subject is {subject or 'missing'}, not {SUBJECT}")
    if issuer != subject:
        found.append(f"it isn't self-signed: the issuer is {issuer}")
    if not re.search(r"^\s*Version:\s*3\b", text, re.MULTILINE):
        found.append("it isn't an X.509 v3 certificate")
    if "Public Key Algorithm: rsaEncryption" not in text or not re.search(r"Public-Key:\s*\(4096 bit\)", text):
        found.append("its key isn't RSA with 4096 bits")
    if not re.search(r"Signature Algorithm:\s*sha256WithRSAEncryption", text):
        found.append("it isn't signed with SHA-256 and RSA")
    constraints, critical = extension(text, "Basic Constraints")
    if constraints != "CA:FALSE" or not critical:
        found.append(f"its basic constraints are {constraints or 'missing'}, not critical CA:FALSE")
    usage, _ = extension(text, "Key Usage")
    if not usage or "Digital Signature" not in usage:
        found.append(f"its key usage is {usage or 'missing'}, not Digital Signature")
    return found


def fingerprint(text):
    m = re.search(r"SHA256 Fingerprint=([0-9A-F:]+)", text, re.IGNORECASE)
    return m.group(1) if m else ""


def main(argv):
    if len(argv) != 3 or argv[1] != "check":
        print("Usage: module_key.py check CERTIFICATE", file=sys.stderr)
        return 2
    try:
        text = describe(argv[2])
    except (OSError, ValueError) as e:
        print(f"module_key.py: {e}", file=sys.stderr)
        return 1
    found = problems(text)
    for p in found:
        print(f"Problem: {p}", file=sys.stderr)
    if found:
        return 1
    print(f"{argv[2]}: Lumen's module signing certificate, SHA-256 fingerprint {fingerprint(text)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
