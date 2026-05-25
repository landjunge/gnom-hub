# soul.py — SoulAG Gedächtnis & Automatische Lerneinheit
import json, threading, os, re
from .db import save_soul_fact, add_chat_message
from .soul_retrieval import retrieve_relevant_facts
from .router import ask_router; from .config import WORKSPACE_DIR

class SoulAG:
    def __init__(self): self.name = "SoulAG"
    def on_message(self, msg: str, sender: str):
        if sender.lower() == "user" or any(x in msg.lower() for x in ["abschluss", "zusammenfassung", "[write:"]): threading.Thread(target=self._extract_and_save, args=(msg,), daemon=True).start()
    def _validate(self, k: str, v: str) -> int:
        v, k_l = str(v), k.lower()
        if k == "active_preset":
            return 2 if v in ["Web Development", "Graphic Design", "Audio Production", "Video Production", "Marketing & Copy", "Research & Analysis"] else 0
        if "path" in k_l or "file" in k_l:
            p = os.path.realpath(os.path.join(str(WORKSPACE_DIR), v)) if not os.path.isabs(v) else os.path.realpath(v)
            if not p.startswith(os.path.realpath(str(WORKSPACE_DIR))): return 0
            if any(part in p.replace("\\", "/").lower() for part in ["src/gnom_hub", "config/", "scripts/", "run.sh", "index.html", ".env"]): return 1
        return 2
    def _extract_and_save(self, msg: str):
        p = f"Du bist SoulAG. Extrahiere wichtige Fakten, Lektionen oder Regeln.\n\nNachricht:\n{msg}\n\nAntworte NUR mit JSON-Array [{{\"key\": \"x\", \"value\": \"y\"}}]"
        try:
            res = ask_router(p, sys="Du bist ein präziser Lerneffekt-Extraktor.", agent_name="SoulAG")
            s, e = res.find("["), res.rfind("]")
            if s != -1 and e != -1:
                for f in json.loads(res[s:e+1]):
                    k, v = f.get("key", ""), f.get("value", "")
                    conf = self._validate(k, v)
                    if conf >= 2: save_soul_fact(k, v, agent="SoulAG")
                    elif conf == 1: add_chat_message("default", "SoulAG", "soulag", "chat", f"@user @WatchdogAG: Unsicherheit bei Fact '{k}': '{v}'. Bitte prüfen.")
        except Exception: pass
    def inject_context(self, sys: str, msg: str) -> str:
        facts = retrieve_relevant_facts(msg, top_k=8)
        ctx = sys + ("\n\n=== RELEVANTE INFORMATIONEN ===\n" + "\n".join(f"- {f}" for f in facts) if facts else "")
        mentions = [m.lower() for m in re.findall(r'@(\w+)', msg)]
        m_ctx = [f"[Ref: @{d['name']} - Role: {d['role']} - {d['description']}]" for k, d in self.get_definitions().items() if k.lower() in mentions]
        return ctx + ("\n\n=== ERWÄHNTE AGENTEN ===\n" + "\n".join(m_ctx) if m_ctx else "")
    def get_definitions(self) -> dict: from .agent_definitions import AGENT_DEFINITIONS; return AGENT_DEFINITIONS
soul_instance = SoulAG()
