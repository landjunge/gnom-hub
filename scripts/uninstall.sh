#!/bin/bash
# ═══════════════════════════════════════════
#  GNOM-HUB — Deinstallation
# ═══════════════════════════════════════════
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$HOME/.gnom-hub"

echo ""
echo "  ╔═══════════════════════════════════╗"
echo "  ║   GNOM-HUB DEINSTALLATION         ║"
echo "  ╚═══════════════════════════════════╝"
echo ""

# Sicherheitsabfrage
echo "  Das wird entfernt:"
echo "    • Alle laufenden Gnom-Hub Prozesse"
echo "    • Virtuelle Umgebung (.venv/)"
echo "    • Log-Dateien (logs_*.txt)"
echo "    • Python-Cache (__pycache__/)"
echo ""
if [ -d "$DATA_DIR" ]; then
    AGENT_COUNT=$(python3 -c "import json; print(len(json.load(open('$DATA_DIR/data/agents.json'))))" 2>/dev/null || echo "?")
    MEM_SIZE=$(du -sh "$DATA_DIR/data/memory.json" 2>/dev/null | cut -f1 || echo "?")
    echo "  ⚠️  Daten in $DATA_DIR:"
    echo "    • $AGENT_COUNT Agenten"
    echo "    • Memory: $MEM_SIZE"
    echo ""
fi

read -p "  Daten behalten? [J/n]: " KEEP_DATA
read -p "  Wirklich deinstallieren? [j/N]: " CONFIRM

if [[ "$CONFIRM" != "j" && "$CONFIRM" != "J" && "$CONFIRM" != "ja" ]]; then
    echo "  Abgebrochen."
    exit 0
fi

# 1. Prozesse killen
echo ""
echo "▸ Prozesse stoppen..."
for pidfile in "$HOME"/.gnom-hub/run/*.pid "$HOME"/.gnom-hub-*/run/*.pid; do
  [ -f "$pidfile" ] || continue
  pid=$(cat "$pidfile" 2>/dev/null)
  [ -n "$pid" ] && kill "$pid" 2>/dev/null
  rm -f "$pidfile"
done
# Fallback: verbleibende Prozesse
ps aux | grep -i "[g]nom_hub\|[a]gents\." | awk '{print $2}' | xargs kill 2>/dev/null
echo "  Hub gestoppt ✓"
sleep 1

# 2. Ports freigeben
echo "▸ Ports freigeben..."
for port in 3002 3100; do
    lsof -ti:$port 2>/dev/null | xargs kill 2>/dev/null && echo "  Port $port freigegeben ✓" || echo "  Port $port frei ✓"
done

# 3. Virtuelle Umgebung löschen
echo "▸ Virtuelle Umgebung..."
if [ -d "$REPO_DIR/.venv" ]; then
    rm -rf "$REPO_DIR/.venv"
    echo "  .venv gelöscht ✓"
else
    echo "  Keine .venv ✓"
fi

# 4. Log-Dateien löschen
echo "▸ Logs bereinigen..."
rm -f "$REPO_DIR"/logs_*.txt 2>/dev/null
echo "  Log-Dateien gelöscht ✓"

# 5. Python Cache löschen
echo "▸ Cache bereinigen..."
find "$REPO_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find "$REPO_DIR" -name "*.pyc" -delete 2>/dev/null
rm -rf "$REPO_DIR"/*.egg-info 2>/dev/null
rm -rf "$REPO_DIR"/src/*.egg-info 2>/dev/null
echo "  Cache gelöscht ✓"

# 6. Daten
if [[ "$KEEP_DATA" == "n" || "$KEEP_DATA" == "N" || "$KEEP_DATA" == "nein" ]]; then
    echo "▸ Daten löschen..."
    rm -rf "$DATA_DIR"
    echo "  $DATA_DIR gelöscht ✓"
else
    echo "▸ Daten behalten ✓"
    echo "  Speicherort: $DATA_DIR"
fi

# 7. Sandbox aufräumen
rm -f "$REPO_DIR/sandbox.py" 2>/dev/null

echo ""
echo " ═══════════════════════════════════════════"
echo "  ✅ Deinstallation abgeschlossen!"
echo " ═══════════════════════════════════════════"
echo ""
if [[ "$KEEP_DATA" != "n" && "$KEEP_DATA" != "N" && "$KEEP_DATA" != "nein" ]]; then
    echo "  Daten gesichert in: $DATA_DIR"
    echo "  Neuinstallation:    bash scripts/install.sh"
else
    echo "  Alles entfernt. Neuinstallation: bash scripts/install.sh"
fi
echo ""
