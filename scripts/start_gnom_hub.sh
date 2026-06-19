#!/bin/bash
# ── Gnom-Hub Start (cross-platform bash variant; Windows uses scripts/start.ps1) ──
# Aktiviert venv, exportiert env aus config/.env, killt alte Instanzen, startet den
# Hub im Hintergrund und öffnet den Browser.
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
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
