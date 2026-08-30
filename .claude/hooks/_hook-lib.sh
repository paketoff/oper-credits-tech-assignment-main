#!/usr/bin/env bash
# Shared helpers for PostToolUse lint hooks.
# Reads the hook payload from stdin and resolves the edited file to an absolute path.

# Print the edited file path from a hook JSON payload, or nothing.
extract_file_path() {
  local payload="$1"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$payload" | jq -r '.tool_response.filePath // .tool_input.file_path // empty' 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$payload" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
response = data.get("tool_response") or {}
tool_input = data.get("tool_input") or {}
path = (response.get("filePath") if isinstance(response, dict) else None) or tool_input.get("file_path") or ""
print(path)
' 2>/dev/null
  fi
}

# Print the project root: $CLAUDE_PROJECT_DIR when set, else two levels above this script.
project_root() {
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    printf '%s' "$CLAUDE_PROJECT_DIR"
  else
    (cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
  fi
}
