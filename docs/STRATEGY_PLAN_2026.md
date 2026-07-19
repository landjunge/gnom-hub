# Gnom-Hub — Strategieplan 2026

**Stand:** 2026-07-19  
**Zielbild:** Schlank · Stabil · State-of-the-Art · ohne Kompromisse an der Kernqualität  
**Bezug:** [TECHNICAL_STATUS_REPORT_2026-07.md](./TECHNICAL_STATUS_REPORT_2026-07.md)

---

## 1. Leitprinzipien

1. **Control Plane ≠ Data Plane**  
   Der Hub orchestriert; er speichert nicht jede Agent-Nebenwirkung im gleichen Write-Pfad wie die User-Chat-Latenz.

2. **Exactly-once wo es zählt, at-least-once wo es erlaubt ist**  
   Jobs dürfen nicht „done“ werden, wenn das LLM leer war. User-Chat muss **immer** < 200 ms speichern.

3. **Ein Launch-Modell, ein Queue-Backend, ein Observability-Pfad**  
   Keine dualen Chat-Stacks, keine dualen Agent-Startstile, keine stillen Fallbacks.

4. **Local-first, cloud-optional**  
   2026: lokaler Orchestrator bleibt USP — aber mit **professionellem** Storage/Queue/API-Design.

5. **Delete ruthlessly**  
   Features ohne Owner, unverdrahtete Module und 4k-LOC-JS-Monolithen bremsen mehr als sie bringen.

---

## 2. Zielarchitektur (2026, ohne Kompromiss)

### 2.1 Logische Schichten

```
┌─────────────────────────────────────────────────────────────┐
│  Web UI (TypeScript, Vite, Web Components or Svelte/React)  │
│  - Chat stream (SSE/WebSocket)  - Showbox  - Ops dashboard  │
└───────────────────────────┬─────────────────────────────────┘
                            │ OpenAPI 3.1 + typed client
┌───────────────────────────▼─────────────────────────────────┐
│  Control Plane (async FastAPI / Starlette)                  │
│  - Authn local token   - Chat command API   - Agent control │
│  - Health / metrics (OpenTelemetry)                         │
└───────┬─────────────────────┬─────────────────────┬─────────┘
        │                     │                     │
   ┌────▼────┐          ┌─────▼─────┐         ┌─────▼─────┐
   │ Chat DB │          │ Job Queue │         │ Object /  │
   │ (OLTP)  │          │ (NATS/    │         │ Workspace │
   │ Postgres│          │  Redis    │         │ FS + blob │
   │ o. libSQL│         │  Streams) │         │           │
   └─────────┘          └─────┬─────┘         └───────────┘
                              │ pull / push
                    ┌─────────▼─────────┐
                    │  Agent Runtime    │
                    │  (1 image, N      │
                    │   workers)        │
                    │  tool sandbox     │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  LLM Gateway      │
                    │  (LiteLLM-style)  │
                    │  MiniMax/OR/Ollama│
                    └───────────────────┘
```

### 2.2 Technologie-Empfehlungen (2026)

| Bereich | Empfehlung | Warum (2026) |
|---------|------------|--------------|
| **API** | FastAPI **async-first**, Pydantic v2, OpenAPI als Vertrag | Bereits im Stack; sync-Chat-Handler raus |
| **Chat/State OLTP** | **PostgreSQL 17** *oder* **libSQL/Turso embedded** (SQLite-Protokoll, multi-writer-fähig) | SQLite-Datei ist bei 9 Prozessen ausgereizt |
| **Job Queue** | **NATS JetStream** oder **Redis Streams** (lokal Docker/one-binary) | Persistente Jobs, Consumer Groups, Retry/Backoff, kein `BEGIN IMMEDIATE`-Kampf |
| **Realtime** | **SSE** primär, WebSocket optional | Chat-Updates ohne Poll-Sturm |
| **Agent Runtime** | Ein Binary/`run_agent`, **N Worker-Threads oder Prozesse** hinter der Queue — *nicht* 8 getrennte Lebenszyklen mit Watchdog-Races | Weniger Spawn-Chaos |
| **Sandbox** | OS-level: `bubblewrap`/Seatbelt oder **Firecracker microVM** für `run`/`write` high-risk | Path-Regex allein ist 2019 |
| **LLM Gateway** | Eigenes dünnes Gateway **oder** LiteLLM-kompatible Schicht: Timeouts, Budget, Structured Outputs, Tool Calling | Free-Model-Rotation bleibt Feature, nicht Chaos |
| **Observability** | **OpenTelemetry** Traces + Prometheus Metrics + strukturierte Logs (JSON) | „database is locked“ muss Trace-ID haben |
| **Frontend** | **Vite + TypeScript +** schlankes Framework (Svelte 5 *oder* React 19) | 12k LOC unbundled JS ist nicht wartbar |
| **Schema/Migration** | **Alembic** (Postgres) oder **Atlas/goose** | Dual-Init `schema.py` + ad-hoc Migrations beenden |
| **Testing** | CI-Matrix: unit | contract | e2e (Testcontainers) | 21 ignorierte Module schließen |
| **Config** | 12-factor, **Pydantic Settings**, keine Desktop-Key-Magie ohne Audit | Reconciler bleibt, aber deterministisch |
| **Memory/TKG** | Behalten als **optionales Addon**; Default-Pfad darf nicht FAISS/Kuzu brauchen | Kern schlanker |

