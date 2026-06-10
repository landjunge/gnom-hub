import sqlite3
import json
import uuid
import time
import logging
from typing import List, Dict, Optional, Tuple
from gnom_hub.db.connection import get_db_connection
from gnom_hub.agents.swarm.swarm_comms import dispatch_by_capability
from gnom_hub.core.config import DB_PATH

logger = logging.getLogger(__name__)

# ── Konfiguration ───────────────────────────────────────────────────────────
MAX_RETRIES     = 2                    # Max. Wiederholungen bei transienten Fehlern
RETRY_DELAY_S   = 30.0                 # Sekunden zwischen Retries
STUCK_TIMEOUT_S = 300.0                # 5 Min — Task in 'running' ohne Update -> failed

# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _log_wf(workflow_id: str, msg: str, level: str = "info", task_id: str = ""):
    """Einheitliches Logging mit Kontext."""
    ctx = f"[WF:{workflow_id[:8]}]"
    if task_id:
        ctx += f"[T:{task_id[:20]}]"
    getattr(logger, level)(f"{ctx} {msg}")


def get_task_output_text(result_str: Optional[str]) -> str:
    """Extrahiert Text aus einem Agenten-Resultat (Content/Text/Summary)."""
    if not result_str:
        return ""
    if isinstance(result_str, dict):
        return result_str.get("content", result_str.get("text", result_str.get("summary",
               result_str.get("result", str(result_str)))))
    try:
        data = json.loads(result_str)
        if isinstance(data, dict):
            return data.get("content", data.get("text", data.get("summary",
                   data.get("result", str(data)))))
        return str(data)
    except (json.JSONDecodeError, TypeError):
        return str(result_str)


def interpolate_template(template: str, variables: Dict[str, str]) -> str:
    """
    Erweiterte Interpolation:
    {task_id}            → kompletter Output-Text
    {task_id:content}    → content-Feld aus result_json
    {task_id:status}     → status-Feld
    {task_id:error}      → error-Feld
    {task_id:data.x.y}   → nested: result["data"]["x"]["y"]
    Fallback: unersetzte Platzhalter bleiben erhalten.
    """
    import re as _re
    result = template

    def _deep_get(d, path):
        for key in path.split('.'):
            if isinstance(d, dict):
                if key not in d:
                    return ""
                d = d[key]
            else:
                return str(d)
        return str(d) if d else ""

    for match in _re.finditer(r'\{(\w+)(?::([\w.]+))?\}', template):
        full   = match.group(0)
        var    = match.group(1)
        field  = match.group(2)

        if var not in variables:
            continue

        val = variables[var]
        if isinstance(val, dict):
            if field:
                result = result.replace(full, _deep_get(val, field))
            else:
                result = result.replace(full,
                    val.get("content", val.get("text", val.get("summary",
                    val.get("result", str(val))))))
        elif isinstance(val, str):
            result = result.replace(full, val if field is None else "")
        else:
            result = result.replace(full, str(val))

    return result


def _get_workflow_name(workflow_id: str) -> str:
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT name FROM workflows WHERE id=?", (workflow_id,)).fetchone()
        return row["name"] if row else ""
    finally:
        conn.close()


def _get_context_id(tasks: list) -> str:
    for t in tasks:
        try:
            inp = json.loads(t.get("input_template", "{}")) if isinstance(t.get("input_template"), str) else {}
            if isinstance(inp, dict) and inp.get("context_id"):
                return inp["context_id"]
        except Exception:
            pass
    return ""


