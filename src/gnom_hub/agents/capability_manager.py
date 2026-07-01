# capability_manager.py — Capability manager with TTL-cache
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from gnom_hub.db.connection import get_db_conn

logger = logging.getLogger(__name__)

# In-memory TTL cache: (agent_name, cap_type, resource) -> expiry_timestamp
_cache: dict = {}
_cache_lock = threading.Lock()


def request_capability(
    agent_name: str,
    cap_type: str,
    resource: str,
    granted_by: str,
    ttl_min: int = 5,
) -> bool:
    """Grant a capability to an agent with a TTL-based expiry."""
    exp = (
        datetime.now(timezone.utc) + timedelta(minutes=ttl_min)
    ).isoformat().replace("+00:00", "Z")
    try:
        with get_db_conn() as conn, conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO capabilities
                    (id, agent_name, capability_type, resource, granted_by, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    f"{agent_name}_{cap_type}_{resource}",
                    agent_name,
                    cap_type,
                    resource,
                    granted_by,
                    exp,
                ),
            )
            with _cache_lock:
                _cache[(agent_name, cap_type, resource)] = time.time() + (ttl_min * 60)
            return True
    except Exception as e:
        logger.error("Failed to grant capability %s/%s to %s: %s", cap_type, resource, agent_name, e)
        return False


def check_capability(agent_name: str, cap_type: str, resource: str) -> bool:
    """Check if an agent has an active, non-expired capability. Uses cache first."""
    key = (agent_name, cap_type, resource)

    # Fast path: check in-memory cache
    with _cache_lock:
        cached = _cache.get(key, 0)
    if cached > time.time():
        return True

    # Slow path: check database
    try:
        now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with get_db_conn() as conn:
            row = conn.execute(
                """
                SELECT expires_at FROM capabilities
                WHERE agent_name = ? AND capability_type = ? AND resource = ?
                  AND is_active = 1 AND expires_at > ?
                """,
                (agent_name, cap_type, resource, now_str),
            ).fetchone()
            if row:
                with _cache_lock:
                    _cache[key] = datetime.fromisoformat(
                        row[0].replace("Z", "+00:00")
                    ).timestamp()
                return True
    except Exception as e:
        logger.error("Capability check failed for %s/%s/%s: %s", agent_name, cap_type, resource, e)

    with _cache_lock:
        _cache.pop(key, None)

    _evict_expired()
    return False


def _evict_expired() -> int:
    """Remove expired entries from the in-memory cache. Returns count removed."""
    now = time.time()
    with _cache_lock:
        expired = [k for k, exp in _cache.items() if exp <= now]
        for k in expired:
            del _cache[k]
    return len(expired)


def cleanup_expired():
    """Deactivate expired capabilities in DB and evict expired cache entries."""
    try:
        now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with get_db_conn() as conn, conn:
            conn.execute(
                "UPDATE capabilities SET is_active = 0 WHERE expires_at <= ?",
                (now_str,),
            )
        evicted = _evict_expired()
        if evicted:
            logger.debug("Evicted %d expired cache entries", evicted)
    except Exception as e:
        logger.error("Failed to clean up expired capabilities: %s", e)
