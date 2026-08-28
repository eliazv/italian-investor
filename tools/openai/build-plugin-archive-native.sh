#!/usr/bin/env bash
set -euo pipefail

if ! command -v zip >/dev/null 2>&1; then
  echo "zip is required." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUT_DIR="${1:-$REPO_ROOT/dist}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

PACKAGE_ROOT="$TMP_DIR/italian-investor"
mkdir -p "$PACKAGE_ROOT/.codex-plugin"

# Uses the hand-authored native manifest directly, so the portal does not need
# to convert/normalize a Claude manifest and no interface defaults are added.
cp "$REPO_ROOT/.codex-plugin/plugin.json" "$PACKAGE_ROOT/.codex-plugin/plugin.json"
cp -R "$REPO_ROOT/skills" "$PACKAGE_ROOT/skills"
cp -R "$REPO_ROOT/assets" "$PACKAGE_ROOT/assets"
cp "$REPO_ROOT/LICENSE" "$PACKAGE_ROOT/LICENSE"
cp "$REPO_ROOT/PRIVACY.md" "$PACKAGE_ROOT/PRIVACY.md"
cp "$REPO_ROOT/SUPPORT.md" "$PACKAGE_ROOT/SUPPORT.md"
cp "$REPO_ROOT/TERMS.md" "$PACKAGE_ROOT/TERMS.md"

find "$PACKAGE_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

mkdir -p "$OUT_DIR"
ARCHIVE="$OUT_DIR/italian-investor-openai-native-submission.zip"
rm -f "$ARCHIVE"

(
  cd "$TMP_DIR"
  zip -qr "$ARCHIVE" italian-investor
)

echo "$ARCHIVE"
