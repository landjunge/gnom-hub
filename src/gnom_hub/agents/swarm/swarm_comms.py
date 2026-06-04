import re
import time
import json
import threading
import logging
from typing import Optional, List, Dict, Union, Tuple
import sqlite3
from gnom_hub.db.connection import get_db_connection

PRIORITY_MAPPING = {
    "critical": 1,
    "high": 3,
    "normal": 5,
    "low": 7
}


logger = logging.getLogger(__name__)

# ── Konfiguration (statt Magic Numbers im Code) ────────────────────────────
MAX_DEPTH          = 8
MAX_CONCURRENT     = 12
RETRY_MAX          = 3
RETRY_BACKOFF_BASE = 5.0
MAX_QUEUE_DEPTH    = 50

# ── Notification-Bus: Agenten warten auf dieses Event statt zu pollen ──────
_new_message_event: Dict[str, threading.Event] = {}
_event_lock = threading.Lock()


def parse_agent_sequence(text: str) -> List[Tuple[str, str]]:
    """
    Parst mehrzeilige Delegationen im Format:
      @CoderAG -> Erstelle HTML
      @WriterAG -> Schreibe Text

    Gibt Liste von (agent_name, aufgabe) Tupeln zurück in der Reihenfolge.
    Auch gemischt mit Fließtext: erkennt alle @Agent -> task Zeilen.
    """
    results = []
    for line in text.split('\n'):
        line = line.strip()
        m = re.match(r'@(\w+)\s*[-–→>]+\s*(.+)', line)
        if m:
            agent = m.group(1).lower()
            task = m.group(2).strip()
            if task:
                results.append((agent, task))
    return results


