import sqlite3, time, logging, json
from datetime import datetime
from pathlib import Path
from typing import Optional

_log = logging.getLogger("soul.memory_layers")

DB_PATH = None  # Wird beim ersten Zugriff via get_db_path() gesetzt


def get_db_path() -> str:
    global DB_PATH
    if DB_PATH is None:
        from gnom_hub.core.config import DATA_DIR
        DB_PATH = str(DATA_DIR / "coordination.db")
    return DB_PATH


class CoordinationDB:
    def __init__(self):
        self._path = get_db_path()
        self._init_db()

    def _init_db(self):
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS worker_stats (
                    agent_name TEXT PRIMARY KEY,
                    total_jobs INTEGER DEFAULT 0,
                    successful_jobs INTEGER DEFAULT 0,
                    failed_jobs INTEGER DEFAULT 0,
                    avg_duration_s REAL DEFAULT 0,
                    last_job_at TEXT,
                    last_job_type TEXT,
                    strengths TEXT DEFAULT '[]',
                    weaknesses TEXT DEFAULT '[]'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_id TEXT,
                    worker TEXT NOT NULL,
                    task_summary TEXT NOT NULL,
                    result TEXT DEFAULT 'unknown',
                    duration_s REAL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    notes TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT,
                    context_id TEXT,
                    name TEXT,
                    task_chain TEXT NOT NULL,
                    overall_result TEXT NOT NULL,
                    failed_at_task TEXT,
                    failure_reason TEXT,
                    duration_s REAL DEFAULT 0,
                    task_count INTEGER DEFAULT 0,
                    user_feedback TEXT DEFAULT 'none',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_worker ON job_history(worker)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_result ON job_history(result)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_wf_result ON workflow_results(overall_result)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_wf_chain ON workflow_results(task_chain)")
            conn.commit()

    def record_job(self, worker: str, task_summary: str, result: str,
                   duration_s: float, context_id: str = None, notes: str = ""):
        try:
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    "INSERT INTO job_history (context_id, worker, task_summary, result, duration_s, created_at, notes) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (context_id, worker, task_summary[:200], result, duration_s,
                     datetime.now().isoformat(), notes)
                )
                conn.execute("""
                    INSERT INTO worker_stats (agent_name, total_jobs, successful_jobs, failed_jobs, last_job_at, last_job_type)
                    VALUES (?, 1, ?, ?, ?, ?)
                    ON CONFLICT(agent_name) DO UPDATE SET
                        total_jobs = total_jobs + 1,
                        successful_jobs = successful_jobs + (CASE WHEN ? = 'success' THEN 1 ELSE 0 END),
                        failed_jobs = failed_jobs + (CASE WHEN ? = 'failed' THEN 1 ELSE 0 END),
                        last_job_at = ?,
                        last_job_type = ?
                """, (
                    worker,
                    1 if result == "success" else 0,
                    1 if result == "failed" else 0,
                    datetime.now().isoformat(),
                    task_summary[:50],
                    result, result,
                    datetime.now().isoformat(),
                    task_summary[:50]
                ))
                conn.commit()
        except Exception as e:
            _log.warning("[CoordDB] record_job failed: %s", e)

    def get_best_worker(self, task_type: str, queue_depths: dict[str, int] = None) -> tuple[Optional[str], Optional[str]]:
        try:
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT agent_name, total_jobs, successful_jobs, failed_jobs, avg_duration_s
                    FROM worker_stats
                    WHERE total_jobs > 0
                    ORDER BY total_jobs DESC
                """).fetchall()
        except Exception:
            rows = []

        candidates = []
        for r in rows:
            total = r["total_jobs"] or 1
            success_rate = (r["successful_jobs"] / total) * 100
            name = r["agent_name"]
            qd = queue_depths.get(name.lower(), 0) if queue_depths else 0

            if success_rate >= 40:
                candidates.append((name, success_rate, qd))
            elif total >= 5 and success_rate < 40:
                _log.info("[CoordDB] Skipping %s: %d%% success rate after %d jobs", name, success_rate, total)
            else:
                candidates.append((name, success_rate, qd))

        candidates.sort(key=lambda x: (-x[1], x[2]))
        if candidates:
            _log.info("[CoordDB] Best worker for task: %s (%.0f%%, queue depth %d)",
                      candidates[0][0], candidates[0][1], candidates[0][2])

        preferred = candidates[0][0] if candidates else None
        fallback = candidates[1][0] if len(candidates) > 1 else None
        return preferred, fallback

    def get_worker_summary(self) -> str:
        try:
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT agent_name, total_jobs, successful_jobs, failed_jobs, last_job_type "
                    "FROM worker_stats ORDER BY total_jobs DESC"
                ).fetchall()
            if not rows:
                return ""
            lines = []
            for r in rows:
                total = r["total_jobs"] or 1
                rate = round((r["successful_jobs"] / total) * 100)
                lines.append(
                    f"  {r['agent_name']}: {r['total_jobs']} Jobs, {rate}% Erfolg"
                    + (f", zuletzt: {r['last_job_type'][:30]}" if r["last_job_type"] else "")
                )
            return "\n".join(lines)
        except Exception:
            return ""

    def get_recent_failures(self, worker: str, limit: int = 3) -> list[str]:
        try:
            with sqlite3.connect(self._path) as conn:
                rows = conn.execute(
                    "SELECT task_summary, notes FROM job_history "
                    "WHERE worker = ? AND result = 'failed' "
                    "ORDER BY created_at DESC LIMIT ?",
                    (worker, limit)
                ).fetchall()
            return [f"{r[0]}: {r[1]}" for r in rows]
        except Exception:
            return []

    def record_workflow(self, workflow_id: str, context_id: str, name: str,
                        task_chain: list[str], overall_result: str,
                        duration_s: float, failed_at_task: str = None,
                        failure_reason: str = None):
        try:
            with sqlite3.connect(self._path) as conn:
                conn.execute("""
                    INSERT INTO workflow_results
                        (workflow_id, context_id, name, task_chain, overall_result,
                         failed_at_task, failure_reason, duration_s, task_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    workflow_id, context_id, name, json.dumps(task_chain),
                    overall_result, failed_at_task, failure_reason,
                    duration_s, len(task_chain), datetime.now().isoformat()
                ))
                conn.commit()
        except Exception as e:
            _log.warning("[CoordDB] record_workflow failed: %s", e)

    def get_best_workflow_patterns(self, min_samples: int = 3, limit: int = 5) -> list[dict]:
        try:
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT task_chain,
                           COUNT(*) as total,
                           SUM(CASE WHEN overall_result = 'success' THEN 1 ELSE 0 END) as successes,
                           ROUND(AVG(CASE WHEN overall_result = 'success' THEN duration_s ELSE NULL END), 1) as avg_duration_s
                    FROM workflow_results
                    GROUP BY task_chain
                    HAVING total >= ?
                    ORDER BY successes DESC, avg_duration_s ASC
                    LIMIT ?
                """, (min_samples, limit)).fetchall()
            result = []
            for r in rows:
                total = r["total"]
                successes = r["successes"] or 0
                result.append({
                    "task_chain": json.loads(r["task_chain"]),
                    "total": total,
                    "successes": successes,
                    "success_rate": round((successes / total) * 100, 1),
                    "avg_duration_s": r["avg_duration_s"] or 0,
                })
            return result
        except Exception:
            return []

    def get_workflow_summary(self, limit: int = 10) -> list[dict]:
        try:
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT name, task_chain, overall_result, failed_at_task,
                           duration_s, user_feedback, created_at
                    FROM workflow_results
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []


_coordination_db: Optional[CoordinationDB] = None

def get_coordination_db() -> CoordinationDB:
    global _coordination_db
    if _coordination_db is None:
        _coordination_db = CoordinationDB()
    return _coordination_db
