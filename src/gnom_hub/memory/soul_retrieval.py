# soul_retrieval.py — Semantic Retrieval via local embeddings / fallbacks
from gnom_hub.database.legacy_db import get_db_conn
from gnom_hub.memory.embeddings import get_embedder

def retrieve_relevant_facts(query: str, top_k: int = 5) -> list:
    q_clean = query.strip()
    if len(q_clean) < 25 or len(q_clean.split()) < 4:
        return []
    try:
        return get_embedder().search_sync(query, top_k)
    except Exception:
        return []

def _fetch_recent(limit: int) -> list:
    try:
        with get_db_conn() as conn:
            rows = conn.execute("""
                SELECT key, value FROM soul_memory 
                ORDER BY 
                    CASE priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 2
                    END ASC,
                    timestamp DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            return [f"{r['key']}: {r['value']}" for r in rows]
    except Exception: return []
