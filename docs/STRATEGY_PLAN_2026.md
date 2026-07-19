# Gnom-Hub — Strategieplan 2026

**Stand:** 2026-07-19 (aktualisiert: **kein Docker, keine Sandbox** als Ziel)  
**Zielbild:** Schlank · Stabil · local-first · ohne Extra-Infrastruktur  
**Bezug:** [TECHNICAL_STATUS_REPORT_2026-07.md](./TECHNICAL_STATUS_REPORT_2026-07.md)

**Randbedingungen (verbindlich):**

- **Kein Docker** (kein Compose, kein Container-Stack, kein „one more service“)  
- **Keine Sandbox** (kein bubblewrap, Firecracker, OS-Isolation als Roadmap-Ziel)  
- Security bleibt **Path-Validator + Grants** im bestehenden Code  
- Alles läuft **nativ** (Python-Hub + Agent-Prozesse auf dem Host)

---

## 1. Leitprinzipien

1. **Control Plane ≠ Data Plane**  
   Der Hub orchestriert; er speichert nicht jede Agent-Nebenwirkung im gleichen Write-Pfad wie die User-Chat-Latenz.

2. **Exactly-once wo es zählt, at-least-once wo es erlaubt ist**  
   Jobs dürfen nicht „done“ werden, wenn das LLM leer war. User-Chat muss **immer** schnell speichern.

3. **Ein Launch-Modell, ein Queue-Pfad, ein Observability-Pfad**  
   Keine dualen Chat-Stacks, keine dualen Agent-Startstile, keine stillen Fallbacks.

4. **Local-first, zero extra daemons**  
   Kein zwingender Zweitprozess (Message-Broker, Container, VM). Verbesserungen im bestehenden Python-/SQLite-Stack.

5. **Delete ruthlessly**  
   Features ohne Owner und unverdrahtete Module raus.

6. **Nur was der User will**  
   Keine Provider-Defaults, keine Infra-Stack-Empfehlungen ohne expliziten Auftrag.

---

## 2. Zielarchitektur (local-first)

### 2.1 Logische Schichten

```
┌─────────────────────────────────────────────────────────────┐
│  Web UI (bestehend → später optional typed)                   │
│  - Chat (SSE)  - Showbox  - Ops (Queue/Health)              │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP localhost
┌───────────────────────────▼─────────────────────────────────┐
│  Hub (FastAPI, nativ)                                       │
│  - Chat, Registry, Queue-Ops, LLM-Routing                   │
└───────┬─────────────────────┬───────────────────────────────┘
        │                     │
   ┌────▼────┐          ┌─────▼─────┐
   │ SQLite  │          │ Workspace │
   │ (WAL)   │          │ FS lokal  │
   └────┬────┘          └───────────┘
        │ agent_messages (gehärtet)
   ┌────▼────────────────────────────┐
   │  8 Agent-Prozesse (run_agent)   │
   │  Path-Validator + Grants        │
   └─────────────────────────────────┘
```

### 2.2 Technologie-Empfehlungen (ohne Docker/Sandbox)

| Bereich | Empfehlung | Warum |
|---------|------------|--------|
| **API** | FastAPI, Pydantic v2, OpenAPI | bereits im Stack |
| **Persistenz** | **SQLite WAL** weiter; Writes serialisieren / Limits | kein neuer DB-Server |
| **Job Queue** | **`agent_messages` in SQLite**, gehärtet (Limits, NACK, DLQ, optional Hub-Claim-API) | bleibt ein Prozess-Modell, kein Broker |
| **Realtime** | SSE (bereits) | weniger Polling |
| **Agent Runtime** | Ein Startstil `run_agent`; Watchdog nur wenn nötig | kein Doppel-Spawn |
| **Security** | Path-Validator + `security_permissions` + Injection-Checks | **kein** Sandbox-Ziel |
| **LLM** | Was in `routing.txt` / UI steht — **kein Force-Provider** | User entscheidet |
| **Observability** | strukturierte Logs + Health + Queue-Stats in der UI | ohne Prometheus-Pflicht |
| **Frontend** | bestehendes JS zuerst stabil; optional später TypeScript | kein Big-Bang |
| **Memory/TKG** | optional, nicht Boot-Pflicht | Kern schlanker |

### 2.3 Was explizit *nicht* Ziel ist

- Docker / Compose / Container-Runtime  
- Sandbox / microVM / bubblewrap als Roadmap  
- Externe Message-Broker (NATS, Redis, …) als Pflicht  
- SQLite als unkontrollierter Message-Bus ohne Limits (schon angegangen)  
- Zwei Agent-Startstile  
- Sync-HTTP Self-Calls Hub→Hub  
- Monolith-JS ohne Not umschreiben  

---

## 3. Schlanker machen: Cut-Liste

| Item | Aktion |
|------|--------|
| Unverdrahtetes `chat.py` (Orchestrator) | mergen oder löschen |
| Legacy `agents.*AG` Startpfad | nur `run_agent` |
| Doku-Drift | ARCHITECTURE.md am Code halten |
| Doppelte Provider-Pfade | ein `ask_router`-Pfad |
| Dead Tests in ignore | reparieren oder entfernen |

### Produkt-Fokus

1. War-Room Chat  
2. Showbox  
3. Job Queue (sichtbar, begrenzt)  
4. Security Grants  
5. LLM Routing (konfigurierbar)  
6. Ops Health  

