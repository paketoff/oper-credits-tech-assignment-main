#!/usr/bin/env bash
# PostToolUse hook: run eslint on an edited frontend TypeScript file.
#
# Project-wide `tsc --noEmit` is deliberately NOT run here: it needs the whole
# project and would cost seconds on every edit. It belongs to /implement step 4
# and to CI. See specs/1-code-quality.md CQ-078.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_hook-lib.sh
. "$SCRIPT_DIR/_hook-lib.sh"

payload="$(cat)"
file="$(extract_file_path "$payload")"
[ -n "$file" ] || exit 0

case "$file" in
  *.ts) ;;
  *) exit 0 ;;
esac

root="$(project_root)"
case "$file" in
  /*) abs="$file" ;;
  *)  abs="$root/$file" ;;
esac

case "$abs" in
  "$root"/frontend/*) ;;
  *) exit 0 ;;
esac

# A deleted or moved file is not a lint failure.
[ -f "$abs" ] || exit 0

[ -f "$root/frontend/package.json" ] || exit 0
[ -d "$root/frontend/node_modules" ] || exit 0
command -v npx >/dev/null 2>&1 || exit 0

cd "$root/frontend" || exit 0

if ! out="$(npx --no-install eslint "$abs" 2>&1)"; then
  printf 'Quality gate failed for %s (specs/1-code-quality.md CQ-079).\n\neslint:\n%s\n' "$abs" "$out" >&2
  exit 2
fi

exit 0
