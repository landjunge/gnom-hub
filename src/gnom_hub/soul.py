from .db import save_soul_fact, get_relevant_facts
from .router import ask_router
import json
import threading

class SoulAG:
    def __init__(self):
        self.name = "SoulAG"
    
    def on_message(self, message: str, sender: str):
        """Wird bei jeder neuen Nachricht aufgerufen"""
        if sender.lower() == "user":
            # Da wir in FastAPI sync laufen, lagern wir den langsamen LLM-Call in einen Thread aus,
            # damit die API nicht blockiert, während SoulAG extrahiert.
            threading.Thread(target=self._extract_and_save, args=(message,), daemon=True).start()
    
    def _extract_and_save(self, message: str):
        """Nutzt LLM um wichtige Informationen zu extrahieren"""
        prompt = f"""Du bist SoulAG. Extrahiere aus der folgenden Nachricht alle wichtigen Fakten, Regeln, Vorlieben und Zugangsdaten.

Nachricht:
{message}

Antworte NUR mit einem JSON-Array. Beispiel:
[{{"key": "db_password", "value": "geheim123"}}, {{"key": "preferred_style", "value": "kein Tailwind"}}]"""

        try:
            # ask_router liefert einen String zurück, den wir parsen
            response_text = ask_router(prompt, sys="Du bist ein präziser Extraktor.", agent_name="SoulAG")
            
            s = response_text.find("[")
            e = response_text.rfind("]")
            if s != -1 and e != -1:
                facts = json.loads(response_text[s:e+1])
                
                if isinstance(facts, list):
                    for fact in facts:
                        if isinstance(fact, dict) and "key" in fact and "value" in fact:
                            save_soul_fact(fact["key"], fact["value"])
        except Exception:
            pass  # Silent fail - SoulAG darf nie das System stören
    
    def inject_context(self, system_prompt: str, user_message: str) -> str:
        """Injiziert relevante Informationen unsichtbar in den System-Prompt"""
        facts = get_relevant_facts(user_message)
        
        if not facts:
            return system_prompt
            
        injection = "\n\n=== RELEVANTE INFORMATIONEN AUS MEINEM GEDÄCHTNIS ===\n"
        for fact in facts:
            injection += f"- {fact}\n"
            
        return system_prompt + injection

soul_instance = SoulAG()
