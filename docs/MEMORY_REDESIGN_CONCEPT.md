# Gnom-Hub Memory Redesign — Architecture Concept

> **Status:** Konzept v3 — finale Architektur (Stand 2026-07-01, nach 2. User-Review)
> **Autor:** Mavis (Mavis Systems Architect Mode)
> **Scope:** Komplettumbau `src/gnom_hub/db/` + `memory_layers/` + `infrastructure/llm/`
> **Mandate:** Token-Reduktion ≥40%, Retrieval-Relevanz ↑, Agent-Task-Erfolgsrate messbar, Graph-Backend-Pfad geöffnet, KPI-Framework Backend-only, Mermaid-Graph integriert.

---

## Teil 1 — Spezialisiertes Agent-Team

Das Team ist so geschnitten, dass **jede Schicht des Memory-Stacks** eine eigene Verantwortliche hat und ein unabhängiger Benchmark-Verifier existiert. So entstehen vier saubere Schnittstellen statt eines monolithischen `repo.put()`/`repo.get()`-Doppels.

### 1.1 `MemoryArchitect` — Lead Designer

**Rolle:** Eigentümer der Schicht-Topologie, Datenmodell-Migration und Backend-Abstraktion.
**Aufgaben:**
- Schema-Design für **3-Tier-Layer** (siehe §2.1) inkl. primärer Keys, Foreign Keys, Indizes
- Design + Pflege des **`MemoryBackend`-Repository-Interfaces** (§2.0) — die kritische Erweiterbarkeits-Schnittstelle
- Migrationsplan von `memory_layers.py` (heute: flache Cache-Buckets) → neues Schema
- Architektur-Entscheidungen (CAP-Kompromisse pro Schicht, TTL-Strategien, Konsistenz-Level)
- Pflege der `docs/MEMORY_ARCHITECTURE.md` (Diagrams, ADRs)

**Liefert:** SQLAlchemy-/sqlite-Modelle, `MemoryBackend`-Interface, Alembic-Migrations, `MEMORY_TOPOLOGY.md`.

### 1.2 `MemoryCurator` — Intelligente Schicht-Verwaltung

