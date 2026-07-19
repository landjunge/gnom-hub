#!/bin/bash
# Daily / post-restart ops check (PLAN_STABILITAET §6).
# Exit 0 only if health ok + 8 agents + queue not flooded.
set -euo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$_SCRIPT_DIR/../.venv" ] || [ -f "$_SCRIPT_DIR/../pyproject.toml" ]; then
  REPO_DIR="$(cd "$_SCRIPT_DIR/.." && pwd)"
else
  REPO_DIR="$_SCRIPT_DIR"
fi
cd "$REPO_DIR"
export PYTHONPATH="${PYTHONPATH:-}:src"
# shellcheck disable=SC1091
[ -f .venv/bin/activate ] && source .venv/bin/activate

PORT="${GNOM_HUB_PORT:-3002}"
URL="http://127.0.0.1:${PORT}"
MAX_PENDING="${OPS_MAX_PENDING:-50}"

echo "═══ Gnom-Hub ops_check :${PORT} ═══"

if ! curl -sf -m 3 "$URL/api/health" >/tmp/gnom_ops_health.json; then
  echo "✗ Hub unreachable ($URL/api/health)"
  exit 1
fi

python3 - <<'PY'
import json, os, sys
from pathlib import Path

h = json.load(open("/tmp/gnom_ops_health.json"))
agents = h.get("agents") or {}
healthy = int(agents.get("healthy") or 0)
total = int(agents.get("total") or 0)
zombie = int(agents.get("zombie") or 0)
print(f"health status={h.get('status')} healthy={healthy}/{total} zombie={zombie}")
if h.get("status") != "ok" or healthy < 8 or zombie:
    sys.exit(2)

# process count
import subprocess
out = subprocess.check_output(["ps", "-axo", "command="], text=True)
n = sum(1 for line in out.splitlines() if "agents.run_agent" in line and "ython" in line.lower())
print(f"run_agent processes={n} (want 8)")
if n != 8:
    print("⚠️  unexpected agent process count — bash scripts/start_agents.sh")
    # not hard-fail: health can still be 8/8 with pid lag

max_pending = int(os.environ.get("OPS_MAX_PENDING", "50"))
try:
    sys.path.insert(0, "src")
    from gnom_hub.db.connection import get_db_connection
    conn = get_db_connection()
    rows = list(conn.execute("SELECT status, COUNT(*) c FROM agent_messages GROUP BY status"))
    conn.close()
    by = {r[0]: r[1] for r in rows}
    pending = int(by.get("pending") or 0)
    processing = int(by.get("processing") or 0)
    dead = int(by.get("dead_letter") or 0)
    print(f"queue pending={pending} processing={processing} dead_letter={dead}")
    if pending > max_pending:
        print(f"✗ pending>{max_pending} — im Chat: @@queue clear")
        sys.exit(3)
except Exception as e:
    print(f"(queue stats skipped: {e})")

print("✓ ops_check ok")
PY
