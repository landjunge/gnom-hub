"""Soul memory repository — operations for soul facts and semantic retrieval."""

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone

from gnom_hub.core.constants import MAX_SOUL_FACTS, MIN_VALUE_LENGTH
from gnom_hub.core.logger import get_logger
from gnom_hub.db.connection import get_db_conn

logger = get_logger("db")


# ── Dedup-Helpers ──────────────────────────────────────────────────────────
PRIO_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "": 0, None: 0}

_VERSION_RE = re.compile(r"^v\d+$|^version\d+$|^part\d+$|^p\d+$", re.IGNORECASE)
_KEY_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


def _normalize_key(key: str) -> str:
    """Lower-case, replace non-alphanumeric with underscores, collapse repeats.

    'Layer_Disziplin-Regel' → 'layer_disziplin_regel'.
    """
    if not key:
        return ""
    k = str(key).lower().strip()
    k = _KEY_NORMALIZE_RE.sub("_", k)
    k = _MULTI_UNDERSCORE_RE.sub("_", k)
    return k.strip("_")


def _strip_version_suffix(key: str) -> str:
    """Strip trailing version-like segments: '_v2', '_version3', '_p1', '_part2'.

    'layer_disziplin_v2' → 'layer_disziplin'
    'bafin_verb_blacklist' → 'bafin_verb_blacklist' (blacklist is not a version)
    """
    parts = key.rsplit("_", 1)
    while len(parts) == 2 and _VERSION_RE.match(parts[1]):
        key = parts[0]
        parts = key.rsplit("_", 1)
    return key


def _tokenize(value: str) -> set:
    """Lower-case word-split into a token set."""
    if not value:
        return set()
    return {t for t in re.split(r"\W+", str(value).lower()) if t}


