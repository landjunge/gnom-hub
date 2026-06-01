import json, re
from gnom_hub.db import get_active_project, _row_to_msg
from gnom_hub.db.connection import get_db_conn
from gnom_hub.infrastructure.router.router import ask_router

def semantic_search_memories(q: str) -> list:
    project = get_active_project()
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT * FROM chat WHERE project = ? ORDER BY timestamp DESC LIMIT 50", (project,)).fetchall()
            memories = [_row_to_msg(r) for r in rows]
    except Exception:
        return []
    if not memories: return []

    candidates = [{"id": m["id"], "content": m["content"]} for m in memories]
    prompt = (
        f"Query: \"{q}\"\n\nMemories:\n{json.dumps(candidates, ensure_ascii=False)}\n\n"
        "Identify memories semantically related to the Query. Return ONLY a valid JSON list of matching IDs."
    )
    ans = ask_router(prompt, sys="You are a precise semantic search system. Return ONLY a JSON list of IDs, e.g. [\"id1\"].", agent_name="SoulAG").content
    try:
        match = re.search(r"\[.*\]", ans, re.DOTALL)
        ids = json.loads(match.group(0)) if match else json.loads(ans)
        id_map = {m["id"]: m for m in memories}
        return [id_map[mid] for mid in ids if mid in id_map]
    except Exception:
        from gnom_hub.db import search_memories
        return search_memories(q)
