import re
import time
import json
import threading
import logging
from typing import Optional, List, Dict
import sqlite3
from gnom_hub.db.connection import get_db_connection

logger = logging.getLogger(__name__)

# ── Konfiguration (statt Magic Numbers im Code) ────────────────────────────
MAX_DEPTH          = 8        # war: 6 – etwas mehr Spielraum
MAX_CONCURRENT     = 12       # war: 6 im 15s-Fenster – jetzt Queue-basiert
RETRY_MAX          = 3
RETRY_BACKOFF_BASE = 5.0      # Sekunden, exponentiell: 5s, 10s, 20s
MAX_QUEUE_DEPTH    = 50       # Backpressure-Limit für anstehende Nachrichten

# ── Notification-Bus: Agenten warten auf dieses Event statt zu pollen ──────
_new_message_event: Dict[str, threading.Event] = {}
_event_lock = threading.Lock()


def get_agent_event(agent_name: str) -> threading.Event:
    with _event_lock:
        if agent_name not in _new_message_event:
            _new_message_event[agent_name] = threading.Event()
        return _new_message_event[agent_name]


def notify_agent(agent_name: str) -> None:
    """Weckt einen wartenden Agenten auf – O(1), kein Polling."""
    with _event_lock:
        evt = _new_message_event.get(agent_name)
    if evt:
        evt.set()


