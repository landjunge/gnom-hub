"""KPI-Repository für TKG Phase 4 (§1.5 PerfArchitect, §2.6 KPI-Framework).

Persists KPI-Datapoints (Token-Economy, Retrieval-Quality, Turn-Count,
Task-Success-Rate, Replay-Metrics) in eine dedizierte Tabelle `kpi_metrics`
in derselben SQLite-DB wie der Rest des Systems.

Design:
- Standalone (keine Cross-Imports auf gnom_hub.db.connection), damit es in
  Tests mit einem temporären DB-Pfad instanziiert werden kann.
- Schema-Ensure im Constructor (idempotent, `IF NOT EXISTS`).
- `KpiRecord` ist eine immutable-frozen Dataclass — wird durch `record()`
  in die DB geschrieben.
- `query()` filtert nach Name + Window + Agent, gibt chronologisch
  sortierte Records zurück.
- `ab_group` ∈ {"control", "treatment"} — A/B-Switch wird vom Caller
  gesetzt, nicht vom Repo.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

ABGroup = Literal["control", "treatment"]


@dataclass(frozen=True)
class KpiRecord:
    """Ein einzelner KPI-Datapoint.

    Attributes:
        name: KPI-Name (z.B. "retrieval_precision_at_5", "token_economy_pct",
              "avg_latency_ms", "turn_count", "task_success").
        agent: Welcher Agent hat den KPI erzeugt (z.B. "coderag", "replay_harness").
               None wenn agent-übergreifend.
        value: Numerischer Wert (REAL in der DB).
        timestamp: Unix-Timestamp (Sekunden, float). Default = now.
        ab_group: A/B-Group "control" | "treatment" (default "control").
        metadata: Optional, zusätzliche strukturierte Daten (wird als JSON
                  in einer separaten Spalte abgelegt, siehe Migration).
    """
    name: str
    value: float
    agent: Optional[str] = None
    timestamp: float = 0.0
    ab_group: ABGroup = "control"
    metadata: Optional[dict] = None

    def __post_init__(self):
        # Default-Timestamp: jetzt (UTC) — frozen, daher via object.__setattr__
        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())
        # metadata zu dict normalisieren
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


class KpiRepository:
    """Repository für `kpi_metrics`-Tabelle in der Hub-DB.

    Schema (idempotent im Constructor):
        CREATE TABLE IF NOT EXISTS kpi_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            agent TEXT,
            value REAL NOT NULL,
            timestamp TEXT NOT NULL,
            ab_group TEXT NOT NULL DEFAULT 'control',
            metadata TEXT DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_kpi_name_ts ON kpi_metrics(name, timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_kpi_agent_ts ON kpi_metrics(agent, timestamp DESC);

    Args:
        db_path: Absoluter Pfad zur SQLite-Datei. Default: `~/.gnom-hub/data/gnomhub.db`.
                 In Tests wird `tempfile.mkdtemp() + "/kpi.db"` empfohlen.
    """

    SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS kpi_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        agent TEXT,
        value REAL NOT NULL,
        timestamp TEXT NOT NULL,
        ab_group TEXT NOT NULL DEFAULT 'control',
        metadata TEXT DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_kpi_name_ts ON kpi_metrics(name, timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_kpi_agent_ts ON kpi_metrics(agent, timestamp DESC);
    """

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        # Ensure parent dir exists (für Tests mit tempfile.mkdtemp())
        parent = Path(self.db_path).parent
        if str(parent) and not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
        # Ensure table exists (idempotent)
        with self._connect() as conn:
            conn.executescript(self.SCHEMA_SQL)
            conn.commit()

    # ── Public API ───────────────────────────────────────────────────────

    def record(self, kpi: KpiRecord) -> int:
        """Insert one KPI datapoint. Returns the row id."""
        ts_iso = self._to_iso(kpi.timestamp)
        meta_json = json.dumps(kpi.metadata or {}, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO kpi_metrics (name, agent, value, timestamp, ab_group, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (kpi.name, kpi.agent, kpi.value, ts_iso, kpi.ab_group, meta_json),
            )
            conn.commit()
            return int(cur.lastrowid or 0)

    def query(
        self,
        kpi_name: str,
        window_hours: int = 24,
        agent: Optional[str] = None,
        ab_group: Optional[ABGroup] = None,
        limit: int = 10000,
    ) -> list[KpiRecord]:
        """Return KPI records filtered by name + window (+ optional agent + ab_group).

        Args:
            kpi_name: Welcher KPI (exact match).
            window_hours: Zeitfenster rückwärts in Stunden. Default 24.
            agent: Optional Agent-Filter. None = alle Agents.
            ab_group: Optional A/B-Group-Filter.
            limit: Max Anzahl Records (default 10000, Schutz vor riesigen Scans).

        Returns:
            Chronologisch sortierte Liste (älteste zuerst).
        """
        now = time.time()
        cutoff_iso = self._to_iso(now - window_hours * 3600.0)
        where = ["name = ?", "timestamp >= ?"]
        params: list = [kpi_name, cutoff_iso]

        if agent is not None:
            where.append("agent = ?")
            params.append(agent)
        if ab_group is not None:
            where.append("ab_group = ?")
            params.append(ab_group)

        sql = f"""
            SELECT name, agent, value, timestamp, ab_group, metadata
            FROM kpi_metrics
            WHERE {' AND '.join(where)}
            ORDER BY timestamp ASC
            LIMIT ?
        """
        params.append(limit)

        out: list[KpiRecord] = []
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        for r in rows:
            try:
                meta = json.loads(r["metadata"] or "{}")
            except (json.JSONDecodeError, TypeError):
                meta = {}
            out.append(KpiRecord(
                name=r["name"],
                agent=r["agent"],
                value=float(r["value"]),
                timestamp=self._from_iso(r["timestamp"]),
                ab_group=r["ab_group"] if r["ab_group"] in ("control", "treatment") else "control",
                metadata=meta,
            ))
        return out

    def latest(self, kpi_name: str, agent: Optional[str] = None) -> Optional[KpiRecord]:
        """Letzten Record für einen KPI-Namen. Convenience-Methode."""
        with self._connect() as conn:
            if agent is None:
                row = conn.execute(
                    "SELECT name, agent, value, timestamp, ab_group, metadata "
                    "FROM kpi_metrics WHERE name = ? ORDER BY timestamp DESC LIMIT 1",
                    (kpi_name,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT name, agent, value, timestamp, ab_group, metadata "
                    "FROM kpi_metrics WHERE name = ? AND agent = ? "
                    "ORDER BY timestamp DESC LIMIT 1",
                    (kpi_name, agent),
                ).fetchone()
        if row is None:
            return None
        try:
            meta = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        return KpiRecord(
            name=row["name"],
            agent=row["agent"],
            value=float(row["value"]),
            timestamp=self._from_iso(row["timestamp"]),
            ab_group=row["ab_group"] if row["ab_group"] in ("control", "treatment") else "control",
            metadata=meta,
        )

    def count(self, kpi_name: Optional[str] = None) -> int:
        """Anzahl Records (optional gefiltert nach Name). Nützlich für Tests."""
        with self._connect() as conn:
            if kpi_name is None:
                row = conn.execute("SELECT COUNT(*) AS n FROM kpi_metrics").fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM kpi_metrics WHERE name = ?",
                    (kpi_name,),
                ).fetchone()
        return int(row["n"] or 0)

    # ── Internals ────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _to_iso(ts: float) -> str:
        """Unix-Timestamp → ISO-8601 UTC-String mit Z-Suffix."""
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _from_iso(s: str) -> float:
        """ISO-8601 → Unix-Timestamp. Fallback: 0.0."""
        if not s:
            return 0.0
        try:
            # Akzeptiert sowohl "2026-...Z" als auch "2026-...+00:00"
            if s.endswith("Z"):
                s2 = s[:-1] + "+00:00"
            else:
                s2 = s
            dt = datetime.fromisoformat(s2)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except (ValueError, TypeError):
            return 0.0


__all__ = ["KpiRepository", "KpiRecord", "ABGroup"]
