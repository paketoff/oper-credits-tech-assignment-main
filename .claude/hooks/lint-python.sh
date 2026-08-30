#!/usr/bin/env bash
# PostToolUse hook: run ruff and mypy on an edited backend Python file.
#
# Exits 0 (silently) when the edit is not a backend .py file, or when the toolchain
# is not installed yet -- the hook is inert until backend/ is scaffolded.
# Exits 2 with the tool output on stderr when a check fails, so Claude Code feeds
# the errors back to the model. See specs/1-code-quality.md CQ-076, CQ-077.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_hook-lib.sh
. "$SCRIPT_DIR/_hook-lib.sh"

payload="$(cat)"
file="$(extract_file_path "$payload")"
[ -n "$file" ] || exit 0

case "$file" in
  *.py) ;;
  *) exit 0 ;;
esac

root="$(project_root)"
case "$file" in
  /*) abs="$file" ;;
  *)  abs="$root/$file" ;;
esac

case "$abs" in
  "$root"/backend/*) ;;
  *) exit 0 ;;
esac

# A deleted or moved file is not a lint failure.
[ -f "$abs" ] || exit 0

[ -f "$root/backend/pyproject.toml" ] || exit 0

have_ruff=0
have_mypy=0
command -v ruff >/dev/null 2>&1 && have_ruff=1
command -v mypy >/dev/null 2>&1 && have_mypy=1
[ "$have_ruff" -eq 1 ] || [ "$have_mypy" -eq 1 ] || exit 0

cd "$root/backend" || exit 0

failed=0
report=""

if [ "$have_ruff" -eq 1 ]; then
  if ! out="$(ruff check --force-exclude "$abs" 2>&1)"; then
    failed=1
    report="${report}ruff:
${out}

"
  fi
fi

if [ "$have_mypy" -eq 1 ]; then
  if ! out="$(mypy --strict "$abs" 2>&1)"; then
    failed=1
    report="${report}mypy --strict:
${out}

"
  fi
fi

if [ "$failed" -eq 1 ]; then
  printf 'Quality gate failed for %s (specs/1-code-quality.md CQ-079).\n\n%s' "$abs" "$report" >&2
  exit 2
fi

exit 0