def dispatch_mention(
    sender: str,
    text: str,
    context_id: str,
    db_path: str,
    current_depth: int = 0,
) -> List[str]:
    """
    Parst @Mentions und legt Nachrichten in die persistente Queue.
    Gibt Liste der angesprochenen Agenten zurück (für Logging).
    """
    if current_depth >= MAX_DEPTH:
        logger.warning(
            "Mention-Dispatch abgebrochen: MAX_DEPTH=%d erreicht "
            "(context_id=%s, sender=%s)", MAX_DEPTH, context_id, sender
        )
        return []

    mentions = re.findall(r'@(\w+)', text)
    if not mentions:
        return []

    dispatched = []
    conn = get_db_connection()

    try:
        # Online- UND Busy-Agenten laden (keine stille Verwerfung mehr!)
        rows = conn.execute(
            "SELECT name, status FROM agents WHERE status IN ('online', 'busy', 'running')"
        ).fetchall()
        agent_map = {r["name"].lower(): r["name"] for r in rows}

        offline_agents = {
            r["name"].lower()
            for r in conn.execute(
                "SELECT name FROM agents WHERE status NOT IN ('online', 'busy', 'running')"
            ).fetchall()
        }

        for mention in set(mentions):  # Deduplizieren
            tgt_lower = mention.lower()

            if tgt_lower == sender.lower():
                continue  # Kein Self-Dispatch

            if tgt_lower in offline_agents:
                logger.info("Agent '%s' offline – Nachricht wird verworfen", mention)
                continue

            if tgt_lower not in agent_map:
                logger.debug("Unbekannter Agent: @%s", mention)
                continue

            tgt_name = agent_map[tgt_lower]

            # Backpressure-Limit prüfen (Queue-Explosionsschutz)
            pending_count = conn.execute("""
                SELECT COUNT(*) FROM agent_messages
                WHERE recipient = ? AND status = 'pending'
            """, (tgt_name,)).fetchone()[0]

            if pending_count >= MAX_QUEUE_DEPTH:
                logger.warning(
                    "Backpressure ausgelöst: Queue von Agent '%s' ist voll (%d offene Jobs).",
                    tgt_name, pending_count
                )
                continue

            # Concurrent-Limit prüfen
            active_count = conn.execute("""
                SELECT COUNT(*) FROM agent_messages
                WHERE recipient = ? AND status = 'processing'
            """, (tgt_name,)).fetchone()[0]

            # Ausgelasteter Agent: trotzdem einreihen, aber mit niedrigerer Priorität
            priority = 7 if active_count >= MAX_CONCURRENT else 5

            if active_count >= MAX_CONCURRENT:
                logger.info(
                    "Agent '%s' ausgelastet (%d Jobs) – Nachricht wird gepuffert (Prio %d)",
                    tgt_name, active_count, priority
                )

            # Nachricht persistent speichern
            conn.execute("""
                INSERT INTO agent_messages
                    (sender, recipient, payload, priority, created_at,
                     deliver_after, context_id, depth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sender,
                tgt_name,
                json.dumps({"text": text, "mention": mention}),
                priority,
                time.time(),
                0.0,           # sofort zustellbar
                context_id,
                current_depth,
            ))
            conn.commit()

            # Agenten aufwecken (falls er wartet)
            notify_agent(tgt_name)
            dispatched.append(tgt_name)

    finally:
        conn.close()

    return dispatched


def fetch_next_message(
    agent_name: str,
    db_path: str,
    timeout: float = 30.0,
) -> Optional[dict]:
    """
    Blockiert maximal `timeout` Sekunden auf die nächste Nachricht.
    Nutzt threading.Event mit Fallback-Schlafzeit von 1s für Cross-Prozess-Kommunikation.
    """
    evt = get_agent_event(agent_name)
    deadline = time.time() + timeout

    while time.time() < deadline:
        conn = get_db_connection()
        try:
            row = conn.execute("""
                SELECT id, sender, payload, context_id, depth, retry_count
                FROM agent_messages
                WHERE recipient    = ?
                  AND status       = 'pending'
                  AND deliver_after <= ?
                ORDER BY priority ASC, id ASC
                LIMIT 1
            """, (agent_name, time.time())).fetchone()

            if row:
                conn.execute(
                    "UPDATE agent_messages SET status='processing', processing_since=? WHERE id=?",
                    (time.time(), row["id"])
                )
                conn.commit()
                return {
                    "msg_id":      row["id"],
                    "sender":      row["sender"],
                    "payload":     json.loads(row["payload"]),
                    "context_id":  row["context_id"],
                    "depth":       row["depth"],
                    "retry_count": row["retry_count"],
                }
        finally:
            conn.close()

        # Cross-Process-Fallback: maximal 1.0 Sekunde blockieren, dann erneut DB prüfen
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        evt.wait(timeout=min(remaining, 1.0))
        evt.clear()

    return None  # Timeout


def ack_message(msg_id: int, db_path: str) -> None:
    """Nachricht als erfolgreich abgearbeitet markieren."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE agent_messages SET status='done' WHERE id=?", (msg_id,)
        )
        conn.commit()
    finally:
        conn.close()


def nack_message(msg_id: int, db_path: str, reason: str = "") -> None:
    """
    Nachricht als fehlgeschlagen markieren.
    Retry mit exponentiellem Backoff, max RETRY_MAX Versuche.
    Danach: Dead-Letter-Queue.
    """
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT retry_count FROM agent_messages WHERE id=?", (msg_id,)
        ).fetchone()

        if not row:
            return

        retries = row["retry_count"] + 1

        if retries >= RETRY_MAX:
            conn.execute(
                "UPDATE agent_messages SET status='dead_letter' WHERE id=?",
                (msg_id,)
            )
            logger.error(
                "Nachricht %d in Dead-Letter-Queue (reason: %s)", msg_id, reason
            )
        else:
            backoff = RETRY_BACKOFF_BASE * (2 ** (retries - 1))  # 5s, 10s, 20s
            conn.execute("""
                UPDATE agent_messages
                SET status='pending', retry_count=?, deliver_after=?, processing_since=NULL
                WHERE id=?
            """, (retries, time.time() + backoff, msg_id))
            logger.warning(
                "Nachricht %d – Retry %d/%d in %.0fs",
                msg_id, retries, RETRY_MAX, backoff
            )

        conn.commit()
    finally:
        conn.close()


