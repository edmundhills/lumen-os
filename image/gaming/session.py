#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Install the Gamescope session's files from image/gaming/session.toml (step
# 1.10b, docs/decisions/0020-gamescope-session.md): each file from its GitHub
# repository at a pinned commit, checked against its SHA-256 before it is
# written, and installed unchanged.
#
# Usage:
#   python3 session.py check MANIFEST              the manifest's format (just lint)
#   python3 session.py install MANIFEST [ROOT]     download, check and install
#                                                  (the lumen-gaming stage)
#   python3 session.py verify MANIFEST [ROOT]      the installed files are the
#                                                  pinned ones (check-gaming.sh)
#
# ROOT defaults to /. Exits 0 on success, 1 on a problem, 2 on a usage error.

import hashlib
import os
import re
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY = re.compile(r"https://github\.com/(?P<owner>[A-Za-z0-9-]+)/(?P<repo>[A-Za-z0-9._-]+)")
COMMIT = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
MODES = {"0644": 0o644, "0755": 0o755}
# Where the files may go: the vendor folders an image owns.
PREFIXES = ("usr/bin/", "usr/lib/systemd/user/", "usr/share/")


class SessionError(Exception):
    pass


def load(path):
    """Read MANIFEST and return its files as dicts with url, sha256, mode and install."""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise SessionError(f"{path}: {e}") from None
    problems, files, seen = [], [], set()
    sources = data.get("source")
    if not isinstance(sources, list) or not sources or set(data) != {"source"}:
        raise SessionError(f"{path}: expected only [[source]] tables")
    for n, source in enumerate(sources, 1):
        where = f"{path}: source {n}"
        repository, commit = source.get("repository", ""), source.get("commit", "")
        m = REPOSITORY.fullmatch(repository)
        if not m:
            problems.append(f"{where}: repository {repository!r} isn't https://github.com/OWNER/REPO")
        if not COMMIT.fullmatch(commit):
            problems.append(f"{where}: commit {commit!r} isn't a full 40-character commit hash")
        if set(source) - {"repository", "commit", "files"} or not isinstance(source.get("files"), list):
            problems.append(f"{where}: expected repository, commit and a list of files")
            continue
        for entry in source["files"]:
            name = entry.get("path", "")
            install = entry.get("install", name)
            mode = entry.get("mode", "0644")
            if set(entry) - {"path", "install", "mode", "sha256"}:
                problems.append(f"{where}: {name}: unknown keys {sorted(set(entry) - {'path', 'install', 'mode', 'sha256'})}")
            if not name or name.startswith("/") or ".." in name.split("/"):
                problems.append(f"{where}: {name!r} isn't a path in the repository")
            if not install.startswith(PREFIXES) or ".." in install.split("/"):
                problems.append(f"{where}: {name} would go to /{install}, outside {', '.join('/' + p for p in PREFIXES)}")
            if mode not in MODES:
                problems.append(f"{where}: {name}: mode {mode!r} isn't 0644 or 0755")
            if not SHA256.fullmatch(entry.get("sha256", "")):
                problems.append(f"{where}: {name}: sha256 isn't 64 lowercase hex digits")
            if install in seen:
                problems.append(f"{where}: /{install} is installed twice")
            seen.add(install)
            if m:
                files.append({
                    "url": f"https://raw.githubusercontent.com/{m['owner']}/{m['repo']}/{commit}/{name}",
                    "sha256": entry.get("sha256", ""), "mode": MODES.get(mode, 0o644), "install": install,
                })
    if problems:
        raise SessionError("\n".join(problems))
    return files


def download(url, attempts=3):
    """The bytes at URL, retried a few times for a flaky network."""
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == attempts:
                raise SessionError(f"couldn't download {url}: {e}") from None
            time.sleep(5 * attempt)


def install(files, root="/", fetch=download):
    """Download each file, check its SHA-256 and write it under ROOT; refuse to replace a file already there."""
    root = Path(root)
    for f in files:
        data = fetch(f["url"])
        digest = hashlib.sha256(data).hexdigest()
        if digest != f["sha256"]:
            raise SessionError(f"{f['url']} has SHA-256 {digest}, not the pinned {f['sha256']}")
        target = root / f["install"]
        if target.exists():
            raise SessionError(f"/{f['install']} is already in the image; the session must not replace it")
        target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        target.write_bytes(data)
        os.chmod(target, f["mode"])
        print(f"Installed /{f['install']} ({f['sha256'][:12]}…)")


def verify(files, root="/"):
    """Problems with the installed files: missing, changed or with another mode."""
    problems = []
    for f in files:
        target = Path(root) / f["install"]
        if not target.is_file():
            problems.append(f"/{f['install']} is missing")
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != f["sha256"]:
            problems.append(f"/{f['install']} has SHA-256 {digest}, not the pinned {f['sha256']}")
        if target.stat().st_mode & 0o7777 != f["mode"]:
            problems.append(f"/{f['install']} has mode {target.stat().st_mode & 0o7777:04o}, not {f['mode']:04o}")
    return problems


def main(argv):
    if len(argv) not in (3, 4) or argv[1] not in ("check", "install", "verify") or (argv[1] == "check" and len(argv) == 4):
        print("Usage: session.py check MANIFEST | install MANIFEST [ROOT] | verify MANIFEST [ROOT]", file=sys.stderr)
        return 2
    root = argv[3] if len(argv) == 4 else "/"
    try:
        files = load(argv[2])
        if argv[1] == "check":
            print(f"{argv[2]}: {len(files)} files")
        elif argv[1] == "install":
            install(files, root)
        else:
            problems = verify(files, root)
            for p in problems:
                print(p)
            return 1 if problems else 0
    except SessionError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
