# soul_retrieval.py — Semantic Retrieval via local embeddings / fallbacks
from gnom_hub.db.legacy_db import get_db_conn
from gnom_hub.memory.embeddings import get_embedder

def retrieve_relevant_facts(query: str, agent_name: str = None, top_k: int = 5) -> list:
    q_clean = query.strip()
    if len(q_clean) < 10:
        return []
    if len(q_clean) < 25 or len(q_clean.split()) < 4:
        return _fetch_recent(agent_name, top_k)
    try:
        return get_embedder().search_sync(query, agent_name=agent_name, top_k=top_k)
    except Exception:
        return []

def _fetch_recent(agent_name: str, limit: int) -> list:
    try:
        with get_db_conn() as conn:
            if agent_name:
                if agent_name.lower() == 'generalag':
                    # GeneralAG is the coordinator and needs to see facts for all agents
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
                else:
                    rows = conn.execute("""
                        SELECT key, value FROM soul_memory 
                        WHERE LOWER(agent) = ? OR agent IS NULL OR LOWER(agent) NOT IN ('coderag', 'researcherag', 'writerag', 'editorag')
                        ORDER BY 
                            CASE priority
                                WHEN 'high' THEN 1
                                WHEN 'medium' THEN 2
                                WHEN 'low' THEN 3
                                ELSE 2
                            END ASC,
                            timestamp DESC 
                        LIMIT ?
                    """, (agent_name.lower(), limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT key, value FROM soul_memory 
                    WHERE agent IS NULL OR LOWER(agent) NOT IN ('coderag', 'researcherag', 'writerag', 'editorag')
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
