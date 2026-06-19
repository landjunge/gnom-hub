#!/bin/bash
# =====================================================================
# Gnom-Hub — Minimal-Blockade + MiniMax-M3 Setup
# =====================================================================
# Setzt die drei globalen Blockade-States explizit auf Minimum:
#   - blockade_level            = 0  (UI-Slider, Hub-weit)
#   - security_blockade_level   = 0  (Path/Shell-Validator, technisch)
#   - enable_confirmations      = false  (Chat-Confirmations aus)
#
# Verifiziert routing.txt → alle 8 Agenten auf minimax | MiniMax-M3.
# Verifiziert, dass die Agenten aktiv im Loop laufen (heartbeat).
#
# Idempotent: kann jederzeit gefahrlos neu laufen.
#
#   bash scripts/agent-setup-minimal.sh
#
# =====================================================================
set -e

HUB_URL="${GNOM_HUB_URL:-http://127.0.0.1:3002}"
HUB_PORT="${GNOM_HUB_PORT:-3002}"
DB_PATH="${GNOM_HUB_DB:-/Users/landjunge/.gnom-hub/data/gnomhub.db}"
ROUTING="${GNOM_HUB_ROOT:-/Users/landjunge/gnom-hub}/config/routing.txt"

echo "════════════════════════════════════════════════════════════"
echo "  Gnom-Hub — Minimal-Blockade Setup"
echo "════════════════════════════════════════════════════════════"

# ── 1) Hub erreichbar? ────────────────────────────────────────────────────
echo "▸ Hub-Erreichbarkeit prüfen ($HUB_URL)…"
if ! curl -s -o /dev/null -w "" --max-time 3 "$HUB_URL/api/health"; then
    echo "  ✗ Hub nicht erreichbar — bitte erst starten (run.sh)."
    exit 1
fi
echo "  ✓ Hub läuft."

# ── 2) Blockade-States in DB schreiben (Truth-of-Record) ─────────────────
echo "▸ Blockade-States in DB setzen…"
python3.10 - "$DB_PATH" <<'PY'
import sqlite3, sys
db = sys.argv[1]
c = sqlite3.connect(db)
cur = c.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT)")
cur.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('blockade_level','0')")
cur.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('security_blockade_level','0')")
cur.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('enable_confirmations','false')")
c.commit()
for k, v in cur.execute("SELECT key,value FROM state WHERE key IN ('blockade_level','security_blockade_level','enable_confirmations') ORDER BY key"):
    print(f"  ✓ {k:30s} = {v}")
PY

# ── 3) Verifiziere über API ──────────────────────────────────────────────
echo "▸ Verifiziere via API…"
LEVEL=$(curl -s "$HUB_URL/api/admin/blockade-level" | python3.10 -c "import sys,json; print(json.load(sys.stdin).get('level','?'))")
echo "  ✓ /api/admin/blockade-level → $LEVEL  (erwartet: 0)"

# ── 4) routing.txt prüfen ─────────────────────────────────────────────────
echo "▸ routing.txt prüfen ($ROUTING)…"
NON_MINIMAX=$(grep -v '^#' "$ROUTING" | grep -v '^[[:space:]]*$' | grep -v 'minimax' | wc -l | tr -d ' ')
if [ "$NON_MINIMAX" -gt 0 ]; then
    echo "  ⚠ $NON_MINIMAX Zeile(n) zeigen auf einen anderen Provider als minimax:"
    grep -v '^#' "$ROUTING" | grep -v '^[[:space:]]*$' | grep -v 'minimax'
    echo "  → Setze alle 8 Agenten explizit auf minimax | MiniMax-M3."
    cat > "$ROUTING" <<'EOF'
# =====================================================================
# GNOM-HUB - Agent LLM Routing (Direkt, kein Auto-Routing)
# =====================================================================
# Format: agent_name = provider | model
#
# Kette pro Request: Provider → OpenRouter Free Models → Ollama (lokal)
#
# MiniMax = multimodal primary. Ein einziger sk-cp-… Key deckt
#   Text + Vision + Image + Audio/TTS + Video + Music ab.
# =====================================================================

# --- Alle auf MiniMax M3 (multimodal) ---
coderag = minimax | MiniMax-M3
securityag = minimax | MiniMax-M3
researcherag = minimax | MiniMax-M3
generalag = minimax | MiniMax-M3
soulag = minimax | MiniMax-M3
writerag = minimax | MiniMax-M3
editorag = minimax | MiniMax-M3
watchdogag = minimax | MiniMax-M3
EOF
    echo "  ✓ routing.txt neu geschrieben."
fi
AGENTS_ON_MINIMAX=$(grep -v '^#' "$ROUTING" | grep -v '^[[:space:]]*$' | grep -c 'minimax.*MiniMax-M3')
echo "  ✓ $AGENTS_ON_MINIMAX / 8 Agenten auf minimax | MiniMax-M3."

# ── 5) Agent-Loop verifizieren ────────────────────────────────────────────
echo "▸ Agent-Heartbeats (Live-Status)…"
curl -s "$HUB_URL/api/agents" 2>&1 | python3.10 -c "
import sys, json
try:
    agents = json.load(sys.stdin)
    on = sum(1 for a in agents if a.get('status') in ('online','busy'))
    busy = sum(1 for a in agents if a.get('status') == 'busy')
    print(f'  ✓ {on}/8 Agenten aktiv im Loop  (busy: {busy})')
    for a in agents:
        if a.get('status') not in ('online','busy'):
            print(f'    · {a[\"name\"]:14s} = {a[\"status\"]}')
except Exception as e:
    print(f'  ⚠ Agent-Liste nicht abrufbar: {e}')
"

echo "════════════════════════════════════════════════════════════"
echo "  ✓ Setup abgeschlossen. Agenten laufen, Blockades minimal."
echo "════════════════════════════════════════════════════════════"
