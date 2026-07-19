#!/usr/bin/env bash
# Build gradual TypeScript frontend → src/gnom_hub/frontend/gnom-ts.js
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TS_DIR="$ROOT/src/gnom_hub/frontend/ts"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found — cannot build frontend TS" >&2
  exit 1
fi

cd "$TS_DIR"
if [[ ! -d node_modules ]]; then
  npm install
fi
npm run typecheck
npm run build
npm test
echo "✓ gnom-ts.js ready at src/gnom_hub/frontend/gnom-ts.js"
