#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Check a re-chunked Lumen image, and measure what an update to it downloads
# (step 1.5c, ADR 0007, risk 14 in docs/risks.md). image/rechunk.sh and the
# image workflow (.github/workflows/build-image.yml) run it on what skopeo
# prints, so it needs neither the images nor the network.
#
# Usage:
#   python3 image/rechunk.py chunked MANIFEST
#       Exit 0 if the image whose manifest (skopeo inspect --raw) is in
#       MANIFEST was re-chunked by rpm-ostree, so it can be the PREVIOUS of
#       image/rechunk.sh, or 1 if not. Says why either way.
#   python3 image/rechunk.py labels BEFORE AFTER
#       Compare two image configs (skopeo inspect --config): the built image
#       and the same image re-chunked. Exit 0 if they have the same labels and
#       settings, apart from what re-chunking is meant to change, or 1 if not.
#   python3 image/rechunk.py download BUDGET_MIB MANIFEST CONFIG [PREVIOUS_MANIFEST PREVIOUS_CONFIG]
#       Write, in Markdown, what updating from the previous build to this one
#       downloads: the layers the previous build doesn't have, by size and
#       what they hold. Exit 1 if the download is over BUDGET_MIB and both
#       builds are re-chunked and on the same base image, or 0 otherwise.
#
# Exits 2 on a usage error or a file it can't read.

import hashlib
import json
import sys

# rpm-ostree records the packages in each layer it makes in this annotation.
COMPONENTS = "ostree.components"
# Labels that re-chunking replaces: the image's ostree commit is a new one.
REPLACED = ("ostree.commit", "ostree.final-diffid")
# Labels image/rechunk.sh adds: Podman's annotations naming the base image.
ADDED = ("org.opencontainers.image.base.name", "org.opencontainers.image.base.digest")
# Labels bootc needs on every bootable image.
REQUIRED = {"containers.bootc": "1", "ostree.bootable": "true"}
VERSION = "org.opencontainers.image.version"
BASE = "org.opencontainers.image.base.name"
# Plain names for the components rpm-ostree makes up.
COMPONENT_NAMES = {"rpmostree-unpackaged-content": "files no package owns"}
MIB = 1024 * 1024


class InputError(Exception):
    pass


def read_json(path):
    """Return the JSON in the file PATH, and the SHA-256 digest of its bytes."""
    try:
        with open(path, "rb") as f:
            data = f.read()
        return json.loads(data), "sha256:" + hashlib.sha256(data).hexdigest()
    except (OSError, ValueError) as e:
        raise InputError(f"{path}: {e}") from e


def layers(manifest):
    """Return the layers of an image manifest, or raise InputError for anything else."""
    if "layers" not in manifest:
        kind = "an image index" if "manifests" in manifest else "not an image manifest"
        raise InputError(f"{kind}, so there are no layers to read")
    return manifest["layers"]


def chunked(manifest):
    """Return (True or False, why): was this image re-chunked by rpm-ostree?

    rpm-ostree writes the ostree commit as the first layer, and names the
    packages in every other layer in its annotations. It reads those names
    back when it is given the image as a previous build, and stops if any
    layer has none.
    """
    try:
        found = layers(manifest)
    except InputError as e:
        return False, str(e)
    if len(found) < 2:
        return False, f"it has {len(found)} layer(s); a re-chunked image has the ostree commit and more"
    unnamed = [i for i, layer in enumerate(found[1:], 1) if COMPONENTS not in (layer.get("annotations") or {})]
    if unnamed:
        return False, (f"{len(unnamed)} of its {len(found)} layers don't say which packages they hold"
                       f" (no {COMPONENTS} annotation), the first being layer {unnamed[0]}")
    return True, f"each of its {len(found)} layers after the first says which packages it holds"


def compare_labels(before, after):
    """Return what differs between two image configs, other than what re-chunking changes."""
    problems = []
    if (before.get("architecture"), before.get("os")) != (after.get("architecture"), after.get("os")):
        problems.append(f"the platform changed from {before.get('os')}/{before.get('architecture')}"
                        f" to {after.get('os')}/{after.get('architecture')}")
    old, new = before.get("config") or {}, after.get("config") or {}
    for key in sorted(set(old) | set(new)):
        if key != "Labels" and old.get(key) != new.get(key):
            problems.append(f"the setting {key} changed from {old.get(key)!r} to {new.get(key)!r}")
    old, new = old.get("Labels") or {}, new.get("Labels") or {}
    for key in sorted(old):
        if key in REPLACED:
            continue
        if key not in new:
            problems.append(f"the label {key} is gone (it was {old[key]!r})")
        elif new[key] != old[key]:
            problems.append(f"the label {key} changed from {old[key]!r} to {new[key]!r}")
    for key in REPLACED:
        if not new.get(key):
            problems.append(f"the label {key} is missing")
    for key, value in REQUIRED.items():
        if new.get(key) != value:
            problems.append(f"the label {key} is {new.get(key)!r}, not {value!r}, so bootc won't take the image")
    for key in sorted(set(new) - set(old) - set(REPLACED) - set(ADDED)):
        problems.append(f"a new label {key}={new[key]!r} appeared; if that is expected, add it to ADDED in rechunk.py")
    return problems


