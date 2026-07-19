"""security_permissions-DB: writer + reader for SecurityAG grants.

Implementiert die zwei Kernrollen aus SecurityAG-Identity v7.3:
- Rolle 1: "Verzeichnisse freigeben" → grant_permission()
- Rolle 2: "Dateien freigeben"      → grant_permission() mit type='file'

Enforcement (ab 2026-07): path_validator._safe ruft check_permission()
für Pfade außerhalb des User-Workspace auf. Directory-Grants matchen
per Prefix (realpath); File-Grants exakt.
"""
import os
import time

from gnom_hub.db.connection import get_db_conn

VALID_RESOURCE_TYPES = {"directory", "file", "tool"}


def grant_permission(
    resource_type: str,
    resource_path: str,
    granted_to: str,
    granted_by: str = "SecurityAG",
    reason: str = "",
    expires_at: str | None = None,
) -> int:
    """Schreibt eine Freigabe in security_permissions. Returns rowid.

    Idempotent: doppelte (resource_path, granted_to, is_active=1)
    wird als UPDATE behandelt (SecurityAG kann mehrfach granted
    ohne Duplikate zu erzeugen).
    """
    if resource_type not in VALID_RESOURCE_TYPES:
        raise ValueError(
            f"resource_type muss eines von {sorted(VALID_RESOURCE_TYPES)} sein, "
            f"nicht {resource_type!r}"
        )
    if not resource_path or not resource_path.strip():
        raise ValueError("resource_path darf nicht leer sein")
    if not granted_to or not granted_to.strip():
        raise ValueError("granted_to darf nicht leer sein")
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with get_db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE security_permissions "
            "SET reason=?, expires_at=?, granted_by=? "
            "WHERE resource_path=? AND granted_to=? AND is_active=1",
            (reason, expires_at, granted_by, resource_path, granted_to),
        )
        if cur.rowcount == 0:
            cur.execute(
                "INSERT INTO security_permissions "
                "(resource_type, resource_path, granted_to, granted_by, "
                " reason, created_at, expires_at, is_active) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                (
                    resource_type,
                    resource_path,
                    granted_to,
                    granted_by,
                    reason,
                    created_at,
                    expires_at,
                ),
            )
        conn.commit()
        return cur.lastrowid or 0


def revoke_permission(resource_path: str, granted_to: str) -> int:
    """Deaktiviert eine Freigabe (is_active=0). Returns Anzahl betroffener Zeilen."""
    with get_db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE security_permissions SET is_active=0 "
            "WHERE resource_path=? AND granted_to=? AND is_active=1",
            (resource_path, granted_to),
        )
        conn.commit()
        return cur.rowcount


def check_permission(granted_to: str, resource_path: str) -> bool:
    """True wenn granted_to eine aktive (nicht-abgelaufene) Freigabe hat.

    granted_to='all' matcht jeden Agenten (Wildcard-Freigabe).
    Abgelaufene Freigaben (expires_at in Vergangenheit) zählen als inaktiv.

    Match-Regeln (realpath, Symlink-sicher):
    - file / tool: exakter Pfad-Match (resource_path == grant)
    - directory: Grant-Pfad ist Prefix des Ziels (inkl. exakt der Dir selbst)
    - zusätzlich: exakter String-Match auf resource_path (Rückwärtskompat
      zu älteren Tests und Grants ohne realpath-Normalisierung)
    """
    if not granted_to or not resource_path:
        return False
    # Canonical form for path comparison; keep raw for legacy exact match.
    try:
        target_real = os.path.realpath(os.path.expanduser(resource_path))
    except (OSError, ValueError):
        target_real = resource_path

    with get_db_conn() as conn:
        cur = conn.cursor()
        # Fast path: exact string match (legacy + tool grants)
        cur.execute(
            "SELECT 1 FROM security_permissions "
            "WHERE granted_to IN (?, 'all') "
            "AND resource_path=? AND is_active=1 "
            "AND (expires_at IS NULL OR expires_at > datetime('now')) "
            "LIMIT 1",
            (granted_to, resource_path),
        )
        if cur.fetchone() is not None:
            return True

        # Directory prefix + realpath exact for file grants
        cur.execute(
            "SELECT resource_type, resource_path FROM security_permissions "
            "WHERE granted_to IN (?, 'all') AND is_active=1 "
            "AND (expires_at IS NULL OR expires_at > datetime('now'))",
            (granted_to,),
        )
        for rtype, gpath in cur.fetchall():
            if not gpath:
                continue
            try:
                g_real = os.path.realpath(os.path.expanduser(gpath))
            except (OSError, ValueError):
                g_real = gpath
            if rtype == "directory":
                if target_real == g_real or target_real.startswith(g_real + os.sep):
                    return True
            elif rtype in ("file", "tool"):
                if target_real == g_real:
                    return True
            else:
                # Unbekannter type: nur exact realpath
                if target_real == g_real:
                    return True
        return False


def list_permissions_for_agent(granted_to: str) -> list[dict]:
    """Listet aktive (nicht-abgelaufene) Freigaben für einen Agenten.

    Returns: Liste von Dicts mit resource_type, resource_path, granted_by,
    reason, created_at, expires_at.
    """
    with get_db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT resource_type, resource_path, granted_by, reason, "
            "       created_at, expires_at "
            "FROM security_permissions "
            "WHERE granted_to=? AND is_active=1 "
            "AND (expires_at IS NULL OR expires_at > datetime('now')) "
            "ORDER BY created_at DESC",
            (granted_to,),
        )
        cols = (
            "resource_type", "resource_path", "granted_by",
            "reason", "created_at", "expires_at",
        )
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]