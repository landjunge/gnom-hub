# soul.py — SoulAG Gedächtnis & Automatische Lerneinheit
import json, threading, os, re, uuid; from .db import save_soul_fact, add_chat_message
from .soul_retrieval import retrieve_relevant_facts; from .router import ask_router; from .config import WORKSPACE_DIR
class SoulAG:
    def __init__(self): self.name = "SoulAG"
    def on_message(self, m: str, s: str):
        if s.lower() == "user" or any(x in m.lower() for x in ["abschluss", "zusammenfassung", "[write:"]): threading.Thread(target=self._ex, args=(m,), daemon=True).start()
    def _val(self, k: str, v: str) -> int:
        kl = k.lower()
        if k == "active_preset": return 2 if str(v) in ["Web Development", "Graphic Design", "Audio Production", "Video Production", "Marketing & Copy", "Research & Analysis"] else 0
        if "path" in kl or "file" in kl:
            p = os.path.realpath(os.path.join(str(WORKSPACE_DIR), str(v)) if not os.path.isabs(str(v)) else str(v))
            return 0 if not p.startswith(os.path.realpath(str(WORKSPACE_DIR))) else (1 if any(x in p.replace("\\", "/").lower() for x in ["src/gnom_hub", "config/", "scripts/", "run.sh", "index.html", ".env"]) else 2)
        return 2
    def _ex(self, m: str):
        try:
            res = ask_router(f"Extrahiere Fakten/Lektionen/Regeln.\n\nNachricht:\n{m}\n\nAntworte NUR mit JSON-Array [{{\"key\": \"x\", \"value\": \"y\"}}]", sys="Du bist Lerneffekt-Extraktor.", agent_name="SoulAG")
            s, e = res.find("["), res.rfind("]")
            if s != -1 and e != -1:
                for f in json.loads(res[s:e+1]):
                    if self._val(f.get("key",""), f.get("value","")) >= 2: save_soul_fact(f["key"], f["value"], agent="SoulAG")
        except Exception: pass
    def inject_context(self, sys: str, msg: str) -> str:
        facts = retrieve_relevant_facts(msg, top_k=8); ctx = sys + ("\n\n=== RELEVANTE INFORMATIONEN ===\n" + "\n".join(f"- {f}" for f in facts) if facts else "")
        m_ctx = [f"[Ref: @{d['name']} - Role: {d['role']} - {d['description']}]" for k, d in self.get_definitions().items() if k.lower() in [x.lower() for x in re.findall(r'@(\w+)', msg)]]
        return ctx + ("\n\n=== ERWÄHNTE AGENTEN ===\n" + "\n".join(m_ctx) if m_ctx else "")
    def get_definitions(self) -> dict: from .agent_definitions import AGENT_DEFINITIONS; return AGENT_DEFINITIONS
soul_instance = SoulAG()
def run_evolution(task: str, hist: str):
    try:
        res = ask_router(f"Analysiere Job '{task}' und den Verlauf:\n{hist}\nSchlage Verbesserungen vor. Antworte NUR im JSON-Format: [{{\"agent\": \"AgentName\", \"rule\": \"Regelinhalt\"}}]", sys="Du bist ein Agenten-Optimierer.", agent_name="GeneralAG")
        s, e = res.find("["), res.rfind("]")
        if s != -1 and e != -1:
            for f in json.loads(res[s:e+1]):
                if f.get("agent") and f.get("rule"):
                    save_soul_fact(f"evolution_{f['agent']}_{uuid.uuid4().hex[:6]}", f["rule"], agent="GeneralAG")
                    add_chat_message("default", "GeneralAG", "generalag", "chat", f"@user @SoulAG: Selbstverbesserungsregel für {f['agent']} gelernt: '{f['rule']}'")
    except Exception: pass
