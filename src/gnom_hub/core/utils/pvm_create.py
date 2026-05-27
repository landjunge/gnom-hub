# pvm_create.py
import json
import hashlib
from datetime import datetime, timezone
from gnom_hub.database.legacy_db import get_db_conn
from gnom_hub.evolution.evolution_v2 import PromptVersion

def create_version(agent: str, prompt: str, modifications: list) -> PromptVersion:
    parent_id = None
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT id FROM prompt_versions WHERE agent = ? AND is_active = 1", (agent,)).fetchone()
            if row: parent_id = row["id"]
    except Exception: pass

    content = prompt + "\n" + "\n".join(modifications)
    version_id = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    created_at_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("UPDATE prompt_versions SET is_active = 0 WHERE agent = ?", (agent,))
                conn.execute("""
                    INSERT OR REPLACE INTO prompt_versions (id, agent, base_prompt, modifications, performance_score, created_at, feedback_count, is_active, parent_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (version_id, agent, prompt, json.dumps(modifications), 1.0, created_at_str, 0, 0, parent_id))
    except Exception: pass

    return PromptVersion(id=version_id, agent=agent, base_prompt=prompt, modifications=modifications, performance_score=1.0, created_at=datetime.now(timezone.utc), feedback_count=0, is_active=False, parent_id=parent_id)
