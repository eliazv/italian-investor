#!/usr/bin/env bash
set -euo pipefail

if ! command -v zip >/dev/null 2>&1; then
  echo "zip is required." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SOURCE="$REPO_ROOT/skills/italian-investor"
OUT_DIR="${1:-$REPO_ROOT/dist}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [[ ! -f "$SKILL_SOURCE/SKILL.md" ]]; then
  echo "Skill not found at $SKILL_SOURCE" >&2
  exit 1
fi

cp -R "$SKILL_SOURCE" "$TMP_DIR/italian-investor"
mkdir -p "$OUT_DIR"
ARCHIVE="$OUT_DIR/italian-investor-skill.zip"
rm -f "$ARCHIVE"

(
  cd "$TMP_DIR"
  zip -qr "$ARCHIVE" italian-investor
)

echo "$ARCHIVE"