**Rolle:** State-Übergänge zwischen Memory-Schichten + aktive Wissens-Kurierung.
**Aufgaben:**
- **Promotion-Pipeline** (Hot → Warm → Cold) mit Trigger-Logik (Composite-Score-gated)
- **Decay-Scoring:** Fakt-Wichtigkeit sinkt ohne Re-Trieval (`composite = importance + 0.1·log(hits+1) − 0.05·days_idle`)
- **Aktive Kuratierung:** LLM-Sidecar (MiniMax/local) bewertet Facts in Batches und schlägt **Importance-Updates** vor — z.B. „dieser Fact wird seit 2 Wochen nicht mehr angefragt, schlage importance 0.7→0.4 vor". Curator übernimmt Vorschlag nur, wenn er konsistent ist (gleicher Trend in 2 aufeinanderfolgenden Sweeps)
- **Dedup-Pipeline** asynchron via Dedup-Queue (siehe §2.2.3 + ADR-002), Cosine ≥0.95 → merge, 0.85–0.95 → `related_to`
- **Cleanup-Loops:** GC für Cold-Tier (>365 Tage ohne Hit), Tombstone-Handling für gelöschte Items
- **„Vergeßlichkeit mit Verstand"** — Hub darf vergessen, aber mit Audit-Trail und Recovery-Path
- **Pattern-Detection:** Curator erkennt wiederkehrende Fact-Cluster (z.B. „alle routing-Bugs aus 2026-06 hängen mit FAISS-ABI zusammen") und schlägt **Cluster-Summary** in L2 vor — wird zur Memory-Erweiterung ohne User-Aktion

**Liefert:** `memory_curator.py`, Background-Tasks im Hub-Event-Loop, Audit-Tabelle, LLM-Sidecar-Integration.

### 1.3 `RetrievalEngineer` — Hybrid-Suche & Relevance-Tuning

**Rolle:** Suchfront-End und Ranking-Qualität.
**Aufgaben:**
- **Hybrid Retrieval**: BM25 (FTS5) + Vector (FAISS) mit Reciprocal Rank Fusion
- Query-Expansion via SoulAG-Sidecar (Synonyme, Topic-Wörter)
- Re-Ranker (MiniMax/Heuristisch) für Top-20 Hits auf 5 reduziert
- Latency-Budget pro Layer (Hot <50ms, Warm <200ms, Cold <800ms)
- Cache für Top-K Frequent-Queries (LRU, 1000 entries, persistent)

**Liefert:** `retrieval_engine.py`, BM25-Index-Builder, Re-Ranker-Modul.

### 1.4 `PerfArchitect` — Benchmark-Framework

**Rolle:** Misst, ob der Umbau tatsächlich besser ist.
**Aufgaben:**
- Definiert **4 KPI-Klassen** (siehe §2.4): Token-Economy, Retrieval-Latency, Agent-Task-Success, Cache-Hit-Rate
- Implementiert den **Backend-Endpoint** `GET /api/memory/kpis` (§2.4.2) — **bewusst ohne UI-Pendant** (User-Mandat)
- **Replay-Harness**: Lädt historische Chat-Traffic-Samples, fährt sie gegen alt vs. neu, vergleicht
- A/B-Switch zur Laufzeit: 50% der Agenten auf altem Stack, 50% auf neuem, gleicher Eingabe
- Pflegt die **10 Test-Cases** (§2.5) inkl. Backend-Swap-Isolation (TC-09) und KPI-Endpoint-Perf (TC-10)
- Prometheus-Format-Output für externe Monitoring-Tooling-Integration

**Liefert:** `benchmark/`-Verzeichnis, `replay_harness.py`, `kpi_repository.py`, KPI-Endpoint, Test-Reports.

### 1.5 `IntegrationQA` — Wiring, Tests, Rollout

**Rolle:** Hält das System zusammenhängend grün während des Umbaus.
**Aufgaben:**
- **Strangler-Fig-Pattern**: Neuer Memory-Stack läuft parallel zum alten, `MemoryRouter` flag-basiert (`USE_NEW_MEMORY=true` in `.env`)
- Schreibt + pflegt **6 Test-Kategorien** (siehe §2.6): unit, integration, regression, load, chaos, e2e
- Feature-Flag-Cleanup nach Rollout
- PR-Review-Fokus: keine `from memory_layers import *`-Direktimporte mehr — alles durch Adapter
- Migration-Runbook inkl. Rollback-Pfad

**Liefert:** Strangler-Adapter, Test-Suite, Migrations-Runbook, Rollout-Plan.

### 1.6 Team-Rollen-Mapping

| Agent | Eigentum | Liefert an | Erhält Inputs von |
|---|---|---|---|
| MemoryArchitect | Schema, Topologie | Alle | — |
| MemoryCurator | Daten-Lifecycle | RetrievalEngineer, PerfArchitect | MemoryArchitect |
| RetrievalEngineer | Read-Path | IntegrationQA | MemoryArchitect, MemoryCurator |
| PerfArchitect | Metriken, Replay | MemoryArchitect (Feedback-Loop) | Alle |
| IntegrationQA | Wiring, Tests, Flags | (Production) | Alle |

**Kommunikations-Protokoll:** Wöchentliches Architecture-Board-Update in `notes/memory-team.md`. Jeder Agent hat Veto-Recht bei Architektur-Entscheidungen, die seinen Eigentums-Bereich betreffen.

---

## Teil 2 — Technisches Konzept

### 2.0 Repository-Pattern: Backend-Abstraktion (kritisch für Erweiterbarkeit)

**Warum vorab:** L2 muss heute SQLite + FAISS nutzen, aber **morgen** möglicherweise ein Graph-Backend (Neo4j, SurrealDB, oder ein leichtgewichtiges NetworkX-over-SQLite für die Fälle, in denen kein externer Graph-Server aufgesetzt werden soll). Ohne abstrakte Schnittstelle wäre der Wechsel ein Großumbau. Mit Repository-Pattern: ein File neu, der Rest bleibt unberührt.

**Interface-Definition** (in `src/gnom_hub/memory/backend.py`):

```python
from typing import Protocol, Iterator
from gnom_hub.memory.record import MemoryRecord, Layer

class MemoryBackend(Protocol):
    """Abstrakte Schnittstelle für L2/L3-Persistenz.
    Konkrete Implementierungen: SQLiteFAISSBackend (default), GraphBackend (future)."""

    # ── CRUD ──
    def get(self, id: str) -> MemoryRecord | None: ...
    def put(self, record: MemoryRecord) -> str: ...           # returns id
    def delete(self, id: str, soft: bool = True) -> bool: ...
    def list_in_layer(self, layer: Layer, agent: str | None = None,
                      limit: int = 1000) -> Iterator[MemoryRecord]: ...
    def count(self, layer: Layer | None = None) -> int: ...

    # ── Query ──
    def query_symbols(self, symbols: list[str], k: int = 10,
                      layer: Layer = "warm") -> list[MemoryRecord]: ...
    def query_vector(self, embedding: np.ndarray, k: int = 10,
                     layer: Layer = "warm") -> list[MemoryRecord]: ...
    def query_hybrid(self, query: str, symbols: list[str],
                     embedding: np.ndarray, k: int = 10,
                     layer: Layer = "warm") -> list[MemoryRecord]: ...

    # ── Lifecycle (vom Curator aufgerufen) ──
    def sweep_decay(self, older_than_days: int) -> int: ...   # returns promoted count
    def sweep_cold_migration(self) -> int: ...
    def promote(self, id: str, from_layer: Layer, to_layer: Layer) -> bool: ...
```

**Implementierung 1 (default): `SQLiteFAISSBackend`**
- `sqlite_faiss_backend.py` — die Standard-Implementierung
- Tabellen `memory_warm`, `memory_cold`, `l2_dedup_queue`, `memory_tombstones`
- FAISS-Index `IndexFlatIP` (384-d) in separater Datei `data/faiss_warm.index`
- FTS5-Index als virtuelle Tabelle
- Hybride Query: BM25 (FTS5) + Vector (FAISS) + Symbole, fusioniert per Reciprocal Rank Fusion intern

**Implementierung 2 (future, nicht Phase 0): `GraphBackend`**
- `graph_backend.py` — kann entweder:
  - **a)** Echter Graph-Server (Neo4j, SurrealDB) via Bolt/Binary-Protocol — Production-grade
  - **b)** `NetworkX`-DiGraph + SQLite-Property-Store — embedded, kein Server, gut für ≤100k Facts
- Beide implementieren exakt dasselbe `MemoryBackend`-Interface
- Aktivierung per `MEMORY_BACKEND=graph` in `.env`, plus backend-spezifische Config

**Factory-Pattern** (in `src/gnom_hub/memory/__init__.py`):
```python
def get_memory_backend() -> MemoryBackend:
    backend_type = os.getenv("MEMORY_BACKEND", "sqlite_faiss")
    match backend_type:
        case "sqlite_faiss": return SQLiteFAISSBackend(...)
        case "graph":        return GraphBackend(...)
        case _: raise ValueError(f"Unknown MEMORY_BACKEND: {backend_type}")
```

**Single-Instance-Regel:** `get_memory_backend()` ist ein Singleton (pro Hub-Prozess). Der Curator, RetrievalEngineer, und alle Konsumenten teilen sich dieselbe Instanz. Das verhindert Cache-Inkonsistenzen und FAISS-Index-Locks.

**Was bewusst NICHT durch das Backend-Interface geht:**
- L1 HOT (immer in-process-Dict, kein Persistenz-Layer)
- Mermaid-Graph (immer in-process, siehe §2.2.6)
- KPI-Metriken (haben eigenes kleines Interface, siehe §2.4)

