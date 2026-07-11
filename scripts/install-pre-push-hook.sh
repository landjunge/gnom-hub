#!/usr/bin/env bash
# scripts/install-pre-push-hook.sh — Symlink local_ci.sh into .git/hooks/pre-push.
#
# Runs once. After this, every `git push` first runs the local CI sequence.
# If anything fails, the push is blocked.
#
# Re-run safely (idempotent).

set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

HOOK=".git/hooks/pre-push"
SOURCE="$(pwd)/scripts/local_ci.sh"

if [[ ! -x "scripts/local_ci.sh" ]]; then
  chmod +x scripts/local_ci.sh
fi

# Backup existing hook if present
if [[ -e "$HOOK" && ! -L "$HOOK" ]]; then
  echo "→ Backing up existing $HOOK → ${HOOK}.bak-$(date +%s)"
  mv "$HOOK" "${HOOK}.bak-$(date +%s)"
fi

# Symlink
ln -sf "$SOURCE" "$HOOK"
chmod +x "$HOOK"

echo "✓ Installed pre-push hook → $SOURCE"
echo
echo "Test it (will run the same checks as GitHub CI):"
echo "  ./scripts/local_ci.sh"
echo
echo "From now on, every 'git push' will run local_ci.sh first."
echo "If anything fails, the push is blocked — exactly like GitHub CI would."
