from fastapi import APIRouter
from datetime import datetime
import uuid
from .db import get_db, save_db
from .routes_nudge import nudge
from pydantic import BaseModel
router = APIRouter()

class ChatMsg(BaseModel):
    content: str
    sender: str = "user"

@router.post("/api/chat")
def post_chat(msg: ChatMsg):
    is_bs = msg.content.startswith("@bs")
    entry = {"id": str(uuid.uuid4()), "agent_id": "war-room", "content": msg.content,
             "metadata": {"type": "brainstorm" if is_bs else "chat", "status": "open", "sender": msg.sender},
             "timestamp": datetime.utcnow().isoformat() + "Z"}
    save_db("memory", get_db("memory") + [entry])
    online = [a for a in get_db("agents") if a.get("status") == "online"]
    nudged = [a["name"] for a in online if nudge(a["id"])]
    return {"status": "broadcasted", "count": len(nudged), "nudged": nudged, "mode": "brainstorm" if is_bs else "task"}

@router.get("/api/chat")
def get_chat(limit: int = 50):
    msgs = [m for m in get_db("memory") if m.get("agent_id") == "war-room"]
    return sorted(msgs, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
