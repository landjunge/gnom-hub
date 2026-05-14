#!/bin/bash
echo "Starte alle Gnom-Hub Agenten..."
source .venv/bin/activate

# Alte Agenten killen falls sie noch laufen
pkill -f "AG.py"
sleep 1

# Start in background
python3 testAG1.py > logs_test1.txt 2>&1 &
python3 testAG2.py > logs_test2.txt 2>&1 &
python3 testAG3.py > logs_test3.txt 2>&1 &
python3 backupAG.py > logs_backup.txt 2>&1 &
python3 summarizerAG.py > logs_summarizer.txt 2>&1 &
python3 generalAG.py > logs_general.txt 2>&1 &
python3 cronjobAG.py > logs_cronjob.txt 2>&1 &
python3 skillsAG.py > logs_skills.txt 2>&1 &
python3 soulAG.py > logs_soul.txt 2>&1 &
python3 tinyAG.py > logs_tiny.txt 2>&1 &
python3 watchdogAG.py > logs_watchdog.txt 2>&1 &

echo "✅ Alle Agenten (inkl. Soul, Skills, Cronjob, Tiny, Watchdog) gestartet."