def _record_wf_result(workflow_id: str, task_chain: list, overall_result: str,
                       failed_at_task: str = None):
    try:
        from gnom_hub.soul.memory_layers import get_coordination_db
        conn = get_db_connection()
        try:
            wf = conn.execute("SELECT name, created_at FROM workflows WHERE id=?", (workflow_id,)).fetchone()
            if not wf:
                return
            start = wf["created_at"] or time.time()
            tasks = conn.execute(
                "SELECT capability, status FROM workflow_tasks WHERE workflow_id=?", (workflow_id,)
            ).fetchall()
            capabilities = [t["capability"] for t in tasks]
        finally:
            conn.close()

        get_coordination_db().record_workflow(
            workflow_id=workflow_id,
            context_id="",
            name=wf["name"],
            task_chain=capabilities,
            overall_result=overall_result,
            duration_s=time.time() - start,
            failed_at_task=failed_at_task,
            failure_reason=None,
        )
    except Exception as e:
        logger.warning("Failed to record workflow result: %s", e)


# ── Core Workflow Functions ─────────────────────────────────────────────────

def create_workflow(name: str, tasks: List[Dict]) -> str:
    """Erstellt einen neuen Workflow mit Tasks. Gibt workflow_id zurück."""
    workflow_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO workflows (id, name, status, created_at)
                VALUES (?, ?, 'pending', ?)
            """, (workflow_id, name, time.time()))
            for t in tasks:
                deps_json = json.dumps(t.get("depends_on", []))
                conn.execute("""
                    INSERT INTO workflow_tasks
                        (workflow_id, task_id, capability, input_template, depends_on, status, retry_count)
                    VALUES (?, ?, ?, ?, ?, 'pending', 0)
                """, (
                    workflow_id, t["task_id"], t["capability"],
                    t["input_template"], deps_json,
                ))
        _log_wf(workflow_id, f"Created with {len(tasks)} tasks: {name}")
        return workflow_id
    finally:
        conn.close()


def start_workflow(workflow_id: str) -> None:
    """Startet einen Workflow und evaluiert bereite Tasks."""
    conn = get_db_connection()
    try:
        with conn:
            row = conn.execute(
                "UPDATE workflows SET status='running' WHERE id=? AND status='pending'",
                (workflow_id,)
            )
            if row.rowcount:
                _log_wf(workflow_id, "STARTED")
    finally:
        conn.close()
    evaluate_workflow(workflow_id)


def evaluate_workflow(workflow_id: str) -> None:
    """
    Evaluiert den Workflow-Status:
    - Erkennt fehlgeschlagene Tasks → Workflow FAILED
    - Erkennt stuck Tasks (running > STUCK_TIMEOUT_S) → Task FAILED
    - Findet bereite Tasks → startet diese
    - Prüft auf Completion
    """
    conn = get_db_connection()
    try:
        # Workflow-Status prüfen
        wf = conn.execute(
            "SELECT status FROM workflows WHERE id=?", (workflow_id,)
        ).fetchone()
        if not wf or wf["status"] in ("completed", "failed"):
            return

        tasks = conn.execute("""
            SELECT task_id, capability, input_template, depends_on,
                   status, msg_id, result_json, retry_count
            FROM workflow_tasks
            WHERE workflow_id = ?
        """, (workflow_id,)).fetchall()

        if not tasks:
            return

        task_map = {t["task_id"]: t for t in tasks}
        now = time.time()

        # 1. Stuck-Task-Erkennung: 'running' + kein Update in STUCK_TIMEOUT_S
        stuck_found = False
        for t in tasks:
            if t["status"] == "running" and t["msg_id"]:
                msg = conn.execute(
                    "SELECT created_at, processing_since FROM agent_messages WHERE id=?",
                    (t["msg_id"],)
                ).fetchone()
                if msg:
                    ts = msg["processing_since"] or msg["created_at"] or 0
                    if (now - ts) > STUCK_TIMEOUT_S:
                        _log_wf(workflow_id, f"Task {t['task_id']} stuck ({int(now-ts)}s) -> FAILED", "warning")
                        summary = f"[STUCK] No update for {int(now-ts)}s"
                        with conn:
                            conn.execute(
                                "UPDATE workflow_tasks SET status='failed', result_json=?, error_summary=? WHERE workflow_id=? AND task_id=?",
                                (json.dumps({"error": "stuck_timeout", "elapsed_s": now - ts}),
                                 summary, workflow_id, t["task_id"])
                            )
                        stuck_found = True
        if stuck_found:
            conn.commit()
            tasks = conn.execute("""
                SELECT task_id, capability, input_template, depends_on,
                       status, msg_id, result_json, retry_count
                FROM workflow_tasks WHERE workflow_id = ?
            """, (workflow_id,)).fetchall()
            task_map = {t["task_id"]: t for t in tasks}

        # 2. Prüfen, ob irgendein Task fehlgeschlagen ist
        task_chain = [t["capability"] for t in tasks]
        any_failed = any(t["status"] == "failed" for t in tasks)
        if any_failed:
            failed_task = next((t["task_id"] for t in tasks if t["status"] == "failed"), None)
            with conn:
                conn.execute(
                    "UPDATE workflows SET status='failed', completed_at=? WHERE id=? AND status='running'",
                    (time.time(), workflow_id)
                )
            _log_wf(workflow_id, f"ABORTED — failed at {failed_task}", "error")
            _record_wf_result(workflow_id, task_chain, "failed", failed_at_task=failed_task)
            return

        # 3. Alle Tasks completed?
        all_completed = all(t["status"] == "completed" for t in tasks)
        if all_completed:
            with conn:
                conn.execute(
                    "UPDATE workflows SET status='completed', completed_at=? WHERE id=? AND status='running'",
                    (time.time(), workflow_id)
                )
            _log_wf(workflow_id, "COMPLETED successfully", "info")
            _record_wf_result(workflow_id, task_chain, "success")
            return

        # 4. Tasks finden, die bereit zum Start sind
        ready_tasks = []
        for t in tasks:
            if t["status"] != "pending":
                continue
            deps = json.loads(t["depends_on"])
            deps_met = all(
                task_map.get(d) and task_map[d]["status"] == "completed"
                for d in deps
            )
            if deps_met:
                ready_tasks.append(t)
    finally:
        conn.close()

    # 5. Bereite Tasks starten (DB-Verbindung ist zu)
    for rt in ready_tasks:
        # Interpolation: Baue Variablen-Dict aus Abhängigkeits-Ergebnissen
        deps = json.loads(rt["depends_on"])
        variables = {}
        deps_failed = False
        for dep in deps:
            dep_task = task_map.get(dep)
            if not dep_task:
                deps_failed = True
                break
            output = get_task_output_text(dep_task["result_json"])
            variables[dep] = output

        if deps_failed:
            _log_wf(workflow_id, f"Dependency {dep} not found for task {rt['task_id']}", "error")
            conn2 = get_db_connection()
            try:
                with conn2:
                    conn2.execute(
                        "UPDATE workflow_tasks SET status='failed' WHERE workflow_id=? AND task_id=?",
                        (workflow_id, rt["task_id"])
                    )
            finally:
                conn2.close()
            evaluate_workflow(workflow_id)
            return

        interpolated = interpolate_template(rt["input_template"], variables)

        _log_wf(workflow_id, f"Dispatching task {rt['task_id']} via capability={rt['capability']}",
                task_id=rt["task_id"])

        target_agent, msg_id = dispatch_by_capability(
            sender="GeneralAG",
            task_type=rt["capability"],
            text=interpolated,
            context_id=workflow_id,
            db_path=str(DB_PATH)
        )

        conn2 = get_db_connection()
        try:
            if target_agent and msg_id:
                with conn2:
                    conn2.execute(
                        "UPDATE workflow_tasks SET status='running', msg_id=? WHERE workflow_id=? AND task_id=?",
                        (msg_id, workflow_id, rt["task_id"])
                    )
                _log_wf(workflow_id, f"Task {rt['task_id']} RUNNING -> {target_agent}", task_id=rt["task_id"])
            else:
                _log_wf(workflow_id, f"DISPATCH FAILED for task {rt['task_id']} (cap={rt['capability']})", "error")
                with conn2:
                    conn2.execute(
                        "UPDATE workflow_tasks SET status='failed', result_json=?, error_summary=? WHERE workflow_id=? AND task_id=?",
                        (json.dumps({"error": "dispatch_failed", "capability": rt["capability"]}),
                         f"[DISPATCH] No agent for capability '{rt['capability']}'",
                         workflow_id, rt["task_id"])
                    )
                evaluate_workflow(workflow_id)
                return
        finally:
            conn2.close()


def handle_task_completion(msg_id: int, result: dict) -> None:
    """
    Callback: Wird von swarm_comms aufgerufen wenn ein Workflow-Task fertig ist.
    Idempotent: doppelte Aufrufe haben keine Wirkung.
    """
    if not msg_id:
        return

    conn = get_db_connection()
    try:
        task = conn.execute("""
            SELECT workflow_id, task_id, status, retry_count
            FROM workflow_tasks WHERE msg_id = ?
        """, (msg_id,)).fetchone()

        if not task:
            return

        workflow_id = task["workflow_id"]
        task_id     = task["task_id"]
        current     = task["status"]

        # Idempotenz: wenn bereits completed oder failed -> nichts tun
        if current in ("completed", "failed"):
            _log_wf(workflow_id, f"Task {task_id} already {current} — idempotent skip", "debug", task_id)
            return

        is_error = result.get("status") == "error"
        result_json_str = json.dumps(result) if isinstance(result, dict) else json.dumps({"content": str(result)})

        if is_error:
            error_msg = result.get("error", result.get("message", "Unknown error"))
            summary = f"[ERROR] {error_msg}"[:200]
            with conn:
                conn.execute(
                    "UPDATE workflow_tasks SET status='failed', result_json=?, error_summary=? WHERE workflow_id=? AND task_id=?",
                    (result_json_str, summary, workflow_id, task_id)
                )
            _log_wf(workflow_id, f"Task {task_id} FAILED: {summary}", "error", task_id)
        else:
            status = "completed"
            with conn:
                conn.execute(
                    "UPDATE workflow_tasks SET status='completed', result_json=? WHERE workflow_id=? AND task_id=?",
                    (result_json_str, workflow_id, task_id)
                )
            _log_wf(workflow_id, f"Task {task_id} COMPLETED", task_id=task_id)

        evaluate_workflow(workflow_id)

    finally:
        conn.close()


def recover_stuck_workflows() -> int:
    """
    Globale Recovery: Findet Workflows, die schon lange in 'running' sind
    und stoppt sie (setzt auf 'failed').
    Wird vom Watchdog periodisch aufgerufen.
    Gibt Anzahl der recovered Workflows zurück.
    """
    recovered = 0
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT id, name FROM workflows WHERE status='running'
        """).fetchall()
        for wf in rows:
            # Prüfe ob alle Tasks entweder completed oder failed sind
            tasks = conn.execute("""
                SELECT status FROM workflow_tasks WHERE workflow_id=?
            """, (wf["id"],)).fetchall()
            if not tasks:
                continue
            statuses = {t["status"] for t in tasks}
            # Wenn keine 'running' oder 'pending' Tasks mehr übrig sind
            if "running" not in statuses and "pending" not in statuses:
                if "failed" in statuses:
                    conn.execute(
                        "UPDATE workflows SET status='failed', completed_at=? WHERE id=?",
                        (time.time(), wf["id"])
                    )
                    _record_wf_result(wf["id"], [], "failed")
                else:
                    conn.execute(
                        "UPDATE workflows SET status='completed', completed_at=? WHERE id=?",
                        (time.time(), wf["id"])
                    )
                    _record_wf_result(wf["id"], [], "success")
                recovered += 1
                _log_wf(wf["id"], f"Recovered (orphan cleanup): {wf['name']}", "warning")
        if recovered:
            conn.commit()
    finally:
        conn.close()
    return recovered
