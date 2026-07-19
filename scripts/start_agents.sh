#!/bin/bash
# Start exactly 8 agents via agents.run_agent (single launch style — PLAN S4.2).
# Kills prior agent processes first so repeated starts never leave duplicate PIDs.
set -euo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$_SCRIPT_DIR/../.venv" ] || [ -f "$_SCRIPT_DIR/../pyproject.toml" ]; then
  REPO_DIR="$(cd "$_SCRIPT_DIR/.." && pwd)"
else
  REPO_DIR="$_SCRIPT_DIR"
fi
cd "$REPO_DIR"

echo "Starte alle Gnom-Hub Agenten (nur agents.run_agent)..."
# shellcheck disable=SC1091
source .venv/bin/activate
export PYTHONPATH=src
set -a
[ -f config/.env ] && . config/.env
set +a

# Stability defaults (do not override user if already set)
export GNOM_QUEUE_MODE="${GNOM_QUEUE_MODE:-hub}"
export SOUL_AUTO_DISPATCH="${SOUL_AUTO_DISPATCH:-0}"

RUN_DIR="${HOME}/.gnom-hub/run"
mkdir -p "$RUN_DIR" logs

_kill_agents() {
  # PID files first
  for pidfile in "$HOME"/.gnom-hub/run/*.pid "$HOME"/.gnom-hub-*/run/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile" 2>/dev/null || true)
    [ -n "${pid:-}" ] && kill -TERM "$pid" 2>/dev/null || true
    rm -f "$pidfile"
  done
  # Kill real Python agent processes only (never pkill -f self-matching shells)
  set +e
  ps -axo pid=,command= | awk '
    /agents\.run_agent/ && /[Pp]ython/ && !/awk/ { print $1 }
    /agents\.[a-zA-Z]+AG/ && /[Pp]ython/ && !/run_agent/ && !/awk/ { print $1 }
  ' | while read -r pid; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  sleep 1
  ps -axo pid=,command= | awk '
    /agents\.run_agent/ && /[Pp]ython/ && !/awk/ { print $1 }
    /agents\.[a-zA-Z]+AG/ && /[Pp]ython/ && !/run_agent/ && !/awk/ { print $1 }
  ' | while read -r pid; do
    kill -KILL "$pid" 2>/dev/null || true
  done
  set -e
  sleep 1
}

_kill_agents

AGENTS=(generalag soulag securityag watchdogag researcherag writerag editorag coderag)
for name in "${AGENTS[@]}"; do
  log="logs/logs_${name}.txt"
  # shellcheck disable=SC2086
  python3 -u -m agents.run_agent --name "$name" >"$log" 2>&1 &
  pid=$!
  echo "$pid" >"$RUN_DIR/${name}.pid"
  echo "  · $name pid=$pid"
done

# Verify process count (Python only)
sleep 1
count=$(ps -axo command= | awk '/agents\.run_agent/ && /[Pp]ython/ && !/awk/ {c++} END{print c+0}')
legacy=$(ps -axo command= | awk '/agents\.[a-zA-Z]+AG/ && /[Pp]ython/ && !/run_agent/ && !/awk/ {c++} END{print c+0}')

echo "✅ Agenten gestartet: run_agent-Prozesse=${count} (Soll 8), Legacy-Stile=${legacy} (Soll 0)"
echo "   GNOM_QUEUE_MODE=${GNOM_QUEUE_MODE} SOUL_AUTO_DISPATCH=${SOUL_AUTO_DISPATCH}"
if [ "$count" -ne 8 ]; then
  echo "⚠️  Erwartet 8 Agenten, habe ${count} — Logs unter logs/logs_*.txt prüfen." >&2
fi
if [ "$legacy" -gt 0 ]; then
  echo "⚠️  Legacy agents.*AG noch aktiv — erneut scripts/start_agents.sh ausführen." >&2
fi
