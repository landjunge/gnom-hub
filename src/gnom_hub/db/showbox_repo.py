# showbox_repo.py — Showbox presentation database operations
import json
import sqlite3
import uuid
from datetime import datetime, timezone

from gnom_hub.core.logger import get_logger
from gnom_hub.db.connection import get_db_conn

logger = get_logger("db.showbox")

# Max-Anzahl Presentations pro Layer (User-Wahl 2026-06-15)
# Worker = 3, system = 3, user = 5
MAX_PRESENTATIONS_PER_LAYER = {
    "worker": 3,
    "system": 3,
    "user": 5,
}

# Geschützte Presentations die nie gelöscht werden
_PROTECTED_NAMES = {"Standard", "Latest Update"}


def _sender_to_layer(sender: str | None) -> str:
    """Mappe Sender-String auf Layer (worker/system/user)."""
    if not sender:
        return "worker"
    s = sender.lower()
    if s in ("user", "war-room"):
        return "user"
    # Worker-Agents (CoderAG, WriterAG, EditorAG, ResearcherAG, ...)
    if any(s.startswith(x) for x in ("coder", "writer", "editor", "researcher")):
        return "worker"
    # System-Agents (GeneralAG, SoulAG, WatchdogAG, SecurityAG, system)
    if any(s.startswith(x) for x in ("general", "soul", "watchdog", "security", "system")):
        return "system"
    # "Agent" oder unbekannt → worker (default)
    return "worker"


def _cleanup_old_presentations(conn, current_layer: str) -> int:
    """Behalte nur die letzten N Presentations pro Layer (aus dem Sender abgeleitet).
    Ältere werden gelöscht."""
    try:
        rows = conn.execute(
            "SELECT name, sender, updated_at FROM showbox_presentations ORDER BY updated_at DESC"
        ).fetchall()
        by_layer: dict = {}
        for r in rows:
            n = r["name"]
            if n in _PROTECTED_NAMES:
                continue
            lay = _sender_to_layer(r["sender"])
            by_layer.setdefault(lay, []).append((n, r["updated_at"]))
        deleted = 0
        for lay, items in by_layer.items():
            keep = MAX_PRESENTATIONS_PER_LAYER.get(lay, 3)
            if len(items) > keep:
                # Lösche die ältesten (alles nach Position 'keep')
                for old_name, _ in items[keep:]:
                    conn.execute(
                        "DELETE FROM showbox_presentations WHERE name = ?", (old_name,)
                    )
                    deleted += 1
        return deleted
    except sqlite3.Error as e:
        logger.warning(f"[DB] Cleanup-Fehler: {e}")
        return 0


def save_showbox_presentation(name: str, slides: list, sender: str = None, buttons: list = None) -> dict:
    """Erstellt oder aktualisiert eine Showbox-Präsentation.
    Nach dem Speichern: nur die letzten N Presentations pro Layer behalten.

    Args:
        buttons: Optionale Liste von dynamischen Buttons (max 8), je {id, icon, label, color, onClick}
    """
    try:
        with get_db_conn() as conn:
            with conn:
                pid = str(uuid.uuid4())
                ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                buttons_json = json.dumps(buttons or [])
                conn.execute("""
                    INSERT INTO showbox_presentations (id, name, slides, sender, updated_at, buttons)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        slides = excluded.slides,
                        sender = excluded.sender,
                        updated_at = excluded.updated_at,
                        buttons = excluded.buttons
                """, (pid, name, json.dumps(slides), sender, ts, buttons_json))
                # Cleanup: nur letzte N pro Layer behalten (Layer aus Sender)
                deleted = _cleanup_old_presentations(conn, _sender_to_layer(sender))
                if deleted:
                    logger.info(f"[DB] Showbox cleanup: {deleted} alte Presentations gelöscht")
                return {"name": name, "slides": slides, "sender": sender, "updated_at": ts, "buttons": buttons or []}
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to save showbox presentation: {e}")
        return None


def get_showbox_presentations() -> list:
    """Gibt alle gespeicherten Showbox-Präsentationen zurück."""
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT * FROM showbox_presentations ORDER BY name ASC").fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["slides"] = json.loads(d["slides"])
                try:
                    d["buttons"] = json.loads(d.get("buttons") or "[]")
                except (json.JSONDecodeError, TypeError):
                    d["buttons"] = []
                res.append(d)
            return res
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to get showbox presentations: {e}")
        return []


def delete_showbox_presentation(name: str) -> bool:
    """Löscht eine Showbox-Präsentation über ihren Namen."""
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM showbox_presentations WHERE name = ?", (name,))
                return True
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to delete showbox presentation: {e}")
        return False


def get_showbox_presentation_by_name(name: str) -> dict:
    """Gibt eine Showbox-Präsentation über ihren Namen zurück."""
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT * FROM showbox_presentations WHERE name = ?", (name,)).fetchone()
            if row:
                d = dict(row)
                d["slides"] = json.loads(d["slides"])
                return d
            return None
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to get showbox presentation: {e}")
        return None


def get_active_showbox() -> str:
    """Gibt den Namen der aktiven Showbox-Präsentation zurück."""
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT value FROM state WHERE key='active_showbox'").fetchone()
            return json.loads(row["value"]) if row else ""
    except (sqlite3.Error, json.JSONDecodeError, TypeError) as e:
        logger.error(f"[DB] Failed to get active showbox: {e}")
        return ""


