import json
from pathlib import Path
from datetime import datetime
import glob

BACKUP_DIR = Path(".backups/swarm")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def save_swarm_checkpoint(souls: list[dict], war_room_state: list[dict]):
    """Speichert Souls + War-Room-History als Timestamp-JSON."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = {
        "timestamp": timestamp,
        "souls": souls,
        "war_room_state": war_room_state  # letzte Nachrichten + extrahierte Souls
    }
    file = BACKUP_DIR / f"swarm_{timestamp}.json"
    file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    # Aufräumen: nur letzte 10 behalten
    all_backups = sorted(BACKUP_DIR.glob("swarm_*.json"), reverse=True)
    for old in all_backups[10:]:
        old.unlink()
    return f"✅ Swarm-Checkpoint gespeichert: {file.name}"

def load_latest_checkpoint() -> dict | None:
    """Lädt den neuesten Checkpoint beim Hub-Start oder @checkpoint restore."""
    all_backups = sorted(BACKUP_DIR.glob("swarm_*.json"), reverse=True)
    if not all_backups:
        return None
    data = json.loads(all_backups[0].read_text(encoding="utf-8"))
    print(f"🔄 Swarm-Checkpoint geladen: {all_backups[0].name}")
    return data
