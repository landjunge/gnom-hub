import json, threading
from .db import save_soul_fact, get_relevant_facts
from .router import ask_router

class SoulAG:
    def __init__(self):
        self.name = "SoulAG"
    
    def on_message(self, message: str, sender: str):
        if sender.lower() == "user":
            threading.Thread(target=self._extract_and_save, args=(message,), daemon=True).start()
    
    def _extract_and_save(self, message: str):
        p = f"Du bist SoulAG. Extrahiere aus der folgenden Nachricht alle wichtigen Fakten, Regeln, Vorlieben und Zugangsdaten.\n\nNachricht:\n{message}\n\nAntworte NUR mit einem JSON-Array. Beispiel:\n[{{\"key\": \"preferred_style\", \"value\": \"kein Tailwind\"}}]"
        try:
            res = ask_router(p, sys="Du bist ein präziser Extraktor.", agent_name="SoulAG")
            s, e = res.find("["), res.rfind("]")
            if s != -1 and e != -1:
                for f in json.loads(res[s:e+1]):
                    if isinstance(f, dict) and "key" in f and "value" in f:
                        save_soul_fact(f["key"], f["value"])
        except Exception: pass

    def on_preset_change(self, preset: str):
        from .preset_service import handle_preset_change
        handle_preset_change(preset)

    def inject_context(self, sys_prompt: str, msg: str) -> str:
        facts = get_relevant_facts(msg)
        if not facts: return sys_prompt
        return sys_prompt + "\n\n=== RELEVANTE INFORMATIONEN ===\n" + "\n".join(f"- {f}" for f in facts)

soul_instance = SoulAG()
