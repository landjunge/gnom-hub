import json
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from gnom_hub.db.connection import get_db_conn
from gnom_hub.agents.swarm.workflow_engine import create_workflow, start_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows")

# Reservierte Status-IDs für Task-Validierung
_VALID_TASK_STATUS = {"pending", "running", "completed", "failed"}


class TaskPayload(BaseModel):
    """Validierter Task-Payload für POST /api/workflows."""
    task_id: str = Field(..., min_length=1, max_length=120,
                          description="Eindeutige Task-ID innerhalb des Workflows")
    capability: str = Field(..., min_length=1, max_length=80,
                            description="Capability-Name (matched against agents)")
    input_template: str = Field(..., min_length=0, max_length=8000)
    depends_on: List[str] = Field(default_factory=list)


class WorkflowPayload(BaseModel):
    """POST /api/workflows Body. Validiert sich selbst via Pydantic v2."""
    name: str = Field(..., min_length=1, max_length=200)
    tasks: List[TaskPayload] = Field(..., min_length=1, max_length=200)

    @field_validator("tasks")
    @classmethod
    def _no_duplicate_task_ids(cls, tasks: List[TaskPayload]) -> List[TaskPayload]:
        """Stellt sicher, dass task_ids innerhalb des Workflows eindeutig sind."""
        seen = set()
        for t in tasks:
            if t.task_id in seen:
                raise ValueError(f"Duplicate task_id: {t.task_id!r}")
            seen.add(t.task_id)
        return tasks

    @field_validator("tasks")
    @classmethod
    def _no_self_dependency(cls, tasks: List[TaskPayload]) -> List[TaskPayload]:
        """Verhindert offensichtliche Selbst-Referenzen (A→A)."""
        for t in tasks:
            if t.task_id in t.depends_on:
                raise ValueError(
                    f"Task {t.task_id!r} depends on itself"
                )
        return tasks


def _safe_get_workflow_status(workflow_id: str) -> Optional[str]:
    """Liest den Workflow-Status aus der DB, None wenn nicht (mehr) vorhanden."""
    try:
        with get_db_conn() as conn:
            row = conn.execute(
                "SELECT status FROM workflows WHERE id=?", (workflow_id,)
            ).fetchone()
            return row["status"] if row else None
    except Exception as e:
        logger.warning("Could not read workflow %s status: %s", workflow_id, e)
        return None


@router.post("")
def api_create_workflow(payload: WorkflowPayload):
    """Erstellt einen Workflow und startet ihn sofort.

    Rückgabe-Codes:
      200 — workflow_id + finaler Status (created/running/completed/failed)
      422 — Pydantic-Validation-Fehler (leere tasks, ungültige Felder, …)
      500 — DB-/Interner Fehler
    """
    tasks_dicts = [
        {
            "task_id": t.task_id,
            "capability": t.capability,
            "input_template": t.input_template,
            "depends_on": t.depends_on,
        }
        for t in payload.tasks
    ]

    try:
        workflow_id = create_workflow(payload.name, tasks_dicts)
    except Exception as e:
        logger.exception("create_workflow failed for %r", payload.name)
        raise HTTPException(500, detail=f"Failed to create workflow: {e}")

    # Versuche zu starten. Wenn dispatch_by_capability fehlschlägt, bleibt der
    # Workflow als 'running' mit einem 'failed'-Task in der DB — der Aufrufer
    # sieht das im Response.
    dispatch_failed = False
    try:
        start_workflow(workflow_id)
    except Exception as e:
        logger.exception("start_workflow failed for %s", workflow_id)
        dispatch_failed = True

    final_status = _safe_get_workflow_status(workflow_id) or "unknown"

    # Wenn die Workflow-Engine den Workflow nach start_workflow als 'failed'
    # markiert hat (weil dispatch_by_capability keinen Agenten fand), ist das
    # ein logischer Dispatch-Fehler — auch wenn keine Exception geflogen ist.
    if final_status == "failed":
        dispatch_failed = True

    body = {
        "status": "success",
        "workflow_id": workflow_id,
        "workflow_status": final_status,
        "task_count": len(payload.tasks),
        "dispatch_failed": dispatch_failed,
    }
    # Wenn dispatch fehlgeschlagen ist UND der Workflow in 'failed' übergegangen
    # ist, gib das im Response mit, damit das Frontend es anzeigen kann.
    if dispatch_failed or final_status == "failed":
        body["status"] = "partial"
    return body


@router.get("/{workflow_id}")
def api_get_workflow(workflow_id: str):
    """Detail-View: Workflow + alle Tasks.

    Schema (vom Frontend in dashboard.js:3206-3215 erwartet):
      {
        id, name, status, created_at, completed_at,
        tasks: [{task_id, capability, input_template, depends_on,
                 status, msg_id, result, error_summary}]
      }
    """
    with get_db_conn() as conn:
        wf = conn.execute("""
            SELECT id, name, status, created_at, completed_at
            FROM workflows
            WHERE id = ?
        """, (workflow_id,)).fetchone()

        if not wf:
            raise HTTPException(404, detail="Workflow not found")

        tasks = conn.execute("""
            SELECT task_id, capability, input_template, depends_on, status,
                   msg_id, result_json, error_summary
            FROM workflow_tasks
            WHERE workflow_id = ?
        """, (workflow_id,)).fetchall()

        tasks_list = []
        for t in tasks:
            res_val = None
            if t["result_json"]:
                try:
                    res_val = json.loads(t["result_json"])
                except Exception:
                    res_val = t["result_json"]

            # depends_on kann String/None/Array sein — robust parsen
            depends_on_raw = t["depends_on"]
            depends_on_val: List[str] = []
            if depends_on_raw:
                try:
                    parsed = json.loads(depends_on_raw)
                    if isinstance(parsed, list):
                        depends_on_val = [str(x) for x in parsed]
                    else:
                        depends_on_val = [str(parsed)]
                except Exception:
                    depends_on_val = []

            tasks_list.append({
                "task_id": t["task_id"],
                "capability": t["capability"] or "",
                "input_template": t["input_template"] or "",
                "depends_on": depends_on_val,
                "status": t["status"] or "pending",
                "msg_id": t["msg_id"],
                "result": res_val,
                "error_summary": t["error_summary"],
            })

        return {
            "id": wf["id"],
            "name": wf["name"],
            "status": wf["status"] or "pending",
            "created_at": wf["created_at"],
            "completed_at": wf["completed_at"],
            "tasks": tasks_list,
        }


@router.get("")
def api_list_workflows():
    """Listet alle Workflows (neueste zuerst)."""
    with get_db_conn() as conn:
        rows = conn.execute("""
            SELECT id, name, status, created_at, completed_at
            FROM workflows
            ORDER BY created_at DESC
        """).fetchall()
        # created_at kann Unix-ts (float) oder ISO-String sein — normalisieren
        out = []
        for r in rows:
            d = dict(r)
            out.append({
                "id": d.get("id"),
                "name": d.get("name"),
                "status": d.get("status") or "pending",
                "created_at": d.get("created_at"),
                "completed_at": d.get("completed_at"),
            })
        return out
