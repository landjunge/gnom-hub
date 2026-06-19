#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
# Gnom-Hub – Scheduled Backup Daemon
# Erstellt ALLE 5 MINUTEN ein neues Backup. KEINES wird überschrieben.
# Trigger: scheduled5min
# Beenden: pkill -f scheduled_backup.sh
# ════════════════════════════════════════════════════════════════

set -uo pipefail

INTERVAL=300  # 5 Minuten
LOGFILE="$HOME/Desktop/gnom_dev/backup_daemon.log"
PIDFILE="$HOME/.gnom-hub/run/backup_daemon.pid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup_all_dbs.sh"

# PID-File schreiben
mkdir -p "$(dirname "$PIDFILE")"
echo $$ > "$PIDFILE"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

log "═══ Scheduled Backup Daemon gestartet (PID $$, Intervall ${INTERVAL}s) ═══"
log "Logfile: $LOGFILE"

cleanup() {
    log "Daemon beendet"
    rm -f "$PIDFILE"
    exit 0
}
trap cleanup SIGTERM SIGINT

# Erstes Backup sofort
log "Erstes Backup wird erstellt..."
bash "$BACKUP_SCRIPT" scheduled5min >> "$LOGFILE" 2>&1
log "Erstes Backup fertig."

while true; do
    sleep "$INTERVAL"
    log "Erstelle 5-Min-Backup..."
    bash "$BACKUP_SCRIPT" scheduled5min >> "$LOGFILE" 2>&1
    log "Backup fertig."
done