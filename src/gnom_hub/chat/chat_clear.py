"""Chat-Commands: clear-Varianten und Datenbereinigung."""
def handle_clear(q=""):
    q = q.strip().lower()
    if q in ("db", "database", "all"):
        from gnom_hub.chat.chat_commands import _post_chat
        from gnom_hub.db.connection import get_db_connection
        from gnom_hub.db.passive_db import get_passive_conn, init_passive_db
        try:
            # 1. Primary DB clean
            with get_db_connection() as conn:
                with conn:
                    conn.execute("DELETE FROM chat")
                    conn.execute("DELETE FROM soul_memory")
                    conn.execute("DELETE FROM showbox_presentations WHERE name != 'Standard'")
                    conn.execute("UPDATE state SET value = '\"\"' WHERE key = 'active_showbox'")
                    conn.execute("UPDATE state SET value = '{}' WHERE key = 'pending_decisions'")
                    conn.execute("UPDATE state SET value = '[]' WHERE key = 'approved_security_writes'")
                    conn.execute("UPDATE state SET value = '[]' WHERE key = 'approved_security_commands'")
                    conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('enable_confirmations', 'false')")
                    conn.execute("UPDATE agents SET active_job = NULL")
                conn.execute("VACUUM")
            
            # 2. Passive DB clean
            try:
                init_passive_db()
                with get_passive_conn() as p_conn:
                    with p_conn:
                        p_conn.execute("DELETE FROM archive_log")
                    p_conn.execute("VACUUM")
            except Exception as ex:
                print(f"Warning clearing passive archive: {ex}")
                
            _post_chat("System", "🧹 **Datenbanken komplett bereinigt:** Alle Chats, Lernfakte (Soul), temporären Showboxen, das passive Archiv, aktive Jobs und System-Blockaden wurden zurückgesetzt und deaktiviert. System-Agenten und Prompts bleiben unverändert.")
            return {"status": "cleared"}
        except Exception as e:
            _post_chat("System", f"❌ Fehler bei der Bereinigung: {e}")
            return {"status": "error", "message": str(e)}
    if q == "all agents":
        sys_ags = ['soulag', 'generalag', 'securityag', 'watchdogag']
        from gnom_hub.db import delete_non_system_agents; delete_non_system_agents(sys_ags)
        from gnom_hub.chat.chat_commands import _post_chat; _post_chat("System", "Alle externen Agenten gelöscht. System-Infrastruktur bleibt intakt.")
        return {"status": "agents_cleared"}
    from gnom_hub.db import get_active_project; p = get_active_project()
    if q == "@projekt":
        from gnom_hub.db import clear_project_chat; clear_project_chat(p)
        import os; import shutil; from gnom_hub.core.config import Config; wd = os.path.join(str(Config.workspace_dir()), p)
        # Path traversal protection
        from pathlib import Path
        wd_resolved = Path(wd).resolve()
        ws_root = Path(str(Config.workspace_dir())).resolve()
        if not str(wd_resolved).startswith(str(ws_root)):
            return {"status": "error", "message": "Ungültiger Projektpfad"}
        wd = str(wd_resolved)
        for f in os.listdir(wd):
            fp = os.path.join(wd, f)
            if os.path.isfile(fp): os.unlink(fp)
            elif os.path.isdir(fp): shutil.rmtree(fp)
        from gnom_hub.chat.chat_commands import _post_chat; _post_chat("System", f"Projekt '{p}' komplett geleert.")
        return {"status": "project_cleared"}
    if q == "chat" or q.startswith("chat "):
        parts = q.split(); from gnom_hub.chat.chat_commands import _post_chat
        if len(parts) > 1:
            target_agent = parts[1].replace("@", "").lower()
            from gnom_hub.db import clear_project_chat_by_sender; clear_project_chat_by_sender(p, target_agent)
            _post_chat("System", f"Chat-Historie von '{target_agent}' gelöscht.")
        else:
            from gnom_hub.db import clear_project_chat; clear_project_chat(p)
            _post_chat("System", f"Kompletter Chat im Projekt '{p}' gelöscht.")
        return {"status": "cleared"}
    from gnom_hub.db import clear_project_chat; clear_project_chat(p)
    return {"status": "cleared"}
