#!/bin/bash
# GnomHub - Clean Architecture Version

echo "🚀 Starte GnomHub..."

# Virtuelle Umgebung aktivieren (falls du eine nutzt)
source .venv/bin/activate

export PYTHONPATH=src
python3 -m gnom_hub
