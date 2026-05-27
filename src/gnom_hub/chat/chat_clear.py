"""Chat-Commands: clear-Varianten und Datenbereinigung."""
def handle_clear(q=""):
    q = q.strip().lower()
    if q == "all agents":
        sys_ags = ['soulag', 'generalag', 'securityag', 'watchdogag']
        from gnom_hub.database.legacy_db import delete_non_system_agents; delete_non_system_agents(sys_ags)
        from gnom_hub.chat.chat_commands import _post_chat; _post_chat("System", "Alle externen Agenten gelöscht. System-Infrastruktur bleibt intakt.")
        return {"status": "agents_cleared"}
    from gnom_hub.database.legacy_db import get_active_project; p = get_active_project()
    if q == "@projekt":
        from gnom_hub.database.legacy_db import clear_project_chat; clear_project_chat(p)
        import os, shutil; from gnom_hub.core.config import Config; wd = os.path.join(str(Config.WORKSPACE_DIR), p)
        for f in os.listdir(wd):
            fp = os.path.join(wd, f)
            if os.path.isfile(fp): os.unlink(fp)
            elif os.path.isdir(fp): shutil.rmtree(fp)
        from gnom_hub.chat.chat_commands import _post_chat; _post_chat("System", f"Projekt '{p}' komplett geleert.")
        return {"status": "project_cleared"}
    if q.startswith("chat"):
        parts = q.split(); from gnom_hub.chat.chat_commands import _post_chat
        if len(parts) > 1:
            target_agent = parts[1].replace("@", "").lower()
            from gnom_hub.database.legacy_db import clear_project_chat_by_sender; clear_project_chat_by_sender(p, target_agent)
            _post_chat("System", f"Chat-Historie von '{target_agent}' gelöscht.")
        else:
            from gnom_hub.database.legacy_db import clear_project_chat; clear_project_chat(p)
            _post_chat("System", f"Kompletter Chat im Projekt '{p}' gelöscht.")
        return {"status": "cleared"}
    from gnom_hub.database.legacy_db import clear_project_chat; clear_project_chat(p)
    return {"status": "cleared"}
