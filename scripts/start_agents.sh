#!/bin/bash
echo "Starte alle Gnom-Hub Agenten..."
source .venv/bin/activate
export PYTHONPATH=src
set -a
[ -f config/.env ] && source config/.env
set +a

# Alte Agenten killen falls sie noch laufen
pkill -f "[pP]ython.*agents\..*AG"
pkill -f "[pP]ython.*AG\.py"
sleep 1

# Start in background with -u for unbuffered output
python3 -u -m agents.run_agent --name generalag > logs/logs_general.txt 2>&1 &
python3 -u -m agents.run_agent --name soulag > logs/logs_soul.txt 2>&1 &
python3 -u -m agents.run_agent --name securityag > logs/logs_security.txt 2>&1 &
python3 -u -m agents.run_agent --name watchdogag > logs/logs_watchdog.txt 2>&1 &
python3 -u -m agents.run_agent --name researcherag > logs/logs_researcher.txt 2>&1 &
python3 -u -m agents.run_agent --name writerag > logs/logs_writer.txt 2>&1 &
python3 -u -m agents.run_agent --name editorag > logs/logs_editor.txt 2>&1 &
python3 -u -m agents.run_agent --name coderag > logs/logs_coder.txt 2>&1 &

echo "✅ Die 8 Hintergrund-Agenten wurden gestartet."