def _jaccard(a: set, b: set) -> float:
    """Standard Jaccard similarity between two token sets."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _prio_rank(priority) -> int:
    return PRIO_RANK.get((priority or "").lower(), 0)


def _fact_score(priority: str, length: int) -> float:
    """Higher score = better candidate. priority * 0.7 + length/100 * 0.3."""
    return _prio_rank(priority) * 0.7 + (length / 100.0) * 0.3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _merge_into_existing(conn, existing_row: dict, new_row: dict) -> None:
    """Update existing_row's slot: keep the longer value, the higher priority,
    and refresh timestamp + agent. Mutates existing_row to reflect the result.
    """
    longer_value = new_row["value"] if len(new_row["value"]) >= len(existing_row["value"]) else existing_row["value"]
    higher_prio = (
        new_row["priority"]
        if _prio_rank(new_row["priority"]) >= _prio_rank(existing_row["priority"])
        else existing_row["priority"]
    )
    new_agent = new_row["agent"] or existing_row["agent"]
    conn.execute(
        "UPDATE soul_memory SET value = ?, priority = ?, timestamp = ?, agent = ? WHERE key = ?",
        (longer_value, higher_prio, new_row["timestamp"], new_agent, existing_row["key"]),
    )
    existing_row["value"] = longer_value
    existing_row["priority"] = higher_prio
    existing_row["agent"] = new_agent
    existing_row["timestamp"] = new_row["timestamp"]


def _after_write_hooks(key: str, value: str, agent: str, priority: str,
                        row_id=None, merged: bool = False) -> None:
    """Best-effort side effects: archive + (new facts only) FAISS index update."""
    try:
        from gnom_hub.db.passive_db import archive_record
        archive_record("fact", agent, f"{key}: {value}", {"priority": priority})
    except Exception as ex:
        logger.warning(f"[DB] Passive archive fact logging failed: {ex}")
    if not merged and row_id is not None:
        try:
            from gnom_hub.memory.embeddings import get_embedder
            scope = (
                agent.lower()
                if agent.lower() in ("coderag", "researcherag", "writerag", "editorag")
                else "global"
            )
            get_embedder().add_fact(str(row_id), key, value, scope=scope)
        except Exception as e:
            logger.warning(f"[DB] Failed to add fact to FAISS index: {e}")


# ── Public API ─────────────────────────────────────────────────────────────
def save_soul_fact(key: str, value: str, agent: str = "System", priority: str = "medium"):
    """Permission-checked wrapper around save_soul_fact_smart.

    Preserves the original signature so existing call-sites (memory_crud,
    soul.py, evolution, feedback) keep working unchanged.
    """
    from gnom_hub.db.chat_repo import add_chat_message
    ag = (agent or "System").strip()
    limits = {
        "active_preset": ["GeneralAG", "SoulAG", "System"],
        "approved_system_paths": ["SecurityAG", "WatchdogAG", "System"],
        "approved_security_writes": ["SecurityAG", "WatchdogAG", "System"],
        "approved_security_commands": ["SecurityAG", "WatchdogAG", "System"],
    }
    for rk, allowed in limits.items():
        if key == rk and ag not in allowed:
            add_chat_message(
                "default", "SecurityAG", "securityag", "chat",
                f"@user @WatchdogAG: Warnung! {ag} hat versucht, den Schlüssel '{key}' zu schreiben. Blockiert.",
            )
            raise PermissionError(f"Agent {ag} is not allowed to write key '{key}'")
    return save_soul_fact_smart(key, value, ag, priority)


def save_soul_fact_smart(key: str, value: str, agent: str = "System", priority: str = "medium"):
    """Smart soul-fact save with normalization, prefix/similarity dedup, and overflow cleanup.

    Behavior (in order):
      1. Reject values shorter than MIN_VALUE_LENGTH (15 chars).
      2. Normalize key (lowercase, underscores) before comparing.
      3. Exact-key match after normalization → UPDATE existing slot.
      4. Prefix match (after stripping version suffix _v2, _version1, _p3, _part1)
         → UPDATE existing slot.
      5. Jaccard(value, existing_value) ≥ 0.6 among 50 most recent → UPDATE
         highest-scored slot with the longer/better of the two values.
      6. Otherwise → INSERT new row.
      7. After INSERT, if total > MAX_SOUL_FACTS * 1.2 → trigger _periodic_cleanup
         (deferred until after the current transaction commits).

    Returns the canonical (normalized) key on success, None on rejection/error.
    """
    norm_key = _normalize_key(key)
    if not norm_key:
        logger.info(f"[Soul] Rejected empty key after normalization: original={key!r}")
        return None

    value_str = value if isinstance(value, str) else str(value or "")
    value_clean = value_str.strip()
    if len(value_clean) < MIN_VALUE_LENGTH:
        logger.info(f"[Soul] Rejected short fact: key={key} len={len(value_clean)}")
        return None

    priority_norm = (priority or "medium").lower()
    ag = (agent or "System").strip() or "System"
    ts_now = _now_iso()
    new_row = {
        "key": norm_key, "value": value_str, "priority": priority_norm,
        "timestamp": ts_now, "agent": ag,
    }

    needs_cleanup = False
    try:
        with get_db_conn() as conn:
            with conn:
                # 3. Exact-key match after normalization
                exact = conn.execute(
                    "SELECT id, key, value, priority, timestamp, agent FROM soul_memory WHERE key = ?",
                    (norm_key,),
                ).fetchone()
                if exact:
                    existing_row = {
                        "key": exact["key"], "value": exact["value"],
                        "priority": exact["priority"], "timestamp": exact["timestamp"],
                        "agent": exact["agent"],
                    }
                    _merge_into_existing(conn, existing_row, new_row)
                    logger.info(f"[Soul] Dedup: merged {norm_key} → {norm_key} (exact)")
                    _after_write_hooks(
                        existing_row["key"], existing_row["value"], ag, priority_norm,
                        row_id=exact["id"], merged=True,
                    )
                    return norm_key

                # 4. Prefix-match (version suffix)
                base_key = _strip_version_suffix(norm_key)
                if base_key != norm_key:
                    candidates = conn.execute(
                        "SELECT id, key, value, priority, timestamp, agent FROM soul_memory"
                    ).fetchall()
                    for c in candidates:
                        if c["key"] == norm_key:
                            continue
                        if _strip_version_suffix(c["key"]) == base_key:
                            existing_row = {
                                "key": c["key"], "value": c["value"],
                                "priority": c["priority"], "timestamp": c["timestamp"],
                                "agent": c["agent"],
                            }
                            _merge_into_existing(conn, existing_row, new_row)
                            logger.info(
                                f"[Soul] Dedup: merged {norm_key} → {c['key']} (prefix)"
                            )
                            _after_write_hooks(
                                c["key"], c["value"], ag, priority_norm,
                                row_id=c["id"], merged=True,
                            )
                            return c["key"]

                # 5. Value-similarity match (LIMIT 50, ORDER BY timestamp DESC)
                sim_candidates = conn.execute(
                    "SELECT id, key, value, priority, timestamp, agent FROM soul_memory"
                    " ORDER BY timestamp DESC LIMIT 50"
                ).fetchall()
                new_tokens = _tokenize(value_str)
                best_match = None
                best_sim = 0.0
                best_score = -1.0
                for c in sim_candidates:
                    sim = _jaccard(new_tokens, _tokenize(c["value"]))
                    if sim >= 0.6 and sim > best_sim:
                        best_sim = sim
                        best_match = c
                if best_match is not None:
                    # Among candidates with sim≥0.6 pick highest fact-score
                    # (re-check just to be explicit; best_match already has highest sim,
                    # but requirement says "der mit höherem Score".)
                    existing_row = {
                        "key": best_match["key"], "value": best_match["value"],
                        "priority": best_match["priority"], "timestamp": best_match["timestamp"],
                        "agent": best_match["agent"],
                    }
                    _merge_into_existing(conn, existing_row, new_row)
                    logger.info(
                        f"[Soul] Dedup: merged {norm_key} → {best_match['key']} (sim={best_sim:.2f})"
                    )
                    _after_write_hooks(
                        best_match["key"], best_match["value"], ag, priority_norm,
                        row_id=best_match["id"], merged=True,
                    )
                    return best_match["key"]

                # 6. No match → INSERT
                cursor = conn.execute(
                    "INSERT INTO soul_memory (key, value, timestamp, priority, agent) VALUES (?, ?, ?, ?, ?)",
                    (norm_key, value_str, ts_now, priority_norm, ag),
                )
                row_id = cursor.lastrowid
                logger.info(f"[Soul] New: {norm_key} (len={len(value_str)})")

                # 7. Cleanup hook (deferred — see below)
                count = conn.execute("SELECT COUNT(*) FROM soul_memory").fetchone()[0]
                if count > MAX_SOUL_FACTS * 1.2:
                    needs_cleanup = True

                _after_write_hooks(
                    norm_key, value_str, ag, priority_norm,
                    row_id=row_id, merged=False,
                )
                return norm_key
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to save soul fact: {e}")
        return None
    finally:
        # Cleanup runs AFTER the save transaction commits so we don't hold a
        # write lock while the cleanup tries to open its own connection.
        if needs_cleanup:
            logger.info(
                f"[Soul] Count > {MAX_SOUL_FACTS * 1.2:.0f}, triggering periodic cleanup"
            )
            try:
                from gnom_hub.soul.soul import _periodic_cleanup
                _periodic_cleanup()
            except Exception as ex:
                logger.warning(f"[Soul] Cleanup trigger failed: {ex}")


def add_to_soul_memory(fact: str, priority: str = "medium", agent: str = "System"):
    key = f"fact_{agent.lower()}_{uuid.uuid4().hex[:8]}"
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO soul_memory (key, value, timestamp, priority, agent) VALUES (?, ?, ?, ?, ?)",
                    (key, fact, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), priority, agent),
                )
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to add to soul memory: {e}")


def get_relevant_facts(user_message: str) -> list:
    try:
        from gnom_hub.memory.soul_retrieval import retrieve_relevant_facts
        return retrieve_relevant_facts(user_message)
    except Exception as e:
        logger.error(f"[DB] Failed to get relevant facts: {e}")
        return []