"""Brainstorm Dispatcher — Hub fragt LLM im Namen der Agenten."""
import os, re, requests, threading, uuid
from datetime import datetime
from dotenv import load_dotenv
from .db import get_db, save_db
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
DS_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DS_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
WORKSPACE_DIR = "/Users/landjunge/Documents/AG-Flega/gnom_workspace"

def _post(sender, content):
    entry = {"id": str(uuid.uuid4()), "agent_id": "war-room", "content": content,
             "metadata": {"type": "brainstorm", "status": "open", "sender": sender},
             "timestamp": datetime.utcnow().isoformat() + "Z"}
    save_db("memory", get_db("memory") + [entry])

def _ask_llm(agent, question, context):
    if not DS_KEY: _post(agent["name"], "[Kein DEEPSEEK_API_KEY]"); return
    desc = agent.get("description", "")
    role_mem = [m for m in get_db("memory") if m.get("agent_id") == agent.get("id") and m.get("type") == "role"]
    sys_prompt = role_mem[-1]["content"].replace("[SYSTEM-ROLLE] ", "") if role_mem else f"Du bist {agent['name']} ({desc}), ein KI-Agent im Gnom-Hub."
    
    # Files im Workspace auslesen
    files_str = ""
    if os.path.exists(WORKSPACE_DIR): files_str = ", ".join(os.listdir(WORKSPACE_DIR))
    
    sys_prompt += f"\n\n[WORKSPACE: AG-Flega/gnom_workspace/ | Vorhandene Dateien: {files_str}]"
    sys_prompt += "\n- Um eine Datei zu erstellen/überschreiben, antworte zwingend mit: [WRITE: dateiname.ext]...dein code/text...[/WRITE]"
    sys_prompt += "\n- Um eine Datei zu lesen, antworte zwingend mit: [READ: dateiname.ext]"
    sys_prompt += "\nDas System wird [WRITE]-Blöcke aus dem Chat löschen und auf der Festplatte speichern, um Chat-Tokens zu sparen!"
    
    user_msg = question
    if context: user_msg += f"\n\nBisherige Diskussion:\n{context}"
    try:
        tokens = 1000 if agent.get("name") in ["Kira", "Lian", "Elara"] else 500
        r = requests.post(DS_URL, headers={"Authorization": f"Bearer {DS_KEY}"},
            json={"model": MODEL, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_msg}],
                  "max_tokens": tokens}, timeout=60)
        
        answer = r.json()["choices"][0]["message"]["content"]
        
        # --- WRITE LOGIC ---
        write_matches = re.finditer(r"\[WRITE:\s*(.*?)\](.*?)\[/WRITE\]", answer, re.DOTALL)
        for match in write_matches:
            fname = match.group(1).strip()
            content = match.group(2).strip()
            try:
                os.makedirs(WORKSPACE_DIR, exist_ok=True)
                with open(os.path.join(WORKSPACE_DIR, fname), "w") as f: f.write(content)
                answer = answer.replace(match.group(0), f"[System: Datei '{fname}' wurde erfolgreich im Workspace gespeichert.]")
            except Exception as e:
                answer = answer.replace(match.group(0), f"[System-Fehler beim Speichern von {fname}: {e}]")
                
        # --- READ LOGIC ---
        read_matches = re.finditer(r"\[READ:\s*(.*?)\]", answer)
        for match in read_matches:
            fname = match.group(1).strip()
            p = os.path.join(WORKSPACE_DIR, fname)
            if os.path.exists(p):
                with open(p, "r") as f:
                    file_content = f.read()[:2000] # Truncate to save tokens
                _post("System", f"Inhalt von {fname}:\n{file_content}\n[...]")
            else:
                _post("System", f"Datei {fname} nicht gefunden!")
                
        _post(agent["name"], answer)
    except Exception as e: _post(agent["name"], f"[Fehler: {str(e)[:80]}]")
def dispatch(question, target=None):
    """Startet LLM-Threads. target=Name → nur dieser Agent, sonst alle Online (außer Infrastruktur)."""
    exclude = ["BackupAG", "GeneralAG", "SummarizerAG"]
    online = [a for a in get_db("agents") if a.get("status") == "online" and a.get("name") not in exclude]
    if target: 
        online = [a for a in get_db("agents") if a.get("status") == "online" and a["name"].lower() == target.lower()]
    chat = [m for m in get_db("memory") if m.get("agent_id") == "war-room"]
    from .zwc_soul import strip_zwc
    ctx = "\n".join(f"[{m.get('metadata',{}).get('sender','?')}] {strip_zwc(m['content'])[:120]}"
                    for m in sorted(chat, key=lambda x: x.get("timestamp",""))[-6:])
    for a in online:
        threading.Thread(target=_ask_llm, args=(a, question, ctx), daemon=True).start()
    return [a["name"] for a in online]