### 2.1 Drei-Schichten-Architektur (Hot/Warm/Cold)

```
┌──────────────────────────────────────────────────────────────┐
│                     AGENT READ PATH                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   Agent Query: "Was weißt du über routing-Bugs?"             │
│       │                                                      │
│       ▼                                                      │
│   ┌─────────┐    Hit     ┌────────────────────────────────┐ │
│   │ L1 HOT  │ ─────────► │  RECALL (auto-injected in      │ │
│   │ <50ms   │            │  LLM prompt via context window)│ │
│   └─────────┘            └────────────────────────────────┘ │
│       │ Miss                                                  │
│       ▼                                                      │
│   ┌─────────┐    Top-K    ┌────────────────────────────────┐ │
│   │ L2 WARM │ ─────────► │  RANKED HITS (cross-session    │ │
│   │ <200ms  │            │  facts, semantic embeddings)   │ │
│   └─────────┘            └────────────────────────────────┘ │
│       │ Miss                                                  │
│       ▼                                                      │
│   ┌─────────┐    Audit    ┌────────────────────────────────┐ │
│   │ L3 COLD │ ─────────► │  COMPRESSED (raw transcripts,   │ │
│   │ <800ms  │            │  older than 30d, BM25-only)    │ │
│   └─────────┘            └────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**L1 HOT (Agent-Gedächtnis, flüchtig):**
- In-Memory-Dict pro Agent-Prozess, **Soft-Cap 200, Hard-Cap 400** (final 2026-07-01)
- TTL: 2h idle, dann GC
- Repräsentation: rohe Strings + Tags, kein Embedding (zu teuer)
- Bei Soft-Cap: Composite-Score-Swap statt Eviction (siehe §2.2.4)
- Bei Hard-Cap (400): gestufte Eviction mit Auto-Promotion (siehe §2.2.4)
- Beim Process-Restart: persistiert sich selbst aus L2

**L2 WARM (Cross-Agent Memory, persistent):**
- SQLite-Tabelle `memory_warm`: `(id, agent, fact, embedding BLOB, importance REAL, last_hit_at, hit_count, created_at, supersedes_id)`
- FAISS-Index auf Embedding-Spalte (IndexFlatIP, 384-d)
- BM25-Sidecar via SQLite FTS5
- Importance-Update: `+0.1 * log(hit_count+1) - 0.05 * days_since_hit`
- Beim Importance <0.05 ODER `last_hit_at > 60d` → migrate L3

**L3 COLD (Archive, billig):**
- SQLite-Tabelle `memory_cold`: nur `(id, agent, fact_compressed, created_at)`
- Komprimiert via LLM-Sidecar (`gpt-4o-mini` lokal — bei `nur free modelle` via `meta-llama/llama-3.3-70b-instruct:free`)
- Lesen nur via explizitem „Archive-Query" mit Audit-Trail (wer hat's angefragt, warum)
- Nach 365d ohne Hit → auto-delete mit 7d Soft-Delete-Window

### 2.2 Intelligente Auto-Verwaltung

#### 2.2.1 Promotion (`L1↔L2`)
- Trigger: L1-Fact von 2+ verschiedenen Agenten innerhalb 24h angefragt → promote to L2
- Trigger: L1-Fact mit `importance>0.7` UND `hit_count≥3` → promote + cluster-near-duplicates

#### 2.2.2 Decay (`L2→L3`)
- Daily-Job um 03:00 lokal: sweep L2 nach Cold-Kriterien
- Soft-Migration: erst 7d Tombstone, dann physisch L3 (rollback-fähig)

#### 2.2.3 Dedup (asynchron via Dedup-Queue, final 2026-07-01)
- **Nicht inline** beim Insert — bei hohem Durchsatz zu teuer (Cosine über alle L2-Records ist O(n) pro Insert)
- Stattdessen: dedizierte **`l2_dedup_queue`-Tabelle** in SQLite, in die jeder L2-Insert seinen `(new_id, fact, embedding)` async reinschreibt (Write ist billig, ~1ms)
- **Curator-Sweep** alle 30–60s (konfigurierbar via `L2_DEDUP_INTERVAL_S`):
  - Queue leeren in Batches von 50
  - Pro Batch: Cosine ≥0.95 gegen existierende L2-Records → **merge** (längere Version behalten, References hochzählen, `supersedes_id` setzen)
  - Cosine 0.85–0.95 → **related_to**-Beziehung speichern (Pluralität bewahren, kein Merge)
  - Queue-Items die nicht gemergt wurden: aus Queue entfernt, Fact bleibt eigenständig
- **Trade-off:** 30–60s Race-Window, in dem zwei Near-Duplicates parallel existieren. Akzeptabel weil:
  - Beide Facts funktionieren unabhängig in L1/L2 (Hits, Embeddings)
  - Nach Sweep wird gemergt — und ältere Version bekommt `supersedes_id`-Link
  - In Retrieval-Results sieht der User faktisch keine Duplikate (Re-Ranker dedupliziert per `related_to` ohnehin)
- **Sweep-Lock:** SQLite `BEGIN IMMEDIATE` Transaktion, damit parallel laufende Inserts nicht kollidieren
- **Wartung:** Queue hat Hard-Cap 10.000 Items. Bei Überlauf → Drop-Oldest + Warning-Log ("L2-Dedup-Backpressure, sweep zu langsam")

#### 2.2.4 L1-Overflow-Policy (final 2026-07-01, User-Review)
- **Soft-Cap 200:** Bei Insert mit aktueller Größe ≥200 → Composite-Score-Swap. Neuer Fact `composite = importance + 0.1·log(hits+1) − 0.05·days_idle` wird mit dem niedrigsten L1-Fact verglichen. Wenn neuer höher → Swap. Keine Eviction, kein Latenzverlust.
- **Hard-Cap 400:** Bei Erreichen der 400 → gestufte Eviction der **Bottom-100**:
  - Pro Candidate: `promotion_gate` = `composite ≥ 0.5` UND `hit_count ≥ 1`
  - Pass → **Auto-Promote zu L2** mit `promotion_reason="l1_overflow_important"`, Audit-Log-Eintrag
  - Fail → **Tombstone-Tabelle L4** (audit-only, nie wieder promotet) mit `discarded_at` Timestamp
  - Recovery-Path: `POST /api/memory/tombstone/{id}/restore` schiebt zurück nach L1 oder L2 je nach Composite-Score
- **Tombstone-Lifecycle:** L4-Records 30 Tage gehalten, dann physisch gelöscht. Während dieser Zeit via `/api/memory/tombstones` einsehbar.
- **Latency-Charakteristik:** Bei 400 Items in Python-Dict ~10ms für Composite-Scan. Voll im 50ms-Budget. Calculation passiert nur am Trigger-Punkt (Insert/Overflow), nicht pro Request.

#### 2.2.5 Symbols ↔ Semantics Brücke
Heute: getrennte Pfade (`fact_cache` für Strings, `soul_embedding` für Vektoren). Neu: **eine einzige `MemoryRecord`-Struktur** mit Feldern für beides:

```python
@dataclass
class MemoryRecord:
    id: str                          # uuid7
    agent: str                       # owner-agent oder 'shared'
    layer: Literal['hot','warm','cold']
    fact: str                        # canonical text
    embedding: np.ndarray | None     # 384-d, None wenn noch nicht embedded
    factsymbols: list[FactSymbol]    # extraktive Symbole: dates, ids, urls, code_refs
    importance: float                # 0.0–1.0, dynamisch
    hit_count: int
    created_at: float
    last_hit_at: float
    supersedes_id: str | None        # bei Dedup-Merge
    related_ids: list[str]           # bei Semantic-Closeness aber nicht-Merge
    provenance: str                  # 'agent_msg' | 'tool_result' | 'user_input' | 'background_job'
