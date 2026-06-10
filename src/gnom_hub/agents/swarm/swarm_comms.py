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
MAX_DEPTH           = 8
MAX_CONCURRENT      = 8       # (war 12) — nur 8 Agenten
RETRY_MAX           = 3
RETRY_BACKOFF_BASE  = 3.0     # (war 5.0) — schnellere Retries
MAX_QUEUE_DEPTH     = 30      # (war 50) — engere Backpressure
DEPENDENCY_TIMEOUT  = 120.0  # Max. Wartezeit auf eine Abhängigkeit (Sekunden)
DEPENDENCY_POLL_S   = 1.0     # (war 3.0) — schnellere Dependency-Auflösung    # Poll-Intervall für Dependency-Checks

# ── Notification-Bus: Agenten warten auf dieses Event statt zu pollen ──────
_new_message_event: Dict[str, threading.Event] = {}
_event_lock = threading.Lock()


def can_accept_message(agent_name: str, conn: sqlite3.Connection) -> bool:
    """Prüft ob ein Agent noch Tasks annehmen kann (Backpressure + Concurrent-Limit).

    Berücksichtigt:
      - MAX_QUEUE_DEPTH: Maximale Anzahl offener (pending) Nachrichten pro Agent
      - MAX_CONCURRENT:  Maximale Anzahl gleichzeitig verarbeiteter (processing) Nachrichten

    Rückgabewert: True = Task kann angenommen werden, False = Queue voll/überlastet
    """
    pending = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE recipient = ? AND status = 'pending'",
        (agent_name,)
    ).fetchone()[0]
    if pending >= MAX_QUEUE_DEPTH:
        logger.warning(
            "Backpressure für Agent '%s': %d pending (Limit %d)",
            agent_name, pending, MAX_QUEUE_DEPTH
        )
        return False

    active = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE recipient = ? AND status = 'processing'",
        (agent_name,)
    ).fetchone()[0]
    if active >= MAX_CONCURRENT:
        logger.info(
            "Auslastung Agent '%s': %d processing (Limit %d) – wird gepuffert",
            agent_name, active, MAX_CONCURRENT
        )
    return True


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
                tgt_name = find_best_agent_for_task(task, conn)
                if not tgt_name:
                    logger.info("Kein Agent für Task '%s' gefunden", task[:60])
                    continue

            if agent_key.lower() == sender.lower():
                continue
            if agent_key in offline and agent_key not in agent_map:
                if tgt_name == agent_map.get(agent_key):
                    tgt_name = find_best_agent_for_task(task, conn)
                    if not tgt_name:
                        logger.info("Agent '%s' offline – kein Ersatz", agent_key)
                        continue

            if not can_accept_message(tgt_name, conn):
                logger.warning(
                    "dispatch_sequence: Überspringe Step %d für '%s' – Queue voll (context=%s)",
                    step_idx, tgt_name, context_id
                )
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

            notify_agent(tgt_name)
            dispatched.append(tgt_name)
            prev_msg_id = msg_id

    finally:
        conn.commit()
        conn.close()

    return dispatched


def _get_queue_depths(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT recipient, COUNT(*) as cnt FROM agent_messages "
        "WHERE status IN ('pending','processing') GROUP BY recipient"
    ).fetchall()
    return {r["recipient"].lower(): r["cnt"] for r in rows}


def _find_capability_for_task(task_lower: str) -> Optional[str]:
    keywords = {
        "code_generation":  ["code", "schreib", "python", "html", "js", "script", "programm", "implementier", "bash"],
        "web_research":     ["recherchier", "suche", "finde", "google", "research", "analyse"],
        "content_creation": ["text", "artikel", "blog", "slogan", "schreib", "dokument", "doc"],
        "editing":          ["korrigier", "review", "prüf", "lektorat", "refaktor", "edit"],
        "summarization":    ["zusammenfass", "summary", "kurzfass"],
        "security_audit":   ["sicherheit", "security", "audit", "vulnerab", "scan"],
    }
    for cap, words in keywords.items():
        if any(w in task_lower for w in words):
            return cap
    return None


