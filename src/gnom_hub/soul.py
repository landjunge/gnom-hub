# soul.py — SoulAG Gedächtnis & Automatische Lerneinheit
import json, threading, os, re, uuid; from .db import save_soul_fact, add_chat_message
from .soul_retrieval import retrieve_relevant_facts; from .router import ask_router; from .config import WORKSPACE_DIR
class SoulAG:
    def __init__(self):
        self.name = "SoulAG"
        self._injections = {}
    def on_message(self, m: str, s: str):
        if s.lower() == "user" or any(x in m.lower() for x in ["abschluss", "zusammenfassung", "[write:"]): threading.Thread(target=self._ex, args=(m,), daemon=True).start()
    def _val(self, k: str, v: str) -> int:
        kl = k.lower()
        if k == "active_preset": return 2 if str(v) in ["Web Development", "Graphic Design", "Audio Production", "Video Production", "Marketing & Copy", "Content Creation", "Research & Analysis"] else 0
        if "path" in kl or "file" in kl:
            p = os.path.realpath(os.path.join(str(WORKSPACE_DIR), str(v)) if not os.path.isabs(str(v)) else str(v))
            return 0 if not p.startswith(os.path.realpath(str(WORKSPACE_DIR))) else (1 if any(x in p.replace("\\", "/").lower() for x in ["src/gnom_hub", "config/", "scripts/", "run.sh", "index.html", ".env"]) else 2)
        return 2
    def _ex(self, m: str):
        try:
            res = ask_router(f"Extrahiere Fakten.\nNachricht:\n{m}\nAntworte NUR mit JSON [{{\"key\": \"x\", \"value\": \"y\"}}]", sys="Du bist Lerneffekt-Extraktor.", agent_name="SoulAG")
            s, e = res.find("["), res.rfind("]")
            if s != -1 and e != -1: [save_soul_fact(f.get("key",""), f.get("value",""), agent="SoulAG") for f in json.loads(res[s:e+1]) if self._val(f.get("key",""), f.get("value","")) >= 2]
        except Exception: pass
    def inject_context(self, sys: str, msg: str, agent_name: str = None) -> str:
        facts = retrieve_relevant_facts(msg, top_k=8)
        if agent_name and facts:
            for f in facts:
                key = (agent_name.lower(), f)
                self._injections[key] = self._injections.get(key, 0) + 1
                if self._injections[key] == 2:
                    try:
                        add_chat_message("default", "SoulAG", "soulag", "chat", f"@user @{agent_name}: [HINWEIS] Ich habe die Information '{f}' bereits zum zweiten Mal im Hintergrund eingespeist. Bitte darauf achten!")
                    except Exception: pass
        ctx = sys + ("\n\n=== RELEVANTE INFORMATIONEN ===\n" + "\n".join(f"- {f}" for f in facts) if facts else "")
        m_ctx = [f"[Ref: @{d['name']} - Role: {d['role']} - {d['description']}]" for k, d in self.get_definitions().items() if k.lower() in [x.lower() for x in re.findall(r'@(\w+)', msg)]]
        return ctx + ("\n\n=== ERWÄHNTE AGENTEN ===\n" + "\n".join(m_ctx) if m_ctx else "")
    def get_definitions(self) -> dict: from .agent_definitions import AGENT_DEFINITIONS; return AGENT_DEFINITIONS
soul_instance = SoulAG()
def _save_rules(res: str, prefix=""):
    s, e = res.find("["), res.rfind("]")
    if s != -1 and e != -1:
        try:
            rules = json.loads(res[s:e+1])
            for f in rules:
                if f.get("agent") and f.get("rule"):
                    agent_name = f["agent"]
                    rule_text = prefix + f["rule"]
                    save_soul_fact(f"evolution_{agent_name}_{uuid.uuid4().hex[:6]}", rule_text, agent="GeneralAG")
                    add_chat_message("default", "GeneralAG", "generalag", "chat", f"@user @SoulAG: Regel für {agent_name} gelernt: '{f['rule']}'")
                    try:
                        from gnom_hub.evolution_v2 import create_version
                        create_version(agent_name, rule_text)
                    except Exception as ex:
                        import logging
                        logging.getLogger("db").error(f"[Soul] Failed to create prompt version for {agent_name}: {ex}")
        except Exception as ex:
            import logging
            logging.getLogger("db").error(f"[Soul] Failed to parse and save rules: {ex}")

def run_evolution(task: str, hist: str):
    try: _save_rules(ask_router(f"Analysiere '{task}' und den Verlauf:\n{hist}\nSchlage Verbesserungen vor. Antworte NUR im JSON-Format: [{{\"agent\": \"AgentName\", \"rule\": \"Regelinhalt\"}}]", sys="Du bist Optimierer.", agent_name="GeneralAG"))
    except Exception: pass

def handle_user_feedback(vote: str, comment: str):
    save_soul_fact(f"feedback_{uuid.uuid4().hex[:6]}", f"Vote: {vote} | {comment}", agent="User")
    add_chat_message("default", "System", "system", "chat", f"@user Feedback: {vote} | {comment}")
    
    try:
        from gnom_hub.evolution_v2 import update_version_score
        from gnom_hub.db import get_chat_history
        
        active_agents = set()
        history = get_chat_history(limit=40)
        for msg in history:
            sender = msg.get("sender")
            if sender and sender.lower() not in ["user", "system", "generalag", "soulag", "watchdogag", "securityag"]:
                from gnom_hub.agent_definitions import AGENT_DEFINITIONS
                for ag_key, ag_def in AGENT_DEFINITIONS.items():
                    if ag_def["name"].lower() == sender.lower():
                        active_agents.add(ag_def["name"])
        
        if not active_agents:
            active_agents = {"CoderAG", "WriterAG", "ResearcherAG", "EditorAG"}
            
        for agent in active_agents:
            update_version_score(agent, vote)
    except Exception as ex:
        import logging
        logging.getLogger("db").error(f"[Soul] Failed to update version scores: {ex}")

    if comment.strip():
        try: _save_rules(ask_router(f"User-Feedback: '{comment}'. Schlage Verbesserungen vor. Antworte NUR im JSON-Format: [{{\"agent\": \"AgentName\", \"rule\": \"Regelinhalt\"}}]", sys="Du bist Optimierer.", agent_name="GeneralAG"), "User-Feedback: ")
        except Exception: pass