```

**Brücke:** `FactSymbol`-Extraktion passiert beim Insert deterministisch (regex + AST-Snippets aus Code-Blöcken). Symbole landen in `factsymbols` (SQLite, kein Vektor). So kann L2-WARM mit `WHERE 'routing.txt' IN factsymbols` **symbolisch ohne Embedding** suchen — viel billiger und exakt.

#### 2.2.6 Mermaid-Graph-Integration (final 2026-07-01, User-Review)

Der bestehende symbolische Kurzzeitspeicher ist als **Mermaid-Graph** realisiert — eine in-process Datenstruktur, die Fakten als Knoten und Beziehungen als Kanten darstellt. Diese Struktur wird **nicht ersetzt**, sondern als symbolischer Sub-Layer von L1 HOT integriert.

**Architektur-Entscheidung: Mermaid-Graph = L1-Symbolische-Sicht**

```
┌──────────────────────────────────────────────────────────┐
│  L1 HOT (in-process, pro Agent-Prozess)                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────┐    ┌─────────────────────────┐ │
│  │  Hot-Dict           │    │  Mermaid-Graph          │ │
│  │  (MemoryRecord ×N)  │◄──►│  (Node = record.id,     │ │
│  │  Soft-Cap 200,      │    │   Edge = related_ids)   │ │
│  │  Hard-Cap 400       │    │  Kompakt, traversierbar │ │
│  └─────────────────────┘    └─────────────────────────┘ │
│           │                          │                  │
│           └──────────┬───────────────┘                  │
│                      ▼                                  │
│         Bei Overflow/Eviction:                          │
│         → L2 (Symbolische-Symbole                       │
│           werden zu L2-Factsymbols)                     │
└──────────────────────────────────────────────────────────┘
```

**Konkrete Integration:**

1. **Mermaid-Node-ID == MemoryRecord.id (uuid7).** Eindeutige Brücke zwischen den beiden Strukturen. Beim Insert eines Mermaid-Nodes wird parallel ein `MemoryRecord` mit `layer='hot'` und derselben ID erzeugt.

2. **Mermaid-Edge == related_ids** im `MemoryRecord`. Wenn im Mermaid-Graph eine Kante `A --[causes]--> B` existiert, wird `record_A.related_ids += [B]`. Bidirektional gepflegt: Hinzufügen einer `related_ids`-Beziehung triggert auch die Mermaid-Edge.

3. **Graph-Traversierung in L1-Reads:** Statt linearer Suche kann der Retrieval-Engineer den Mermaid-Graph benutzen, um **2-hop-Nachbarschaften** zu explorieren: "Wenn A ein Treffer ist, schau auch auf A's direkte Nachbarn." Das ist sub-ms und billiger als zusätzliche L2-Queries.

4. **Persistenz:** Der Mermaid-Graph wird **nicht** in L2/L3 als Graph gespeichert. Stattdessen werden bei L1-Eviction (Hard-Cap erreicht) die `related_ids` in den L2-`MemoryRecord` übernommen. Ein zukünftiges `GraphBackend` (§2.0) kann diese `related_ids` nativ als Graph-Edges speichern — der Pfad ist vorbereitet, ohne Breaking Changes.

5. **Mermaid-Serialisierung als Debug-Tool:** `GET /api/memory/graph?agent=X&layer=hot` gibt den aktuellen L1-Graph als Mermaid-`graph TD`-Markup zurück. Nützlich für Visualisierung im Frontend, **aber explizit nicht Phase-0-Scope** — ist nur ein Side-Effect der Architektur, nicht eine UI-Anforderung.

6. **Wo der Mermaid-Graph heute lebt:** Die bestehende Implementation in `src/gnom_hub/soul/mermaid_graph.py` (oder äquivalent — beim Implementieren zu prüfen) wird **nicht ausgetauscht**, sondern gewrappt: `MermaidMemoryAdapter` implementiert die L1-Read/Write-API und delegiert intern an den bestehenden Graph-Code.

**Was bewusst NICHT passiert:**
- Kein Mermaid-Parser in L2 — dort reichen `related_ids` als Liste
- Keine Mermaid-UI-Komponente (User-Mandat: "Benchmarking soll vorerst nur als Backend existieren — keine eigene UI-Seite"; analog für Memory-Visualisierung)
- Kein Mermaid-zu-Graph-DB-Mapping vor Phase 3

**Mermaid-spezifische Risiken:**

| Risiko | Mitigation |
|---|---|
| Mermaid-Graph-Operationen langsamer als Dict-Lookup bei 400 Nodes | Benchmark TC-08 (Mermaid-Traversal-vs-Linear-Scan), Hard-Limit bei p95 >5ms |
| Inkonsistenz zwischen Mermaid-Edges und `related_ids` | `MermaidMemoryAdapter` ist einzige Schreibstelle; alle Updates gehen durch ihn |
| Große Mermaid-Graphen blähen Prozess-Memory auf | Hard-Cap 400 greift genauso; L1-Eviction räumt auch Mermaid-Knoten auf |

### 2.3 Moderne Retrieval-Methoden

#### 2.3.1 Pipeline pro Query

```
Query eingehend
   │
   ├─► [Symbol-Extractor] → ["routing.txt", "SoulAG", "2026-06-25"]
   │       │
   │       └─► L2 FTS5 Fulltext-Match (exact + stemmed)  ─┐
   │       │                                              │
   │       └─► L2 Fuzzy-Symbol-Match (Levenshtein ≤2)    ─┤
   │                                                       │
   ├─► [Embedder] → vector(384)                            │
   │       │                                              │
   │       └─► FAISS Top-50 by cosine                     ─┤
   │                                                       │
   └─► [RRF Fusion] hybrid_score = Σ rank_i^(-1)        ─┘
              │
              ▼
   [Re-Ranker MiniMax/local → Top-5]
              │
              ▼
   [Cache-Check LRU by hash(query+symbols)]
       │  Hit  → return
       └─  Miss → compute + cache
