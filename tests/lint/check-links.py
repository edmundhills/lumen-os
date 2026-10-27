#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the relative links in Markdown files.

Usage: check-links.py FILE...

Run from the repository root. A link to another file in the repository must
point at a file or folder that exists, and a link to a heading (#anchor) must
match a heading in the target file, using GitHub's rules for heading anchors.
Links to websites are not checked, so this needs no network.

Exits 0 when every link is good, 1 otherwise.
"""

import re
import sys
import urllib.parse
from pathlib import Path

FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
CODE_SPAN = re.compile(r"(`+).+?\1")
# [text](target) and ![alt](target), with an optional "title".
INLINE_LINK = re.compile(
    r"!?\[(?:[^\[\]]|\[[^\[\]]*\])*\]"
    r"\(\s*(<[^>]*>|[^\s()]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)"
)
# [label]: target
REFERENCE = re.compile(r"^ {0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)")
HTML_ID = re.compile(r"<[^>]*\s(?:id|name)=[\"']([^\"']+)[\"']")
URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def text_lines(path):
    """Yield (line number, line) for the lines outside fenced code blocks."""
    fence = None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = FENCE.match(line)
        if fence:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
                fence = None
        elif match:
            fence = match.group(1)
        else:
            yield number, line


def slug(heading):
    """The anchor GitHub gives a heading."""
    text = re.sub(r"<[^>]+>", "", heading)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "").replace("*", "").strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path, cache={}):
    """Every anchor in a Markdown file: its headings, plus explicit HTML ids."""
    if path not in cache:
        found, seen = set(), {}
        for _, line in text_lines(path):
            found.update(HTML_ID.findall(line))
            match = HEADING.match(line)
            if match:
                base = slug(match.group(2))
                count = seen.get(base, 0)
                seen[base] = count + 1
                found.add(base if count == 0 else f"{base}-{count}")
        cache[path] = found
    return cache[path]


def problem(source, target, root):
    """What is wrong with a link from SOURCE to TARGET, or None."""
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if not target or URL_SCHEME.match(target) or target.startswith("//"):
        return None
    path_part, _, anchor = target.partition("#")
    path_part = urllib.parse.unquote(path_part)
    anchor = urllib.parse.unquote(anchor)
    dest = (source.parent / path_part).resolve() if path_part else source.resolve()
    if dest != root and root not in dest.parents:
        return "points outside the repository"
    if not dest.exists():
        return "no such file or folder"
    if anchor and dest.suffix == ".md" and anchor not in anchors(dest):
        return f"no heading with the anchor #{anchor}"
    return None


def main(files):
    root = Path.cwd().resolve()
    broken = 0
    for name in files:
        source = Path(name)
        for number, line in text_lines(source):
            line = CODE_SPAN.sub("", line)
            targets = [m.group(1) for m in INLINE_LINK.finditer(line)]
            targets += [m.group(1) for m in REFERENCE.finditer(line)]
            for target in targets:
                reason = problem(source, target, root)
                if reason:
                    broken += 1
                    print(f"{name}:{number}: {target}: {reason}")
    if broken:
        print(f"{broken} broken link(s)")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
