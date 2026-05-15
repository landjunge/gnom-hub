"""Brainstorm Dispatcher — Hub fragt LLM im Namen der Agenten."""
import os, re, requests, threading, uuid
from datetime import datetime
from dotenv import load_dotenv
from .db import get_db, save_db
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"
def _post(sender, content):
    entry = {"id": str(uuid.uuid4()), "agent_id": "war-room", "content": content,
             "metadata": {"type": "brainstorm", "status": "open", "sender": sender},
             "timestamp": datetime.utcnow().isoformat() + "Z"}
    save_db("memory", get_db("memory") + [entry])
def _ask_llm(agent, question, context):
    if not OR_KEY: _post(agent["name"], "[Kein OPENROUTER_API_KEY]"); return
    desc = agent.get("description", "")
    role_mem = [m for m in get_db("memory") if m.get("agent_id") == agent.get("id") and m.get("type") == "role"]
    sys_prompt = role_mem[-1]["content"].replace("[SYSTEM-ROLLE] ", "") if role_mem else f"Du bist {agent['name']} ({desc}), ein KI-Agent im Gnom-Hub."
    user_msg = question
    if context: user_msg += f"\n\nBisherige Diskussion:\n{context}"
    try:
        tokens = 400 if agent.get("name") in ["Kira", "Lian", "Elara"] else 200
        r = requests.post(OR_URL, headers={"Authorization": f"Bearer {OR_KEY}"},
            json={"model": MODEL, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_msg}],
                  "max_tokens": tokens}, timeout=60)
        _post(agent["name"], r.json()["choices"][0]["message"]["content"])
    except Exception as e: _post(agent["name"], f"[Fehler: {str(e)[:80]}]")
def dispatch(question, target=None):
    """Startet LLM-Threads. target=Name → nur dieser Agent, sonst alle Online (außer Infrastruktur)."""
    exclude = ["BackupAG", "GeneralAG", "SummarizerAG"]
    online = [a for a in get_db("agents") if a.get("status") == "online" and a.get("name") not in exclude]
    if target: 
        online = [a for a in get_db("agents") if a.get("status") == "online" and a["name"].lower() == target.lower()]
    chat = [m for m in get_db("memory") if m.get("agent_id") == "war-room"]
    ctx = "\n".join(f"[{m.get('metadata',{}).get('sender','?')}] {m['content'][:120]}"
                    for m in sorted(chat, key=lambda x: x.get("timestamp",""))[-6:])
    for a in online:
        threading.Thread(target=_ask_llm, args=(a, question, ctx), daemon=True).start()
    return [a["name"] for a in online]