---

## 4. Stabiler machen

### 4.1 Zuverlässigkeit

| Regel | Umsetzung |
|-------|-----------|
| User-Chat schnell | kurze Transaktionen, Write-Serialisierung im Hub |
| Empty / Router-Fehler | **NACK**, nicht ACK |
| Poison | DLQ + Limits |
| Backpressure | max pending / concurrent pro Agent |
| Storm | Auto-DLQ stale pending; `@@queue clear` |

### 4.2 Prozessmodell

```
hub (API, nativ)
 └─ start_background_agents → run_agent × 8
      (ein Startstil, sauberes Kill/Reap)
```

Kein Container, kein Supervisor-Cluster.

### 4.3 Observability (leicht)

- Queue depth / leases / last error in der Sidebar  
- Health: process + heartbeat + queue  
- Logs unter `logs/`  

---

## 5. Phasen-Roadmap

### Phase 0 — Freeze & Truth ✅ weitgehend erledigt

Doppel-Spawn, busy_timeout, Soft-Register, NACK, Recovery-Fix, SSE, Ops-Panel, Queue-Hygiene (Welle A).

### Phase 1 — Reliability auf SQLite (aktueller Fokus)

1. Hub Write-Serialisierung weiter ziehen (wo noch nötig)  
2. Optional: **Hub-Claim-API** (Claim nur im Hub-Prozess — **ohne** Broker/Docker)  
3. Chat SSE nutzen / Polls drosseln  
4. Job-State klar: pending → processing → done|dead_letter  
5. Frontend-Hotfixes (API-Prefix etc.)  

**Exit:** Dauerbetrieb ohne „Hub unreachable“, Queue nicht permanent > Limits.

### Phase 2 — SQLite sauber halten (kein neuer Server)

- Schema/Migrationen aufräumen  
- weniger Connection-Leaks  
- Queue-Tabellen/Indizes optimieren  
- **Nicht:** Postgres/NATS/Redis/Docker  

### Phase 3 — Runtime & Security (ohne Sandbox)

1. Ein Launch-Modell festzurren  
2. Path-Validator + Grants schärfen (bestehend)  
3. Gatekeeper nur wenn gewollt, policy im Code  
4. Kein OS-Sandbox-Projekt  

### Phase 4 — UI (optional, später)

Strangler nur wenn stabil; kein Docker-Dev-Stack.

### Phase 5 — Intelligence (optional)

TKG/Memory erst nach Stabilität.

---

## 6. Konkrete nächste Schritte

| # | Schritt | Done when |
|---|---------|-----------|
| 1 | Nur User-gewollte Routing-Änderungen | kein Force-MiniMax etc. |
| 2 | Queue-Limits + `@@queue` im Alltag nutzen | Storm bleibt aus |
| 3 | Weitere Lock-Quellen im Hub (ohne neue Infra) | Chat p99 niedrig |
| 4 | Optional Hub-Claim (HTTP), Agents ohne `BEGIN IMMEDIATE` | weniger Multi-Writer |
| 5 | CI-Ignore-Liste schrumpfen | weniger blinde Flecken |

---

## 7. Zielmetriken

| Metrik | Ziel |
|--------|------|
| Chat POST p99 | < 200 ms lokal |
| Job-Verlust bei LLM-Fehler | 0 (NACK/DLQ) |
| Agenten | 8, ein Startstil, 0 Zombies |
| `database is locked` im Chat-Pfad | ≈ 0 |
| Extra-Dienste | **0** (kein Docker, kein Broker) |

---

## 8. ADRs

Empfohlen nur wenn wirklich nötig:

1. Queue bleibt SQLite (+ optional Hub-Claim) — **kein** Broker  
2. OLTP bleibt SQLite — **kein** Postgres-Server  
3. Agent Runtime: multi-process `run_agent`  
4. Frontend: später optional typed  

**Nicht vorgesehen:** Sandbox-ADR, Docker-ADR.

Bestehende ADR-001 (NATS) gilt als **verworfen / obsolet** zugunsten local-only.

---

## 9. Risiken

| Risiko | Gegenmaßnahme |
|--------|----------------|
| SQLite bleibt Multi-Writer | Limits, Serialisierung, optional Hub-Claim |
| Feature-Creep | Cut-Liste + User-OK |
| Doku drängt Infra | dieser Plan: Docker/Sandbox explizit raus |

---

## 10. Nordstern

> **Gnom-Hub** bleibt ein **lokaler** Multi-Agent-Hub: ein Python-Prozess (Hub), Agenten als normale Prozesse, eine SQLite-DB, Workspace auf der Platte — ohne Docker und ohne Sandbox-Roadmap.

---

## 11. Mapping Status → Strategie

| Status-Problem | Strategie |
|----------------|-----------|
| P0.1 SQLite Multi-Writer | Limits + Write-Serial + optional Hub-Claim |
| P0.2 Connection Leaks | `get_db_conn` |
| P0.3 ACK on LLM fail | NACK |
| P1.1 Fake notify | kürzere Polls / später Hub-Claim-Wake |
| P1.3 Process races | ein Startstil, Reap |
| P2 Frontend | nur Hotfixes bis stabil |

---

*Operative Arbeit: nur Punkte aus Abschnitt 6 und Phase 1 — ohne neue Infrastruktur.*
