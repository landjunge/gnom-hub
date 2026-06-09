#!/bin/bash
# GnomHub - Clean Architecture Version
echo "🚀 Starte GnomHub..."

# Virtuelle Umgebung aktivieren
source .venv/bin/activate
export PYTHONPATH=src

# Monitor starten (Hintergrund) - freed haengende Agenten nach 2 Min automatisch
pkill -f "scripts/gnom-monitor.py" 2>/dev/null
python3 scripts/gnom-monitor.py &
echo "✅ Monitor gestartet (PID $!)"

python3 -m gnom_hub
