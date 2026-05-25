# soul_retrieval.py — Keyword-Matching & Jaccard Ähnlichkeits-Retrieval
import re, datetime
from .db import get_db_conn

def _tokenize(text: str) -> set:
    return set(re.findall(r'\w+', (text or '').lower()))

def retrieve_relevant_facts(query: str, top_k: int = 5) -> list:
    q_tokens = _tokenize(query)
    if not q_tokens: return _fetch_recent(top_k)
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT key, value FROM soul_memory").fetchall()
        scored = []
        for r in rows:
            k, v = r['key'], r['value']
            k_tokens, v_tokens = _tokenize(k), _tokenize(v)
            all_tokens = k_tokens | v_tokens
            overlap = q_tokens & all_tokens
            if overlap:
                score = (len(q_tokens & k_tokens) * 2.0 + len(q_tokens & v_tokens)) / len(q_tokens)
                scored.append((score, f"{k}: {v}"))
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            return [x[1] for x in scored[:top_k]]
    except Exception: pass
    return _fetch_recent(top_k)

def _fetch_recent(limit: int) -> list:
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT key, value FROM soul_memory ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            return [f"{r['key']}: {r['value']}" for r in rows]
    except: return []
