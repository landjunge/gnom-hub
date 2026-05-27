# smr_retrieve.py
from gnom_hub.db import get_db_conn
from gnom_hub.smr_math import cosine_similarity

def retrieve_similar_sync(query: str, top_k: int = 8, raw: bool = False) -> list:
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT key, value, priority FROM soul_memory").fetchall()
        if not rows: return []
        scored = []
        for r in rows:
            sc = cosine_similarity(query, r["value"])
            if sc < 0.60:
                continue
            if not raw:
                priority = (r["priority"] or "medium").lower()
                if priority == "high":
                    weight = 1.3
                elif priority == "low":
                    weight = 0.7
                else:
                    weight = 1.0
                sc = sc * weight
            scored.append((sc, f"{r['key']}: {r['value']}"))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [fact for sc, fact in scored[:top_k] if sc > 0.0]
    except Exception: return []

async def retrieve_similar(query: str, top_k: int = 8, raw: bool = False) -> list:
    return retrieve_similar_sync(query, top_k, raw=raw)

async def retrieve_with_fallback(query: str, top_k: int = 8) -> list:
    return await retrieve_similar(query, top_k)
