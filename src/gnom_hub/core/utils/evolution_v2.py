# evolution_v2.py — Prompt Versioning & Auto-Rollback
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from gnom_hub.database.legacy_db import get_db_conn, add_chat_message, log_audit_event

class PromptVersion:
    def __init__(
        self,
        id: str,
        agent: str,
        base_prompt: str,
        modifications: List[str],
        performance_score: float,
        created_at: datetime,
        feedback_count: int,
        is_active: bool = False,
        parent_id: Optional[str] = None
    ):
        self.id = id
        self.agent = agent
        self.base_prompt = base_prompt
        self.modifications = modifications
        self.performance_score = performance_score
        self.created_at = created_at
        self.feedback_count = feedback_count
        self.is_active = is_active
        self.parent_id = parent_id

    def __repr__(self):
        return f"<PromptVersion id={self.id} agent={self.agent} score={self.performance_score:.2f} active={self.is_active}>"

def _row_to_version(row) -> PromptVersion:
    try:
        mods = json.loads(row["modifications"])
    except Exception:
        mods = []
    
    # Parse created_at ISO string to datetime
    try:
        dt = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)

    return PromptVersion(
        id=row["id"],
        agent=row["agent"],
        base_prompt=row["base_prompt"],
        modifications=mods,
        performance_score=float(row["performance_score"]),
        created_at=dt,
        feedback_count=int(row["feedback_count"]),
        is_active=bool(row["is_active"]),
        parent_id=row["parent_id"]
    )

def get_active_version(agent_name: str) -> Optional[PromptVersion]:
    try:
        with get_db_conn() as conn:
            row = conn.execute(
                "SELECT * FROM prompt_versions WHERE agent = ? AND is_active = 1",
                (agent_name,)
            ).fetchone()
            if row:
                return _row_to_version(row)
    except Exception as e:
        import logging
        logging.getLogger("db").error(f"[EvolutionV2] Error getting active version: {e}")
    return None

def get_version_by_id(version_id: str) -> Optional[PromptVersion]:
    try:
        with get_db_conn() as conn:
            row = conn.execute(
                "SELECT * FROM prompt_versions WHERE id = ?",
                (version_id,)
            ).fetchone()
            if row:
                return _row_to_version(row)
    except Exception as e:
        import logging
        logging.getLogger("db").error(f"[EvolutionV2] Error getting version by ID: {e}")
    return None

def create_version(agent_name: str, new_rule: str, base_prompt: Optional[str] = None) -> PromptVersion:
    # 1. Get current active version (parent)
    parent = get_active_version(agent_name)
    
    if parent:
        base = parent.base_prompt
        modifications = parent.modifications + [new_rule]
        parent_id = parent.id
    else:
        # If no parent, get base prompt from definition
        from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
        agent_def = AGENT_DEFINITIONS.get(agent_name.lower())
        if agent_def:
            base = base_prompt or agent_def.get("sys_prompt") or "Du bist ein Assistent."
        else:
            base = base_prompt or "Du bist ein Assistent."
        modifications = [new_rule]
        parent_id = None

    # 2. Compute content hash
    content = base + "\n" + "\n".join(modifications)
    version_id = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    created_at_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 3. Save to database in a transaction
    try:
        with get_db_conn() as conn:
            with conn:
                # Deactivate current versions for this agent
                conn.execute(
                    "UPDATE prompt_versions SET is_active = 0 WHERE agent = ?",
                    (agent_name,)
                )
                # Insert the new active version
                conn.execute(
                    """
                    INSERT INTO prompt_versions (
                        id, agent, base_prompt, modifications, performance_score, created_at, feedback_count, is_active, parent_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        agent_name,
                        base,
                        json.dumps(modifications),
                        1.0,  # Initial score
                        created_at_str,
                        0,    # Initial feedback count
                        1,    # is_active = True
                        parent_id
                    )
                )
    except Exception as e:
        import logging
        logging.getLogger("db").error(f"[EvolutionV2] Error saving new prompt version: {e}")

    new_version = PromptVersion(
        id=version_id,
        agent=agent_name,
        base_prompt=base,
        modifications=modifications,
        performance_score=1.0,
        created_at=datetime.now(timezone.utc),
        feedback_count=0,
        is_active=True,
        parent_id=parent_id
    )

    log_audit_event(
        agent=agent_name,
        event_type="prompt_evolution",
        details={"version_id": version_id, "parent_id": parent_id, "new_rule": new_rule}
    )
    return new_version

def use_version(version: PromptVersion):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute(
                    "UPDATE prompt_versions SET is_active = 0 WHERE agent = ?",
                    (version.agent,)
                )
                conn.execute(
                    "UPDATE prompt_versions SET is_active = 1 WHERE id = ?",
                    (version.id,)
                )
        add_chat_message(
            "default",
            "System",
            "system",
            "chat",
            f"🔄 Prompt-Rollback für **{version.agent}**: Version `{version.id}` reaktiviert."
        )
        log_audit_event(
            agent=version.agent,
            event_type="prompt_rollback",
            details={"version_id": version.id}
        )
    except Exception as e:
        import logging
        logging.getLogger("db").error(f"[EvolutionV2] Error switching version: {e}")

def update_version_score(agent_name: str, vote: str) -> Optional[PromptVersion]:
    version = get_active_version(agent_name)
    if not version:
        return None

    # Calculate new score
    new_count = version.feedback_count + 1
    vote_val = 1.0 if vote == "up" else 0.0
    new_perf_score = (version.performance_score * version.feedback_count + vote_val) / new_count

    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute(
                    "UPDATE prompt_versions SET performance_score = ?, feedback_count = ? WHERE id = ?",
                    (new_perf_score, new_count, version.id)
                )
        version.performance_score = new_perf_score
        version.feedback_count = new_count
    except Exception as e:
        import logging
        logging.getLogger("db").error(f"[EvolutionV2] Error updating version score: {e}")
        return version

    # Track: Wenn neue Evolution schlechter als vorherige -> Auto-Rollback
    if version.parent_id:
        last_good_version = get_version_by_id(version.parent_id)
        if last_good_version:
            if new_perf_score < last_good_version.performance_score * 0.95:
                add_chat_message(
                    "default",
                    "System",
                    "system",
                    "chat",
                    f"⚠️ Performance-Regression bei **{agent_name}** erkannt! (Score: {new_perf_score:.2f} < {last_good_version.performance_score:.2f} * 0.95). Führe Auto-Rollback durch."
                )
                use_version(last_good_version)
                last_good_version.is_active = True
                return last_good_version

    return version