def find_best_agent_for_task(task: str, conn: sqlite3.Connection) -> Optional[str]:
    """
    Dreistufige Agenten-Wahl:
      1. coordination.db: Wer hat ähnliche Jobs am besten erledigt?
      2. agent_capabilities + Queue-Tiefe: Wer ist frei + kompetent?
      3. Keyword-Heuristik: Letzter Fallback
    """
    task_lower = task.lower()
    queue_depths = _get_queue_depths(conn)

    # Stufe 1: coordination.db — Erfolgsrate aus der Job-History
    try:
        from gnom_hub.soul.memory_layers import get_coordination_db
        capability = _find_capability_for_task(task_lower)
        if capability:
            preferred, fallback = get_coordination_db().get_best_worker(capability, queue_depths)
            if preferred:
                row = conn.execute(
                    "SELECT name FROM agents WHERE LOWER(name) = ? AND status IN ('online','busy','running')",
                    (preferred.lower(),)
                ).fetchone()
                if row:
                    _log.info("Agent-Wahl: coordination.db → %s (%.0f%% Erfolg, Queue %d)",
                              preferred,
                              _get_success_rate(conn, preferred),
                              queue_depths.get(preferred.lower(), 0))
                    return row["name"]
    except Exception as e:
        _log.debug("coordination.db nicht verfügbar: %s", e)

    # Stufe 2: agent_capabilities + Queue-Tiefe + Erfolgsrate
    capability = _find_capability_for_task(task_lower)
    if capability:
        rows = conn.execute("""
            SELECT ac.agent_name, ac.confidence
            FROM agent_capabilities ac
            JOIN agents a ON a.name = ac.agent_name AND a.status IN ('online','busy','running')
            WHERE ac.capability = ?
            ORDER BY ac.confidence DESC
        """, (capability,)).fetchall()

        scored = []
        for r in rows:
            name = r["agent_name"]
            qd = queue_depths.get(name.lower(), 0)
            success_rate = _get_success_rate(conn, name)
            score = r["confidence"] * 10 - qd * 2 + success_rate * 0.3
            scored.append((score, name, qd, success_rate))

        scored.sort(key=lambda x: x[0], reverse=True)
        for score, name, qd, sr in scored:
            if sr >= 40 or not _has_enough_jobs(conn, name):
                _log.info("Agent-Wahl: capabilities → %s (Score=%.1f, Queue=%d, Erfolg=%.0f%%)",
                          name, score, qd, sr)
                return name
            else:
                _log.info("Agent übersprungen: %s (nur %.0f%% Erfolg nach mehreren Jobs)", name, sr)

        if scored:
            _log.info("Agent-Wahl: capabilities → %s (letzter, trotz niedriger Erfolgsrate)", scored[-1][1])
            return scored[-1][1]

    # Stufe 3: Keyword-Heuristik als letzter Fallback
    agent_hints = {
        "coderag":     ["code", "python", "html", "js", "create", "erstell", "bau", "implementier", "script", "write"],
        "writerag":    ["text", "slogan", "artikel", "blog", "dokument", "schreib", "content"],
        "researcherag":["recherchier", "suche", "finde", "research", "analyse", "fakten"],
        "editorag":    ["korrigier", "review", "prüf", "lektorat", "refaktor", "qualität"],
    }
    for agent_key, agent_words in agent_hints.items():
        if any(w in task_lower for w in agent_words):
            row = conn.execute(
                "SELECT name FROM agents WHERE name = ? AND status IN ('online','busy','running')",
                (agent_key,)
            ).fetchone()
            if row:
                _log.info("Agent-Wahl: keyword fallback → %s", row["name"])
                return row["name"]

    return None


def _get_success_rate(conn: sqlite3.Connection, agent_name: str) -> float:
    try:
        from gnom_hub.soul.memory_layers import get_coordination_db
        cdb = get_coordination_db()
        with sqlite3.connect(cdb._path) as c:
            row = c.execute(
                "SELECT total_jobs, successful_jobs FROM worker_stats WHERE agent_name = ?",
                (agent_name,)
            ).fetchone()
            if row and row[0] > 0:
                return (row[1] / row[0]) * 100
    except Exception:
        pass
    return 0.0


