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
