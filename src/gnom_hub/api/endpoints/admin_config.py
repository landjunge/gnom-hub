from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Dict, Optional
from gnom_hub.db.state_repo import SQLiteStateRepository as SR
from gnom_hub.db.agent_role import set_agent_role, update_agent_role_memory

router = APIRouter(prefix="/api/admin")
ROLES = {
    "de": {"general": "SYSTEM-ROLLE: GENERAL. Task-Verteilung, Koordination. Analysiere @job und verteile Aufgaben via @Name -> Aufgabe. Keine Erklärungen."}, "en": {"general": "SYSTEM ROLE: GENERAL. Task distribution and coordination. Analyze @job and distribute tasks via @Name -> Task. No explanations."}}

@router.put("/agents/{agent_id}/role")
def set_role(agent_id: str, role: str):
    if role not in ("general", "normal"): return {"error": "Invalid role"}
    a = set_agent_role(agent_id, role)
    if not a: return {"error": "Agent not found"}
    c = ROLES[SR().get_language()].get(role)
    update_agent_role_memory(a["id"], c)
    from gnom_hub.agents.role_prompt import implant
    return {"agent": a["name"], "role": role, "file": implant(a["name"], c) if c else None}

@router.get("/language")
def get_sys_language(): return {"language": SR().get_language()}

@router.post("/language")
async def set_sys_language(req: Request):
    SR().set_language((await req.json()).get("language", "en"))
    return {"status": "ok"}

class PresetPayload(BaseModel): preset: str

@router.get("/preset")
def get_preset(): return {"preset": (SR().get_value("active_preset", "Web Development") or "").strip('"\'')}

@router.post("/preset")
def set_preset(p: PresetPayload):
    from gnom_hub.core.utils.preset_service import handle_preset_change
    handle_preset_change(p.preset)
    return {"status": "ok", "preset": p.preset}

@router.get("/presets")
def get_all_presets():
    from gnom_hub.core.utils.preset_service import load_presets
    presets = load_presets()
    return {"presets": list(presets.get("prompts", {}).keys())}

class BrowserDockerPayload(BaseModel):
    use_docker: bool

@router.get("/browser_docker")
def get_browser_docker():
    return {"use_docker": SR().get_value("browser_use_docker", True)}

@router.post("/browser_docker")
def set_browser_docker(p: BrowserDockerPayload):
    SR().set_value("browser_use_docker", p.use_docker)
    return {"status": "ok", "use_docker": p.use_docker}


class GeneratePresetPayload(BaseModel):
    description: str
    answer: Optional[str] = None

SYSTEM_PRESET_GEN = """Du bist der Gnom-Hub Preset-Generator. Deine Aufgabe ist es, für den User maßgeschneiderte Teampresets (Gangs) für die 4 Worker-Agenten (coderag, researcherag, writerag, editorag) zu entwerfen.

Du musst immer ein valides JSON-Objekt zurückgeben. Es darf keinerlei Text außerhalb des JSON-Objekts existieren.

Falls die Anfrage des Users ungenau, zu kurz oder nicht eindeutig ist (z.B. weniger als 5 Worte oder sehr allgemein), setze "status" auf "clarify" und formuliere eine kurze, präzise Gegenfrage auf Deutsch in "question".
Wenn du genug Informationen hast (oder wenn das Feld 'answer' im Kontext befüllt ist), setze "status" auf "success" und generiere das vollständige Preset in "preset".

JSON-Struktur:
{
  "status": "clarify" | "success",
  "question": "...", // Nur falls status = "clarify"
  "preset": { // Nur falls status = "success"
    "name": "Name des Presets (z.B. Game Development)",
    "description": "Eine kurze Zusammenfassung (Fokus) auf Deutsch",
    "prompt_modifier": {
      "coderag": "System-Rolle für coderag (auf Englisch, z.B. SYSTEM-ROLLE: GAME DEVELOPER. Write clean PhaserJS game code...)",
      "researcherag": "System-Rolle für researcherag (auf Englisch, z.B. SYSTEM-ROLLE: GAME RESEARCHER. Research game mechanics...)",
      "writerag": "System-Rolle für writerag (auf Englisch, z.B. SYSTEM-ROLLE: GAME WRITER. Draft game dialogs and tutorials...)",
      "editorag": "System-Rolle für editorag (auf Englisch, z.B. SYSTEM-ROLLE: GAME EDITOR. Audit code, performance, assets...)"
    }
  }
}

Wichtig: Die System-Rollen der Agenten müssen auf Englisch verfasst sein, da die LLM-Modelle damit am besten arbeiten. Der Name und die Beschreibung des Presets sowie die Gegenfragen müssen auf Deutsch sein."""

@router.post("/presets/generate")
def generate_preset(p: GeneratePresetPayload):
    from gnom_hub.infrastructure.router.router import ask_router
    import json
    prompt_content = f"User will ein Preset für folgendes Thema: {p.description}"
    if p.answer:
        prompt_content += f"\nZusätzliche Details vom User: {p.answer}"
    
    eo = ask_router(prompt_content, sys=SYSTEM_PRESET_GEN, agent_name="GeneralAG")
    
    try:
        raw = eo.content.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        data = json.loads(raw)
        return data
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error parsing preset generator response: {e}. Raw content: {eo.content}")
        return {
            "status": "error",
            "message": f"Fehler beim Parsen der LLM-Antwort: {str(e)}",
            "raw": eo.content
        }


class SaveCustomPresetPayload(BaseModel):
    name: str
    description: str
    prompt_modifier: Dict[str, str]

@router.post("/presets/save_custom")
def save_custom_preset(p: SaveCustomPresetPayload):
    from gnom_hub.core.config import CONFIG_DIR
    import json
    preset_data = {
        "name": p.name,
        "description": p.description,
        "prompt_modifier": p.prompt_modifier,
        "model": {"primary": "stage_3"},
        "allowed_tools": ["coderag"]
    }
    pdir = CONFIG_DIR / "presets"
    pdir.mkdir(parents=True, exist_ok=True)
    fn = p.name.lower().replace(" ", "_") + ".json"
    preset_file = pdir / fn
    with open(preset_file, "w", encoding="utf-8") as f:
        json.dump(preset_data, f, indent=2, ensure_ascii=False)
    return {"status": "success", "file": str(preset_file)}
