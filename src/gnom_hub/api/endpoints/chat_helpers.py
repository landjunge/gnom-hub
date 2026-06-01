import re
from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.chat.chat_commands import _post_chat

def _parse(t):
    t_clean = t.strip()
    m_gen = re.match(r"@generalag\s+@(\w+)\s*(.*)", t_clean, re.IGNORECASE | re.DOTALL)
    if m_gen:
        tag = m_gen.group(1).lower()
        if tag in ("bs","clear","status","research","job","free","git","project","resume","approve_decision","reject_decision","bake","emergency","notfall","diagnose","help","hilfe","confirmations"):
            return m_gen.group(2).strip(), None, tag
    m = re.match(r"@{1,2}(\w+)\s*(.*)", t_clean, re.DOTALL)
    r, tag = (m.group(2).strip() if m else None), (m.group(1).lower() if m else None)
    if not m: return t_clean, None, None
    if tag in ("bs","clear","status","research","job","free","git","project","resume","approve_decision","reject_decision","bake","emergency","notfall","diagnose","help","hilfe","confirmations"):
        return r or t_clean, None, tag
    return r or t_clean, tag, None

def _handle_sys(q, m):
    if m == "proj":
        q_str = (q or "").strip()
        parts = q_str.split(None, 1)
        if parts and parts[0].lower() in ("delete", "remove"):
            from gnom_hub.db import get_active_project, delete_project_completely
            from gnom_hub.core.config import Config
            import os, shutil
            
            target_proj = parts[1].strip() if len(parts) > 1 else ""
            if not target_proj or target_proj.lower() == "current":
                target_proj = get_active_project()
                
            if target_proj.lower() == "default":
                _post_chat("System", "Das 'default' Projekt kann nicht gelöscht werden.")
                return {"status": "error"}
                
            # Complete DB cleanup
            delete_project_completely(target_proj)
            
            # Workspace directory cleanup
            wd = os.path.join(str(Config.WORKSPACE_DIR), target_proj)
            if os.path.exists(wd):
                try:
                    shutil.rmtree(wd)
                except Exception as e:
                    print(f"Error removing project dir: {e}")
                    
            # Switch back to default if current project was deleted
            current = get_active_project()
            if current.lower() == target_proj.lower():
                SQLiteStateRepository().set_active_project("default")
                _post_chat("System", f"Projekt '{target_proj}' wurde vollständig gelöscht. Zurück zum Haupt-Hub (default).")
            else:
                _post_chat("System", f"Projekt '{target_proj}' wurde vollständig gelöscht.")
        else:
            SQLiteStateRepository().set_active_project(q_str or "default")
            _post_chat("System", f"Project: {q_str or 'default'}")
    return {"status": "ok"}