def describe(layer, index):
    """Return what a layer of a re-chunked image holds, in a few words."""
    if index == 0:
        return "the ostree commit: the metadata of every file and folder"
    names = (layer.get("annotations") or {}).get(COMPONENTS)
    if names is None:
        return "not named (this image isn't re-chunked)"
    names = [COMPONENT_NAMES.get(n, n) for n in names.split(",") if n]
    if not names:
        return "nothing yet: kept empty for packages added later"
    if len(names) > 4:
        return ", ".join(names[:3]) + f" and {len(names) - 3} more"
    return ", ".join(names)


def mib(size):
    return f"{size / MIB:,.1f} MiB"


def download(budget_mib, manifest, config, digest, previous=None):
    """Return (Markdown report, True if within the budget) for an update from PREVIOUS.

    MANIFEST, CONFIG and DIGEST describe the new build; PREVIOUS is None or a
    (manifest, config, digest) tuple for the build users have now.
    """
    new_layers = layers(manifest)
    total = sum(layer["size"] for layer in new_layers)
    labels = (config.get("config") or {}).get("Labels") or {}
    lines = ["### Download from the previous build", ""]
    lines.append(f"This build: {labels.get(VERSION, 'no version label')} (`{digest}`),"
                 f" {len(new_layers)} layers, {mib(total)} compressed.")
    if previous is None:
        lines += ["", "There is no previous build to compare with, so an update to this one downloads all of it.", ""]
        return "\n".join(lines), True

    old_manifest, old_config, old_digest = previous
    old_labels = (old_config.get("config") or {}).get("Labels") or {}
    have = {layer["digest"] for layer in layers(old_manifest)}
    missing = [(i, layer) for i, layer in enumerate(new_layers) if layer["digest"] not in have]
    size = sum(layer["size"] for _, layer in missing)
    old_chunked, _ = chunked(old_manifest)
    lines.append(f"Previous build: {old_labels.get(VERSION, 'no version label')} (`{old_digest}`).")
    lines += ["", f"An update downloads **{len(missing)} of {len(new_layers)} layers, {mib(size)}**.", ""]

    budget = budget_mib * MIB
    within = True
    if not old_chunked:
        lines.append("The previous build isn't re-chunked, so its layers can't match these: this update"
                     " downloads nearly everything, once. The budget applies from the next build.")
    elif not old_labels.get(BASE) or not labels.get(BASE):
        lines.append(f"A build doesn't name its base image (label {BASE}), so the budget can't be applied.")
    elif old_labels[BASE] != labels[BASE]:
        lines.append(f"The base image changed, from `{old_labels[BASE]}` to `{labels[BASE]}`, so most of"
                     f" this download is Fedora's updates. The budget of {budget_mib} MiB covers builds on"
                     " the same base.")
    elif size > budget:
        within = False
        lines.append(f"**Over the budget** of {budget_mib} MiB for a build on the same base image. The"
                     " layers below say what changed. Make the change smaller, or give the files that"
                     " change on every build a layer of their own (ADR 0007).")
    else:
        lines.append(f"Within the budget of {budget_mib} MiB for a build on the same base image.")

    if missing:
        lines += ["", "| Layer | Size | Holds |", "| ---: | ---: | --- |"]
        for i, layer in sorted(missing, key=lambda m: -m[1]["size"])[:20]:
            lines.append(f"| {i} | {mib(layer['size'])} | {describe(layer, i)} |")
        if len(missing) > 20:
            lines.append(f"| | | and {len(missing) - 20} smaller layers |")
    lines.append("")
    return "\n".join(lines), within


def main(argv):
    usage = (
        "Usage: rechunk.py chunked MANIFEST\n"
        "       rechunk.py labels BEFORE AFTER\n"
        "       rechunk.py download BUDGET_MIB MANIFEST CONFIG [PREVIOUS_MANIFEST PREVIOUS_CONFIG]"
    )
    command, args = (argv[1], argv[2:]) if len(argv) > 1 else (None, [])
    try:
        if command == "chunked" and len(args) == 1:
            ok, why = chunked(read_json(args[0])[0])
            print(f"{args[0]}: {'re-chunked' if ok else 'not re-chunked'}: {why}")
            return 0 if ok else 1
        if command == "labels" and len(args) == 2:
            problems = compare_labels(read_json(args[0])[0], read_json(args[1])[0])
            for problem in problems:
                print(f"After re-chunking, {problem}.", file=sys.stderr)
            if not problems:
                print("The re-chunked image has the same labels and settings.")
            return 1 if problems else 0
        if command == "download" and len(args) in (3, 5) and args[0].isdigit():
            manifest, digest = read_json(args[1])
            previous = None
            if len(args) == 5:
                old_manifest, old_digest = read_json(args[3])
                previous = (old_manifest, read_json(args[4])[0], old_digest)
            report, within = download(int(args[0]), manifest, read_json(args[2])[0], digest, previous)
            print(report)
            if not within:
                print("The update is over the download budget.", file=sys.stderr)
            return 0 if within else 1
    except InputError as e:
        print(f"rechunk.py: {e}", file=sys.stderr)
        return 2
    except (KeyError, TypeError, AttributeError) as e:
        print(f"rechunk.py: unexpected input, at {e!r}", file=sys.stderr)
        return 2
    print(usage, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
