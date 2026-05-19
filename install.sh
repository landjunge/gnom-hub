#!/bin/bash
# ═══════════════════════════════════════════
#  GNOM-HUB — Installation
# ═══════════════════════════════════════════
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$HOME/.gnom-hub/data"
LOG_DIR="$HOME/.gnom-hub/logs"
VENV_DIR="$REPO_DIR/.venv"

G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; R='\033[0;31m'; B='\033[1m'; N='\033[0m'

echo ""
echo "  ██████╗  ███╗   ██╗ ██████╗ ███╗   ███╗"
echo " ██╔════╝  ████╗  ██║██╔═══██╗████╗ ████║"
echo " ██║  ███╗ ██╔██╗ ██║██║   ██║██╔████╔██║"
echo " ██║   ██║ ██║╚██╗██║██║   ██║██║╚██╔╝██║"
echo " ╚██████╔╝ ██║ ╚████║╚██████╔╝██║ ╚═╝ ██║"
echo "  ╚═════╝  ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝"
echo "              INSTALLER"
echo " ─────────────────────────────"
echo ""

# ── 1. Python prüfen ──
echo -e "${B}▸ Python prüfen...${N}"
if ! command -v python3 &>/dev/null; then
    echo -e "${R}✗ Python 3 nicht gefunden. Bitte installieren: brew install python3${N}"
    exit 1
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  Python $PY_VER ${G}✓${N}"

# ── 2. Virtuelle Umgebung ──
echo -e "${B}▸ Virtuelle Umgebung...${N}"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo -e "  .venv erstellt ${G}✓${N}"
else
    echo -e "  .venv existiert ${G}✓${N}"
fi
source "$VENV_DIR/bin/activate"

# ── 3. Core installieren ──
echo -e "${B}▸ Core-Dependencies installieren...${N}"
pip install -q fastapi uvicorn pydantic requests python-dotenv
pip install -q -e "$REPO_DIR"
echo -e "  Core installiert ${G}✓${N}"

# ══════════════════════════════════════
#  TOOL-AUSWAHL — Was soll der Gnom können?
# ══════════════════════════════════════
echo ""
echo -e "${Y}═══════════════════════════════════════════${N}"
echo -e "${B}  🔧 TOOL-AUSWAHL — Was soll der Gnom können?${N}"
echo -e "${Y}═══════════════════════════════════════════${N}"
echo ""
echo -e "Wähle aus, welche Fähigkeiten du installieren willst."
echo -e "Jedes Tool wird erklärt — du entscheidest."
echo ""

# ── Tool 1: Browser-Automation ──
echo -e "${C}┌─────────────────────────────────────────────┐${N}"
echo -e "${C}│${N} ${B}🌐 BROWSER-AUTOMATION (Playwright)${N}"
echo -e "${C}│${N}"
echo -e "${C}│${N}  Gibt dem Gnom einen echten Chromium-Browser."
echo -e "${C}│${N}  Er kann Webseiten öffnen, Formulare ausfüllen,"
echo -e "${C}│${N}  Buttons klicken, Daten extrahieren und"
echo -e "${C}│${N}  Screenshots von Webseiten machen."
echo -e "${C}│${N}"
echo -e "${C}│${N}  ${Y}Command:${N} @browser öffne google.com"
echo -e "${C}│${N}  ${Y}Braucht:${N} ~150 MB (Chromium-Download)"
echo -e "${C}└─────────────────────────────────────────────┘${N}"
read -p "  Installieren? [j/N] " BROWSER
if [[ "$BROWSER" =~ ^[jJyY]$ ]]; then
    pip install -q playwright
    playwright install chromium
    echo -e "  Browser-Automation ${G}✓${N}"
else
    echo -e "  Browser-Automation ${R}übersprungen${N}"
fi
echo ""

# ── Tool 2: Desktop-Steuerung ──
echo -e "${C}┌─────────────────────────────────────────────┐${N}"
echo -e "${C}│${N} ${B}🖥️  DESKTOP-STEUERUNG (PyAutoGUI)${N}"
echo -e "${C}│${N}"
echo -e "${C}│${N}  Der Gnom sieht deinen Bildschirm und kann"
echo -e "${C}│${N}  Maus und Tastatur steuern. Perfekt für"
echo -e "${C}│${N}  automatisierte Desktop-Workflows."
echo -e "${C}│${N}"
echo -e "${C}│${N}  ${Y}Commands:${N} @desktop, @vision"
echo -e "${C}│${N}  ${Y}Braucht:${N} ~5 MB + Accessibility-Rechte (macOS)"
echo -e "${C}└─────────────────────────────────────────────┘${N}"
read -p "  Installieren? [j/N] " DESKTOP
if [[ "$DESKTOP" =~ ^[jJyY]$ ]]; then
    pip install -q pyautogui Pillow
    echo -e "  Desktop-Steuerung ${G}✓${N}"
    echo -e "  ${Y}⚠ macOS: Accessibility-Rechte für Terminal/IDE aktivieren!${N}"
else
    echo -e "  Desktop-Steuerung ${R}übersprungen${N}"
fi
echo ""

# ── Tool 3: Sprache ──
echo -e "${C}┌─────────────────────────────────────────────┐${N}"
echo -e "${C}│${N} ${B}🎤 SPRACHE (Whisper + TTS)${N}"
echo -e "${C}│${N}"
echo -e "${C}│${N}  Spracherkennung (Whisper) und Text-to-Speech."
echo -e "${C}│${N}  Der Gnom kann dir zuhören und antworten."
echo -e "${C}│${N}"
echo -e "${C}│${N}  ${Y}Braucht:${N} ~500 MB (Whisper-Modell beim ersten Start)"
echo -e "${C}└─────────────────────────────────────────────┘${N}"
read -p "  Installieren? [j/N] " SPEECH
if [[ "$SPEECH" =~ ^[jJyY]$ ]]; then
    pip install -q faster-whisper pyttsx3
    echo -e "  Sprache ${G}✓${N}"
