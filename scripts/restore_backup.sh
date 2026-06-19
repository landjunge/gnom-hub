# Restore-Script – Backup zurückspielen
# Usage: ./scripts/restore_backup.sh <backup-name>
# Beispiel: ./scripts/restore_backup.sh 2026-06-13_20-30-15_cleanAll

set -euo pipefail

BACKUP_NAME="${1:-}"
if [[ -z "$BACKUP_NAME" ]]; then
    echo "Usage: $0 <backup-name>"
    echo "Verfügbare Backups:"
    ls -1 /Users/landjunge/gnom-hub/dev/backups_datenbanken/ | grep -v "^_" | grep -v "^\\."
    exit 1
fi

BACKUP_DIR="/Users/landjunge/gnom-hub/dev/backups_datenbanken/$BACKUP_NAME"
DATA_DIR="${GNOM_HUB_HOME:-$HOME/.gnom-hub}/data"

[[ -d "$BACKUP_DIR" ]] || { echo "FEHLER: $BACKUP_DIR existiert nicht"; exit 1; }
[[ -f "$BACKUP_DIR/manifest.json" ]] || { echo "FEHLER: manifest.json fehlt"; exit 1; }

echo "═══ Backup: $BACKUP_NAME ═══"
cat "$BACKUP_DIR/manifest.json" | python3 -m json.tool | head -20

echo ""
echo "⚠️  WARNUNG: Überschreibt aktuelle Datenbanken in $DATA_DIR"
read -p "Fortfahren? (j/N): " CONFIRM
[[ "$CONFIRM" == "j" || "$CONFIRM" == "J" ]] || { echo "Abgebrochen."; exit 0; }

# SHA256-Verifikation
echo ""
echo "Prüfe SHA256-Hashes…"
python3 - "$BACKUP_DIR" <<'PYEOF'
import json, hashlib, os, sys
d = sys.argv[1]
mf = json.load(open(os.path.join(d, "manifest.json")))
ok = err = 0
for f in mf["files"]:
    p = os.path.join(d, f["rel"])
    if not os.path.exists(p):
        print(f"  ✗ FEHLT: {f['rel']}"); err += 1; continue
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if h == f["sha256"]:
        ok += 1
    else:
        print(f"  ✗ HASH MISMATCH: {f['rel']}"); err += 1
print(f"  ✓ {ok} OK, ✗ {err} Fehler")
sys.exit(0 if err == 0 else 1)
PYEOF

# Restore (nur data/-Pfade, da Workspace optional)
echo ""
echo "Restore Datenbanken nach $DATA_DIR…"
cp -p "$BACKUP_DIR"/data/gnomhub.db*          "$DATA_DIR/" 2>/dev/null || true
cp -p "$BACKUP_DIR"/data/passive_archive.db* "$DATA_DIR/" 2>/dev/null || true
cp -p "$BACKUP_DIR"/data/soul_*              "$DATA_DIR/" 2>/dev/null || true

echo "✅ Restore abgeschlossen. Hub neu starten."