def dispatch_sequence(
    sender: str,
    text: str,
    context_id: str,
    db_path: str,
    current_depth: int = 0,
) -> List[str]:
    """
    Zerlegt eine mehrzeilige Delegation in sequenzielle Tasks.
    Jeder Task hat eine sequence_id und sequence_step.
    Task N+1 wartet auf Task N (depends_on_msg_id).
    Gibt Liste der angesprochenen Agenten zurück.
    """
    if current_depth >= MAX_DEPTH:
        logger.warning("dispatch_sequence: MAX_DEPTH=%d erreicht", MAX_DEPTH)
        return []

    steps = parse_agent_sequence(text)
    if not steps:
        return dispatch_mention(sender, text, context_id, db_path, current_depth)

    dispatched = []
    conn = get_db_connection()
    try:
        agent_rows = conn.execute(
            "SELECT name, status FROM agents WHERE status IN ('online', 'busy', 'running')"
        ).fetchall()
        agent_map = {r["name"].lower(): r["name"] for r in agent_rows}
        offline = {r["name"].lower() for r in conn.execute(
            "SELECT name FROM agents WHERE status NOT IN ('online', 'busy', 'running')"
        ).fetchall()}

        seq_id = str(int(time.time() * 1000000))
        prev_msg_id = None

        for step_idx, (agent_key, task) in enumerate(steps):
            tgt_name = agent_map.get(agent_key)
            if not tgt_name:
                # Fallback: capability-basiert suchen
                tgt_name = find_best_agent_for_task(task, conn)
                if not tgt_name:
                    logger.info("Kein Agent für Task '%s' gefunden", task[:60])
                    continue

            if agent_key.lower() == sender.lower():
                continue
            if agent_key in offline:
                logger.info("Agent '%s' offline – überspringe", agent_key)
                continue

            payload = json.dumps({"text": f"@{tgt_name} {task}", "mention": tgt_name})

            cursor = conn.execute("""
                INSERT INTO agent_messages
                    (sender, recipient, payload, priority, created_at,
                     deliver_after, context_id, depth, parent_msg_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sender, tgt_name, payload, 5, time.time(),
                0.0, context_id, current_depth + 1,
                prev_msg_id,
            ))
            msg_id = cursor.lastrowid

            # Speichere sequence_id im payload für Logging
            if step_idx > 0 and prev_msg_id is not None:
                payload_obj = json.loads(payload)
                payload_obj["_sequence"] = {"id": seq_id, "step": step_idx, "depends_on_msg": prev_msg_id}
                conn.execute(
                    "UPDATE agent_messages SET payload = ? WHERE id = ?",
                    (json.dumps(payload_obj), msg_id)
                )

            conn.commit()
            notify_agent(tgt_name)
            dispatched.append(tgt_name)
            prev_msg_id = msg_id

    finally:
        conn.close()

    return dispatched


def find_best_agent_for_task(task: str, conn: sqlite3.Connection) -> Optional[str]:
    """Schlagwort-basierte Capability-Suche als Fallback."""
    keywords = {
        "code_generation": ["code", "schreib", "python", "html", "js", "script", "programm"],
        "web_research": ["recherchier", "suche", "finde", "google", "research"],
        "content_creation": ["text", "artikel", "blog", "slogan", "schreib"],
        "editing": ["korrigier", "review", "prüf", "lektorat"],
        "summarization": ["zusammenfass", "summary"],
    }
    task_lower = task.lower()
    for cap, words in keywords.items():
        if any(w in task_lower for w in words):
            row = conn.execute("""
                SELECT ac.agent_name
                FROM agent_capabilities ac
                JOIN agents a ON a.name = ac.agent_name AND a.status IN ('online','busy','running')
                WHERE ac.capability = ?
                ORDER BY ac.confidence DESC LIMIT 1
            """, (cap,)).fetchone()
            if row:
                return row["agent_name"]
    return None


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
    parent_msg_id: Optional[int] = None,
    priority: Optional[Union[str, int]] = None,
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

    # Strip <think>...</think> block to prevent mentions inside thoughts from triggering dispatches
    clean_text = re.sub(r'<think>[\s\S]*?</think>', '', text)
    mentions = re.findall(r'@(\w+)', clean_text)
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

            # Priorität ermitteln
            prio_val = None
            if priority is not None:
                if isinstance(priority, str):
                    prio_val = PRIORITY_MAPPING.get(priority.lower(), 5)
                elif isinstance(priority, int):
                    prio_val = priority
            if prio_val is None:
                prio_val = 7 if active_count >= MAX_CONCURRENT else 5

            if active_count >= MAX_CONCURRENT:
                logger.info(
                    "Agent '%s' ausgelastet (%d Jobs) – Nachricht wird gepuffert (Prio %d)",
                    tgt_name, active_count, prio_val
                )

            # Nachricht persistent speichern
            conn.execute("""
                INSERT INTO agent_messages
                    (sender, recipient, payload, priority, created_at,
                     deliver_after, context_id, depth, parent_msg_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sender,
                tgt_name,
                json.dumps({"text": text, "mention": mention}),
                prio_val,
                time.time(),
                0.0,           # sofort zustellbar
                context_id,
                current_depth,
                parent_msg_id,
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
    Prüft parent_msg_id-Abhängigkeiten: Wenn die Eltern-Nachricht noch nicht
    abgeschlossen ist, wird diese Nachricht zurückgestellt (re-queue mit delay).
    """
    evt = get_agent_event(agent_name)
    deadline = time.time() + timeout

    while time.time() < deadline:
        conn = get_db_connection()
        try:
            conn.execute('BEGIN IMMEDIATE')
            try:
                row = conn.execute("""
                    SELECT id, sender, payload, context_id, depth,
                           retry_count, parent_msg_id
                    FROM agent_messages
                    WHERE recipient    = ?
                      AND status       = 'pending'
                      AND deliver_after <= ?
                    ORDER BY priority ASC, id ASC
                    LIMIT 1
                """, (agent_name, time.time())).fetchone()

                if row:
                    # Dependency-Check: parent_msg_id muss abgeschlossen sein
                    parent_id = row["parent_msg_id"]
                    if parent_id is not None:
                        parent_status = conn.execute(
                            "SELECT status FROM agent_messages WHERE id = ?",
                            (parent_id,)
                        ).fetchone()
                        if parent_status and parent_status["status"] != "done":
                            # Abhängigkeit noch nicht erfüllt – zurückstellen
                            conn.execute("""
                                UPDATE agent_messages
                                SET deliver_after = ?, status = 'pending'
                                WHERE id = ?
                            """, (time.time() + 3.0, row["id"]))
                            conn.commit()
                            # Kurz warten, dann weitersuchen
                            conn.close()
                            time.sleep(1.5)
                            continue

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
                        "parent_msg_id": row["parent_msg_id"],
                    }
                else:
                    conn.rollback()
            except:
                conn.rollback()
                raise
        finally:
            conn.close()

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
            "UPDATE agent_messages SET status='done', completed_at=? WHERE id=?", (time.time(), msg_id)
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
                "UPDATE agent_messages SET status='dead_letter', completed_at=? WHERE id=?",
                (time.time(), msg_id)
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


def process_swarm_mentions(sender: str, text: str, depth: int = 0, parent_msg_id: Optional[int] = None):
    """
    Router-Schnittstelle. Erkennt mehrzeilige Delegationen und routet
    sie entweder als Sequenz oder als einfache Mentions.
    """
    from gnom_hub.core.config import DB_PATH
    from gnom_hub.db import get_active_project
    proj = get_active_project() or "default"
    clean = re.sub(r'<think>[\s\S]*?</think>', '', text)
    steps = parse_agent_sequence(clean)
    if len(steps) >= 2:
        dispatch_sequence(sender, clean, proj, str(DB_PATH), depth)
    elif len(steps) == 1:
        dispatch_mention(sender, clean, proj, str(DB_PATH), depth + 1, parent_msg_id=parent_msg_id)
    else:
        dispatch_mention(sender, clean, proj, str(DB_PATH), depth + 1, parent_msg_id=parent_msg_id)


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
    parent_msg_id: Optional[int] = None,
    priority: Optional[Union[str, int]] = None,
) -> Tuple[Optional[str], Optional[int]]:
    """
    Routet eine Aufgabe basierend auf den Fähigkeiten der Agenten statt über direkten Namen.
    Gibt Tuple (target_agent, msg_id) zurück.
    """
    conn = get_db_connection()
    try:
        target = find_best_agent_for(task_type, conn)
        if not target:
            logger.warning("Kein Agent für Capability '%s' verfügbar", task_type)
            return None, None

        # Backpressure-Limit prüfen
        pending_count = conn.execute("""
            SELECT COUNT(*) FROM agent_messages
            WHERE recipient = ? AND status = 'pending'
        """, (target,)).fetchone()[0]

        if pending_count >= MAX_QUEUE_DEPTH:
            logger.warning(
                "Backpressure ausgelöst: Queue von Agent '%s' ist voll (%d offene Jobs).",
                target, pending_count
            )
            return None, None

        # Concurrent-Limit prüfen
        active_count = conn.execute("""
            SELECT COUNT(*) FROM agent_messages
            WHERE recipient = ? AND status = 'processing'
        """, (target,)).fetchone()[0]

        # Priorität ermitteln
        prio_val = None
        if priority is not None:
            if isinstance(priority, str):
                prio_val = PRIORITY_MAPPING.get(priority.lower(), 5)
            elif isinstance(priority, int):
                prio_val = priority
        if prio_val is None:
            prio_val = 7 if active_count >= MAX_CONCURRENT else 5

        # Nachricht an den passenden Agenten in DB speichern
        cursor = conn.execute("""
            INSERT INTO agent_messages
                (sender, recipient, payload, priority, created_at,
                 deliver_after, context_id, depth, parent_msg_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sender,
            target,
            json.dumps({"text": f"@{target} {text}", "mention": target}),
            prio_val,
            time.time(),
            0.0,
            context_id,
            current_depth,
            parent_msg_id,
        ))
        msg_id = cursor.lastrowid
        conn.commit()

        notify_agent(target)
        return target, msg_id
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
                    "UPDATE agent_messages SET status='dead_letter', retry_count=?, processing_since=NULL, completed_at=? WHERE id=?",
                    (retries, time.time(), msg_id)
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
