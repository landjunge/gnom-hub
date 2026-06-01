#!/usr/bin/env python3
import sys
from pathlib import Path

# Fix python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gnom_hub.db.connection import get_db_connection
from gnom_hub.core.config import DB_PATH

def clean_database():
    print(f"🧹 Bereinige Datenbank: {DB_PATH}")
    try:
        with get_db_connection() as conn:
            with conn:
                # 1. Clear chat history
                conn.execute("DELETE FROM chat")
                print("  - Chat-Historie gelöscht.")
                # 2. Clear showbox presentations except Standard
                conn.execute("DELETE FROM showbox_presentations WHERE name != 'Standard'")
                print("  - Showboxen bereinigt (außer 'Standard').")
                # 3. Reset active showbox and pending decisions
                conn.execute("UPDATE state SET value = '\"\"' WHERE key = 'active_showbox'")
                conn.execute("UPDATE state SET value = '{}' WHERE key = 'pending_decisions'")
                conn.execute("UPDATE state SET value = '[]' WHERE key = 'approved_security_writes'")
                conn.execute("UPDATE state SET value = '[]' WHERE key = 'approved_security_commands'")
                print("  - Status-Variablen und Blockaden zurückgesetzt.")
                # 4. Clean active jobs of all agents
                conn.execute("UPDATE agents SET active_job = NULL")
                print("  - Aktive Jobs zurückgesetzt.")
            conn.execute("VACUUM")
        print("✅ Datenbank erfolgreich bereinigt. System-Agenten und Prompts blieben intakt.")
    except Exception as e:
        print(f"❌ Fehler bei der Bereinigung: {e}")

if __name__ == "__main__":
    clean_database()
