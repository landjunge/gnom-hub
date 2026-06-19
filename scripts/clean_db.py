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
                # 2. Clear soul memory
                conn.execute("DELETE FROM soul_memory")
                print("  - Lernfakte (Soul Memory) gelöscht.")
                # 3. Clear showbox presentations except Standard
                conn.execute("DELETE FROM showbox_presentations WHERE name != 'Standard'")
                print("  - Showboxen bereinigt (außer 'Standard').")
                # 4. Reset active showbox and pending decisions
                conn.execute("UPDATE state SET value = '\"\"' WHERE key = 'active_showbox'")
                conn.execute("UPDATE state SET value = '{}' WHERE key = 'pending_decisions'")
                conn.execute("UPDATE state SET value = '[]' WHERE key = 'approved_security_writes'")
                conn.execute("UPDATE state SET value = '[]' WHERE key = 'approved_security_commands'")
                conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('enable_confirmations', 'false')")
                print("  - Status-Variablen und Blockaden zurückgesetzt und deaktiviert.")
                # 5. Clean active jobs of all agents
                conn.execute("UPDATE agents SET active_job = NULL")
                print("  - Aktive Jobs zurückgesetzt.")
            conn.execute("VACUUM")
            
        # 6. Clear passive archive DB
        try:
            from gnom_hub.db.passive_db import get_passive_conn, init_passive_db
            init_passive_db()
            with get_passive_conn() as p_conn:
                with p_conn:
                    p_conn.execute("DELETE FROM archive_log")
                p_conn.execute("VACUUM")
            print("  - Passives Archiv komplett gelöscht.")
        except Exception as ex:
            print(f"  ⚠️ Warnung beim Löschen des passiven Archivs: {ex}")
            
        print("✅ Datenbanken erfolgreich bereinigt. System-Agenten und Prompts blieben intakt.")
    except Exception as e:
        print(f"❌ Fehler bei der Bereinigung: {e}")

if __name__ == "__main__":
    clean_database()
