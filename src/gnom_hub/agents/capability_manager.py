# capability_manager.py — capability manager with TTL-cache
import logging
import sqlite3, time; from datetime import datetime, timezone, timedelta; from gnom_hub.db.connection import get_db_conn
_cache = {}
def request_capability(agent_name: str, cap_type: str, resource: str, granted_by: str, ttl_min: int = 5) -> bool:
    exp = (datetime.now(timezone.utc) + timedelta(minutes=ttl_min)).isoformat().replace("+00:00", "Z")
    try:
        with get_db_conn() as conn, conn:
            conn.execute("""
                INSERT OR REPLACE INTO capabilities (id, agent_name, capability_type, resource, granted_by, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (f"{agent_name}_{cap_type}_{resource}", agent_name, cap_type, resource, granted_by, exp))
            _cache[(agent_name, cap_type, resource)] = time.time() + (ttl_min * 60)
            return True
    except Exception: return False
def check_capability(agent_name: str, cap_type: str, resource: str) -> bool:
    k = (agent_name, cap_type, resource)
    if _cache.get(k, 0) > time.time(): return True
    try:
        now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with get_db_conn() as conn:
            row = conn.execute("""
                SELECT expires_at FROM capabilities
                WHERE agent_name = ? AND capability_type = ? AND resource = ? AND is_active = 1 AND expires_at > ?
            """, (agent_name, cap_type, resource, now_str)).fetchone()
            if row:
                _cache[k] = datetime.fromisoformat(row[0].replace("Z", "+00:00")).timestamp()
                return True
    except Exception as e: logging.getLogger(__name__).error('Fehler in Capability-Prüfung: %s', e)
    _cache.pop(k, None); return False
def cleanup_expired():
    try:
        now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with get_db_conn() as conn, conn:
            conn.execute("UPDATE capabilities SET is_active = 0 WHERE expires_at <= ?", (now_str,))
        _cache.clear()
    except Exception as e: logging.getLogger(__name__).error('Fehler in Bereinigung abgelaufener Capabilities: %s', e)
