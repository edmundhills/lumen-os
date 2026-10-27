#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test the lint checks in run.sh: each one must catch a file that breaks its rule.
#
# Usage: bash tests/lint/selftest.sh
#
# `just test` runs this in the lint container. It copies the repository to a
# temporary folder, checks that the copy passes and that markdownlint can
# measure a table that holds an emoji, adds one fault for each check, and checks
# that every check then fails. Exits 0 when all of that holds.

set -u

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd) || exit 2
work=$(mktemp -d) || exit 2
trap 'rm -rf -- "$work"' EXIT

status=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() {
  status=1
  printf '  FAIL  %s\n' "$1"
  [[ -z ${2:-} ]] || printf '%s\n' "$2" | sed 's/^/        /'
}

printf 'Lumen OS lint self-test\n'

# Copy what git tracks or would track, and make the copy a git repository.
while IFS= read -r -d '' f; do
  [[ -f $repo/$f ]] || continue
  mkdir -p -- "$work/$(dirname -- "$f")"
  cp -p -- "$repo/$f" "$work/$f"
done < <(git -C "$repo" ls-files -z --cached --others --exclude-standard)
git -C "$work" init -q && git -C "$work" add -A || exit 2

if out=$(bash "$work/tests/lint/run.sh" 2>&1); then
  pass "An unchanged copy of the repository passes"
else
  fail "An unchanged copy of the repository should pass" "$out"
fi

# markdownlint measures any table cell that isn't plain ASCII with
# Intl.Segmenter, which crashes Node if its full ICU data is missing
# (tests/lint/Containerfile).
printf '# Table\n\n| Check | OK? |\n| --- | --- |\n| Emoji | ✅ |\n' >"$work/table.md"
if out=$(cd -- "$work" && markdownlint-cli2 :table.md 2>&1); then
  pass "markdownlint measures a table that holds an emoji"
else
  fail "markdownlint should measure a table that holds an emoji (exit status $?)" "$out"
fi
rm -- "$work/table.md"

# One fault for each check, named by a word from its line in run.sh's output.
cd -- "$work" || exit 2
printf 'This file has no licence header.\n' >fault.txt
printf 'This line ends with a space. \n' >>fault.txt
# shellcheck disable=SC2016 # the unquoted $1 is the fault
printf '#!/usr/bin/env bash\necho $1\n' >fault.sh
printf 'if true; then\n    echo "indented by 4 spaces, not 2"\nfi\n' >>fault.sh
printf '# Fault\n\n#No space after the hash\n\n[A link](no-such-file.md)\n' >fault.md
printf '\nfault:\n  echo "a recipe indented by 2 spaces, not 4"\n' >>justfile
printf 'key: 1\nkey: 2\n' >fault.yaml
printf 'on: push\njobs:\n  fault:\n    needs: no-such-job\n    runs-on: ubuntu-24.04\n    steps:\n      - run: "true"\n' >.github/workflows/fault.yml
rm -- glass/README.md
git add -A

faults=(
  "reuse:a file without a licence header"
  "shellcheck:an unquoted variable"
  "shfmt:a badly indented script"
  "markdownlint:a heading with no space after the #"
  "check-links:a link to a missing file"
  "yamllint:a key given twice"
  "actionlint:a job that needs a missing job"
  "just:a badly indented justfile recipe"
  "Whitespace:a line that ends in a space"
  "layout:a missing README"
)
if out=$(bash tests/lint/run.sh 2>&1); then
  fail "Lint should fail on a copy with a fault for every check" "$out"
else
  for fault in "${faults[@]}"; do
    word=${fault%%:*}
    if grep -Eq "^  FAIL  .*\\b$word\\b" <<<"$out"; then
      pass "The $word check catches ${fault#*:}"
    else
      fail "The $word check misses ${fault#*:}" "$out"
    fi
  done
fi

exit "$status"