else
    echo -e "  Sprache ${R}übersprungen${N}"
fi
echo ""

# ── Tool 4: Selenium ──
echo -e "${C}┌─────────────────────────────────────────────┐${N}"
echo -e "${C}│${N} ${B}🕷️  SELENIUM (Alternative Browser-Engine)${N}"
echo -e "${C}│${N}"
echo -e "${C}│${N}  Alternative zu Playwright. Ältere, aber"
echo -e "${C}│${N}  robustere Browser-Automation. Nutzt deinen"
echo -e "${C}│${N}  installierten Chrome/Firefox."
echo -e "${C}│${N}"
echo -e "${C}│${N}  ${Y}Braucht:${N} ~2 MB + Chrome oder Firefox"
echo -e "${C}└─────────────────────────────────────────────┘${N}"
read -p "  Installieren? [j/N] " SELENIUM
if [[ "$SELENIUM" =~ ^[jJyY]$ ]]; then
    pip install -q selenium
    echo -e "  Selenium ${G}✓${N}"
else
    echo -e "  Selenium ${R}übersprungen${N}"
fi
echo ""

# ══════════════════════════════════════
#  SYSTEM-SETUP
# ══════════════════════════════════════

# ── 4. Datenverzeichnisse ──
echo -e "${B}▸ Datenverzeichnisse...${N}"
mkdir -p "$DATA_DIR" "$LOG_DIR" "$HOME/.gnom-hub/run"
echo -e "  $DATA_DIR ${G}✓${N}"

# ── 5. .env prüfen ──
if [ ! -f "$REPO_DIR/.env" ]; then
    echo -e "${B}▸ .env erstellen...${N}"
    cat > "$REPO_DIR/.env" <<'EOF'
# Gnom-Hub Konfiguration
# Mindestens einen Key setzen:

# OpenRouter (kostenlose Modelle)
# OPENROUTER_KEY_FREE_1=sk-or-...

# DeepSeek (bezahlter Fallback)
# DEEPSEEK_API_KEY=sk-...

# Hub-Port (Standard: 3002)
# GNOM_HUB_PORT=3002
EOF
    echo -e "  .env Template erstellt — ${Y}Keys eintragen!${N} ${G}✓${N}"
else
    echo -e "  .env existiert ${G}✓${N}"
fi

# ── 6. Datenbanken ──
echo -e "${B}▸ Datenbanken prüfen...${N}"
for db in memory chat jobs ideas tokens tools domains; do
    if [ ! -f "$DATA_DIR/$db.json" ]; then
        echo "[]" > "$DATA_DIR/$db.json"
    fi
done
echo -e "  Datenbanken ${G}✓${N}"

# ── 7. LLM-Provider ──
echo ""
echo -e "${Y}═══════════════════════════════════════════${N}"
echo -e "${B}  🧠 LLM-PROVIDER — Woher kommt die Intelligenz?${N}"
echo -e "${Y}═══════════════════════════════════════════${N}"
echo ""
echo -e "  Der Gnom braucht mindestens einen LLM-Provider."
echo -e "  Trag die Keys in ${B}.env${N} ein:"
echo ""
echo -e "  ${C}1)${N} ${B}DeepSeek${N}      — Schnell, günstig (~\$0.14/1M Tokens)"
echo -e "                     DEEPSEEK_API_KEY=sk-..."
echo ""
echo -e "  ${C}2)${N} ${B}OpenRouter${N}    — Kostenlose Modelle verfügbar"
echo -e "                     OPENROUTER_KEY_FREE_1=sk-or-..."
echo ""
echo -e "  ${C}3)${N} ${B}Ollama (lokal)${N} — Kostenlos, braucht GPU"
echo -e "                     brew install ollama && ollama pull deepseek-r1"
echo ""

# ── Zusammenfassung ──
echo ""
echo -e "${G}═══════════════════════════════════════════${N}"
echo -e "${B}  ✅ Installation abgeschlossen!${N}"
echo -e "${G}═══════════════════════════════════════════${N}"
echo ""
echo -e "  Installiert:"
echo -e "    ${G}✓${N} Core (FastAPI, Uvicorn, Pydantic)"
[[ "$BROWSER" =~ ^[jJyY]$ ]]  && echo -e "    ${G}✓${N} Browser-Automation (Playwright)"
[[ "$DESKTOP" =~ ^[jJyY]$ ]]  && echo -e "    ${G}✓${N} Desktop-Steuerung (PyAutoGUI)"
[[ "$SPEECH" =~ ^[jJyY]$ ]]   && echo -e "    ${G}✓${N} Sprache (Whisper + TTS)"
[[ "$SELENIUM" =~ ^[jJyY]$ ]] && echo -e "    ${G}✓${N} Selenium"
echo ""
echo -e "  ${Y}Nicht vergessen:${N}"
echo -e "    → LLM-Keys in ${B}.env${N} eintragen"
echo ""
echo -e "  ${B}Frontend:${N}   http://127.0.0.1:3002"
echo -e "  ${B}Agenten:${N}    bash start_agents.sh"
echo ""

# ── 8. Hub starten ──
echo -e "${B}▸ Gnom-Hub starten...${N}"
source "$VENV_DIR/bin/activate"
python -m gnom_hub