```

#### 2.3.2 Re-Rank-Modul

Nicht jedes Top-Ergebnis von BM25+Vector ist relevant. Re-Ranker ist ein kleines Cross-Encoder-Modell oder — wenn kein Cross-Encoder verfügbar — Heuristik:

```
relevance = 0.4 * cosine
          + 0.3 * bm25_norm
          + 0.2 * symbol_overlap_ratio
          + 0.1 * recency_decay
```

#### 2.3.3 Query-Expansion (Sidecar SoulAG)

Bei jeder Query: MiniMax/Local LLM bekommt `QUERY → expanded_keywords[]` Aufgabe (max 8 Wörter, latent 0.3). Kosten ~50 Tokens, gewinnt Recall ~15%.

### 2.4 Benchmark-Framework

**Scope-Constraint (User-Mandat 2026-07-01):** Das Benchmarking existiert **ausschließlich als Backend**. Es wird eine API-Schnittstelle definiert, **keine eigene Frontend-Seite** gebaut. Konsumiert werden die KPIs via `curl`/`fetch`/Monitoring-Tooling oder in Phase 3+ über bestehende Dashboard-Komponenten — aber kein neuer UI-Tab.

#### 2.4.1 KPI-Klassen

| Klasse | Metrik | Zielwert |
|---|---|---|
| **K1: Token-Economy** | Avg-Tokens/Task; Sum-LLM-Spend/Monat | ≥40% Reduktion vs. baseline |
| **K2: Retrieval-Latency** | p50/p95/p99 für L1, L2, L3 | L1<50ms; L2<200ms; L3<800ms |
| **K3: Agent-Task-Success** | % Tasks ohne Retry; % Tasks mit Validator-Pass | ≥+10pp vs. baseline |
| **K4: Cache-Hit-Rate** | % Top-K-Queries aus LRU; L1→L2-Hit | ≥60% L1-Hit; ≥30% L2-Hit |

#### 2.4.2 KPI-Backend-Endpoint: `GET /api/memory/kpis`

**Explizit nur Backend, kein UI:**

```json
GET /api/memory/kpis?window=24h&agent=coderag&kpi=token_economy

