#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is required." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required." >&2
  exit 1
fi

if ! command -v zip >/dev/null 2>&1; then
  echo "zip is required." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL_SOURCE="$REPO_ROOT/skills/italian-investor"

if [[ ! -f "$SKILL_SOURCE/SKILL.md" ]]; then
  echo "Skill not found at $SKILL_SOURCE" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cp -R "$SKILL_SOURCE" "$TMP_DIR/italian-investor"
(
  cd "$TMP_DIR"
  zip -qr italian-investor.zip italian-investor
)

ARCHIVE="$TMP_DIR/italian-investor.zip"
SKILL_ID="${1:-}"

if [[ -z "$SKILL_ID" ]]; then
  echo "Creating OpenAI API skill..." >&2
  curl --fail-with-body --silent --show-error \
    -X POST "https://api.openai.com/v1/skills" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -F "files=@$ARCHIVE;type=application/zip"
else
  echo "Creating a new version for $SKILL_ID and setting it as default..." >&2
  curl --fail-with-body --silent --show-error \
    -X POST "https://api.openai.com/v1/skills/$SKILL_ID/versions" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -F "default=true" \
    -F "files=@$ARCHIVE;type=application/zip"
fi

echo
