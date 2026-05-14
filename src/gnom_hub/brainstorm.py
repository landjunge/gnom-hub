"""Brainstorm Dispatcher — Hub fragt LLM im Namen der Agenten."""
import threading, uuid, os, re, requests
from datetime import datetime
from .db import get_db, save_db

OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-chat-v3-0324"

def _post(sender, content):
    entry = {"id": str(uuid.uuid4()), "agent_id": "war-room", "content": content,
             "metadata": {"type": "brainstorm", "status": "open", "sender": sender},
             "timestamp": datetime.utcnow().isoformat() + "Z"}
    save_db("memory", get_db("memory") + [entry])

def _ask_llm(agent, question, context):
    if not OR_KEY: _post(agent["name"], "[Kein OPENROUTER_API_KEY]"); return
    desc = agent.get("description", "")
    prompt = f"Du bist {agent['name']} ({desc}), ein KI-Agent im Gnom-Hub.\n{question}"
    if context: prompt += f"\n\nBisherige Diskussion:\n{context}"
    try:
        r = requests.post(OR_URL, headers={"Authorization": f"Bearer {OR_KEY}"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 1000}, timeout=60)
        _post(agent["name"], r.json()["choices"][0]["message"]["content"])
    except Exception as e: _post(agent["name"], f"[Fehler: {str(e)[:80]}]")

def dispatch(question, target=None):
    """Startet LLM-Threads. target=Name → nur dieser Agent, sonst alle Online."""
    online = [a for a in get_db("agents") if a.get("status") == "online"]
    if target: online = [a for a in online if a["name"].lower() == target.lower()]
    chat = [m for m in get_db("memory") if m.get("agent_id") == "war-room"]
    ctx = "\n".join(f"[{m.get('metadata',{}).get('sender','?')}] {m['content'][:120]}"
                    for m in sorted(chat, key=lambda x: x.get("timestamp",""))[-6:])
    for a in online:
        threading.Thread(target=_ask_llm, args=(a, question, ctx), daemon=True).start()
    return [a["name"] for a in online]
