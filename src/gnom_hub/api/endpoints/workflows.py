import json
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from gnom_hub.db.connection import get_db_conn
from gnom_hub.agents.swarm.workflow_engine import create_workflow, start_workflow

router = APIRouter(prefix="/api/workflows")

class TaskPayload(BaseModel):
    task_id: str
    capability: str
    input_template: str
    depends_on: List[str] = []

class WorkflowPayload(BaseModel):
    name: str
    tasks: List[TaskPayload]

@router.post("")
def api_create_workflow(payload: WorkflowPayload):
    tasks_dicts = []
    for t in payload.tasks:
        tasks_dicts.append({
            "task_id": t.task_id,
            "capability": t.capability,
            "input_template": t.input_template,
            "depends_on": t.depends_on
        })
        
    try:
        workflow_id = create_workflow(payload.name, tasks_dicts)
        start_workflow(workflow_id)
        return {"status": "success", "workflow_id": workflow_id}
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to create workflow: {e}")

@router.get("/{workflow_id}")
def api_get_workflow(workflow_id: str):
    with get_db_conn() as conn:
        wf = conn.execute("""
            SELECT id, name, status, created_at, completed_at
            FROM workflows
            WHERE id = ?
        """, (workflow_id,)).fetchone()
        
        if not wf:
            raise HTTPException(404, detail="Workflow not found")
            
        tasks = conn.execute("""
            SELECT task_id, capability, input_template, depends_on, status, msg_id, result_json, error_summary
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
                    
            tasks_list.append({
                "task_id": t["task_id"],
                "capability": t["capability"],
                "input_template": t["input_template"],
                "depends_on": json.loads(t["depends_on"]),
                "status": t["status"],
                "msg_id": t["msg_id"],
                "result": res_val,
                "error_summary": t.get("error_summary"),
            })
            
        return {
            "id": wf["id"],
            "name": wf["name"],
            "status": wf["status"],
            "created_at": wf["created_at"],
            "completed_at": wf["completed_at"],
            "tasks": tasks_list
        }

@router.get("")
def api_list_workflows():
    with get_db_conn() as conn:
        rows = conn.execute("""
            SELECT id, name, status, created_at, completed_at
            FROM workflows
            ORDER BY created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
