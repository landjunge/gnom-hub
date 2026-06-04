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

def create_workflow(name: str, tasks: List[Dict]) -> str:
    """
    Erstellt einen neuen Workflow und seine Tasks in der Datenbank.
    Gibt die erzeugte workflow_id (UUID) zurück.
    """
    workflow_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO workflows (id, name, status, created_at)
                VALUES (?, ?, 'pending', ?)
            """, (workflow_id, name, time.time()))
            
            for t in tasks:
                depends_on_json = json.dumps(t.get("depends_on", []))
                conn.execute("""
                    INSERT INTO workflow_tasks 
                        (workflow_id, task_id, capability, input_template, depends_on, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                """, (
                    workflow_id,
                    t["task_id"],
                    t["capability"],
                    t["input_template"],
                    depends_on_json,
                ))
        return workflow_id
    finally:
        conn.close()

def start_workflow(workflow_id: str) -> None:
    """
    Startet einen registrierten Workflow und evaluiert die ersten Tasks.
    """
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                UPDATE workflows
                SET status = 'running'
                WHERE id = ? AND status = 'pending'
            """, (workflow_id,))
        evaluate_workflow(workflow_id)
    finally:
        conn.close()

def get_task_output_text(result_str: Optional[str]) -> str:
    """
    Hilfsfunktion, um den lesbaren Text aus einem Agenten-Resultat zu extrahieren.
    """
    if not result_str:
        return ""
    try:
        data = json.loads(result_str)
        if isinstance(data, dict):
            # CoderAG/SoulAG etc. packen das Resultat in "content"
            return data.get("content", data.get("text", str(data)))
        return str(data)
    except Exception:
        return result_str

def evaluate_workflow(workflow_id: str) -> None:
    """
    Überprüft den Zustand eines Workflows und startet bereite Folge-Tasks.
    Markiert den Workflow als abgeschlossen oder fehlgeschlagen bei Bedarf.
    """
    conn = get_db_connection()
    try:
        # 1. Alle Tasks des Workflows laden
        tasks = conn.execute("""
            SELECT task_id, capability, input_template, depends_on, status, msg_id, result_json
            FROM workflow_tasks
            WHERE workflow_id = ?
        """, (workflow_id,)).fetchall()
        
        if not tasks:
            return
            
        task_map = {t["task_id"]: t for t in tasks}
        
        # 2. Prüfen, ob irgendein Task fehlgeschlagen ist -> dann bricht der Workflow ab
        any_failed = any(t["status"] == "failed" for t in tasks)
        if any_failed:
            with conn:
                conn.execute("""
                    UPDATE workflows
                    SET status = 'failed', completed_at = ?
                    WHERE id = ? AND status = 'running'
                """, (time.time(), workflow_id))
            logger.info("❌ [WORKFLOW ENGINE] Workflow %s als FEHLGESCHLAGEN markiert.", workflow_id)
            return

        # 3. Prüfen, ob alle Tasks abgeschlossen sind -> dann ist der Workflow fertig
        all_completed = all(t["status"] == "completed" for t in tasks)
        if all_completed:
            with conn:
                conn.execute("""
                    UPDATE workflows
                    SET status = 'completed', completed_at = ?
                    WHERE id = ? AND status = 'running'
                """, (time.time(), workflow_id))
            logger.info("✅ [WORKFLOW ENGINE] Workflow %s erfolgreich BEENDET.", workflow_id)
            return

        # 4. Nach bereiten Tasks suchen
        ready_tasks = []
        for t in tasks:
            if t["status"] != "pending":
                continue
                
            deps = json.loads(t["depends_on"])
            # Ein Task ist bereit, wenn alle seine Abhängigkeiten im Zustand 'completed' sind
            if all(task_map.get(dep) and task_map[dep]["status"] == "completed" for dep in deps):
                ready_tasks.append(t)
    finally:
        conn.close()

    # 5. Bereite Tasks starten (connection is closed, safe to call dispatch_by_capability)
    for rt in ready_tasks:
        # Input-Template interpolieren mit Ergebnissen der Abhängigkeiten
        deps = json.loads(rt["depends_on"])
        interpolate_args = {}
        for dep in deps:
            dep_task = task_map[dep]
            output_text = get_task_output_text(dep_task["result_json"])
            interpolate_args[dep] = output_text
            
        try:
            interpolated_text = rt["input_template"].format(**interpolate_args)
        except Exception as e:
            logger.error(
                "Error interpolating task %s input template: %s. Marking task as failed.",
                rt["task_id"], e
            )
            conn2 = get_db_connection()
            try:
                with conn2:
                    conn2.execute("""
                        UPDATE workflow_tasks
                        SET status = 'failed'
                        WHERE workflow_id = ? AND task_id = ?
                    """, (workflow_id, rt["task_id"]))
            finally:
                conn2.close()
            evaluate_workflow(workflow_id)
            return

        logger.info(
            "🚀 [WORKFLOW ENGINE] Starte Task '%s' für Workflow %s (Capability: %s)...",
            rt["task_id"], workflow_id, rt["capability"]
        )
        
        # Über Capability dispatchen
        target_agent, msg_id = dispatch_by_capability(
            sender="GeneralAG",
            task_type=rt["capability"],
            text=interpolated_text,
            context_id=workflow_id,
            db_path=str(DB_PATH)
        )
        
        conn2 = get_db_connection()
        try:
            if target_agent and msg_id:
                with conn2:
                    conn2.execute("""
                        UPDATE workflow_tasks
                        SET status = 'running', msg_id = ?
                        WHERE workflow_id = ? AND task_id = ?
                    """, (msg_id, workflow_id, rt["task_id"]))
            else:
                logger.error(
                    "Failed to dispatch capability %s for task %s in workflow %s. Marking task as failed.",
                    rt["capability"], rt["task_id"], workflow_id
                )
                with conn2:
                    conn2.execute("""
                        UPDATE workflow_tasks
                        SET status = 'failed'
                        WHERE workflow_id = ? AND task_id = ?
                    """, (workflow_id, rt["task_id"]))
                conn2.close()
                evaluate_workflow(workflow_id)
                return
        finally:
            conn2.close()

def handle_task_completion(msg_id: int, result: dict) -> None:
    """
    Wird aufgerufen, wenn ein Callback für einen Workflow-Task eingeht.
    Findet den Task über msg_id und aktualisiert seinen Status.
    """
    conn = get_db_connection()
    try:
        task = conn.execute("""
            SELECT workflow_id, task_id
            FROM workflow_tasks
            WHERE msg_id = ?
        """, (msg_id,)).fetchone()
        
        if not task:
            return
            
        workflow_id = task["workflow_id"]
        task_id = task["task_id"]
        
        status = "completed" if result.get("status") != "error" else "failed"
        result_json_str = json.dumps(result)
        
        logger.info(
            "📥 [WORKFLOW ENGINE] Task '%s' in Workflow %s fertiggestellt mit Status: %s",
            task_id, workflow_id, status
        )
        
        with conn:
            conn.execute("""
                UPDATE workflow_tasks
                SET status = ?, result_json = ?
                WHERE workflow_id = ? AND task_id = ?
            """, (status, result_json_str, workflow_id, task_id))
            
        # Workflow re-evaluieren
        evaluate_workflow(workflow_id)
    finally:
        conn.close()