def _has_enough_jobs(conn: sqlite3.Connection, agent_name: str, threshold: int = 5) -> bool:
    try:
        from gnom_hub.soul.memory_layers import get_coordination_db
        cdb = get_coordination_db()
        with sqlite3.connect(cdb._path) as c:
            row = c.execute(
                "SELECT total_jobs FROM worker_stats WHERE agent_name = ?", (agent_name,)
            ).fetchone()
            return row and row[0] >= threshold
    except Exception:
        return False


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

            is_critical = (isinstance(priority, str) and priority.lower() == "critical") or priority == 0

            if not is_critical and not can_accept_message(tgt_name, conn):
                continue

            if is_critical:
                prio_val = 0
            else:
                active_count = conn.execute(
                    "SELECT COUNT(*) FROM agent_messages WHERE recipient = ? AND status = 'processing'",
                    (tgt_name,)
                ).fetchone()[0]
                prio_val = None
                if priority is not None:
                    if isinstance(priority, str):
                        prio_val = PRIORITY_MAPPING.get(priority.lower(), 5)
                    elif isinstance(priority, int):
                        prio_val = priority
                if prio_val is None:
                    prio_val = 7 if active_count >= MAX_CONCURRENT else 5

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
    Prüft parent_msg_id-Abhängigkeiten:
    - Parent ist 'dead_letter' → diese Nachricht auch in DLQ
    - Parent nach DEPENDENCY_TIMEOUT nicht 'done' → diese Nachricht in DLQ
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
                    parent_id = row["parent_msg_id"]
                    if parent_id is not None:
                        parent_row = conn.execute(
                            "SELECT status, created_at FROM agent_messages WHERE id = ?",
                            (parent_id,)
                        ).fetchone()

                        if not parent_row:
                            # Parent existiert nicht mehr → abbrechen
                            conn.execute(
                                "UPDATE agent_messages SET status='dead_letter', completed_at=? WHERE id=?",
                                (time.time(), row["id"])
                            )
                            conn.commit()
                            logger.error("Sequenz-Abbruch: parent_msg_id %d existiert nicht (Child %d)", parent_id, row["id"])
                            time.sleep(0.5)
                            continue

                        if parent_row["status"] == "dead_letter":
                            # Parent fehlgeschlagen → auch dieses Child in DLQ
                            fail_dependent_messages(row["id"], "parent_msg_id=%d in dead_letter" % parent_id, conn)
                            conn.commit()
                            logger.error("Sequenz-Abbruch: Parent %d in DLQ – Child %d ebenfalls abgebrochen", parent_id, row["id"])
                            time.sleep(0.5)
                            continue

                        if parent_row["status"] != "done":
                            # Parent noch nicht fertig – prüfe auf Timeout.
                            # Verwende processing_since (Start der Bearbeitung) statt
                            # created_at (Einreihen in Queue) – sonst timeoutet eine
                            # frisch gestartete, aber alte Message sofort.
                            parent_ps = conn.execute(
                                "SELECT processing_since FROM agent_messages WHERE id = ?",
                                (parent_id,)
                            ).fetchone()
                            ps = parent_ps["processing_since"] if parent_ps else None
                            if ps is not None:
                                elapsed = time.time() - ps
                                if elapsed > DEPENDENCY_TIMEOUT:
                                    fail_dependent_messages(parent_id, "DEPENDENCY_TIMEOUT=%.0fs" % DEPENDENCY_TIMEOUT, conn)
                                    conn.commit()
                                    logger.error("Sequenz-Abbruch: Parent %d nach %.0fs processing – Kaskade ausgelöst", parent_id, elapsed)
                                    time.sleep(0.5)
                                    continue

                            conn.execute("""
                                UPDATE agent_messages
                                SET deliver_after = ?, status = 'pending'
                                WHERE id = ?
                            """, (time.time() + DEPENDENCY_POLL_S, row["id"]))
                            conn.commit()
                            time.sleep(1.5)
                            continue

                    conn.execute(
                        "UPDATE agent_messages SET status='processing', processing_since=? WHERE id=?",
                        (time.time(), row["id"])
                    )
                    conn.commit()
                    return {
                        "msg_id":        row["id"],
                        "sender":        row["sender"],
                        "payload":       json.loads(row["payload"]),
                        "context_id":    row["context_id"],
                        "depth":         row["depth"],
                        "retry_count":   row["retry_count"],
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
    """Nachricht als erfolgreich abgearbeitet markieren.

    Setzt bei allen wartenden Children (parent_msg_id = msg_id, status = 'pending')
    deliver_after auf 0 zurück, damit fetch_next_message sie sofort findet.

    Optimierung: Die meisten Messages haben keine abhängigen Children. Ein günstiger
    SELECT 1 ... LIMIT 1 (Index-Only-Lookup) prüft, ob Children existieren. Nur dann
    werden der UPDATE und notify_agent() ausgeführt. Der COMMIT erfolgt einmalig.
    """
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE agent_messages SET status='done', completed_at=? WHERE id=?",
            (time.time(), msg_id)
        )
        children_exist = conn.execute(
            "SELECT 1 FROM agent_messages WHERE parent_msg_id = ? AND status = 'pending' LIMIT 1",
            (msg_id,)
        ).fetchone() is not None
        if children_exist:
            conn.execute(
                "UPDATE agent_messages SET deliver_after=0 WHERE parent_msg_id = ? AND status = 'pending'",
                (msg_id,)
            )
            agents = conn.execute(
                "SELECT DISTINCT recipient FROM agent_messages WHERE parent_msg_id = ? AND status = 'pending'",
                (msg_id,)
            ).fetchall()
            for row in agents:
                notify_agent(row["recipient"])
        conn.commit()
    finally:
        conn.close()