# ── Permanent-Default-Showbox (8 dynamische Buttons, onClick leer) ──
_DEFAULT_BUTTONS = [
    {"id": "b1", "icon": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
     "label": "B1", "color": "green", "onClick": ""},
    {"id": "b2", "icon": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
     "label": "B2", "color": "cyan", "onClick": ""},
    {"id": "b3", "icon": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
     "label": "B3", "color": "purple", "onClick": ""},
    {"id": "b4", "icon": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
     "label": "B4", "color": "orange", "onClick": ""},
    {"id": "b5", "icon": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
     "label": "B5", "color": "yellow", "onClick": ""},
    {"id": "b6", "icon": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3" fill="currentColor"><animate attributeName="r" values="3;5;3" dur="2s" repeatCount="indefinite"/></circle></svg>',
     "label": "B6", "color": "blue", "onClick": ""},
    {"id": "b7", "icon": '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M12 2c-1 3-3 5-3 8 0 2 1 3 3 3s3-1 3-3c0-1-1-2-1-3 1 0 2 1 2 3 0 3-2 5-4 5s-4-2-4-5c0-4 3-6 4-8z"/></svg>',
     "label": "B7", "color": "red", "onClick": ""},
    {"id": "b8", "icon": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
     "label": "B8", "color": "gray", "onClick": ""},
]


def ensure_default_showbox() -> str:
    """Stellt sicher dass 'Gnom-Hub Live' mit 8 Buttons existiert.
    Wird beim Hub-Start aufgerufen. Setzt es NUR als aktiv wenn noch KEIN
    active_showbox gesetzt war (User-Mandat 2026-07-11 23:17 — vorher wurde
    die User-Auswahl beim Hub-Start jedes Mal auf 'Gnom-Hub Live' zurückgesetzt).
    Gibt den Namen zurück."""
    name = "Gnom-Hub Live"
    try:
        existing = get_showbox_presentation_by_name(name)
        if not existing or not (existing.get("buttons") or len(existing.get("buttons") or []) < 8):
            slide = (
                '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;'
                'height:100%;gap:10px;padding:12px;box-sizing:border-box;text-align:center;'
                'background:radial-gradient(ellipse at center,rgba(0,229,255,0.05) 0%,transparent 60%);">'
                '<div style="font-size:1.4rem;font-weight:700;color:#fff;'
                'text-shadow:0 0 12px rgba(0,229,255,0.8);">🧠 Gnom-Hub</div>'
                '<div style="font-size:0.6rem;color:rgba(255,255,255,0.5);">'
                '8 dynamische Buttons · klicke unten</div>'
                '<div style="font-size:0.7rem;color:#39ff7a;margin-top:8px;">● 8 Agents online</div>'
                '</div>'
            )
            save_showbox_presentation(name, [slide], sender="System", buttons=_DEFAULT_BUTTONS)
            logger.info(f"[SHOWBOX] Default '{name}' mit 8 Buttons erstellt.")
        active = get_active_showbox()
        # Nur setzen wenn NOCH NIE ein active_showbox gesetzt war
        # (state-Tabelle leer für active_showbox) oder aktiver Eintrag zeigt
        # auf nicht-existente Showbox. NIEMALS User-Auswahl überschreiben.
        if not active or not get_showbox_presentation_by_name(active):
            with get_db_conn() as conn:
                with conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO state (key, value) VALUES ('active_showbox', ?)",
                        (json.dumps(name),),
                    )
            logger.info(f"[SHOWBOX] Default '{name}' als aktiv gesetzt (war: '{active}').")
        else:
            logger.info(f"[SHOWBOX] User-Auswahl beibehalten: '{active}'.")
        return active or name
    except Exception as e:
        logger.error(f"[SHOWBOX] ensure_default_showbox failed: {e}")
        return ""


STICKY_SHOWBOX_NAMES = ("gnom-hub-designs",)


def set_active_showbox(name: str):
    """Setzt den Namen der aktiven Showbox-Präsentation.

    Sticky-Logic: wenn die aktive Showbox eine protected Name ist (z.B.
    'gnom-hub-designs'), wird sie nicht durch eine andere Showbox ersetzt.
    User-Mandat 2026-07-12: User will die Designs-Showbox sehen, nicht
    Worker-Output der die Showbox ständig überschreibt.
    """
    try:
        if not name.startswith("Blockade:"):
            from gnom_hub.db.system_repo import get_state_value
            pending = get_state_value("pending_decisions", {})
            has_pending = any(d.get("status") == "pending" for d in pending.values())
            if has_pending:
                logger.info(f"[DB] Override active showbox to '{name}' blocked: pending decision in progress.")
                return
            # Sticky-Check: protected Showbox nicht überschreiben
            current_active = get_active_showbox()
            if current_active in STICKY_SHOWBOX_NAMES and name not in STICKY_SHOWBOX_NAMES:
                logger.info(f"[DB] Sticky active '{current_active}' protected — not overwriting with '{name}'")
                return
        with get_db_conn() as conn:
            with conn:
                conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('active_showbox', ?)", (json.dumps(name.strip()),))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to set active showbox: {e}")
