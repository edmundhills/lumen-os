#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Lumen OS contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run every lint check on the repository and report each one.
#
# Usage: bash tests/lint/run.sh
#
# `just lint` runs this in the lint container (tests/lint/Containerfile), which
# has every tool it needs. It checks the files git tracks or would track, so
# ignored files are skipped. Exits 0 when every check passes, 1 otherwise.

set -u

# The folders of the repository layout in CLAUDE.md; each needs a README.md.
readonly LAYOUT_DIRS=(
  apps apps/backup apps/settings apps/store apps/welcome apps/windows-app
  cli compat design design/tokens docs docs/decisions glass hardware image
  installer services services/backupd services/health services/hwd
  services/settingsd services/updated shell tests windows-setup
)

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." || exit 2
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  printf '%s is not a git checkout, so there is nothing to check.\n' "$PWD" >&2
  exit 2
fi

passes=0 failures=0

# check NAME COMMAND...: run one check, and show its output only if it fails.
check() {
  local name=$1 out status
  shift
  if out=$("$@" 2>&1); then
    passes=$((passes + 1))
    printf '  PASS  %s\n' "$name"
  else
    status=$?
    failures=$((failures + 1))
    printf '  FAIL  %s\n' "$name"
    [[ -z $out ]] || printf '%s\n' "$out" | sed 's/^/        /'
    # A tool that crashes can stop without saying why, so say how it ended.
    if ((status > 128)); then
      printf '        (crashed with exit status %d)\n' "$status"
    elif [[ -z $out ]]; then
      printf '        (no output; exit status %d)\n' "$status"
    fi
  fi
}

# Sort the files git tracks or would track into the lists the checks need.
shell_files=() markdown_files=() yaml_files=() workflow_files=() text_files=()
while IFS= read -r -d '' f; do
  [[ -f $f ]] || continue # deleted, but not yet staged
  case $f in
    *.md) markdown_files+=("$f") ;;
    *.sh) shell_files+=("$f") ;;
    *.yaml | *.yml)
      yaml_files+=("$f")
      [[ $f != .github/workflows/* ]] || workflow_files+=("$f")
      ;;
    *)
      # A file with no extension is a shell script if its first line says so.
      if [[ ${f##*/} != *.* ]] && head -n 1 -- "$f" | grep -Eq '^#!.*[/ ](ba)?sh([[:space:]]|$)'; then
        shell_files+=("$f")
      fi
      ;;
  esac
  grep -Iq '' -- "$f" && text_files+=("$f") # skips binary files such as images
done < <(git ls-files -z --cached --others --exclude-standard)

# The tools refuse an empty file list, so each wrapper does nothing without files.
shell_lint() { ((${#shell_files[@]} == 0)) || shellcheck -- "${shell_files[@]}"; }
shell_format() { ((${#shell_files[@]} == 0)) || shfmt -d -- "${shell_files[@]}"; }
# A leading ':' makes markdownlint-cli2 read each name as a path, not a glob.
markdown_style() { ((${#markdown_files[@]} == 0)) || markdownlint-cli2 "${markdown_files[@]/#/:}"; }
yaml_style() { ((${#yaml_files[@]} == 0)) || yamllint --strict -- "${yaml_files[@]}"; }
workflows() { ((${#workflow_files[@]} == 0)) || actionlint -- "${workflow_files[@]}"; }

# Text files use LF line endings, have no trailing spaces or tabs, and end with a newline.
whitespace() {
  local f lines status=0
  for f in "${text_files[@]}"; do
    if grep -q $'\r' -- "$f"; then
      printf '%s: Windows line endings (CR LF); the repository uses LF\n' "$f"
      status=1
    fi
    if lines=$(grep -n '[[:blank:]]$' -- "$f"); then
      printf '%s: trailing whitespace on line %s\n' "$f" "$(printf '%s\n' "$lines" | cut -d: -f1 | paste -sd, -)"
      status=1
    fi
    if [[ -n $(tail -c 1 -- "$f") ]]; then
      printf '%s: no newline at the end of the file\n' "$f"
      status=1
    fi
  done
  return "$status"
}

# Every folder of the layout has a README, and the two copies of the GPL agree.
layout() {
  local d status=0
  for d in "${LAYOUT_DIRS[@]}"; do
    if [[ ! -f $d/README.md ]]; then
      printf '%s/README.md is missing (CLAUDE.md, "Repo layout")\n' "$d"
      status=1
    fi
  done
  if [[ $(sha256sum <LICENSE) != "$(sha256sum <LICENSES/GPL-3.0-or-later.txt)" ]]; then
    printf 'LICENSE and LICENSES/GPL-3.0-or-later.txt differ: both are the GPL-3.0 text from gnu.org\n'
    status=1
  fi
  return "$status"
}

printf 'Lumen OS lint\n'
check "Licences and copyright (reuse lint)" reuse lint
check "Shell scripts (shellcheck)" shell_lint
check "Shell formatting (shfmt, .editorconfig)" shell_format
check "Markdown style (markdownlint, .markdownlint.yaml)" markdown_style
check "Markdown links (check-links.py)" python3 tests/lint/check-links.py "${markdown_files[@]}"
check "YAML style (yamllint, .yamllint.yaml)" yaml_style
check "GitHub Actions workflows (actionlint)" workflows
check "justfile formatting (just --fmt)" just --fmt --check
check "Whitespace and line endings" whitespace
check "Repository layout and licence files" layout

printf '\nPassed: %d   Failed: %d\n' "$passes" "$failures"
((failures == 0))