def nack_message(msg_id: int, db_path: str, reason: str = "") -> None:
    """
    Nachricht als fehlgeschlagen markieren.
    Retry mit exponentiellem Backoff, max RETRY_MAX Versuche.
    Danach: Dead-Letter-Queue + Kaskade auf abhängige Messages.
    """
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT retry_count, sender, recipient FROM agent_messages WHERE id=?", (msg_id,)
        ).fetchone()

        if not row:
            return

        retries = row["retry_count"] + 1

        if retries >= RETRY_MAX:
            fail_dependent_messages(msg_id, "max_retries (%s)" % reason, conn)
            conn.commit()
            # GeneralAG benachrichtigen
            from gnom_hub.chat.chat_commands import _post_chat
            _post_chat("System", f"⚠️ Agent **{row['recipient']}** gescheitert an: {reason[:200]}")
        else:
            backoff = RETRY_BACKOFF_BASE * (2 ** (retries - 1))
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

        if not can_accept_message(target, conn):
            logger.warning(
                "dispatch_by_capability: Ziel '%s' kann keine weiteren Tasks annehmen",
                target
            )
            return None, None

        active_count = conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE recipient = ? AND status = 'processing'",
            (target,)
        ).fetchone()[0]

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
            WHERE status = 'processing' AND (processing_since <= ? OR processing_since IS NULL)
        """, (stuck_cutoff,)).fetchall()

        for row in rows:
            msg_id = row["id"]
            retries = row["retry_count"] + 1
            recipient = row["recipient"]

            if retries >= RETRY_MAX:
                conn.execute(
                    "UPDATE agent_messages SET status='dead_letter', retry_count=?, processing_since=NULL, completed_at=? WHERE id=?",
                    (retries, time.time(), msg_id)
                )
                # Auch abhängige Messages kaskadieren (retry_count bleibt unverändert)
                fail_dependent_messages(msg_id, "parent_stuck_retries_%d" % retries, conn)
                logger.error(
                    "Nachricht %d (Ziel=%s) zu oft blockiert – Kaskade ausgelöst",
                    msg_id, recipient
                )
            else:
                backoff = RETRY_BACKOFF_BASE * (2 ** (retries - 1))
                conn.execute("""
                    UPDATE agent_messages
                    SET status='pending', retry_count=?, deliver_after=?, processing_since=NULL
                    WHERE id=?
                """, (retries, now + backoff, msg_id))
                logger.warning(
                    "Nachricht %d (Ziel=%s) blockiert. Retry %d/%d in %.0fs",
                    msg_id, recipient, retries, RETRY_MAX, backoff
                )
                notify_agent(recipient)

        conn.commit()
    finally:
        conn.close()


def fail_dependent_messages(msg_id: int, reason: str, conn: sqlite3.Connection) -> None:
    """Schickt msg_id + den gesamten Abhängigkeitsbaum in die DLQ.

    Verwendet einen einzelnen rekursiven CTE, um alle transitiven Abhängigkeiten
    zu sammeln, und aktualisiert sie in einem einzigen UPDATE. Das vermeidet
    N Einzel-Updates (wie die alte rekursive Version) und skaliert auf tiefe
    Chains.

    Eine 'done'-Message wird nicht überschrieben (WHERE status != 'done'),
    aber ihre Children werden trotzdem in die DLQ geschickt.
    """
    now = time.time()
    affected = conn.execute("""
        WITH RECURSIVE dep_tree(id) AS (
            SELECT ?
            UNION ALL
            SELECT m.id FROM agent_messages m
            JOIN dep_tree ON m.parent_msg_id = dep_tree.id
        )
        UPDATE agent_messages
        SET status='dead_letter', completed_at=?
        WHERE status != 'done' AND id IN (SELECT id FROM dep_tree)
    """, (msg_id, now)).rowcount
    if affected:
        logger.error("%d Messages in DLQ (root=%d, reason=%s)", affected, msg_id, reason)
