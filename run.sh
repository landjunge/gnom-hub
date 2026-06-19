#!/bin/bash
# GnomHub - Clean Architecture Version
echo "🚀 Starte GnomHub..."

# Virtuelle Umgebung aktivieren
source .venv/bin/activate
export PYTHONPATH=src

# Monitor starten (nach Hub-Start)
MONITOR_PIDFILE="$HOME/.gnom-hub/run/gnom-monitor.pid"
if [ -f "$MONITOR_PIDFILE" ]; then
  old_pid=$(cat "$MONITOR_PIDFILE" 2>/dev/null)
  [ -n "$old_pid" ] && kill "$old_pid" 2>/dev/null
  rm -f "$MONITOR_PIDFILE"
fi
sleep 3
python3 scripts/gnom-monitor.py &
echo $! > "$MONITOR_PIDFILE"
echo "✅ Monitor gestartet (PID $!)"

python3 -m gnom_hub
