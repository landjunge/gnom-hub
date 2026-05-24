#!/bin/bash
# ═══════════════════════════════════════════
#  GNOM-HUB — Installation & App Builder
# ═══════════════════════════════════════════
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$REPO_DIR/.venv"
ICON_PNG="$REPO_DIR/frontend/assets/logo.png"
APP_DIR="/Applications/Gnom-Hub.app"

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
    echo -e "${R}✗ Python 3 nicht gefunden. brew install python3${N}"; exit 1
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
pip install -q fastapi uvicorn pydantic requests python-dotenv mcp
pip install -q -e "$REPO_DIR"
echo -e "  6 Packages installiert ${G}✓${N}"

# ── 4. Verzeichnisse & Datenbanken ──
echo -e "${B}▸ Datenverzeichnisse...${N}"
mkdir -p "$REPO_DIR/logs" "$REPO_DIR/gnom_workspace/default"
echo -e "  Verzeichnisse ${G}✓${N}"

# ── 5. .env prüfen ──
if [ ! -f "$REPO_DIR/config/.env" ]; then
    echo -e "${B}▸ config/.env erstellen...${N}"
    cat > "$REPO_DIR/config/.env" <<'EOF'
# ── Gnom-Hub Konfiguration ──
# Mindestens einen Key setzen:

# DeepSeek (günstig, schnell)
# DEEPSEEK_API_KEY=sk-...

# OpenRouter (kostenlose Modelle)
# OPENROUTER_KEY_FREE_1=sk-or-...

# FTP Deploy (optional)
# FTP_HOST=...
# FTP_USER=...
# FTP_PASS=...
# FTP_REMOTE_DIR=...
EOF
    echo -e "  config/.env Template erstellt — ${Y}Keys eintragen!${N} ${G}✓${N}"
else
    echo -e "  config/.env existiert ${G}✓${N}"
fi

# ── 6. macOS App Bundle bauen ──
echo ""
echo -e "${B}▸ Gnom-Hub.app bauen...${N}"

mkdir -p "${APP_DIR}/Contents/MacOS" "${APP_DIR}/Contents/Resources"

# Icon (logo.png ist JPEG-Format, iconutil braucht echtes PNG)
if [ -f "$ICON_PNG" ]; then
    ICONSET="/tmp/GnomIcon.iconset"
    REAL_PNG="/tmp/gnom_icon.png"
    sips -s format png "$ICON_PNG" --out "$REAL_PNG" > /dev/null 2>&1
    rm -rf "$ICONSET" && mkdir -p "$ICONSET"
    sips -z 16 16     "$REAL_PNG" --out "${ICONSET}/icon_16x16.png"      > /dev/null 2>&1
    sips -z 32 32     "$REAL_PNG" --out "${ICONSET}/icon_16x16@2x.png"   > /dev/null 2>&1
    sips -z 32 32     "$REAL_PNG" --out "${ICONSET}/icon_32x32.png"      > /dev/null 2>&1
    sips -z 64 64     "$REAL_PNG" --out "${ICONSET}/icon_32x32@2x.png"   > /dev/null 2>&1
    sips -z 128 128   "$REAL_PNG" --out "${ICONSET}/icon_128x128.png"    > /dev/null 2>&1
    sips -z 256 256   "$REAL_PNG" --out "${ICONSET}/icon_128x128@2x.png" > /dev/null 2>&1
    sips -z 256 256   "$REAL_PNG" --out "${ICONSET}/icon_256x256.png"    > /dev/null 2>&1
    sips -z 512 512   "$REAL_PNG" --out "${ICONSET}/icon_256x256@2x.png" > /dev/null 2>&1
    sips -z 512 512   "$REAL_PNG" --out "${ICONSET}/icon_512x512.png"    > /dev/null 2>&1
    sips -z 1024 1024 "$REAL_PNG" --out "${ICONSET}/icon_512x512@2x.png" > /dev/null 2>&1
    iconutil -c icns "$ICONSET" -o "${APP_DIR}/Contents/Resources/AppIcon.icns" 2>/dev/null || true
    rm -rf "$ICONSET" "$REAL_PNG"
fi

# Launcher
cat > "${APP_DIR}/Contents/MacOS/Gnom-Hub" << LAUNCHER
#!/bin/bash
DIR="${REPO_DIR}"
cd "\$DIR"
source .venv/bin/activate
set -a; [ -f config/.env ] && source config/.env; set +a
mkdir -p logs
pkill -f "[pP]ython.*gnom_hub" 2>/dev/null
pkill -f "[pP]ython.*agents\..*AG" 2>/dev/null
sleep 1
python3 -m gnom_hub > logs/logs_hub.txt 2>&1 &
sleep 2
for ag in generalAG soulAG researcherAG writerAG editorAG coderAG; do
    python3 -u -m agents.\${ag} > logs/logs_\${ag}.txt 2>&1 &
done
open "http://127.0.0.1:3002"
wait
LAUNCHER
chmod +x "${APP_DIR}/Contents/MacOS/Gnom-Hub"

# Info.plist
cat > "${APP_DIR}/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>Gnom-Hub</string>
    <key>CFBundleDisplayName</key><string>Gnom-Hub</string>
    <key>CFBundleIdentifier</key><string>de.netzwerkpunkt.gnom-hub</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>CFBundleExecutable</key><string>Gnom-Hub</string>
    <key>CFBundleIconFile</key><string>AppIcon</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>LSUIElement</key><true/>
</dict>
</plist>
PLIST

echo -e "  Gnom-Hub.app → /Applications ${G}✓${N}"

# ── 7. Dock hinzufügen ──
# Prüfen ob schon im Dock
if ! defaults read com.apple.dock persistent-apps 2>/dev/null | grep -q "Gnom-Hub"; then
    defaults write com.apple.dock persistent-apps -array-add "<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>${APP_DIR}</string><key>_CFURLStringType</key><integer>0</integer></dict><key>file-label</key><string>Gnom-Hub</string><key>file-type</key><integer>41</integer></dict><key>tile-type</key><string>file-tile</string></dict>"
    killall Dock 2>/dev/null || true
    echo -e "  Dock-Icon hinzugefügt ${G}✓${N}"
else
    echo -e "  Dock-Icon existiert bereits ${G}✓${N}"
fi

# ── 8. LLM-Provider Info ──
echo ""
echo -e "${Y}═══════════════════════════════════════════${N}"
echo -e "${B}  🧠 LLM-PROVIDER${N}"
echo -e "${Y}═══════════════════════════════════════════${N}"
echo ""
echo -e "  Keys in ${B}config/.env${N} eintragen:"
echo -e "  ${C}1)${N} ${B}Ollama (lokal)${N}  — brew install ollama && ollama pull deepseek-r1"
echo -e "  ${C}2)${N} ${B}DeepSeek${N}        — DEEPSEEK_API_KEY=sk-..."
echo -e "  ${C}3)${N} ${B}OpenRouter${N}      — OPENROUTER_KEY_FREE_1=sk-or-..."
echo ""

# ── Fertig ──
echo -e "${G}═══════════════════════════════════════════${N}"
echo -e "${B}  ✅ Installation abgeschlossen!${N}"
echo -e "${G}═══════════════════════════════════════════${N}"
echo ""
echo -e "  ${B}Starten:${N}  Klick auf 🧠 Gnom-Hub im Dock"
echo -e "  ${B}Oder:${N}     open /Applications/Gnom-Hub.app"
echo -e "  ${B}War Room:${N} http://127.0.0.1:3002"
echo ""
