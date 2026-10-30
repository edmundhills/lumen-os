#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Python bytecode that matches its source, for the live system (step 1.8b-3b,
# docs/decisions/0012-install-iso.md, Follow-up).
#
# The image gives every file the time 0, but Fedora's .pyc files record the
# time their source had when the package was built, so Python takes almost all
# of them for stale and compiles the module again whenever it imports it. On
# an installed system /usr is read-only, so that only costs time. The live
# session's /usr is writable, so Python writes the new bytecode into it, and
# where a program's SELinux policy doesn't allow that, as for tuned-ppd, the
# policy logs it.
#
# Usage:
#   python3 image/live/bytecode.py fix ROOT
#       Compile again every stale .pyc of this Python under ROOT's
#       /usr/lib*/python3.*, checked by a hash of its source (PEP 552) instead
#       of the source's time, which nothing that copies the file can upset.
#   python3 image/live/bytecode.py check ROOT
#       List the stale .pyc files there, if there are any.
#
# The live stage of image/Containerfile runs `fix`, image/live/check-live.sh
# runs `check`, and image/test_bytecode.py tests both. Exits 0 when all is
# well, 1 when a .pyc is stale or can't be compiled, and 2 on a usage error.

import glob
import importlib.util
import os
import py_compile
import struct
import sys

# The flag in a .pyc's header that says it is checked by a hash, not a time.
HASH_BASED = 0b1


def bytecode_files(root):
    """Return the .pyc files of this Python under ROOT's /usr/lib*/python3.*, in their __pycache__ folders."""
    pattern = os.path.join(root, "usr/lib*/python3.*/**/__pycache__", f"*.{sys.implementation.cache_tag}*.pyc")
    return sorted(glob.glob(pattern, recursive=True))


def source_of(pyc):
    """Return the source a __pycache__ file was compiled from, and its optimization level.

    The names are MODULE.CACHE_TAG.pyc and MODULE.CACHE_TAG.opt-N.pyc.
    """
    parts = os.path.basename(pyc).split(".")
    level = int(parts[2][4:]) if len(parts) == 4 and parts[2].startswith("opt-") else 0
    return os.path.join(os.path.dirname(os.path.dirname(pyc)), parts[0] + ".py"), level


def is_stale(pyc, source):
    """Return whether Python would compile SOURCE again rather than use PYC."""
    with open(pyc, "rb") as f:
        header = f.read(16)
    if len(header) < 16 or header[:4] != importlib.util.MAGIC_NUMBER:
        return True
    flags, mtime, size = struct.unpack("<III", header[4:])
    if flags & HASH_BASED:
        return False
    st = os.stat(source)
    return mtime != int(st.st_mtime) & 0xFFFFFFFF or size != st.st_size & 0xFFFFFFFF


def find_stale(root):
    """Return the number of .pyc files with a source under ROOT, and [(pyc, source, level)] for the stale ones."""
    total, stale = 0, []
    for pyc in bytecode_files(root):
        source, level = source_of(pyc)
        if not os.path.isfile(source):
            continue
        total += 1
        if is_stale(pyc, source):
            stale.append((pyc, source, level))
    return total, stale


def fix(root):
    """Compile every stale .pyc under ROOT again, checked by its source's hash; return the ones that failed."""
    failed = []
    for pyc, source, level in find_stale(root)[1]:
        # The path tracebacks show: the file's, on the system ROOT holds.
        shown = os.path.join("/", os.path.relpath(source, root))
        try:
            py_compile.compile(source, cfile=pyc, dfile=shown, doraise=True, optimize=level,
                               invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH)
        except (OSError, py_compile.PyCompileError) as e:
            failed.append(f"{source}: {e}")
    return failed


def main(argv):
    if len(argv) != 3 or argv[1] not in ("fix", "check") or not os.path.isdir(argv[2]):
        print("Usage: bytecode.py fix|check ROOT", file=sys.stderr)
        return 2
    command, root = argv[1], argv[2]
    total, stale = find_stale(root)
    if command == "check":
        if stale:
            print(f"{len(stale)} of {total} .pyc files are stale, for example:")
            print("\n".join(pyc for pyc, _, _ in stale[:10]))
            return 1
        print(f"None of {total} .pyc files is stale")
        return 0
    failed = fix(root)
    print(f"Compiled {len(stale) - len(failed)} of {total} .pyc files again, checked by their source's hash")
    if failed:
        print(f"{len(failed)} could not be compiled:\n" + "\n".join(failed[:10]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
