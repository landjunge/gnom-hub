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
    def inject_context(self, sys: str, msg: str) -> str:
        facts = get_relevant_facts(msg)
        return sys + "\n\n=== RELEVANTE INFORMATIONEN ===\n" + "\n".join(f"- {f}" for f in facts) if facts else sys
    def get_definitions(self) -> dict:
        from .agent_definitions import AGENT_DEFINITIONS; return AGENT_DEFINITIONS
soul_instance = SoulAG()
