#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
# Gnom-Hub – Backup aller Datenbanken
# Erstellt NIE überschriebene, eindeutig benannte Snapshots
# Usage: ./scripts/backup_all_dbs.sh [trigger]
# Trigger: manual (default) | cleanAll | pre-push | scheduled
# ════════════════════════════════════════════════════════════════

set -euo pipefail

TRIGGER="${1:-manual}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Backup-Root: ~/Desktop/gnom_dev/backups_datenbanken (außerhalb des Repos,
# überlebt Reinstallation). Fallback: $REPO_ROOT/dev/...
BACKUP_ROOT="${GNOM_BACKUP_ROOT:-$HOME/Desktop/gnom_dev/backups_datenbanken}"
if [[ ! -d "$(dirname "$BACKUP_ROOT")" ]]; then
    BACKUP_ROOT="$REPO_ROOT/dev/backups_datenbanken"
fi

# Timestamp: YYYY-MM-DD_HH-MM-SS + Trigger
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_NAME="${TIMESTAMP}_${TRIGGER}"
# BACKUP_ROOT ist bereits oben gesetzt (Desktop oder Fallback)
BACKUP_DIR="$BACKUP_ROOT/$BACKUP_NAME"
TEMP_DIR="$BACKUP_ROOT/.tmp_$$_$RANDOM"

# Daten-Pfade (übereinstimmend mit src/gnom_hub/core/config.py)
# Default: ~/.gnom-hub/data (Port 3002)
GNOM_HUB_HOME="${GNOM_HUB_HOME:-$HOME/.gnom-hub}"
DATA_DIR="$GNOM_HUB_HOME/data"
MAIN_DB="$DATA_DIR/gnomhub.db"
PASSIVE_DB="$DATA_DIR/passive_archive.db"
WAL_MAIN="$DATA_DIR/gnomhub.db-wal"
SHM_MAIN="$DATA_DIR/gnomhub.db-shm"
WAL_PASSIVE="$DATA_DIR/passive_archive.db-wal"
SHM_PASSIVE="$DATA_DIR/passive_archive.db-shm"

# Embedded-Index-Files (soul_embeddings_*.index, soul_fact_ids_*.json)
EMBEDDINGS_DIR="$DATA_DIR"

# Optional: Workspace sichern? (kann groß sein)
WORKSPACE_DIR="${GNOM_HUB_WORKSPACE:-$HOME/gnom_workspace}"
BACKUP_WORKSPACE="${BACKUP_WORKSPACE:-0}"

# ── Helpers ────────────────────────────────────────────────────
log()  { echo "[$(date +%H:%M:%S)] $*"; }
fail() { log "FEHLER: $*"; rm -rf "$TEMP_DIR"; exit 1; }

# ── Pre-Check ──────────────────────────────────────────────────
mkdir -p "$BACKUP_ROOT"
mkdir -p "$TEMP_DIR"
[[ -d "$DATA_DIR" ]] || fail "DATA_DIR existiert nicht: $DATA_DIR"

log "Starte Backup: $BACKUP_NAME"
log "Quelle: $DATA_DIR"
log "Ziel:   $BACKUP_DIR"

# ── Manifest sammeln ──────────────────────────────────────────
MANIFEST="$TEMP_DIR/manifest.json"
declare -a FILE_LIST
TOTAL_SIZE=0

add_file() {
    local src="$1" rel="$2" hash="$3" size="$4"
    FILE_LIST+=("$(printf '{"path":"%s","rel":"%s","sha256":"%s","size":%d}' \
        "$src" "$rel" "$hash" "$size" | python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read())))')")
    TOTAL_SIZE=$((TOTAL_SIZE + size))
}

sha256_of() { shasum -a 256 "$1" | awk '{print $1}'; }

copy_with_hash() {
    local src="$1" rel="$2"
    [[ -f "$src" ]] || { log "  ⚠️  fehlt: $src"; return 1; }
    local dest="$TEMP_DIR/$rel"
    mkdir -p "$(dirname "$dest")"
    # .backup wäre sicherer, aber für Files im cold state reicht cp
    cp -p "$src" "$dest"
    local size hash
    size=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest")
    hash=$(sha256_of "$dest")
    add_file "$src" "$rel" "$hash" "$size"
    log "  ✓ $rel (${size} bytes, sha256=${hash:0:12}…)"
}

# ── 1. Haupt-DB + WAL + SHM ───────────────────────────────────
log "[1/3] Haupt-Datenbank…"
copy_with_hash "$MAIN_DB"  "data/gnomhub.db"         || true
copy_with_hash "$WAL_MAIN" "data/gnomhub.db-wal"      || true
copy_with_hash "$SHM_MAIN" "data/gnomhub.db-shm"     || true

# ── 2. Passive DB + WAL + SHM ─────────────────────────────────
log "[2/3] Passive Archive…"
copy_with_hash "$PASSIVE_DB"   "data/passive_archive.db"     || true
copy_with_hash "$WAL_PASSIVE"  "data/passive_archive.db-wal" || true
copy_with_hash "$SHM_PASSIVE"  "data/passive_archive.db-shm" || true

