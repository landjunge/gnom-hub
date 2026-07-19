import json
import logging
import re
import sqlite3
import threading
import time

from gnom_hub.db.connection import get_db_connection

PRIORITY_MAPPING = {
    "critical": 1,
    "high": 3,
    "normal": 5,
    "low": 7
}


logger = logging.getLogger(__name__)

# ── Konfiguration (statt Magic Numbers im Code) ────────────────────────────
MAX_DEPTH           = 15
MAX_CONCURRENT      = 2       # hard cap concurrent jobs per agent (Wave A)
RETRY_MAX           = 3
RETRY_BACKOFF_BASE  = 3.0
MAX_QUEUE_DEPTH     = 20      # Wave A: prevent pending storms (was 100)
STALE_PENDING_S     = 600.0   # Auto-DLQ pending older than 10 min
STALE_PROCESSING_S  = 300.0   # Align recover default
DEPENDENCY_TIMEOUT  = 120.0
DEPENDENCY_POLL_S   = 1.0

# ── Notification-Bus: Agenten warten auf dieses Event statt zu pollen ──────
_new_message_event: dict[str, threading.Event] = {}
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
        logger.warning(
            "Concurrent-Limit Agent '%s': %d processing (Limit %d) – abgelehnt",
            agent_name, active, MAX_CONCURRENT
        )
        return False
    return True


def parse_agent_sequence(text: str) -> list[tuple[str, str]]:
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
) -> list[str]:
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


