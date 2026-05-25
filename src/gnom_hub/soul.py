import json, threading
from .db import save_soul_fact, get_relevant_facts
from .router import ask_router
class SoulAG:
    def __init__(self): self.name = "SoulAG"
    def on_message(self, message: str, sender: str):
        if sender.lower() == "user": threading.Thread(target=self._extract_and_save, args=(message,), daemon=True).start()
    def _extract_and_save(self, msg: str):
        p = f"Du bist SoulAG. Extrahiere alle wichtigen Fakten/Vorlieben/Regeln.\n\nNachricht:\n{msg}\n\nAntworte NUR mit JSON-Array [{{\"key\": \"x\", \"value\": \"y\"}}]"
        try:
            res = ask_router(p, sys="Du bist ein präziser Extraktor.", agent_name="SoulAG")
            s, e = res.find("["), res.rfind("]")
            if s != -1 and e != -1:
                for f in json.loads(res[s:e+1]): save_soul_fact(f["key"], f["value"])
        except Exception: pass
    def on_preset_change(self, preset: str):
        from .preset_service import handle_preset_change; handle_preset_change(preset)
    def inject_context(self, sys: str, msg: str, agent: str = None) -> str:
        if agent:
            from .db import get_state_value
            pr = self.get_preset_prompt((get_state_value("active_preset") or "Web Development").strip('"\''), agent.lower())
            if pr: sys = pr + "\n\n" + sys
        facts = get_relevant_facts(msg)
        return sys + "\n\n=== RELEVANTE INFORMATIONEN ===\n" + "\n".join(f"- {f}" for f in facts) if facts else sys
    def get_definitions(self) -> dict:
        from .agent_definitions import AGENT_DEFINITIONS; return AGENT_DEFINITIONS
    def get_preset_prompt(self, preset: str, agent: str) -> str:
        from .preset_service import get_preset_prompt; return get_preset_prompt(preset, agent)
soul_instance = SoulAG()
