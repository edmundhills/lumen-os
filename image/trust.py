#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check Lumen's container trust settings: an image under one of Lumen's names
# is accepted only with Lumen's signature (step 1.7,
# docs/decisions/0008-image-signing.md). bootc pulls updates through
# containers/image, which reads three things:
#
#   /etc/containers/policy.json         which images need which signatures
#   /etc/containers/registries.d/*.yaml where to find the signatures
#   /usr/share/pki/containers/lumen.pub the key CI signs with (policy.json names it)
#
# Usage: python3 image/trust.py check ROOT
#
# ROOT is the folder those paths are under: image/overlay for `just lint`, and
# / inside the image for image/check-image.sh. Exits 0 when the settings are
# Lumen's, 1 when they aren't (saying why), and 2 on a usage error.

import base64
import json
import sys
from pathlib import Path

import yaml

REGISTRY = "ghcr.io/edmundhills"
# Lumen's images, one repository each (docs/architecture.md, section 9.5).
REPOSITORIES = tuple(f"{REGISTRY}/{name}" for name in ("lumen", "lumen-nvidia", "lumen-gaming", "lumen-gaming-nvidia"))
KEY_PATH = "/usr/share/pki/containers/lumen.pub"
POLICY_PATH = "etc/containers/policy.json"
REGISTRIES_D = "etc/containers/registries.d"

# Lumen's images need a signature by Lumen's key. matchRepository accepts the
# signature under any tag of the same repository: cosign signs the digest, and
# CI moves tags such as dev to an image it has already signed.
SIGNED = [{"type": "sigstoreSigned", "keyPath": KEY_PATH, "signedIdentity": {"type": "matchRepository"}}]
ANYTHING = [{"type": "insecureAcceptAnything"}]
REJECT = [{"type": "reject"}]
# The policy rejects what it doesn't name, so it names every other transport
# containers/image has, to keep `podman load`, `skopeo copy oci:…` and the rest
# working as they do on Fedora.
OTHER_TRANSPORTS = ("containers-storage", "dir", "docker-archive", "docker-daemon", "oci", "oci-archive", "sif", "tarball")


def within(scope, repository):
    """Is SCOPE the repository itself, or a tag, digest or path inside it?"""
    return scope == repository or scope.startswith((repository + ":", repository + "@", repository + "/"))


def covers(scope, repository):
    """Does SCOPE apply to REPOSITORY: the repository itself, or a registry or namespace it is in?"""
    return scope == repository or repository.startswith(scope + "/")


def check_policy(policy):
    """Return the problems with a parsed policy.json."""
    problems = []
    if not isinstance(policy, dict):
        return ["policy.json is not a JSON object"]
    if policy.get("default") != REJECT:
        problems.append(
            f"the default is {json.dumps(policy.get('default'))}, not {json.dumps(REJECT)}:"
            " bootc's --enforce-container-sigpolicy refuses a policy that accepts anything by default"
        )
    transports = policy.get("transports")
    if not isinstance(transports, dict):
        return problems + ["policy.json has no transports"]
    docker = transports.get("docker")
    if not isinstance(docker, dict):
        return problems + ["policy.json has no docker transport"]
    if docker.get("") != ANYTHING:
        problems.append(
            f'images from other registries need {json.dumps(docker.get(""))}, not {json.dumps(ANYTHING)}:'
            " Toolbx, distrobox and Podman pull them unsigned, as on Fedora"
        )
    for repository in REPOSITORIES:
        if repository not in docker:
            problems.append(f"{repository} is missing: its images would be accepted unsigned")
    for scope, requirements in docker.items():
        if any(within(scope, repository) for repository in REPOSITORIES) and requirements != SIGNED:
            problems.append(f"{scope} needs {json.dumps(requirements)}, not a signature by {KEY_PATH}: {json.dumps(SIGNED)}")
    for name in OTHER_TRANSPORTS:
        if transports.get(name) != {"": ANYTHING}:
            problems.append(f'the {name} transport is {json.dumps(transports.get(name))}, not {{"": {json.dumps(ANYTHING)}}}')
    for name in transports:
        if name != "docker" and name not in OTHER_TRANSPORTS:
            problems.append(f"the {name} transport is not one Lumen's policy expects")
    return problems


def check_key(path):
    """Return the problems with the public key file at PATH."""
    try:
        text = path.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as e:
        return [f"cannot read the signing key: {e}"]
    lines = text.strip().splitlines()
    if len(lines) < 3 or lines[0] != "-----BEGIN PUBLIC KEY-----" or lines[-1] != "-----END PUBLIC KEY-----":
        return [f"{path} is not a PEM public key (cosign.pub)"]
    try:
        der = base64.b64decode("".join(lines[1:-1]), validate=True)
    except ValueError as e:
        return [f"{path} is not a PEM public key: {e}"]
    # A DER-encoded SubjectPublicKeyInfo is a SEQUENCE.
    if not der.startswith(b"\x30"):
        return [f"{path} is not a PEM public key: its body is not DER"]
    return []


def check_registries(folder):
    """Return the problems with the registries.d files in FOLDER."""
    problems, scopes, default = [], {}, None
    # containers/image reads only the files whose names end in .yaml.
    for path in sorted(folder.glob("*.yaml")):
        try:
            config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as e:
            problems.append(f"cannot read {path}: {e}")
            continue
        if not isinstance(config, dict):
            problems.append(f"{path} is not a YAML mapping")
            continue
        if config.get("default-docker"):
            default = config["default-docker"]
        for scope, settings in (config.get("docker") or {}).items():
            if scope in scopes:
                # containers/image stops with an error when a scope is set twice.
                problems.append(f"{scope} is set in both {scopes[scope][0].name} and {path.name}")
            scopes[scope] = (path, settings or {})
    for repository in REPOSITORIES:
        matching = [scope for scope in scopes if covers(scope, repository)]
        settings = scopes[max(matching, key=len)][1] if matching else (default or {})
        if settings.get("use-sigstore-attachments") is not True:
            problems.append(f"no registries.d file says use-sigstore-attachments: true for {repository}")
    for scope, (path, settings) in scopes.items():
        if any(within(scope, r) for r in REPOSITORIES) and settings.get("use-sigstore-attachments") is not True:
            problems.append(f"{path.name} does not say use-sigstore-attachments: true for {scope}")
    return problems


def check(root):
    """Return the problems with the trust settings under ROOT."""
    problems = []
    policy_path = root / POLICY_PATH
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        problems.append(f"cannot read {policy_path}: {e}")
    else:
        problems += check_policy(policy)
    problems += check_key(root / KEY_PATH.lstrip("/"))
    problems += check_registries(root / REGISTRIES_D)
    return problems


def main(argv):
    if len(argv) != 3 or argv[1] != "check" or not Path(argv[2]).is_dir():
        print("Usage: trust.py check ROOT", file=sys.stderr)
        return 2
    problems = check(Path(argv[2]))
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