def process_swarm_mentions(sender: str, text: str, depth: int = 0):
    """
    Kompatibilitäts-Schnittstelle für den Router.
    """
    from gnom_hub.core.config import DB_PATH
    from gnom_hub.db import get_active_project
    proj = get_active_project() or "default"
    dispatch_mention(sender, text, proj, str(DB_PATH), depth)


def find_best_agent_for(task_type: str, conn: sqlite3.Connection) -> Optional[str]:
    """
    Findet den am besten geeigneten verfügbaren Agenten für eine Fähigkeit.
    Priorisiert Confidence und wählt bei Gleichstand den Agenten mit der kleinsten Queue-Tiefe.
    """
    row = conn.execute("""
        SELECT ac.agent_name,
               ac.confidence,
               COALESCE(q.pending_count, 0) AS queue_depth
        FROM agent_capabilities ac
        JOIN agents a
            ON a.name = ac.agent_name
           AND a.status IN ('online', 'busy', 'running')
        LEFT JOIN (
            SELECT recipient, COUNT(*) AS pending_count
            FROM agent_messages
            WHERE status = 'pending'
            GROUP BY recipient
        ) q ON q.recipient = ac.agent_name
        WHERE ac.capability = ?
        ORDER BY queue_depth ASC, ac.confidence DESC
        LIMIT 1
    """, (task_type,)).fetchone()

    return row["agent_name"] if row else None


def dispatch_by_capability(
    sender: str,
    task_type: str,
    text: str,
    context_id: str,
    db_path: str,
    current_depth: int = 0,
) -> Optional[str]:
    """
    Routet eine Aufgabe basierend auf den Fähigkeiten der Agenten statt über direkten Namen.
    """
    conn = get_db_connection()
    try:
        target = find_best_agent_for(task_type, conn)
        if not target:
            logger.warning("Kein Agent für Capability '%s' verfügbar", task_type)
            return None

        # Nachricht an den passenden Agenten absenden
        dispatch_mention(
            sender=sender,
            text=f"@{target} {text}",
            context_id=context_id,
            db_path=db_path,
            current_depth=current_depth,
        )
        return target
    finally:
        conn.close()


def recover_stuck_messages(db_path: str, timeout: float = 300.0) -> None:
    """
    Findet blockierte/abgestürzte Nachrichten und gibt sie wieder frei oder schiebt sie in die DLQ.
    """
    conn = get_db_connection()
    try:
        now = time.time()
        stuck_cutoff = now - timeout
        rows = conn.execute("""
            SELECT id, retry_count, recipient, sender FROM agent_messages
            WHERE status = 'processing' AND processing_since <= ?
        """, (stuck_cutoff,)).fetchall()

        for row in rows:
            msg_id = row["id"]
            retries = row["retry_count"] + 1
            recipient = row["recipient"]
            sender = row["sender"]

            if retries >= RETRY_MAX:
                conn.execute(
                    "UPDATE agent_messages SET status='dead_letter', retry_count=?, processing_since=NULL WHERE id=?",
                    (retries, msg_id)
                )
                logger.error(
                    "Nachricht %d (Ziel=%s, Sender=%s) zu oft blockiert – verschoben in dead_letter",
                    msg_id, recipient, sender
                )
            else:
                backoff = RETRY_BACKOFF_BASE * (2 ** (retries - 1))
                conn.execute("""
                    UPDATE agent_messages
                    SET status='pending', retry_count=?, deliver_after=?, processing_since=NULL
                    WHERE id=?
                """, (retries, now + backoff, msg_id))
                logger.warning(
                    "Nachricht %d (Ziel=%s, Sender=%s) blockiert. Retry %d/%d in %.0fs",
                    msg_id, recipient, sender, retries, RETRY_MAX, backoff
                )
                notify_agent(recipient)

        conn.commit()
    finally:
        conn.close()