### 2.3 Was explizit *nicht* mehr Ziel ist

- SQLite als Message-Bus zwischen 9 Prozessen  
- Zwei Agent-Startstile (`run_agent` vs `agents.*AG`)  
- Sync-HTTP Self-Calls Hub→Hub (historisch Soul-Pulse)  
- Polling alle 0,5–2 s als Wakeup-Ersatz  
- „Soft-OK online“ ohne ehrlichen Degradation-Status in der UI  
- Monolith-JS ohne Typecheck  

---

## 3. Schlanker machen: Cut-Liste

### Sofort löschen / mergen (Woche 1–2)

| Item | Aktion |
|------|--------|
| Unverdrahtetes `api/endpoints/chat.py` (Orchestrator) | Mergen in einen Chat-Service **oder** löschen |
| Legacy `agents.*AG` Startpfad | Nur noch `run_agent --name` |
| Tote Doku-Aussagen (SoulAG-Default) | ARCHITECTURE.md sync |
| Doppelte Provider-Pfade / Re-Exports | Ein `ask_router` Import-Pfad |
| Browser-/Stress-Tests in ignore, die nie laufen | Reparieren **oder** aus Repo entfernen |

### Produkt-Fokus (was bleibt)

1. **War-Room Chat** (User ↔ GeneralAG ↔ Workers)  
2. **Showbox** (strukturierte Agent-Outputs)  
3. **Job Queue** mit sichtbarem Status  
4. **Security Grants** für Workspace außerhalb Default  
5. **LLM Routing** mit Budget und Failover  
6. **Ops Health** (process + queue + model)  

Alles andere (TKG, Offload-Canvas, Token-Economy-UI, Bake, …) wird **Feature-Flag + Addon**, nicht Boot-Pflicht.

---

## 4. Stabiler machen: Engineering-Standards

### 4.1 Zuverlässigkeit

| Regel | Umsetzung |
|-------|-----------|
| User-Chat-Write ≤ 100 ms p99 | Dedizierte Chat-Store-Connection / separates Topic; nie hinter Agent-LLM |
| Jobs: empty LLM → **NACK + backoff** | Nie `ack` bei `[ROUTER-FEHLER]` / leerem Content |
| Poison messages | Nach N Retries → DLQ + UI-Badge |
| Idempotenz | `msg_id` / `client_request_id` auf Chat + Jobs |
| Backpressure | Harte Queue-Limits pro Agent + 429 an API |

### 4.2 Prozessmodell

**Heute:** 1 Hub + 8 OS-Prozesse + Watchdog-Restart-Races.  
**Ziel:**

```
hub (API)
 └─ agent-supervisor (ein Supervisor)
      ├─ worker pool size = f(CPU, config)
      └─ je Worker: pull job → tools → complete
```

- Supervisor owned PID-Lifecycle (kein PID-File-Zoo)  
- Health = Supervisor-Report, nicht 8 Heartbeat-Writer  
- Optional: Agents als **Plugins** im selben Prozess *mit* Thread/Process-Pool — Queue bleibt extern

### 4.3 Observability (non-negotiable)

- Trace pro User-Message: `chat_id → job_id → llm_span → tool_spans`  
- Metrics: `chat_post_seconds`, `queue_depth`, `llm_errors_total`, `db_busy_total`  
- Alert: queue depth > N, no healthy workers, p99 chat > 1 s  

---

## 5. Phasen-Roadmap (klare Reihenfolge)

### Phase 0 — Freeze & Truth (3–5 Tage) ✅ teilweise erledigt

**Ziel:** Messbare Baseline, keine neuen Features.