def find_best_agent_for_task(task: str, conn: sqlite3.Connection) -> str | None:
    """
    3-stufige Agent-Auswahl:
    1. coordination.db — Erfolgsrate + Fehlerhistorie (lernt aus echten Jobs)
    2. agent_capabilities — Confidence-Score + Queue-Tiefe
    3. Keyword-Heuristik — letzter Fallback
    """
    task_lower = task.lower()

    # Capability → Task-Keyword Mapping
    keywords = {
        "code_generation":  ["code", "schreib", "python", "html", "js", "script", "programm", "implementier", "bash"],
        "web_research":     ["recherchier", "suche", "finde", "google", "research", "analyse"],
        "content_creation": ["text", "artikel", "blog", "slogan", "schreib", "dokument", "doc"],
        "editing":          ["korrigier", "review", "prüf", "lektorat", "refaktor", "edit"],
        "summarization":    ["zusammenfass", "summary", "kurzfass"],
        "security_audit":   ["sicherheit", "security", "audit", "vulnerab", "scan"],
    }

    # Welche Capabilities passen zum Task?
    matched_caps = [cap for cap, words in keywords.items() if any(w in task_lower for w in words)]

    # 1. coordination.db — Erfolgsrate entscheidet
    if matched_caps:
        try:
            from gnom_hub.soul.memory_layers import get_coordination_db
            coord = get_coordination_db()
            import sqlite3 as _sq
            with _sq.connect(str(coord._path)) as cdb:
                cdb.row_factory = _sq.Row
                # Agenten mit Jobs in den letzten 7 Tagen — nach Erfolgsrate sortiert
                # Nur Agenten nehmen die auch online/busy sind
                rows = cdb.execute("""
                    SELECT ws.agent_name,
                           ws.total_jobs,
                           ws.successful_jobs,
                           ws.failed_jobs,
                           CASE WHEN ws.total_jobs > 0
                                THEN CAST(ws.successful_jobs AS REAL) / ws.total_jobs
                                ELSE 0.5
                           END AS success_rate
                    FROM worker_stats ws
                    WHERE ws.total_jobs >= 2
                    ORDER BY success_rate DESC, ws.total_jobs DESC
                """).fetchall()

            for row in rows:
                agent_name = row["agent_name"]
                # Ist dieser Agent online?
                a_row = conn.execute(
                    "SELECT name FROM agents WHERE name = ? AND status IN ('online','busy','running')",
                    (agent_name,)
                ).fetchone()
                if not a_row:
                    continue
                # Hat dieser Agent eine passende Capability?
                for cap in matched_caps:
                    cap_row = conn.execute(
                        "SELECT agent_name FROM agent_capabilities WHERE agent_name = ? AND capability = ?",
                        (agent_name, cap)
                    ).fetchone()
                    if cap_row:
                        # Schlechte Erfolgsrate (<40%) → überspringen, nächsten nehmen
                        if row["success_rate"] < 0.4 and row["total_jobs"] >= 5:
                            logger.warning(
                                "[Routing] %s übersprungen (Erfolgsrate %.0f%% bei %d Jobs)",
                                agent_name, row["success_rate"] * 100, row["total_jobs"]
                            )
                            break
                        logger.info(
                            "[Routing] %s gewählt via coordination.db (%.0f%% Erfolg, %d Jobs)",
                            agent_name, row["success_rate"] * 100, row["total_jobs"]
                        )
                        return agent_name
        except Exception as e:
            logger.debug("[Routing] coordination.db Fehler: %s", e)

    # 2. agent_capabilities — Confidence + Queue-Tiefe
    for cap in matched_caps:
        row = conn.execute("""
            SELECT ac.agent_name
            FROM agent_capabilities ac
            JOIN agents a ON a.name = ac.agent_name AND a.status IN ('online','busy','running')
            LEFT JOIN (
                SELECT recipient, COUNT(*) AS pending_count
                FROM agent_messages WHERE status = 'pending'
                GROUP BY recipient
            ) q ON q.recipient = ac.agent_name
            WHERE ac.capability = ?
            ORDER BY COALESCE(q.pending_count, 0) ASC, ac.confidence DESC
            LIMIT 1
        """, (cap,)).fetchone()
        if row:
            logger.info("[Routing] %s gewählt via agent_capabilities (%s)", row["agent_name"], cap)
            return row["agent_name"]

    # 3. Keyword-Heuristik — letzter Fallback
    agent_hints = {
        "coderag":     ["code", "python", "html", "js", "create", "erstell", "bau", "implementier", "script"],
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
                logger.info("[Routing] %s gewählt via Keyword-Heuristik", row["name"])
                return row["name"]

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


def _slice_text_for_mention(text: str, mention: str) -> str:
    """Focus multi-@ blasts so each worker only gets *their* task slice.

    GeneralAG often writes one big plan with @ResearcherAG … @CoderAG … and
    previously every worker received the full plan → wait-for-each-other stalls
    (SUPERVISOR-R2). Prefer the segment starting at @Agent until the next @Agent.
    """
    clean = text or ""
    matches = list(re.finditer(r"@(\w+)", clean))
    if not matches:
        return clean
    mention_l = mention.lower()
    for i, m in enumerate(matches):
        if m.group(1).lower() != mention_l:
            continue
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(clean)
        slice_ = clean[start:end].strip()
        # Drop other @mentions that might remain at edges
        if len(slice_) >= 20:
            return slice_
    # Fallback: single-line containing @mention
    for line in clean.splitlines():
        if re.search(rf"@{re.escape(mention)}\b", line, re.I):
            return line.strip()
    return clean


def dispatch_mention(
    sender: str,
    text: str,
    context_id: str,
    db_path: str,
    current_depth: int = 0,
    parent_msg_id: int | None = None,
    priority: str | int | None = None,
) -> list[str]:
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

    dispatched: list[str] = []
    last_err = None
    from gnom_hub.db.db_lock import cross_process_write_lock

    for _attempt in range(5):
        conn = None
        try:
            with cross_process_write_lock(timeout_s=8.0):
                conn = get_db_connection()
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

                for mention in set(mentions):
                    tgt_lower = mention.lower()

                    if tgt_lower == sender.lower():
                        continue

                    if tgt_lower in offline_agents:
                        logger.info("Agent '%s' offline – Nachricht wird verworfen", mention)
                        continue

                    if tgt_lower not in agent_map:
                        logger.debug("Unbekannter Agent: @%s", mention)
                        continue

                    tgt_name = agent_map[tgt_lower]

                    is_critical = (
                        (isinstance(priority, str) and priority.lower() == "critical")
                        or priority == 0
                    )

                    if not is_critical and not can_accept_message(tgt_name, conn):
                        continue

                    if is_critical:
                        prio_val = 0
                    else:
                        active_count = conn.execute(
                            "SELECT COUNT(*) FROM agent_messages WHERE recipient = ? AND status = 'processing'",
                            (tgt_name,),
                        ).fetchone()[0]
                        prio_val = None
                        if priority is not None:
                            if isinstance(priority, str):
                                prio_val = PRIORITY_MAPPING.get(priority.lower(), 5)
                            elif isinstance(priority, int):
                                prio_val = priority
                        if prio_val is None:
                            prio_val = 7 if active_count >= MAX_CONCURRENT else 5

                    agent_text = _slice_text_for_mention(clean_text, mention)
                    conn.execute(
                        """
                        INSERT INTO agent_messages
                            (sender, recipient, payload, priority, created_at,
                             deliver_after, context_id, depth, parent_msg_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sender,
                            tgt_name,
                            json.dumps({"text": agent_text, "mention": mention}),
                            prio_val,
                            time.time(),
                            0.0,
                            context_id,
                            current_depth,
                            parent_msg_id,
                        ),
                    )
                    conn.commit()
                    notify_agent(tgt_name)
                    dispatched.append(tgt_name)

            last_err = None
            break
        except sqlite3.OperationalError as e:
            last_err = e
            if "locked" not in str(e).lower():
                logger.error("dispatch_mention failed: %s", e)
                raise
            # retry with backoff
            time.sleep(0.12 * (_attempt + 1))
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    if last_err is not None and not dispatched:
        logger.error("dispatch_mention failed after retries: %s", last_err)
        raise last_err
    return dispatched


def fetch_next_message(
    agent_name: str,
    db_path: str,
    timeout: float = 30.0,
) -> dict | None:
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
            try:
                conn.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as _le:
                # Never crash the agent loop on lock — wait and poll again.
                if "locked" in str(_le).lower():
                    conn.close()
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        return None
                    evt.wait(timeout=min(remaining, 0.5))
                    evt.clear()
                    continue
                raise
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
                            fail_dependent_messages(row["id"], f"parent_msg_id={parent_id} in dead_letter", conn)
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
                                    fail_dependent_messages(parent_id, f"DEPENDENCY_TIMEOUT={DEPENDENCY_TIMEOUT:.0f}s", conn)
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
            fail_dependent_messages(msg_id, f"max_retries ({reason})", conn)
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


def process_swarm_mentions(sender: str, text: str, depth: int = 0, parent_msg_id: int | None = None):
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


def find_best_agent_for(task_type: str, conn: sqlite3.Connection) -> str | None:
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
    parent_msg_id: int | None = None,
    priority: str | int | None = None,
) -> tuple[str | None, int | None]:
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


def recover_stuck_messages(db_path: str, timeout: float = 120.0) -> None:
    """
    Findet blockierte/abgestürzte Nachrichten und gibt sie wieder frei oder schiebt sie in die DLQ.
    Wave A: also auto-DLQ stale pending (storm leftovers).
    Supervisor-Fix 2026-07: default timeout 120s (was 300s); chat notify on requeue/DLQ.
    """
    from gnom_hub.db.db_lock import cross_process_write_lock

    chat_notes: list[str] = []
    with cross_process_write_lock(timeout_s=10.0):
        conn = get_db_connection()
        try:
            try:
                conn.execute("PRAGMA busy_timeout=10000")
            except Exception:
                pass
            now = time.time()
            stuck_cutoff = now - timeout
            rows = conn.execute("""
                SELECT id, retry_count, recipient, sender, substr(payload,1,120) AS p
                FROM agent_messages
                WHERE status = 'processing'
                  AND (
                        (processing_since IS NOT NULL AND processing_since <= ?)
                     OR (processing_since IS NULL AND created_at <= ?)
                  )
            """, (stuck_cutoff, stuck_cutoff)).fetchall()

            for row in rows:
                msg_id = row["id"]
                retries = row["retry_count"] + 1
                recipient = row["recipient"]
                sender = row["sender"] or "?"

                if retries >= RETRY_MAX:
                    conn.execute(
                        "UPDATE agent_messages SET status='dead_letter', retry_count=?, processing_since=NULL, completed_at=? WHERE id=?",
                        (retries, time.time(), msg_id)
                    )
                    fail_dependent_messages(msg_id, f"parent_stuck_retries_{retries}", conn)
                    logger.error(
                        "Nachricht %d (Ziel=%s) zu oft blockiert – Kaskade ausgelöst",
                        msg_id, recipient
                    )
                    chat_notes.append(
                        f"⚠️ **Queue DLQ:** msg #{msg_id} {sender}→{recipient} "
                        f"nach {retries} Retries stecken geblieben (> {int(timeout)}s processing)."
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
                    if retries >= 2:
                        chat_notes.append(
                            f"♻️ **Queue Retry:** msg #{msg_id} {sender}→{recipient} "
                            f"Retry {retries}/{RETRY_MAX} (stuck > {int(timeout)}s)."
                        )

            # Wave A: pending older than STALE_PENDING_S → dead_letter
            stale_pending = now - STALE_PENDING_S
            n_stale = conn.execute("""
                UPDATE agent_messages
                SET status='dead_letter', completed_at=?, retry_count=retry_count
                WHERE status='pending' AND created_at <= ? AND deliver_after <= ?
            """, (now, stale_pending, now)).rowcount
            if n_stale:
                logger.warning(
                    "Auto-DLQ: %d stale pending messages (>%ss)", n_stale, int(STALE_PENDING_S)
                )

            cap = MAX_QUEUE_DEPTH * 8
            total_pending = conn.execute(
                "SELECT COUNT(*) FROM agent_messages WHERE status='pending'"
            ).fetchone()[0]
            if total_pending > cap:
                excess = total_pending - cap
                conn.execute("""
                    UPDATE agent_messages SET status='dead_letter', completed_at=?
                    WHERE id IN (
                        SELECT id FROM agent_messages
                        WHERE status='pending'
                        ORDER BY created_at ASC
                        LIMIT ?
                    )
                """, (now, excess))
                logger.warning("Auto-DLQ: %d excess pending over global cap %d", excess, cap)

            conn.commit()
        finally:
            conn.close()

    # Chat notify outside lock (best-effort)
    if chat_notes:
        try:
            from gnom_hub.db import add_chat_message, get_active_project
            proj = get_active_project() or "default"
            for note in chat_notes[:5]:
                add_chat_message(
                    proj, "System", "system", "chat", note,
                    {"type": "chat", "sender": "System", "queue_recovery": True},
                )
        except Exception as e:
            logger.debug("stuck-recovery chat notify failed: %s", e)


def clear_queue(
    *,
    statuses: tuple[str, ...] = ("pending", "processing"),
    older_than_s: float | None = None,
    recipient: str | None = None,
) -> dict:
    """Admin/ops: move matching queue rows to dead_letter. Returns counts."""
    allowed = {"pending", "processing", "failed"}
    statuses = tuple(s for s in statuses if s in allowed) or ("pending",)
    conn = get_db_connection()
    try:
        now = time.time()
        # Fixed allow-list only — no user-controlled SQL fragments.
        if statuses == ("pending", "processing"):
            where = "status IN ('pending', 'processing')"
        elif statuses == ("pending",):
            where = "status = 'pending'"
        elif statuses == ("processing",):
            where = "status = 'processing'"
        else:
            where = "status = 'pending'"
        # where is a fixed allow-list string only (see branches above).
        sql = f"SELECT COUNT(*) FROM agent_messages WHERE {where}"  # noqa: S608
        params: list = []
        if older_than_s is not None:
            sql += " AND created_at <= ?"
            params.append(now - older_than_s)
        if recipient:
            sql += " AND lower(recipient)=lower(?)"
            params.append(recipient)
        before = conn.execute(sql, params).fetchone()[0]
        upd = f"UPDATE agent_messages SET status='dead_letter', completed_at=? WHERE {where}"  # noqa: S608
        uparams: list = [now]
        if older_than_s is not None:
            upd += " AND created_at <= ?"
            uparams.append(now - older_than_s)
        if recipient:
            upd += " AND lower(recipient)=lower(?)"
            uparams.append(recipient)
        n = conn.execute(upd, uparams).rowcount
        conn.commit()
        return {"moved_to_dlq": n, "matched": before, "statuses": list(statuses)}
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


# ── Deterministic Routing Wrapper (opt-in) ─────────────────────────────────
#
# ``dispatch_by_capability_with_resolution`` ist ein **dünner Wrapper** über
# :func:`dispatch_by_capability` — die Kernfunktion bleibt unverändert.
# Dieser Wrapper löst den Intent zuerst deterministisch auf (siehe
# :mod:`gnom_hub.agents.routing`) und benutzt dann die Whitelist-Filterung
# der existierenden Funktion. So entsteht eine Brücke zwischen LLM-Intent
# (``intent_text``) und der deterministischen Capability-Maschinerie, ohne
# den bisherigen Pfad zu brechen.


def dispatch_by_capability_with_resolution(
    sender: str,
    intent_text: str,
    text: str,
    context_id: str,
    db_path: str,
    available_capabilities: list[str] | None = None,
    node_resolver_fn=None,
    session_id: str = "default",
    current_depth: int = 0,
    parent_msg_id: int | None = None,
    priority: str | int | None = None,
) -> tuple[str | None, int | None]:
    """Wie :func:`dispatch_by_capability`, aber mit deterministischem Vor-Layer.

    Ablauf
    ------
    1. Wenn der Intent einen ``node_id`` enthält (Pattern ``^[a-f0-9]{8}$``),
       wird via :func:`gnom_hub.agents.routing.resolve_with_node_id` der
       Offload-Content geladen und als High-Confidence-Quelle benutzt.
    2. Sonst läuft :func:`gnom_hub.agents.routing.resolve_capability`.
    3. Das Ergebnis (``ResolvedCapability``) wird in eine
       Capability-Anforderung an ``dispatch_by_capability`` umgewandelt.
    4. Wenn die Auflösung ``("" , 0.0, "none")`` liefert, wird die
       Fallback-Chain (``general``) als Anforderung benutzt.

    Die Funktion modifiziert **nicht** :func:`dispatch_by_capability`.
    """
    # Lokale Imports zur Vermeidung von Zyklen beim Modul-Init.
    try:
        from gnom_hub.agents.routing import (
            build_fallback_chain as _build_chain,
        )
        from gnom_hub.agents.routing import (
            resolve_capability as _resolve_cap,
        )
        from gnom_hub.agents.routing import (
            resolve_with_node_id as _resolve_with_nid,
        )
    except Exception as _routing_exc:
        logger.debug("routing import failed; fallback to direct dispatch: %s", _routing_exc)
        # Wenn das Routing-Modul nicht verfügbar ist, verhalten wir uns wie
        # die Original-Funktion (general-Fallback).
        return dispatch_by_capability(
            sender, "general", text, context_id, db_path,
            current_depth, parent_msg_id, priority,
        )

    # Wenn keine ``available_capabilities`` übergeben wurden, aus der DB laden.
    if available_capabilities is None:
        try:
            from gnom_hub.db.connection import get_db_conn
            with get_db_conn() as _conn:
                _rows = _conn.execute(
                    "SELECT DISTINCT capability FROM agent_capabilities"
                ).fetchall()
                available_capabilities = [r["capability"] for r in _rows]
        except Exception as _db_exc:
            logger.debug("available_capabilities lookup failed: %s", _db_exc)
            available_capabilities = []

    # node_id-aware Resolver (Brücke zu Offload)
    if node_resolver_fn is None and session_id:
        try:
            from gnom_hub.memory.node_resolver import resolve_node as _rn_default

            def _node_resolver_factory(_sid: str):
                def _fn(nid: str) -> str | None:
                    return _rn_default(nid, _sid)
                return _fn

            node_resolver_fn = _node_resolver_factory(session_id)
        except Exception:
            node_resolver_fn = None

    try:
        resolved = _resolve_with_nid(
            intent_text,
            available_capabilities,
            node_resolver_fn=node_resolver_fn,
        )
    except Exception as _res_exc:
        logger.debug("resolve_with_node_id raised; fallback: %s", _res_exc)
        resolved = _resolve_cap(intent_text, available_capabilities)

    # Capability-Auswahl mit Fallback-Chain
    if resolved.source == "none" or not resolved.capability:
        chain = _build_chain("", available_capabilities)
        chosen = next((c for c in chain if c), "general")
    else:
        chosen = resolved.capability

    return dispatch_by_capability(
        sender=sender,
        task_type=chosen,
        text=text,
        context_id=context_id,
        db_path=db_path,
        current_depth=current_depth,
        parent_msg_id=parent_msg_id,
        priority=priority,
    )
