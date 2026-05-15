#!/bin/bash
echo "Starte alle Gnom-Hub Agenten..."
source .venv/bin/activate
set -a
[ -f .env ] && source .env
set +a

# Alte Agenten killen falls sie noch laufen
pkill -f "python3.*AG.py"
sleep 1

# Start in background
python3 kira.py > logs_kira.txt 2>&1 &
python3 lian.py > logs_lian.txt 2>&1 &
python3 elara.py > logs_elara.txt 2>&1 &
python3 backupAG.py > logs_backup.txt 2>&1 &
python3 generalAG.py > logs_general.txt 2>&1 &

echo "✅ Das reine Trio (Kira, Lian, Elara) plus General & Backup gestartet. Kein Bloat mehr."