{
  "ts": 1782936000.0,
  "window": "24h",
  "filter": {"agent": "coderag"},
  "kpis": {
    "token_economy": {
      "avg_tokens_per_task": 1240,
      "sum_prompt_tokens_24h": 184500,
      "sum_completion_tokens_24h": 91200,
      "vs_baseline_reduction_pct": 42.3
    },
    "retrieval_latency_ms": {
      "l1": {"p50": 12, "p95": 38, "p99": 47},
      "l2": {"p50": 95, "p95": 178, "p99": 240},
      "l3": {"p50": 410, "p95": 720, "p99": 950}
    },
    "cache_hit_rate": {
      "l1_hit": 0.68,
      "l2_hit": 0.32,
      "l3_hit": 0.04
    },
    "agent_task_success": {
      "no_retry_rate": 0.84,
      "validator_pass_rate": 0.91,
      "vs_baseline_delta_pp": 12
    }
  },
  "metadata": {
    "memory_backend": "sqlite_faiss",
    "ab_group": "treatment",
    "sample_size": 4218
  }
}
```

**Query-Parameter:**
- `window` ∈ {`1h`, `24h`, `7d`, `30d`, `all`} — default `24h`
- `agent` — optional, default = alle aggregiert
- `kpi` — optional, default = alle; Komma-getrennt für mehrere
- `format` ∈ {`json` (default), `prometheus`} — Prometheus-Format für Monitoring-Integration

**Implementation:**
- Endpoint in `src/gnom_hub/api/endpoints/memory_kpis.py`
- Read-only über `kpi_repository.py` (eigene Mini-Read-Model, KEIN Write-Pfad)
- Datenquelle: `kpi_events`-Tabelle (Cursor-Append bei jedem LLM-Call, jeder Retrieval-Operation, jedem Agent-Task-Ende)
- Performance-Budget: Endpoint-Antwort <200ms p95

**Was bewusst NICHT existiert (User-Mandat):**
- Keine HTML-Page `/memory/dashboard` o.ä.
- Keine WebSocket-Streams für Live-Updates
- Keine Chart-Komponenten
- Keine neuen Frontend-JS-Files

Monitoring-Tooling (Grafana, Prometheus, curl-Skript im Cron) wird später extern angedockt.

#### 2.4.3 A/B-Harness (Phase 3+)

- `bench/replay_harness.py` lädt `.bench/` Korpus (echte Chat-Traffic aus DB, anonymisiert)
- Pro Task: zwei Runs (alt vs. neu), gleicher Input, gleicher Random-Seed
- Output: `POST /api/memory/bench-report` (Backend-only) mit allen 4 KPIs als JSON + Markdown-Report als File

#### 2.4.4 Live-A/B-Routing

Per-Agent-Flag `MEMORY_AB_GROUP` ∈ {`control`, `treatment`}:
- Control: alter Memory-Pfad
- Treatment: neuer Pfad (Hot+Warm+Cold)
- Vergleich gemessen in `/api/memory/ab-results` (Backend-only, kein UI)

### 2.5 Konkrete Test-Cases (≥5)

#### TC-01 — Token-Budget pro Routine-Task
- **Setup:** 100 deterministische Tasks aus `.bench/routine_100.json`
- **Measure:** Sum `completion_tokens + prompt_tokens` (von LLM-API-Audit-Log)
- **Pass-Criteria:** Reduction ≥40% vs. pre-rewrite baseline
- **Tool:** `python -m bench.token_budget_test`

#### TC-02 — Recall@5 für semantische Queries
- **Setup:** 50 Query/Expected-Hit-Pairs manuell kuratiert (z.B. „routing-bug" → erwartet Fact-ID abc123)
- **Measure:** Recall@5, MRR (Mean Reciprocal Rank)
- **Pass-Criteria:** Recall@5 ≥0.85, MRR ≥0.7
- **Tool:** `pytest -k recall_at_k`

#### TC-03 — Layer-Speed-Budget
- **Setup:** 1000 zufällige Queries, je mit Layer-Pin (L1/L2/L3)
- **Measure:** p95 Latenz + Cache-Hit-Rate
- **Pass-Criteria:** L1<50ms, L2<200ms, L3<800ms
- **Tool:** `pytest -k layer_latency`

#### TC-04 — Promotion-Korrektheit
- **Setup:** Synthetische Insert-Sequenz: 3 Hits von 2 Agents auf denselben L1-Fact
- **Measure:** Fact nach 24h in L2 mit `promoted_by='auto'`
- **Pass-Criteria:** 100% der Triggers greifen
- **Tool:** `pytest -k promotion_logic`

#### TC-05 — Cold-Migration ohne Datenverlust
- **Setup:** 100 L2-Facts mit Importance-Drift über simulierte 90 Tage
- **Measure:** Anzahl in L3 nach `curator.sweep()`; Sum-Hits auf L3-Inhalte über 30d
- **Pass-Criteria:** Alle 100 migriert, ≥80% mindestens 1 Hit in L3 innerhalb 30d (also kein Datengrab)
- **Tool:** `pytest -k cold_migration_e2e`

#### TC-06 — Cache-Wirksamkeit
- **Setup:** 1000 identische Queries in 60s
- **Measure:** Hit-Rate, Tokens gespart
- **Pass-Criteria:** Hit-Rate ≥95% nach 10s
- **Tool:** `pytest -k cache_warmup`

#### TC-07 (Bonus) — Decay verhindert Fact-Suppression
- **Setup:** L2-Fact mit hoher Importance wird in einem Audit vom selben Tag wiederverwendet
- **Measure:** Importance steigt statt zu sinken
- **Pass-Criteria:** Delta-Importance > 0 nach Hit
- **Tool:** `pytest -k decay_resilience`

#### TC-08 — Mermaid-Graph-Konsistenz (final 2026-07-01)
- **Setup:** 100 zufällige L1-Inserts, davon 30 mit `related_ids`-Beziehungen; parallel Mermaid-Graph beobachten
- **Measure:** Anzahl Mermaid-Nodes == Anzahl L1-Records; Anzahl Mermaid-Edges == Sum `related_ids` Counts; Bidirektionalität (A→B impliziert B→A) zu 100%
- **Pass-Criteria:** Identity-Bedingung exakt; Bidirektionalität exakt; bei L1-Eviction werden äquivalente Mermaid-Knoten/Edges entfernt
- **Tool:** `pytest -k mermaid_consistency`

#### TC-09 — Repository-Backend-Swap-Isolation (final 2026-07-01)
- **Setup:** Implementiere `InMemoryTestBackend` (trivial: Dict-basiert). Schreibe Tests die gegen `MemoryBackend`-Interface laufen, nicht gegen konkrete Implementierung. Aktiviere `MEMORY_BACKEND=inmemory_test` und führe alle TC-01 bis TC-08 aus.
- **Measure:** Alle Tests grün, ohne dass eine Zeile in RetrievalEngineer/Curator geändert wurde
- **Pass-Criteria:** 100% der Tests passieren mit dem Test-Backend
- **Tool:** `pytest --memory-backend=inmemory_test`
- **Warum das wichtig ist:** Beweist, dass das Repository-Pattern wirklich abstrahiert — wenn der Graph-Backend später kommt, sind keine Code-Änderungen außerhalb von `graph_backend.py` nötig.

#### TC-10 (Bonus) — KPI-Endpoint-Performance
- **Setup:** 10.000 synthetische KPI-Events in `kpi_events` einspeisen, dann `GET /api/memory/kpis?window=24h` aufrufen
- **Measure:** Endpoint p95 Latenz
- **Pass-Criteria:** <200ms p95
- **Tool:** `pytest -k kpi_endpoint_perf`

### 2.6 Test-Strategie (für IntegrationQA)

| Kategorie | Was | Tool | Frequenz |
|---|---|---|---|
| Unit | Pure-Functions (Dedup, Decay, FTS5-Wrapper) | `pytest` | pro Commit |
| Integration | DB-Layer + FAISS + Re-Ranker | `pytest` | pro PR |
| Regression | Vergleich: pre/post Benchmarks | `bench/replay` | pro Release |
| Load | 10k Inserts in 60s, 1k Queries/s | `locust` | pro Monat |
| Chaos | Random 30% der Facts löschen, Curator-Recovery | `pytest -k chaos` | pro Release |
| E2E | Echter Hub-Chat-Request, End-to-End-Memory-Flow | Playwright + Hub-API | pro Release |

### 2.7 Migration & Rollout

**Phase 0 — Basis (KW 1):**
- Schema-Definition + Alembic-Migrationen
- `MemoryRecord`-Dataclass final
- Strangler-Adapter schreiben (alter Pfad bleibt default)

**Phase 1 — Parallel-Run (KW 2):**
- `USE_NEW_MEMORY=false` per default
- A/B-Harness: 1% Treatment-Traffic für Real-World-Daten
- Curator + Re-Ranker inaktiv (nur Logging)

**Phase 2 — Schrittweise Hochskalierung (KW 3–4):**
- 10% → 50% → 100% Treatment
- KPI-Tracking sichtbar im Dashboard
- Go/No-Go pro Phase basierend auf K1/K3

**Phase 3 — Cleanup (KW 5):**
- Alter Memory-Layer als deprecated markiert
- Final-Cut: 1 Release später, alter Code weg
- ADR in `docs/memory-architecture-decisions.md`

### 2.8 Risikoregister

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|---|---|---|---|
| FAISS-ABI-Bruch mit numpy 2.x | mittel | hoch (Total-Recall-Failure) | numpy<2 Pin im pyproject, smoke-test in CI |
| SoulAG LLM-Loop beim Re-Rank | niedrig | mittel | Token-Cap + Timeout, Re-Ranker-Disabled-Fallback |
| Cold-Migration verliert wichtige Facts | mittel | hoch | Soft-Delete-Window, Audit-Trail, Recovery-Script |
| Cache vergiftet durch Müll-Queries | niedrig | mittel | LRU-Eviction + manuelle Cache-Reset-API |
| A/B-Harness wirkt sich auf User-Latency aus | sehr niedrig | niedrig | Treatment nur 1% in Phase 1 |

---

## TL;DR (für schnelles Lesen)

1. **3-Schichten-Stack:** Hot (RAM, flüchtig) / Warm (SQLite+FAISS+BM25) / Cold (komprimiertes Archiv)
2. **Repository-Pattern:** Abstrakte `MemoryBackend`-Schnittstelle, SQLite+FAISS default, Graph-Backend drop-in-fähig
3. **5-Agent-Team:** Architect, Curator, RetrievalEngineer, PerfArchitect, IntegrationQA
4. **Mermaid-Integration:** Bestehender Mermaid-Graph bleibt als symbolischer Sub-Layer von L1, gewrappt durch Adapter
5. **Hybrid Retrieval:** BM25 + Vector + Symbol-Match + Mermaid-2-hop via Reciprocal Rank Fusion
6. **KPI-Framework:** 4 Klassen, 10 Test-Cases, **Backend-only** `GET /api/memory/kpis` (kein UI)
7. **Strangler-Migration:** 5-Wochen-Plan, Feature-Flag-Default-false, KPI-Go/No-Go
8. **Outcome:** ≥40% Token-Reduktion, messbare Task-Success-Steigerung, kein Datenverlust, Graph-Backend-Pfad geöffnet

---

## Anhang A — Design-Decisions-Log

Dokumentation der expliziten Architektur-Entscheidungen, die nach User-Review vom 2026-07-01 finalisiert wurden.

### ADR-001: L1-Hard-Cap = 400 (statt initialer Spec 300)

**Status:** accepted · 2026-07-01

**Kontext:** Initialer Konzeptentwurf hatte Hard-Cap 300, basierend auf Linear-Scan-Latency-Schätzung. User-Review identifizierte, dass bei komplexen Multi-Step-Tasks (z.B. CoderAG während eines Refactorings) 300 Facts zu schnell erreicht werden und wichtige Working-Memory-Inhalte vorzeitig in L2 gepromoted werden, wo sie langsamer retrieven.

**Entscheidung:** Hard-Cap auf **400** angehoben.

**Konsequenzen:**
- Linear-Scan bei 400 Items: ~10ms — bleibt im 50ms-Budget, aber am oberen Ende der Komfortzone
- Bei typischen 8-Agent-Hub-Workload: durchschnittlich 150-200 Facts pro Agent aktiv — Hard-Cap ist Reserve, nicht Norm
- Trigger-Frequenz für Overflow-Eviction sinkt von ~1×/Tag auf ~1×/Woche → Curator entlastet
- **Monitoring-Pflicht:** Falls p95-Latency im L1-Read-Path über 30ms steigt → Hard-Cap auf 350 senken, ADR revidieren

### ADR-002: L2-Dedup asynchron via Dedup-Queue

**Status:** accepted · 2026-07-01

**Kontext:** Initialer Entwurf sah inline-Cosine-Check bei jedem L2-Insert vor. Bei geschätztem Production-Throughput (50-200 Inserts/s im Hub-Hauptverkehr) ist O(n)-Cosine pro Insert nicht tragbar — würde Insert-Latency um 5-20ms treiben und DB-Locks überproportional lange halten.

**Entscheidung:** Dedup-Operation wird in **dedizierte `l2_dedup_queue`-Tabelle** async verschoben, durch separaten Curator-Sweep alle 30–60s abgearbeitet.

**Konsequenzen:**
- L2-Insert bleibt unter 1ms (nur Queue-Write, kein Cosine)
- 30–60s Race-Window akzeptiert, weil: (a) beide Near-Duplicates funktional identisch sind, (b) Re-Ranker dedupliziert ohnehin per `related_to`-Beziehung, (c) nach Sweep ist `supersedes_id`-Link gesetzt
- Neue Failure-Mode: **Dedup-Backpressure**. Queue-Hard-Cap 10.000, bei Überlauf Drop-Oldest + Warning. Sentry-Alert bei `L2_DEDUP_BACKPRESSURE`-Event-Rate > 5/min
- Curator-Sweep-Lock via `BEGIN IMMEDIATE` Transaktion, um parallele Insert-Wellen sicher zu handhaben
- Konfig-Parameter: `L2_DEDUP_INTERVAL_S=45` default, overridebar via `.env`

### ADR-003: Hybrid-Scheduling Curator (Event + Periodic)

**Status:** accepted · 2026-07-01

**Kontext:** Diskussion ob Curator rein event-driven oder rein periodic laufen soll. User-Review bestätigte Hybrid als richtigen Mittelweg.

**Entscheidung:** Hybrid mit klarer Taxonomie — inline-Trigger für State-Changes (Insert, Overflow), periodic für Time-basierte Sweeps (Decay, Cold-Migration, Audit).

**Konsequenzen:**
- Atomarität von Insert + Dedup-Check bleibt erhalten (kein Race-Window)
- Decay-Funktionen können korrekt zeitbasiert feuern
- Bulk-Operations (Cold-Migration 10k+ Records) laufen außerhalb des Hot-Paths (03:00 daily)
- Operator-Hook: `POST /api/memory/curator/run_now?job=<name>` für manuelle Auslösung bei Ops-Issues

### ADR-004: Auto-Promotion-Threshold composite ≥ 0.5

**Status:** accepted · 2026-07-01

**Kontext:** Beim L1-Overflow-Eviction braucht es einen klaren Schwellwert, welcher Fact promoted vs. discarded wird.

**Entscheidung:** `composite = importance + 0.1·log(hits+1) − 0.05·days_idle` ≥ 0.5 UND `hit_count ≥ 1` → Auto-Promote. Sonst Discard zu L4-Tombstone.

**Begründung:** 0.5 als Threshold bedeutet, dass ein Fact entweder von Natur aus wichtig ist (importance ≥ 0.5) oder durch häufige Nutzung Wichtigkeit akkumuliert hat (z.B. importance=0.3, hits=10, days_idle=0 → 0.3 + 0.1·log(11) − 0 = 0.53 → promoted). Schwelle verhindert, dass Noisy-Facts mit importance=0.1 und 1 Hit den Promotion-Pfad verstopfen.

**Konsequenzen:** Promotion-Rate empirisch monitoren. Falls >30% der L1-Inserts auto-promoted werden → Threshold auf 0.6 anheben, ADR revidieren.

### ADR-005: Repository-Pattern mit abstraktem `MemoryBackend`-Interface

**Status:** accepted · 2026-07-01

**Kontext:** User-Mandat: L2 soll heute SQLite+FAISS nutzen, aber Architektur muss spätere Erweiterung um Graph-Backend ohne Großumbau ermöglichen. Initialer Entwurf band Konsumenten direkt an SQLite+FAISS-Implementierungen.

**Entscheidung:** Abstrakte `MemoryBackend`-Schnittstelle (Protocol) in `src/gnom_hub/memory/backend.py`. Konkrete Implementierungen: `SQLiteFAISSBackend` (default), `GraphBackend` (future), `InMemoryTestBackend` (Tests). Factory `get_memory_backend()` liest `MEMORY_BACKEND` aus `.env`. Alle Konsumenten (Curator, RetrievalEngineer, etc.) bekommen den Backend per Singleton-Injection, nie per Direktimport.

**Konsequenzen:**
- + ~150 LoC Interface-Definition (gut investiert)
- + Test-Backend ohne SQLite+FAISS-Abhängigkeit möglich
- + Graph-Backend-Drop-In: ein neues File, sonst nichts
- − Indirektion: Stacktrace wird eine Ebene tiefer (akzeptabel, dokumentiert)
- − Refactoring bestehender Direkt-Aufrufe von `fact_cache`/`soul_embedding` zu `MemoryRecord`+`MemoryBackend` ist Vorarbeit in Phase 0

**Validierung:** Test-Case TC-09 beweist die Isolation explizit.

### ADR-006: Mermaid-Graph als symbolischer Sub-Layer von L1

**Status:** accepted · 2026-07-01

**Kontext:** Der bestehende symbolische Kurzzeitspeicher ist als Mermaid-Graph implementiert (in-process DiGraph). User-Mandat: bestehende Struktur sinnvoll integrieren, nicht ersetzen. Initialer Reflex war, den Mermaid-Code in `MemoryRecord.factsymbols` aufzulösen — verworfen, weil damit die Traversierbarkeit (2-hop-Nachbarschaft) verloren ginge.

**Entscheidung:** Mermaid-Graph bleibt als **parallel-strukturierter Sub-Layer von L1 HOT** bestehen, gewrappt durch `MermaidMemoryAdapter`. Node-ID == MemoryRecord.id, Edge == related_ids-Beziehung. Bidirektional konsistent gehalten durch Single-Write-Path (Adapter). Persistenz erst bei L1-Eviction (related_ids wandern in L2-Records).

**Konsequenzen:**
- Bestehende Mermaid-basierte Logik (SoulAG, Visualisierungen) funktioniert weiter
- + 2-hop-Traversal in L1-Reads ohne zusätzliche Backend-Query
- − Single-Write-Path-Disziplin muss im Adapter erzwungen werden
- − Risiko der Mermaid-Performance bei 400 Nodes (mitigation: TC-08 misst das)

**Validierung:** Test-Case TC-08 misst Identity- und Bidirektionalitäts-Bedingungen.
