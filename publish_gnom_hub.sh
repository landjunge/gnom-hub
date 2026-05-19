#!/bin/bash
# 🚀 GNOM-HUB PUBLISH SCRIPT
# Überträgt das Frontend auf netzwerkpunkt.de

HOST="185.243.11.43"
USER="sysuser_a"
PASS='5Rdv4uH6~Owlqn~k'
REMOTE_DIR="netzwerkpunkt.de/httpdocs"

LOCAL_DIR="/Users/landjunge/Documents/AG-Flega/frontend"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 Gnom-Hub Deploy gestartet...${NC}"

upload_file() {
    local local_file="$1"
    local remote_path="$2"
    local result
    result=$(curl -s -w "%{http_code}" \
        -T "$local_file" \
        --user "$USER:$PASS" \
        "ftp://$HOST/$REMOTE_DIR/$remote_path" \
        --ftp-create-dirs \
        --connect-timeout 30 \
        --max-time 120 -o /dev/null 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✅ $remote_path${NC}"
    else
        echo -e "  ${RED}❌ $remote_path (Fehler: $result)${NC}"
        ERRORS=1
    fi
}

ERRORS=0
echo -e "\n${YELLOW}📤 Übertrage Frontend...${NC}"
upload_file "$LOCAL_DIR/index.html"  "index.html"
upload_file "$LOCAL_DIR/themes.js"   "themes.js"

if [ $ERRORS -eq 0 ]; then
    echo -e "\n${GREEN}✨ Gnom-Hub veröffentlicht!${NC}"
    echo -e "   🌐 https://netzwerkpunkt.de/"
else
    echo -e "\n${RED}⚠️ Deploy mit Fehlern abgeschlossen!${NC}"
    exit 1
fi
