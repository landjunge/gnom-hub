#!/bin/bash

# Publish-Script für das Kreativ-Universum von Kira, Lian und Elara
# Ziel: königliches-feenreich.de/trio

HOST="185.243.11.43"
USER="sysuser_a"
PASS='yE2KNv_jdd28$dlf'
LOCAL_DIR="/Users/landjunge/Documents/AG-Flega/kreativ_universe_kira_lian_elara"
REMOTE_DIR="xn--knigliches-feenreich-39b.de/httpdocs/trio"

echo "🌌 Verbinde mit königliches-feenreich.de..."
echo "✨ Übertrage die Kreationen von Kira, Lian und Elara nach /trio..."

# Upload-Schleife für alle Dateien im Ordner
find "$LOCAL_DIR" -type f ! -name ".DS_Store" | while read file; do
    relative_path="${file#$LOCAL_DIR/}"
    
    curl -s -o /dev/null \
        -T "$file" \
        --user "$USER:$PASS" \
        "ftp://$HOST/$REMOTE_DIR/$relative_path" \
        --ftp-create-dirs \
        --connect-timeout 30 \
        --max-time 120
        
    echo "  ✅ $relative_path"
done

echo "✅ Veröffentlichung abgeschlossen!"
echo "🌍 Live unter: https://xn--knigliches-feenreich-39b.de/trio/"
