# smr_retrieve.py
from gnom_hub.db.connection import get_db_conn
from gnom_hub.memory.smr.smr_math import cosine_similarity

def retrieve_similar_sync(query: str, top_k: int = 8, agent_name: str = None, raw: bool = False) -> list:
    try:
        with get_db_conn() as conn:
            if agent_name:
                if agent_name.lower() == 'generalag':
                    rows = conn.execute(
                        "SELECT key, value, priority FROM soul_memory"
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT key, value, priority FROM soul_memory WHERE LOWER(agent) = ? OR agent IS NULL OR LOWER(agent) NOT IN ('coderag', 'researcherag', 'writerag', 'editorag')",
                        (agent_name.lower(),)
                    ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT key, value, priority FROM soul_memory WHERE agent IS NULL OR LOWER(agent) NOT IN ('coderag', 'researcherag', 'writerag', 'editorag')"
                ).fetchall()
        if not rows: return []
        scored = []
        for r in rows:
            sc = cosine_similarity(query, r["value"])
            if sc < 0.60:
                continue
            if not raw:
                p = (r["priority"] or "medium").lower()
                weight = 1.3 if p == "high" else (0.7 if p == "low" else 1.0)
                sc = sc * weight
            scored.append((sc, f"{r['key']}: {r['value']}"))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [fact for sc, fact in scored[:top_k] if sc > 0.0]
    except Exception: return []

async def retrieve_similar(query: str, top_k: int = 8, agent_name: str = None, raw: bool = False) -> list:
    return retrieve_similar_sync(query, top_k=top_k, agent_name=agent_name, raw=raw)

async def retrieve_with_fallback(query: str, top_k: int = 8, agent_name: str = None) -> list:
    similar = await retrieve_similar(query, top_k=top_k, agent_name=agent_name)
    if similar: return similar
    try:
        with get_db_conn() as conn:
            if agent_name:
                if agent_name.lower() == 'generalag':
                    rows = conn.execute(
                        "SELECT key, value FROM soul_memory ORDER BY timestamp DESC LIMIT ?",
                        (top_k,)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT key, value FROM soul_memory WHERE LOWER(agent) = ? OR agent IS NULL OR LOWER(agent) NOT IN ('coderag', 'researcherag', 'writerag', 'editorag') ORDER BY timestamp DESC LIMIT ?",
                        (agent_name.lower(), top_k)
                    ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT key, value FROM soul_memory WHERE agent IS NULL OR LOWER(agent) NOT IN ('coderag', 'researcherag', 'writerag', 'editorag') ORDER BY timestamp DESC LIMIT ?",
                    (top_k,)
                ).fetchall()
            return [f"{r['key']}: {r['value']}" for r in rows]
    except Exception: return []