# ── 3. Embedding-Indexe & Soul-IDs ─────────────────────────────
log "[3/3] Embeddings & Soul-IDs…"
if [[ -d "$EMBEDDINGS_DIR" ]]; then
    for f in "$EMBEDDINGS_DIR"/soul_embeddings_*.index \
             "$EMBEDDINGS_DIR"/soul_fact_ids_*.json; do
        [[ -f "$f" ]] || continue
        rel="data/$(basename "$f")"
        copy_with_hash "$f" "$rel" || true
    done
fi

# ── Optional: Workspace ───────────────────────────────────────
if [[ "$BACKUP_WORKSPACE" == "1" && -d "$WORKSPACE_DIR" ]]; then
    log "[+] Workspace…"
    for proj in "$WORKSPACE_DIR"/*; do
        [[ -d "$proj" ]] || continue
        pname=$(basename "$proj")
        for f in "$proj"/*; do
            [[ -f "$f" ]] || continue
            rel="workspace/$pname/$(basename "$f")"
            copy_with_hash "$f" "$rel" || true
        done
    done
fi

# ── Manifest schreiben ────────────────────────────────────────
log "Erstelle manifest.json…"
python3 - "$TEMP_DIR" "$TRIGGER" "$TOTAL_SIZE" "${FILE_LIST[@]}" <<'PYEOF'
import json, os, sys, subprocess
from datetime import datetime

tmp_dir   = sys.argv[1]
trigger   = sys.argv[2]
total_sz  = int(sys.argv[3])
files_arg = sys.argv[4:]

files = []
for raw in files_arg:
    try:
        files.append(json.loads(raw))
    except json.JSONDecodeError:
        pass

# git-revision (optional, leer wenn kein repo)
try:
    rev = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=os.path.dirname(tmp_dir), stderr=subprocess.DEVNULL
    ).decode().strip()
except Exception:
    rev = ""

manifest = {
    "backup_name": os.path.basename(tmp_dir),
    "trigger":     trigger,
    "created_at":  datetime.now().isoformat(timespec="seconds"),
    "git_rev":     rev,
    "total_size":  total_sz,
    "file_count":  len(files),
    "files":       files,
    "restore_hint": "tar -xzf backup.tar.gz -C /path/to/restore ; python3 scripts/verify_backup.py <dir>",
}

with open(os.path.join(tmp_dir, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
PYEOF

# ── Optional: tar.gz zusätzlich ───────────────────────────────
if [[ "${BACKUP_TAR:-0}" == "1" ]]; then
    log "Erstelle backup.tar.gz…"
    (cd "$TEMP_DIR" && tar -czf "$TEMP_DIR/backup.tar.gz" .)
    log "  ✓ backup.tar.gz ($(stat -f%z "$TEMP_DIR/backup.tar.gz" 2>/dev/null) bytes)"
fi

# ── Atomar verschieben ────────────────────────────────────────
mv "$TEMP_DIR" "$BACKUP_DIR"

# Manifest backup_name korrigieren (war bisher .tmp_…)
python3 -c "
import json, pathlib
p = pathlib.Path('$BACKUP_DIR/manifest.json')
m = json.loads(p.read_text())
m['backup_name'] = '$BACKUP_NAME'
p.write_text(json.dumps(m, indent=2, ensure_ascii=False))
"

log "✅ Backup erfolgreich: $BACKUP_DIR"

# DB-Integrität nach Backup verifizieren
if command -v python3.10 >/dev/null 2>&1; then
    log "🔍 Verifiziere DB-Integrität…"
    if python3.10 "$REPO_ROOT/scripts/verify_dbs.py"; then
        log "✓ DBs ok"
    else
        log "⚠️ DB-Verifikation fehlgeschlagen — Backup trotzdem erstellt"
    fi
else
    log "ℹ python3.10 nicht gefunden — DB-Verifikation übersprungen"
fi
log "   Dateien: $(ls -1 "$BACKUP_DIR" | wc -l | tr -d ' ')"
log "   Größe:   $(du -sh "$BACKUP_DIR" | awk '{print $1}')"

# ── _INDEX.md aktualisieren ───────────────────────────────────
INDEX_FILE="$BACKUP_ROOT/_INDEX.md"
TIMESTAMP_READABLE=$(date +"%Y-%m-%d %H:%M:%S")
TOTAL_MB=$(awk "BEGIN {printf \"%.2f\", $TOTAL_SIZE/1048576}")

if [[ ! -f "$INDEX_FILE" ]]; then
    cat > "$INDEX_FILE" <<HEADER
# Backup-Übersicht

> **Lokale Dev-Notiz.** Gitignored.
> Alle Snapshots sind **unveränderlich** — wird nie überschrieben.

| Datum | Trigger | Größe | Dateien | Pfad |
|---|---|---|---|---|
HEADER
fi

echo "| $TIMESTAMP_READABLE | \`$TRIGGER\` | ${TOTAL_MB} MB | $((${#FILE_LIST[@]})) | [\`$BACKUP_NAME\`](./$BACKUP_NAME/) |" >> "$INDEX_FILE"

log "📋 _INDEX.md aktualisiert"