- [x] Doppel-Agent-Spawn killen  
- [x] busy_timeout / Soft-Register / Chat-Fail-fast  
- [ ] **Alle** `get_db_connection()`-Leaks → `get_db_conn()`  
- [ ] Empty-LLM → NACK (nicht ACK)  
- [ ] `processing_since IS NULL` Recovery-Fix  
- [ ] ARCHITECTURE.md + Status-Report im Repo (dieses Dokument)  
- [ ] Dashboard: Queue depth + last chat latency  

**Exit-Kriterium:** 30 min Dauerlast (1 Chat / 5 s) ohne „Hub unreachable“, 8 Agenten konstant.

---

### Phase 1 — Reliability Hardening (1–2 Wochen)

**Ziel:** Auf SQLite *noch* betreibbar, aber korrekt.

1. **Write-Serialisierung im Hub**  
   - Single Writer Thread / `asyncio.Queue` für alle Hub-DB-Writes  
   - Agenten schreiben Jobs nur über Hub-API *oder* getrennte Queue-DB  

2. **Chat-API async + SSE**  
   - `POST /api/chat` speichert + enqueued, returned `202` + `message_id`  
   - Client subscribed `GET /api/chat/stream`  

3. **Job-State-Machine**  
   - `pending → leased → succeeded|failed|dead_letter`  
   - Lease-Timeout mit Owner-Token (kein blindes Requeue)  

4. **LLM Gateway Hardening**  
   - Structured timeouts, circuit breaker pro Provider  
   - Budget/day; Free-Pool bleibt, Paid bevorzugen wenn Key da  

5. **Frontend Hotfix**  
   - `workspace.js` API-Prefix  
   - Chat send: optimistic UI + Retry  

**Exit-Kriterium:** Kein Job-Verlust bei erzwungenem 429; Chat p99 < 300 ms.

---

### Phase 2 — Storage & Queue Modernisierung (2–4 Wochen)

**Ziel:** SQLite-als-Bus ablösen.

#### Option A — Empfohlen für Single-Machine 2026

| Component | Choice |
|-----------|--------|
| OLTP | **libSQL** (embedded, multi-client) *oder* Postgres via Docker Desktop |
| Queue | **NATS JetStream** (eine Binary, persist streams) |
| Blobs | Workspace-FS + Content-Addressed Cache |

#### Option B — Maximal einfach, etwas weniger „pro“

| Component | Choice |
|-----------|--------|
| OLTP + Queue | **Postgres** only (`LISTEN/NOTIFY` + `FOR UPDATE SKIP LOCKED`) |

**Migrationspfad:**

1. Schema in Migrationstool  
2. Dual-write Queue (SQLite + NATS) eine Woche  
3. Read-cutover Agents → NATS  
4. SQLite-Queue-Tabellen deprecated  

**Exit-Kriterium:** 8 Agenten + Chat + Showbox ohne `database is locked` in 24 h Log.

---

### Phase 3 — Runtime & Security (2–3 Wochen)

1. **Supervisor-basiertes Agent-Modell** (ein Lifecycle)  
2. **Tool Sandbox** für `run`/`write` (OS isolation)  
3. **Capability tokens** statt nur DB-Grants-Strings  
4. Gatekeeper wieder aktiv, aber **policy-as-code** (z. B. Cedar/OPA-lite), nicht ad-hoc  
5. Local auth token für API (auch single-user)  

**Exit-Kriterium:** Malicious path escape Tests grün; kein Tool-Call außerhalb Grant.

---

### Phase 4 — UI & DX (2–3 Wochen, parallel ab Phase 2)

1. Vite + TypeScript Scaffold, OpenAPI-Client generieren  
2. Chat + Showbox + Agents als getrennte Packages  
3. `dashboard.js` schrittweise ersetzen (Strangler)  
4. Storybook/Playwright E2E **in CI** (nicht ignore)  
5. Design-Tokens / Showbox-Spec als versionsierte Schemas (JSON Schema 2020-12)

**Exit-Kriterium:** Kein untyped 4k-LOC-Dashboard mehr im kritischen Pfad.

---

### Phase 5 — Intelligence Layer (optional, nach Stabilität)

Erst **nach** Phase 2:

- TKG/Memory als Service mit eigenem Store  
- Deterministic routing + LLM fallback (bereits ansatzweise in `routing.py`)  
- Evaluation harness: golden tasks, regression scores  
- Cost/latency dashboards pro Agent  

---

## 6. Konkrete nächste Schritte (diese Woche)

Priorisiert, umsetzbar, messbar:

