from fastapi import APIRouter
from pydantic import BaseModel
from gnom_hub.db.state_repo import SQLiteStateRepository

router = APIRouter(prefix="/api/admin")

class BakeRequest(BaseModel):
    name: str
    template: str = "chat"
    embed_api_key: bool = True
    preset_file: str = ""

@router.post("/bake")
def bake_supergnom_endpoint(req: BakeRequest):
    import os, json
    from gnom_hub.core.config import PROJECT_ROOT, CONFIG_DIR
    try:
        if req.preset_file:
            preset_path = CONFIG_DIR / "presets" / req.preset_file
            if preset_path.exists():
                data = json.loads(preset_path.read_text(encoding="utf-8"))
                from gnom_hub.db import set_state_value
                if data.get("agent_settings"):
                    set_state_value("agent_settings", data["agent_settings"])
        from gnom_hub.core.utils.compiler import bake_supergnom
        from pathlib import Path
        path = bake_supergnom(req.name, req.template)
        dist_path = Path(path)
        if req.embed_api_key:
            key = os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("OPENROUTER_KEY_FREE_1","")
            if key:
                env_file = dist_path / "config" / ".env"
                with open(env_file, "a", encoding="utf-8") as f:
                    f.write(f"\nDEEPSEEK_API_KEY={key}\n")
                keys_file = dist_path / "keys.txt"
                with open(keys_file, "w", encoding="utf-8") as f:
                    f.write(f"DEEPSEEK_API_KEY={key}\n")
        return {"status": "ok", "path": str(dist_path)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.post("/clean-all")
def clean_all():
    """Alles zurücksetzen: DB, Tokens, Workspace, Logs. Dann Neustart."""
    import os, shutil
    from gnom_hub.db.connection import get_db_connection
    from gnom_hub.db.passive_db import get_passive_conn
    from gnom_hub.core.config import CONFIG_DIR, WORKSPACE_DIR, PROJECT_ROOT

    conn = get_db_connection()
    # Alle nicht-essentiellen Tabellen leeren
    for tbl in ['chat','audit_log','prompt_versions','capabilities','showbox_presentations',
                'explainable_outputs','agent_messages','swarm_callbacks','agent_capabilities',
                'workflows','workflow_tasks','soul_memory','token_budget_logs','token_budget_alerts']:
        try: conn.execute(f'DELETE FROM {tbl}')
        except: pass
    # State reset
    conn.execute("DELETE FROM state WHERE key NOT IN ('active_project','language','active_showbox','enable_confirmations')")
    conn.execute("UPDATE agents SET status='online', circuit_state='CLOSED', consecutive_failures=0")
    conn.commit()
    conn.close()

    # Token-File löschen
    for token_file in list(CONFIG_DIR.glob('.gnom-hub-tokens*.json')):
        try: token_file.unlink()
        except: pass

    # Passive DB
    try:
        pconn = get_passive_conn()
        for t in pconn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            try: pconn.execute(f'DELETE FROM {t["name"]}')
            except: pass
        pconn.commit()
        pconn.close()
    except: pass

    # Workspace leeren
    wd = os.path.join(str(WORKSPACE_DIR), 'default')
    if os.path.exists(wd):
        for item in os.listdir(wd):
            item_path = os.path.join(wd, item)
            try:
                if os.path.isdir(item_path): shutil.rmtree(item_path)
                else: os.remove(item_path)
            except: pass

    # Neustart in 3s (nachdem die Antwort zurück ist)
    import threading
    def delayed_restart():
        import time; time.sleep(3)
        from gnom_hub.infrastructure.process.process_manager import restart_hub
        restart_hub()
    threading.Thread(target=delayed_restart, daemon=True).start()

    return {"status": "cleaned", "msg": "Alles geleert. Hub startet neu in 3s."}

class ToolDef(BaseModel):
    name: str
    description: str = ""
    method: str = "GET"
    path: str = ""

@router.get("/tools")
def list_tools():
    return SQLiteStateRepository().get_value("tools", [])

@router.post("/tools")
def register_tool(t: ToolDef):
    repo = SQLiteStateRepository()
    tools = [x for x in repo.get_value("tools", []) if x["name"] != t.name] + [t.dict()]
    repo.set_value("tools", tools)
    return {"registered": t.name}

@router.delete("/tools/{name}")
def remove_tool(name: str):
    repo = SQLiteStateRepository()
    tools = [t for t in repo.get_value("tools", []) if t["name"] != name]
    repo.set_value("tools", tools)
    return {"removed": name}
