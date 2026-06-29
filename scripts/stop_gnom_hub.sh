#!/bin/bash
# ── Gnom-Hub Stop (Total Kill) ──
# Killt:
#   1. Hub-Mains (gnom_hub ohne agents.run_agent)
#   2. Alle Sub-Prozesse (agents.run_agent) — auch Waisen mit PPID=1
#   3. Prozesse auf bekannten Hub-Ports
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "🛑 Gnom-Hub Total-Stop..."

# 1. PID-File Cleanup
for pidfile in "$HOME"/.gnom-hub/run/*.pid "$HOME"/.gnom-hub-*/run/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile" 2>/dev/null)
    procname=$(basename "$pidfile" .pid)
    [ -n "$pid" ] && kill -TERM "$pid" 2>/dev/null && echo "  $procname gestoppt (PID $pid)"
    rm -f "$pidfile"
done
sleep 1

# 2. Hub-Mains (ohne agents.run_agent)
for pid in $(pgrep -f "gnom_hub" 2>/dev/null | grep -v "agents.run_agent" 2>/dev/null); do
    kill -TERM "$pid" 2>/dev/null && echo "  Hub-Main gestoppt (PID $pid)"
done

# 3. Agent-Subprozesse (auch Waisen)
for pid in $(pgrep -f "agents.run_agent" 2>/dev/null); do
    kill -TERM "$pid" 2>/dev/null && echo "  Agent gestoppt (PID $pid)"
done

sleep 3

# 4. Hard-Kill für Überlebende
remaining=$(pgrep -f "gnom_hub|agents.run_agent" 2>/dev/null)
if [ -n "$remaining" ]; then
    echo "  ⚠️  ${#remaining[@]} Prozess(e) überlebend — SIGKILL..."
    for pid in $remaining; do
        kill -KILL "$pid" 2>/dev/null
    done
fi

# 5. Port-Cleanup
for port in 3002 3003 3004 3005 3006 3012; do
    pid=$(lsof -nP -iTCP:$port -sTCP:LISTEN -t 2>/dev/null)
    if [ -n "$pid" ]; then
        kill -KILL "$pid" 2>/dev/null
        echo "  Port $port freigegeben (PID $pid)"
    fi
done

# 6. Sanity-Check
final=$(pgrep -f "gnom_hub|agents.run_agent" 2>/dev/null | wc -l | tr -d ' ')
echo "  Verbleibend: $final Prozess(e)"
echo "✓ Gnom-Hub gestoppt."
