"""KPI-Endpoint für TKG Phase 4 (§2.6.2).

GET /api/memory/kpis?window=24h&agent=X&kpi=Y

Liefert aggregierte KPI-Datapoints aus dem `kpi_metrics`-Repository.
Unterstützt A/B-Switch via `MEMORY_AB_GROUP` env var (default "control").

Beispiel:
    GET /api/memory/kpis?window=24h&kpi=avg_latency_ms
    → {
        "kpis": [...],
        "ab_group": "control",
        "window_hours": 24,
        "kpi_name": "avg_latency_ms"
      }
"""
from __future__ import annotations

import os
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from gnom_hub.memory.kpi_repository import KpiRecord, KpiRepository

router = APIRouter()


# ── A/B-Group Resolution ────────────────────────────────────────────────────

_AB_GROUP_PATTERN = re.compile(r"^(control|treatment)$", re.IGNORECASE)


def _resolve_ab_group() -> str:
    """Liest `MEMORY_AB_GROUP` env var. Default "control".

    Validiert: nur "control" oder "treatment" werden akzeptiert.
    Alles andere fällt auf "control" zurück (defensive).
    """
    raw = os.getenv("MEMORY_AB_GROUP", "control")
    if _AB_GROUP_PATTERN.match(raw):
        return raw.lower()
    return "control"


# ── Helper: Default-DB-Pfad ─────────────────────────────────────────────────


def _get_default_repo() -> KpiRepository:
    """Erzeugt eine KpiRepository-Instanz mit der Hub-Default-DB.

    Lazy-Import der Config um zirkuläre Imports zu vermeiden.
    """
    from gnom_hub.core.config import Config
    return KpiRepository(str(Config.DB_PATH))


def _parse_window(window: str) -> int:
    """Parse `window`-String ("24h", "1d", "30m", "1w") → Stunden (int).

    Unterstützte Suffixe:
        h = hours, d = days (×24), m = minutes (/60), w = weeks (×168)

    Default bei unbekanntem Format: 24 Stunden.
    """
    if not window:
        return 24
    s = window.strip().lower()
    m = re.match(r"^(\d+)\s*([hdwm]?)$", s)
    if not m:
        return 24
    n = int(m.group(1))
    unit = m.group(2) or "h"
    if unit == "h":
        return max(1, n)
    if unit == "d":
        return max(1, n * 24)
    if unit == "w":
        return max(1, n * 24 * 7)
    if unit == "m":
        return max(1, n // 60 if n >= 60 else 1)
    return 24


# ── Endpoint ────────────────────────────────────────────────────────────────


@router.get("/api/memory/kpis")
def get_memory_kpis(
    window: str = Query("24h", description="Zeitfenster, z.B. '24h', '7d', '1w'"),
    agent: Optional[str] = Query(None, description="Agent-Filter (z.B. 'coderag')"),
    kpi: Optional[str] = Query(None, description="KPI-Name-Filter (z.B. 'avg_latency_ms')"),
    ab_group: Optional[str] = Query(None, description="A/B-Group Override (control|treatment)"),
):
    """Aggregierte KPI-Datapoints aus dem `kpi_metrics`-Repository.

    Args:
        window: Zeitfenster (Suffix h/d/w/m, default "24h").
        agent: Optional Agent-Filter.
        kpi: Optional KPI-Name. Wenn None → alle KPIs (gruppiert nach Name).
        ab_group: Optional Override für die A/B-Group. Default aus
                  `MEMORY_AB_GROUP` env var.

    Returns:
        Dict mit `kpis` (Liste je KPI-Name), `ab_group`, `window_hours`.

    Raises:
        HTTPException 400: bei ungültigem ab_group-Wert.
    """
    # A/B-Group-Override (falls explizit gesetzt)
    if ab_group is not None:
        if not _AB_GROUP_PATTERN.match(ab_group):
            raise HTTPException(
                status_code=400,
                detail=f"ab_group must be 'control' or 'treatment', got {ab_group!r}",
            )
        effective_ab = ab_group.lower()
    else:
        effective_ab = _resolve_ab_group()

    window_hours = _parse_window(window)
    repo = _get_default_repo()

    if kpi is not None:
        # ── Einzelner KPI-Name ────────────────────────────────────────
        records = repo.query(
            kpi_name=kpi,
            window_hours=window_hours,
            agent=agent,
            ab_group=effective_ab,  # type: ignore[arg-type]
        )
        kpis = {
            kpi: {
                "name": kpi,
                "count": len(records),
                "avg": _avg([r.value for r in records]),
                "min": min((r.value for r in records), default=None),
                "max": max((r.value for r in records), default=None),
                "values": [_record_to_dict(r) for r in records],
            }
        }
    else:
        # ── Alle KPIs (gruppiert nach Name) ───────────────────────────
        names = _known_kpi_names(repo)
        kpis = {}
        for name in names:
            records = repo.query(
                kpi_name=name,
                window_hours=window_hours,
                agent=agent,
                ab_group=effective_ab,  # type: ignore[arg-type]
            )
            if not records:
                continue
            kpis[name] = {
                "name": name,
                "count": len(records),
                "avg": _avg([r.value for r in records]),
                "min": min((r.value for r in records), default=None),
                "max": max((r.value for r in records), default=None),
                "values": [_record_to_dict(r) for r in records],
            }

    return {
        "kpis": kpis,
        "ab_group": effective_ab,
        "window_hours": window_hours,
        "kpi_name": kpi,
        "agent": agent,
    }


# ── Internals ───────────────────────────────────────────────────────────────


def _avg(values: list[float]) -> Optional[float]:
    return (sum(values) / len(values)) if values else None


def _record_to_dict(r: KpiRecord) -> dict:
    return {
        "name": r.name,
        "agent": r.agent,
        "value": r.value,
        "timestamp": r.timestamp,
        "ab_group": r.ab_group,
        "metadata": r.metadata or {},
    }


def _known_kpi_names(repo: KpiRepository) -> list[str]:
    """Distinct KPI-Namen aus der DB. Limit 200 (Schutz)."""
    try:
        with repo._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                "SELECT DISTINCT name FROM kpi_metrics ORDER BY name ASC LIMIT 200"
            ).fetchall()
        return [r["name"] for r in rows]
    except Exception:
        return []


__all__ = ["router", "get_memory_kpis"]
