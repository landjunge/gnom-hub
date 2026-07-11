"""Replay-Harness für TKG Phase 4 (§1.5 PerfArchitect, §2.6 KPI-Framework).

Liest ein JSON-Chat-Log und rekonstruiert die User-Queries gegen den
`RetrievalEngine`. Jeder Query löst eine echte Retrieval-Pipeline aus
(Vector + Graph + Symbol-Match) und produziert KPIs:

- `avg_latency_ms` — Mittelwert der Query-Latency
- `retrieval_precision_at_5` — Anteil der Top-5-Treffer die "relevant" sind
- `token_economy_pct` — Tokens-reduced-Vergleich zu einer naiven Baseline
  (Flat-Scan aller Facts) als grober Schätzwert
- `queries_run` — Anzahl der replay-eden Queries

Die KPIs werden via `KpiRepository` in die `kpi_metrics`-Tabelle geschrieben,
damit der `/api/memory/kpis`-Endpoint sie ausliefern kann.

JSON-Log-Format (siehe `example_log.json`):
    {
      "name": "...",
      "messages": [
        {"id": "m1", "sender": "user", "agent": "generalag", "content": "...",
         "timestamp": "2026-..."}
      ]
    }

Der Harness extrahiert alle User-Messages (sender="user") als Replay-Queries.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gnom_hub.memory.kpi_repository import KpiRecord, KpiRepository
from gnom_hub.memory_tkg.retrieval_engine import RetrievalEngine

_log = logging.getLogger(__name__)

# ── Datentypen ──────────────────────────────────────────────────────────────


@dataclass
class ReplayMessage:
    """Eine einzelne Chat-Message aus dem Replay-Log."""
    id: str
    sender: str
    agent: str
    content: str
    timestamp: str = ""


@dataclass
class ReplayResult:
    """Output eines `ReplayHarness.replay()`-Calls.

    Attributes:
        queries_run: Anzahl der replay-eden User-Queries.
        avg_latency_ms: Durchschnittliche Latency in ms.
        retrieval_precision_at_5: Anteil der Top-5-Treffer mit Symbol-Overlap
            zur Query (grobe Heuristik, da wir kein Gold-Set haben).
        token_economy_pct: Geschätzte Token-Reduktion in Prozent ggü. einer
            naiven Flat-Scan-Baseline (0.0–100.0).
        queries: Detail-Liste pro Query (id, latency_ms, n_facts, top_score).
        log_file: Pfad zur Log-Datei (für Audit).
        started_at: Unix-Timestamp.
        duration_ms: Gesamtdauer des Replays.
        ab_group: A/B-Group der aufgenommenen KPIs.
    """
    queries_run: int = 0
    avg_latency_ms: float = 0.0
    retrieval_precision_at_5: float = 0.0
    token_economy_pct: float = 0.0
    queries: list[dict[str, Any]] = field(default_factory=list)
    log_file: str = ""
    started_at: float = 0.0
    duration_ms: float = 0.0
    ab_group: str = "control"


# ── Replay-Harness ──────────────────────────────────────────────────────────


class ReplayHarness:
    """Replay-Engine: liest Chat-Log, rekonstruiert User-Queries, schreibt KPIs.

    Args:
        kpi_repo: KpiRepository (persistiert die Metriken).
        engine: RetrievalEngine (führt die Hybrid-Retrieval-Pipeline aus).
        ab_group: A/B-Group für die geschriebenen KPIs (default "control").
                  Wird via `MEMORY_AB_GROUP` env var gesteuert.
        log_path: Optional Default-Log-Pfad (kann pro `replay()`-Call
                  überschrieben werden).
    """

    def __init__(
        self,
        kpi_repo: KpiRepository,
        engine: RetrievalEngine,
        ab_group: str = "control",
        log_path: str | None = None,
    ):
        self.kpi_repo = kpi_repo
        self.engine = engine
        # A/B-Group normalisieren
        self.ab_group = ab_group if ab_group in ("control", "treatment") else "control"
        self.log_path = log_path

    # ── Public API ───────────────────────────────────────────────────────

    def replay(self, log_file: str | None = None) -> ReplayResult:
        """Replay eines Chat-Logs.

        Args:
            log_file: Pfad zur JSON-Log-Datei. None → nutze self.log_path.

        Returns:
            ReplayResult mit aggregierten Metriken. Schreibt zusätzlich
            einzelne KPI-Datapoints in den `KpiRepository`.
        """
        path = log_file or self.log_path
        if not path:
            raise ValueError("log_file is required (no self.log_path fallback set)")
        path_str = str(path)

        started = time.time()
        messages = self._load_log(path_str)
        user_queries = [m for m in messages if m.sender.lower() == "user" and m.content.strip()]
        n = len(user_queries)

        result = ReplayResult(
            queries_run=n,
            log_file=path_str,
            started_at=started,
            ab_group=self.ab_group,
        )

        if n == 0:
            # Leeres Log → leere Result, keine KPIs
            result.duration_ms = (time.time() - started) * 1000.0
            return result

        # ── Per-Query Replay ────────────────────────────────────────────
        latencies: list[float] = []
        precisions: list[float] = []
        token_baseline_total = 0
        token_replay_total = 0

        for msg in user_queries:
            query_text = msg.content.strip()
            t0 = time.time()
            try:
                rr = self.engine.query(query_text, k=5)
            except Exception as e:  # noqa: BLE001
                # Replay darf nicht crashen, einzelne Fehler werden ignoriert
                _log.debug("replay query failed (skipped): %s", e)
                continue
            dt_ms = (time.time() - t0) * 1000.0
            latencies.append(dt_ms)

            # Precision@5 Heuristik: Anteil der Top-5 mit Symbol-Overlap zur Query
            top5 = rr.top_facts(5)
            p5 = self._precision_at_5(query_text, top5)
            precisions.append(p5)

            # Token-Economy: Schätzwert
            # Baseline: alle Facts geladen (flat) → |all_facts|·fact_text_len
            # Replay: nur Top-5 → 5·fact_text_len
            # Reduction = 1 - (5 / n_facts_in_backend)
            n_total = self._backend_fact_count()
            if n_total > 0:
                baseline = n_total
                replay = min(5, n_total)
                token_baseline_total += baseline
                token_replay_total += replay

            result.queries.append({
                "msg_id": msg.id,
                "agent": msg.agent,
                "latency_ms": dt_ms,
                "n_facts": len(rr.facts),
                "top_score": rr.facts[0].score if rr.facts else 0.0,
                "precision_at_5": p5,
                "cached": rr.cached,
            })

            # KPI: per-Query Latency persistieren
            self.kpi_repo.record(KpiRecord(
                name="query_latency_ms",
                value=dt_ms,
                agent=msg.agent,
                ab_group=self.ab_group,  # type: ignore[arg-type]
                metadata={"replay_msg_id": msg.id, "n_facts": len(rr.facts)},
            ))

        # ── Aggregate ───────────────────────────────────────────────────
        if latencies:
            result.avg_latency_ms = sum(latencies) / len(latencies)
        if precisions:
            result.retrieval_precision_at_5 = sum(precisions) / len(precisions)
        if token_baseline_total > 0:
            reduction = 1.0 - (token_replay_total / token_baseline_total)
            result.token_economy_pct = max(0.0, min(100.0, reduction * 100.0))

        result.duration_ms = (time.time() - started) * 1000.0

        # ── Aggregierte KPIs persistieren ──────────────────────────────
        for kpi_name, value in [
            ("avg_latency_ms", result.avg_latency_ms),
            ("retrieval_precision_at_5", result.retrieval_precision_at_5),
            ("token_economy_pct", result.token_economy_pct),
            ("queries_run", float(result.queries_run)),
            ("replay_duration_ms", result.duration_ms),
        ]:
            self.kpi_repo.record(KpiRecord(
                name=kpi_name,
                value=value,
                agent="replay_harness",
                ab_group=self.ab_group,  # type: ignore[arg-type]
                metadata={"log_file": path_str, "ab_group": self.ab_group},
            ))

        return result

    # ── Internals ───────────────────────────────────────────────────────

    def _load_log(self, path: str) -> list[ReplayMessage]:
        """Lade JSON-Log und konvertiere Messages."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Replay log not found: {path}")
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Akzeptiere entweder top-level "messages" oder eine flache Liste
        if isinstance(data, list):
            raw_msgs = data
        else:
            raw_msgs = data.get("messages", [])
            # Wenn ab_group im Log-File steht, übernehmen (sonst behalten wir self.ab_group)
            file_ab = data.get("ab_group")
            if file_ab in ("control", "treatment"):
                self.ab_group = file_ab
        out: list[ReplayMessage] = []
        for m in raw_msgs:
            try:
                out.append(ReplayMessage(
                    id=str(m.get("id", "")),
                    sender=str(m.get("sender", "")),
                    agent=str(m.get("agent", "")),
                    content=str(m.get("content", "")),
                    timestamp=str(m.get("timestamp", "")),
                ))
            except Exception as e:  # noqa: BLE001
                # Defensive: einzelne kaputte Messages überspringen
                _log.debug("replay message parse failed (skipped): %s", e)
                continue
        return out

    def _precision_at_5(self, query: str, top5_facts: list) -> float:
        """Heuristik: Anteil der Top-5-Facts mit ≥1 Wort-Overlap zur Query.

        Kein Gold-Set vorhanden → wir nutzen Wort-Overlap als Proxy für
        "relevanz". User-Messages haben viele Wörter (Sätze), daher nehmen
        wir nur "substantielle" Wörter (≥3 Zeichen, alpha).
        """
        if not top5_facts:
            return 0.0
        query_words = {
            w.lower() for w in query.split()
            if len(w) >= 3 and w.isalpha()
        }
        if not query_words:
            return 0.0
        hits = 0
        for sf in top5_facts:
            fact_text = getattr(sf, "fact", None)
            if fact_text is None:
                continue
            text = getattr(fact_text, "text", "")
            fact_words = {w.lower() for w in text.split() if len(w) >= 3 and w.isalpha()}
            if query_words & fact_words:
                hits += 1
        return hits / len(top5_facts)

    def _backend_fact_count(self) -> int:
        """Anzahl Facts im Backend (für Token-Economy-Berechnung).

        Defensive: Manche Backends haben keine `count_facts()`-Methode.
        Wir versuchen mehrere Signaturen, fallback 0.
        """
        b = self.engine.backend
        # Methode 1: count_facts() direkt
        for meth in ("count_facts", "count_all_facts", "count"):
            fn = getattr(b, meth, None)
            if callable(fn):
                try:
                    val = fn()
                    if isinstance(val, int):
                        return max(val, 1)
                    if isinstance(val, dict) and "facts" in val:
                        return max(int(val["facts"]), 1)
                except Exception as e:  # noqa: BLE001
                    _log.debug("count_facts probe %s failed: %s", meth, e)
        # Methode 2: Zugriff auf _facts (In-Memory-Backend-spezifisch)
        facts_dict = getattr(b, "_facts", None)
        if isinstance(facts_dict, dict) and facts_dict:
            return len(facts_dict)
        return 0


__all__ = ["ReplayHarness", "ReplayResult", "ReplayMessage"]
