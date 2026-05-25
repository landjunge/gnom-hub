# soul_retrieval.py — Semantic Reranking & Retrieval via LLM
import json
from .db import get_db_conn; from .router import ask_router

def retrieve_relevant_facts(query: str, top_k: int = 5) -> list:
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT key, value FROM soul_memory").fetchall()
        if not rows: return []
        facts = [f"{r['key']}: {r['value']}" for r in rows]
        p = f"Query: {query}\nFacts:\n" + "\n".join(f"{i}: {f}" for i, f in enumerate(facts)) + f"\nNenne Indizes der max {top_k} semantisch relevantesten Fakten als JSON-Liste, z.B. [0, 2]."
        res = ask_router(p, sys="Du bist ein präziser semantischer Suchfilter.", agent_name="SoulAG")
        s, e = res.find("["), res.rfind("]")
        if s != -1 and e != -1:
            return [facts[int(i)] for i in json.loads(res[s:e+1]) if 0 <= int(i) < len(facts)]
    except Exception: pass
    return _fetch_recent(top_k)

def _fetch_recent(limit: int) -> list:
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT key, value FROM soul_memory ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            return [f"{r['key']}: {r['value']}" for r in rows]
    except: return []
