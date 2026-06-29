#!/bin/bash
# ── Gnom-Hub Start (cross-platform bash variant; Windows uses scripts/start.ps1) ──
# Aktiviert venv, exportiert env aus config/.env, killt alte Instanzen, startet den
# Hub im Hintergrund und öffnet den Browser.
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

if [ ! -d ".venv" ]; then
    echo "✗ .venv fehlt — bitte zuerst python3 install.py ausführen." >&2
    exit 1
fi

source .venv/bin/activate
set -a
[ -f config/.env ] && . config/.env
set +a

mkdir -p logs

# ── Alte Prozesse beenden ──
for pidfile in "$HOME"/.gnom-hub/run/*.pid "$HOME"/.gnom-hub-*/run/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile" 2>/dev/null)
    [ -n "$pid" ] && kill "$pid" 2>/dev/null && true
    rm -f "$pidfile"
done
sleep 1

# ── TOTAL KILL: alle laufenden Hub-Prozesse + Waisen (PPID=1) killen ──
# Sonst sammeln sich über Tage Waisen-Prozesse an, weil Sub-Prozesse
# nach Hub-Tod von init/launchd adoptiert werden.
echo "🧹 Total-Kill: alle Hub-Mains + Agent-Subprozesse..."
# Hub-Mains (gnom_hub ohne agents.run_agent)
for pid in $(pgrep -f "gnom_hub" 2>/dev/null | grep -v "agents.run_agent" 2>/dev/null); do
    kill -TERM "$pid" 2>/dev/null
done
# Sub-Prozesse (agents.run_agent) — auch Waisen
for pid in $(pgrep -f "agents.run_agent" 2>/dev/null); do
    kill -TERM "$pid" 2>/dev/null
done
# Kurz warten, dann Hard-Kill für Überlebende
sleep 3
for pid in $(pgrep -f "gnom_hub" 2>/dev/null); do
    kill -KILL "$pid" 2>/dev/null
done
for pid in $(pgrep -f "agents.run_agent" 2>/dev/null); do
    kill -KILL "$pid" 2>/dev/null
done
# Auch alle Prozesse die noch auf Hub-Ports lauschen
for port in 3002 3003 3004 3005 3006 3012; do
    pid=$(lsof -nP -iTCP:$port -sTCP:LISTEN -t 2>/dev/null)
    [ -n "$pid" ] && kill -KILL "$pid" 2>/dev/null
done
sleep 1
remaining=$(pgrep -f "gnom_hub\|agents.run_agent" 2>/dev/null | wc -l | tr -d ' ')
echo "   Verbleibend nach Kill: $remaining Prozess(e)"

# OMP / BLAS thread limits — verhindert FAISS-Init-Crash auf macOS
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export KMP_DUPLICATE_LIB_OK=TRUE

# Hub starten
python3 -u -m gnom_hub > logs/logs_hub.txt 2>&1 &
sleep 4

# Browser öffnen
URL="http://127.0.0.1:${GNOM_HUB_PORT:-3002}"
if command -v open >/dev/null 2>&1; then
    open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL"
fi

echo "🚀 Gnom-Hub läuft auf $URL"
echo "   Stop: ./stop_gnom_hub.sh"
