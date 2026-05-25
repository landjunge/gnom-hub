# smr_retrieve.py
from gnom_hub.db import get_db_conn
from gnom_hub.smr_math import cosine_similarity

async def retrieve_similar(query: str, top_k: int = 8) -> list:
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT key, value FROM soul_memory").fetchall()
        if not rows: return []
        scored = []
        for r in rows:
            sc = cosine_similarity(query, r["value"])
            scored.append((sc, f"{r['key']}: {r['value']}"))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [fact for sc, fact in scored[:top_k] if sc > 0.0]
    except Exception: return []

async def retrieve_with_fallback(query: str, top_k: int = 8) -> list:
    similar = await retrieve_similar(query, top_k)
    if similar: return similar
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT key, value FROM soul_memory ORDER BY timestamp DESC LIMIT ?", (top_k,)).fetchall()
            return [f"{r['key']}: {r['value']}" for r in rows]
    except Exception: return []
