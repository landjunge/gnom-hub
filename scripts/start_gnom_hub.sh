#!/bin/bash
# ── Gnom-Hub Start (cross-platform bash variant; Windows uses scripts/start.ps1) ──
# Aktiviert venv, exportiert env aus config/.env, killt alte Instanzen, startet den
# Hub im Hintergrund und öffnet den Browser.
#
# WICHTIG: pgrep/kill dürfen set -e nicht abbrechen (leeres pgrep = exit 1).
set -euo pipefail

# Repo-Root: dieses Script lebt in scripts/ (oder als Symlink im Root)
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$_SCRIPT_DIR/../.venv" ] || [ -f "$_SCRIPT_DIR/../pyproject.toml" ]; then
    REPO_DIR="$(cd "$_SCRIPT_DIR/.." && pwd)"
elif [ -d "$_SCRIPT_DIR/.venv" ] || [ -f "$_SCRIPT_DIR/pyproject.toml" ]; then
    REPO_DIR="$_SCRIPT_DIR"
else
    REPO_DIR="$_SCRIPT_DIR"
fi
cd "$REPO_DIR"

if [ ! -d ".venv" ]; then
    echo "✗ .venv fehlt — bitte zuerst python3 install.py ausführen." >&2
    exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate
set -a
[ -f config/.env ] && . config/.env
set +a

# Sticky-Showbox darf Agent-Deliveries nicht blocken (Test/Default)
export GNOM_HUB_DISABLE_STICKY="${GNOM_HUB_DISABLE_STICKY:-1}"

mkdir -p logs "$HOME/.gnom-hub/run"

# ── Alte Prozesse beenden (set +e: leere pgrep/kill sind OK) ──
set +e
for pidfile in "$HOME"/.gnom-hub/run/*.pid "$HOME"/.gnom-hub-*/run/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile" 2>/dev/null)
    [ -n "$pid" ] && kill "$pid" 2>/dev/null
    rm -f "$pidfile"
done
sleep 1

echo "🧹 Total-Kill: alle Hub-Mains + Agent-Subprozesse..."
# Nur python -m gnom_hub / agents.run_agent — nicht den Start-Wrapper selbst
for pid in $(pgrep -f "python.*-m gnom_hub" 2>/dev/null); do
    kill -TERM "$pid" 2>/dev/null
done
for pid in $(pgrep -f "agents.run_agent|agents\.[a-zA-Z]+AG" 2>/dev/null); do
    kill -TERM "$pid" 2>/dev/null
done
sleep 2
for pid in $(pgrep -f "python.*-m gnom_hub" 2>/dev/null); do
    kill -KILL "$pid" 2>/dev/null
done
for pid in $(pgrep -f "agents.run_agent|agents\.[a-zA-Z]+AG" 2>/dev/null); do
    kill -KILL "$pid" 2>/dev/null
done
for port in 3002 3003 3004 3005 3006 3012; do
    for pid in $(lsof -nP -iTCP:$port -sTCP:LISTEN -t 2>/dev/null); do
        kill -KILL "$pid" 2>/dev/null
    done
done
sleep 1
remaining=$(pgrep -f "python.*-m gnom_hub|agents.run_agent" 2>/dev/null | wc -l | tr -d ' ')
remaining=${remaining:-0}
echo "   Verbleibend nach Kill: $remaining Prozess(e)"
set -e

# OMP / BLAS thread limits — verhindert FAISS-Init-Crash auf macOS
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export KMP_DUPLICATE_LIB_OK=TRUE

# Hub starten
# nohup + disown: schützt vor SIGHUP beim Parent-Shell-Exit
nohup python3 -u -m gnom_hub > logs/logs_hub.txt 2>&1 &
HUB_PID=$!
disown

URL="http://127.0.0.1:${GNOM_HUB_PORT:-3002}"
# Warte bis Health antwortet (max ~20s)
ok=0
for _i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 2
    if curl -sf -m 2 "$URL/api/health" >/dev/null 2>&1; then
        ok=1
        break
    fi
done

if [ "$ok" != "1" ]; then
    echo "✗ Hub startete nicht auf $URL — siehe logs/logs_hub.txt" >&2
    tail -30 logs/logs_hub.txt >&2 || true
    exit 1
fi

# Browser öffnen
if command -v open >/dev/null 2>&1; then
    open "$URL" 2>/dev/null || true
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" 2>/dev/null || true
fi

# 8 Agents — single launch style (PLAN S4.2); kills duplicates first
if [ -x "$REPO_DIR/scripts/start_agents.sh" ]; then
    bash "$REPO_DIR/scripts/start_agents.sh" || true
elif [ -f "$REPO_DIR/scripts/start_agents.sh" ]; then
    bash "$REPO_DIR/scripts/start_agents.sh" || true
fi

echo "🚀 Gnom-Hub läuft auf $URL (PID $HUB_PID)"
echo "   Agents: bash scripts/start_agents.sh (wird beim Start bereits aufgerufen)"
echo "   Stop: ./stop_gnom_hub.sh"
