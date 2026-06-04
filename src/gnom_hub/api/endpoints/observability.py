from fastapi import APIRouter
from gnom_hub.db.connection import get_db_conn
import sqlite3
import json

router = APIRouter(prefix="/api/observability")

@router.get("/metrics")
def get_observability_metrics():
    with get_db_conn() as conn:
        # 1. Agent-specific metrics: Queue Wait & Execution Latencies, counts
        agent_rows = conn.execute("""
            SELECT 
                recipient as agent_name,
                COUNT(*) as total_count,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'dead_letter' THEN 1 ELSE 0 END) as fail_count,
                AVG(processing_since - created_at) as avg_queue_wait,
                AVG(completed_at - processing_since) as avg_exec_time
            FROM agent_messages
            GROUP BY recipient
        """).fetchall()

        agent_metrics = []
        for r in agent_rows:
            agent_metrics.append({
                "agent_name": r["agent_name"],
                "total_count": r["total_count"],
                "success_count": r["success_count"],
                "fail_count": r["fail_count"],
                "success_rate": (r["success_count"] / r["total_count"]) if r["total_count"] > 0 else 1.0,
                "avg_queue_wait_ms": (r["avg_queue_wait"] * 1000) if r["avg_queue_wait"] is not None else 0.0,
                "avg_exec_time_ms": (r["avg_exec_time"] * 1000) if r["avg_exec_time"] is not None else 0.0
            })

        # 2. Capability-specific metrics by joining workflow_tasks with agent_messages
        capability_metrics = []
        try:
            cap_rows = conn.execute("""
                SELECT 
                    t.capability,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN m.status = 'done' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN m.status = 'dead_letter' THEN 1 ELSE 0 END) as fail_count,
                    AVG(m.processing_since - m.created_at) as avg_queue_wait,
                    AVG(m.completed_at - m.processing_since) as avg_exec_time
                FROM workflow_tasks t
                JOIN agent_messages m ON m.id = t.msg_id
                GROUP BY t.capability
            """).fetchall()

            for r in cap_rows:
                capability_metrics.append({
                    "capability": r["capability"],
                    "total_count": r["total_count"],
                    "success_count": r["success_count"],
                    "fail_count": r["fail_count"],
                    "success_rate": (r["success_count"] / r["total_count"]) if r["total_count"] > 0 else 1.0,
                    "avg_queue_wait_ms": (r["avg_queue_wait"] * 1000) if r["avg_queue_wait"] is not None else 0.0,
                    "avg_exec_time_ms": (r["avg_exec_time"] * 1000) if r["avg_exec_time"] is not None else 0.0
                })
        except sqlite3.OperationalError:
            pass

        # 3. Overall workflow stats
        workflow_stats = {
            "total_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "avg_duration_s": 0.0
        }
        workflows_list = []
        try:
            wf_rows = conn.execute("""
                SELECT 
                    id, 
                    name, 
                    status, 
                    created_at, 
                    completed_at,
                    (completed_at - created_at) as duration
                FROM workflows
                ORDER BY created_at DESC
            """).fetchall()

            total_duration = 0.0
            durations_count = 0
            for r in wf_rows:
                workflow_stats["total_count"] += 1
                if r["status"] == "completed":
                    workflow_stats["completed_count"] += 1
                elif r["status"] == "failed":
                    workflow_stats["failed_count"] += 1

                if r["duration"] is not None:
                    total_duration += r["duration"]
                    durations_count += 1

                workflows_list.append({
                    "id": r["id"],
                    "name": r["name"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "completed_at": r["completed_at"],
                    "duration_s": r["duration"]
                })

            if durations_count > 0:
                workflow_stats["avg_duration_s"] = total_duration / durations_count
        except sqlite3.OperationalError:
            pass

        return {
            "agents": agent_metrics,
            "capabilities": capability_metrics,
            "workflows_summary": workflow_stats,
            "workflows": workflows_list
        }
