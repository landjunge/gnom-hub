#!/bin/bash
# ═══════════════════════════════════════════════════
# Gnom-Hub.app Builder — Dock-fähiges macOS App Bundle
# ═══════════════════════════════════════════════════
set -e

WORKSPACE="$(cd "$(dirname "$0")" && pwd)"
ICON_PNG="${WORKSPACE}/frontend/assets/logo.png"
APP_DIR="/Applications/Gnom-Hub.app"
APP_NAME="Gnom-Hub"

echo "🧠 Building ${APP_NAME}.app..."

# ── 1. App Bundle Struktur ──
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"

# ── 2. Icon aus logo.png ──
if [ -f "$ICON_PNG" ]; then
    ICONSET="/tmp/GnomIcon.iconset"
    rm -rf "$ICONSET" && mkdir -p "$ICONSET"
    for s in 16 32 64 128 256 512; do
        sips -z $s $s "$ICON_PNG" --out "${ICONSET}/icon_${s}x${s}.png" > /dev/null 2>&1
        s2=$((s*2))
        sips -z $s2 $s2 "$ICON_PNG" --out "${ICONSET}/icon_${s}x${s}@2x.png" > /dev/null 2>&1
    done
    iconutil -c icns "$ICONSET" -o "${APP_DIR}/Contents/Resources/AppIcon.icns" 2>/dev/null || true
    rm -rf "$ICONSET"
    echo "  ✅ Icon kompiliert"
fi

# ── 3. Launch-Script ──
cat > "${APP_DIR}/Contents/MacOS/${APP_NAME}" << 'LAUNCHER'
#!/bin/bash
DIR="WORKSPACE_PLACEHOLDER"
cd "$DIR"
source .venv/bin/activate
set -a; [ -f config/.env ] && source config/.env; set +a
mkdir -p logs

# Kill alte Prozesse
pkill -f "[pP]ython.*gnom_hub" 2>/dev/null
pkill -f "[pP]ython.*agents\..*AG" 2>/dev/null
sleep 1

# Hub starten
python3 -m gnom_hub > logs/logs_hub.txt 2>&1 &
sleep 2

# Agenten starten
for ag in generalAG soulAG researcherAG writerAG editorAG coderAG; do
    python3 -u -m agents.${ag} > logs/logs_${ag}.txt 2>&1 &
done

# Browser öffnen
open "http://127.0.0.1:3002"

# Warten bis Hub-Prozess endet
wait
LAUNCHER

# Workspace-Pfad einsetzen
sed -i '' "s|WORKSPACE_PLACEHOLDER|${WORKSPACE}|g" "${APP_DIR}/Contents/MacOS/${APP_NAME}"
chmod +x "${APP_DIR}/Contents/MacOS/${APP_NAME}"

# ── 4. Info.plist ──
cat > "${APP_DIR}/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key><string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key><string>de.netzwerkpunkt.gnom-hub</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>CFBundleExecutable</key><string>${APP_NAME}</string>
    <key>CFBundleIconFile</key><string>AppIcon</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>LSUIElement</key><true/>
</dict>
</plist>
PLIST

echo "  ✅ App Bundle erstellt: ${APP_DIR}"
echo ""
echo "📌 Zum Dock hinzufügen:"
echo "   Rechtsklick auf ${APP_NAME} in /Applications → 'Im Dock behalten'"
echo ""
echo "🚀 Oder direkt starten: open '${APP_DIR}'"
