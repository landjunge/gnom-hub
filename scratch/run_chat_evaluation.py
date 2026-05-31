# run_chat_evaluation.py — Chat-Verlauf analysieren und Prompt-Evolution triggern
import sys
import json
import os
from pathlib import Path

# Set up project path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from gnom_hub.db.legacy_db import get_chat_history, get_active_project, add_chat_message, save_soul_fact
from gnom_hub.infrastructure.router.router import ask_router
from gnom_hub.core.utils.evolution_v2 import create_version

def evaluate_chat():
    proj = get_active_project() or "default"
    print(f"Lese Chat-Historie für Projekt '{proj}'...")
    
    history = get_chat_history(proj, limit=50)
    if not history:
        print("Kein Chat-Verlauf gefunden.")
        return
        
    # Format chat history
    formatted_lines = []
    for msg in reversed(history):
        sender = msg.get("sender", "Unbekannt")
        content = msg.get("content", "").strip()
        # Clean thoughts / showbox tags for brevity
        content_clean = content
        import re
        content_clean = re.sub(r"<think>[\s\S]*?</think>", "", content_clean)
        content_clean = re.sub(r"<SHOWBOX[\s\S]*?</SHOWBOX>", "", content_clean)
        content_clean = content_clean.strip()
        if content_clean:
            formatted_lines.append(f"{sender}: {content_clean}")
            
    chat_log = "\n".join(formatted_lines)
    
    print("\n--- Analysierter Chat-Verlauf ---")
    print(chat_log[:1000] + ("\n... [TRUNCATED]" if len(chat_log) > 1000 else ""))
    print("---------------------------------")
    
    sys_prompt = (
        "Du bist der Swarm-Optimierer für Gnom-Hub. Analysiere den Chatverlauf und schlage Optimierungen "
        "oder Verhaltensregeln vor, um die Zusammenarbeit der Agenten, die Systemsicherheit und das User-Erlebnis zu verbessern."
    )
    
    user_prompt = (
        f"Hier ist der aktuelle Chatverlauf:\n\"\"\"\n{chat_log}\n\"\"\"\n\n"
        "Extrahiere aus diesem Verlauf konkrete Verhaltensregeln für die Agenten (z.B. CoderAG, GeneralAG, WriterAG, ResearcherAG, EditorAG, WatchdogAG).\n"
        "Fokus:\n"
        "- Was wünscht sich der User bezüglich Git-Aktionen (z.B. push, commit)?\n"
        "- Wie sollen Blockaden oder Berechtigungen kommuniziert werden?\n"
        "- Welche Interaktionsmuster müssen korrigiert werden?\n\n"
        "Antworte AUSSCHLIESSLICH im folgenden JSON-Format (keine Markdown-Formatierung, kein Einleitungstext):\n"
        "[\n"
        "  {\"agent\": \"AgentName\", \"rule\": \"Regelinhalt in deutscher Sprache\"}\n"
        "]\n"
        "Falls keine neuen Regeln gelernt werden müssen, antworte mit []"
    )
    
    print("Sende Analyse-Anfrage an LLM...")
    response = ask_router(user_prompt, sys=sys_prompt, agent_name="GeneralAG").content
    print("Antwort empfangen:", response)
    
    # Parse rules
    try:
        s, e = response.find("["), response.rfind("]")
        if s == -1 or e == -1:
            print("Keine gültige JSON-Liste in der Antwort gefunden.")
            return
            
        rules = json.loads(response[s:e+1])
        if not rules:
            print("Keine neuen Regeln extrahiert.")
            return
            
        print(f"\nEs wurden {len(rules)} Regeln gelernt:")
        for r in rules:
            agent = r.get("agent")
            rule = r.get("rule")
            if agent and rule:
                print(f"- [{agent}] {rule}")
                # Save rule to soul memory
                import uuid
                fact_key = f"evolution_{agent}_{uuid.uuid4().hex[:6]}"
                save_soul_fact(fact_key, rule, agent="GeneralAG")
                
                # Create a new version of the prompt
                try:
                    create_version(agent, rule)
                    print(f"  -> Neue Prompt-Version für {agent} erstellt!")
                except Exception as ex:
                    print(f"  -> Fehler beim Erstellen der Prompt-Version für {agent}: {ex}")
                
                # Post to chat
                add_chat_message(proj, "GeneralAG", "generalag", "chat", f"@user @SoulAG: Regel für **{agent}** gelernt: '{rule}'")
                
    except Exception as ex:
        print(f"Fehler beim Verarbeiten der Antwort: {ex}")

if __name__ == "__main__":
    evaluate_chat()
