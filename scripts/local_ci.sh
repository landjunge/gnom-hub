#!/usr/bin/env bash
# scripts/local_ci.sh — Run the exact CI sequence locally before pushing.
#
# Use this when:
#   - You don't want 8 failed CI runs to debug the same thing remotely.
#   - You want a green CI badge on the first push.
#
# Exit codes:
#   0  — all checks pass, safe to git push
#   1  — lint failed (ruff)
#   2  — tests failed
#   3  — env setup failed
#
# Install as a pre-push hook:
#   ./scripts/install-pre-push-hook.sh
#
# Or run manually:
#   ./scripts/local_ci.sh

set -uo pipefail

# Resolve symlinks: if invoked via .git/hooks/pre-push → scripts/local_ci.sh,
# we want the real script's directory, not .git/hooks/.
SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$0")"
cd "$(dirname "$SCRIPT_PATH")/.." || exit 3

VENV=".venv"
PY="${VENV}/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "✗ ${PY} not found. Run: python3 install.py"
  exit 3
fi

echo "═══ local_ci.sh — same sequence as .github/workflows/ci.yml ═══"
echo

# ── Step 1: Ruff Lint (was the silent killer in 8 of my pushes) ────────────
echo "[1/2] ruff check src/ tests/"
RUFF=""
if "$PY" -m ruff --version >/dev/null 2>&1; then
  RUFF=("$PY" -m ruff)
elif command -v ruff >/dev/null 2>&1; then
  RUFF=(ruff)
else
  echo "✗ ruff not found. Install via: pip install 'ruff>=0.6.0'"
  exit 3
fi
if ! "${RUFF[@]}" check src/ tests/; then
  echo
  echo "✗ ruff failed. Fix the issues above or run: ruff check --fix"
  exit 1
fi
echo "✓ ruff clean"
echo

# ── Step 2: Pytest with the exact same --ignore list as CI ────────────────
echo "[2/2] pytest tests/ (with CI --ignore list)"
if ! "$PY" -m pytest tests/ -q \
    --ignore=tests/test_stress_50.py \
    --ignore=tests/test_faiss_lock.py \
    --ignore=tests/test_browser_action.py \
    --ignore=tests/test_browser_chat_mouse.py \
    --ignore=tests/test_browser_full.py \
    --ignore=tests/test_browser_workflows.py \
    --ignore=tests/test_llm_page_browser.py \
    --ignore=tests/integration/test_prompt_pipeline_golden.py \
    --ignore=tests/test_agent_names_frozen.py \
    --ignore=tests/test_default_preset_content.py \
    --ignore=tests/test_gnom_hub.py \
    --ignore=tests/test_migrations.py \
    --ignore=tests/test_openrouter.py \
    --ignore=tests/test_workspace_config.py \
    --ignore=tests/test_golden_landing_page.py \
    --ignore=tests/test_golden_demo_video.py 2>&1; then
  echo
  echo "✗ tests failed. See output above."
  exit 2
fi
echo
echo "═══ local_ci.sh — all green, safe to git push ═══"
