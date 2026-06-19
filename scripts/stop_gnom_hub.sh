#!/bin/bash
# ── Gnom-Hub Stop ──
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# PID-File Cleanup
for pidfile in "$HOME"/.gnom-hub/run/*.pid "$HOME"/.gnom-hub-*/run/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile" 2>/dev/null)
    procname=$(basename "$pidfile" .pid)
    [ -n "$pid" ] && kill "$pid" 2>/dev/null && echo "  $procname gestoppt"
    rm -f "$pidfile"
done
sleep 1

# Verbleibende gnom_hub Prozesse
remaining=$(ps aux | grep -E "[g]nom_hub|[a]gents\.run_agent" | awk '{print $2}')
if [ -n "$remaining" ]; then
    kill $remaining 2>/dev/null && echo "  Verbleibende Prozesse gestoppt"
fi

echo "Gnom-Hub beendet."