| # | Schritt | Owner-Fokus | Done when |
|---|---------|-------------|-----------|
| 1 | Leak-Audit: `rg "with get_db_connection"` → `get_db_conn` | DB | 0 Leaks, FD-Count stabil |
| 2 | `agent_base`: empty/ROUTER-FEHLER → `nack_message` + backoff | Agents | Job erscheint wieder als pending |
| 3 | Recovery-SQL: `processing_since IS NULL` nur mit `created_at`-Alter | Queue | Kein Thrash in Logs |
| 4 | Heartbeat setzt **nicht** status=online wenn busy/processing | Registry | Status konsistent |
| 5 | Chat SSE Prototype (auch nur Hub→Browser) | API/UI | Poll-Intervall kann ≥5 s |
| 6 | ADR: „Queue = NATS vs Postgres SKIP LOCKED“ entscheiden | Architecture | ADR in `docs/plans/` |
| 7 | CI: 3 kritische ignore-Tests reaktivieren oder löschen | QA | Ignorierliste schrumpft |
| 8 | Ops-Panel: queue depth, agent lease, last error | Frontend | Sichtbar ohne Log-Lesen |

---

## 7. Zielmetriken (Definition of Done für „deutlich besser“)

| Metrik | Heute (ca.) | Ziel 90 Tage |
|--------|-------------|--------------|
| Chat POST p99 | oft >15 s unter Lock, sonst ~30 ms | **< 200 ms** |
| Job-Verlust bei LLM-Fehler | häufig (ACK) | **0** (NACK/DLQ) |
| Agent-Prozesse | 8 (+historisch 16) | **Supervisor + N workers**, deterministisch |
| `database is locked` / h | häufig unter Last | **≈ 0** im Chat-Pfad |
| Frontend critical path | untyped monolithe | **typed modules** |
| CI ignore-Liste | 21 Module | **≤ 5** (nur echte Live-Akzeptanz) |
| Trace-Coverage kritische Pfade | nein | **ja** (OTel) |

---

## 8. Architektur-Entscheidungen (ADRs vorbereiten)

Empfohlene ADRs in `docs/plans/adr/`:

1. **ADR-001** Queue-Backend (NATS JetStream vs Postgres)  
2. **ADR-002** OLTP (libSQL vs Postgres)  
3. **ADR-003** Agent Runtime (multi-process vs supervisor pool)  
4. **ADR-004** Frontend stack (Svelte 5 vs React 19)  
5. **ADR-005** Sandbox model (OS bubblewrap vs microVM)  
6. **ADR-006** LLM Gateway boundaries & budget policy  

Keine große Migration ohne ADR + Rollback-Plan.

---

## 9. Risiko der Modernisierung (ehrlich)

| Risiko | Gegenmaßnahme |
|--------|----------------|
| Big-Bang Rewrite tötet Momentum | Strangler: Queue zuerst, UI zuletzt |
| libSQL/NATS Lernkurve | Phase 1 bleibt auf gehärtetem SQLite lauffähig |
| Feature-Verlust | Cut-Liste nur mit User-OK; Flags statt Delete wo unklar |
| CI bricht | Dual-run Migrations + Feature flags |

---

## 10. Strategisches Nordstern-Statement

> **Gnom-Hub 2026** ist ein local-first Multi-Agent Control Plane mit professioneller Job-Queue, typsicherem UI und sandboxed Tools — nicht eine SQLite-Datei, die von neun Prozessen um die Wette beschrieben wird.

Der Wert des Projekts (Agenten-Rollen, Showbox, Security-Grants, Router) bleibt.  
Was sich ändert: **die Tragstruktur**.

---

## 11. Anhang — Mapping Status → Strategie

| Status-Problem | Strategie-Antwort |
|----------------|-------------------|
| P0.1 SQLite Multi-Writer | Phase 1 Write-Queue → Phase 2 NATS/Postgres |
| P0.2 Connection Leaks | Phase 0 Audit |
| P0.3 ACK on LLM fail | Phase 0 NACK |
| P1.1 Fake notify | Phase 2 echte Queue-Consumer-Wakeup |
| P1.3 Process races | Phase 3 Supervisor |
| P1.4 Free LLM | Phase 1 Gateway + Budget |
| P2 Frontend | Phase 4 Strangler |
| P2 Tests ignore | Phase 0–1 CI hygiene |

---

*Dieses Dokument ist die strategische Leitplanke. Operative Tickets sollten 1:1 aus Abschnitt 6 und den Phasen-Checklisten geschnitten werden.*
