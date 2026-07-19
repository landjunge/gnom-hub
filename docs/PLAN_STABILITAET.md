# Gnom-Hub — Plan: Stabilität & Geschwindigkeit

**Stand:** 2026-07-19  
**Status:** verbindlicher Arbeitsplan (ersetzt Priorität der alten „Modernisierungs“-Roadmap)  
**Quellen:** User-Wille (Session), Code-Ist, README-Abgleich, erledigte Fixes (Welle A / Phase 0)

---

## 0. Auftrag in einem Satz

> **Vorhandenes System so reparieren und halten, dass Chat und Agenten lokal schnell und fehlerfrei laufen — ohne neue Infrastruktur und ohne ungebetene Defaults.**

---

## 1. Was der User will (verbindlich)

| Will | Nicht will |
|------|------------|
| Schnell | Docker / Compose / Container |
| Fehlerfrei | Sandbox / microVM / bubblewrap |
| Erst fixen was da ist | NATS/Redis/Postgres als Pflicht |
| Local-first (nativ) | MiniMax oder andere Provider **erzwingen** |
| Funktionen behalten | Feature-Neubau vor Stabilität |
| Doku dem Code anpassen | Marketing-README als Spec (`main`-Branch-Story) |
| Klare Arbeit ohne Stack-Aufzwingen | „2026 State of the Art“-Umbau ohne Auftrag |

**Erfolgsmaßstab:** Chat kommt durch; Agenten arbeiten; Queue explodiert nicht; kein „Hub unreachable“; alles nativ auf dem Host.

---

## 2. Ist-Zustand (kurz)

### Vorhanden (nicht neu bauen)
- 8 Agenten, FastAPI-Hub, Chat, Queue (`agent_messages`), Showbox  
- Security (Path + Grants), LLM-Routing, Health/Ops  
- Memory/TKG/Offload als Module (teilweise optional / nicht im Kern-Loop)  
- Start/Stop-Scripts, Tests (CI ~537 grün mit Ignore-Liste)

### Bereits verbessert (behalten)
- Doppel-Agent-Spawn weitgehend behoben  
- kurze DB-Timeouts, Soft-Register/Heartbeat  
- Empty/ROUTER-FEHLER → **NACK**  
- Queue-Limits, Auto-DLQ stale, `@@queue` / admin clear  
- Write-Serialisierung (Chat/Registry)  
- Ops: Queue/Leases in Sidebar, SSE-Chat  
- MiniMax-Force **rückgängig** (Routing = Config/UI)  
- Strategie: Docker/Sandbox raus  

### Offene Risiken (das ist der Plan-Inhalt)
1. SQLite Multi-Writer unter Last (Hub + 8 Agenten)  
2. Connection-Hygiene / verbleibende Lock-Hotspots  
3. Queue kann wieder volllaufen (Spam, Worker-Mentions)  
4. Free-LLM liefert oft Müll → NACK hilft, UX bleibt schwach  
5. Doku-Drift (Root-README, Branch `main` vs `master`)  
6. Halb tote Pfade / ignorierte Tests  
7. Optional: Agenten claimen noch direkt in SQLite (BEGIN IMMEDIATE)  

---

## 3. Architektur-Rahmen (nur Constraints, kein Umbau-Zwang)

```
Browser ──HTTP──► Hub (FastAPI, nativ, :3002)
                    │
                    ├── SQLite WAL (~/.gnom-hub/data/gnomhub.db + Neben-DBs)
                    │
                    └── 8× run_agent (Prozesse)
                         Path-Validator + Grants
                         LLM laut routing.txt / UI
```

- **Ein** Startstil: `agents.run_agent`  
- **Keine** Extra-Daemons  
- Security = bestehendes Grant/Path-Modell  
- Provider = nur was konfiguriert ist  

---

## 4. Phasen (logische Reihenfolge)

### Phase S0 — Wahrheit & Baseline ✅ weitgehend

- [x] User-Wille dokumentiert  
- [x] READMEs inventarisiert + Code-Abgleich  
- [x] Strategie ohne Docker/Sandbox  
- [x] MiniMax-Force entfernt  
- [x] Root-README + README.de an Code anpassen (GeneralAG-Default, Routing, Testzahlen)  
- [ ] Branch `main` vs `master` klären (main veraltet/marketing) — **offen, nur wenn User will**  

**Exit:** Keine Doku behauptet mehr Sandbox/Docker/SoulAG-Default als Wahrheit.

---

### Phase S1 — Chat & Hub immer erreichbar (P0)

**Ziel:** Chat POST p99 lokal &lt; ~300 ms; kein 15s-Timeout.

| # | Arbeit | Done when | Stand 2026-07-19 |
|---|--------|-----------|------------------|
| S1.1 | Lock-Hotspots messen (wann blockiert Chat?) | 1 Seite Log-Muster / Repro | ✅ Burst 10× POST: p50 **35 ms**, max **41 ms** (idle) |
| S1.2 | Verbleibende lange Writes aus Chat-Pfad halten | Chat bleibt &lt;300 ms unter Agent-Last | ✅ Concurrent Chat+HB: max **216 ms** Chat; nach Last **23 ms** |
| S1.3 | Heartbeat/Register/Audit nicht Chat blockieren | Register soft + kurz | ✅ HB parallel max ~135 ms; Chat bleibt dispatched |
| S1.4 | Nach Restart: Queue prüfen (`@@queue stats`) | pending nicht im Hunderter-Bereich | ✅ pending/processing sinken; DLQ-Altlast geleert |

**Messung (lokal :3002, hub-claim, openrouter/free):** Chat-POST bleibt unter 300 ms-Ziel. Queue-Backlog unter Free-LLM-Latenz normal (drain in ~1 min nach 15er Burst).

**Nicht in S1:** neuer Store, neuer Broker, Frontend-Rewrite.

---

### Phase S2 — Queue & Agenten zuverlässig (P0/P1)

**Ziel:** Jobs enden korrekt; kein Storm; kein stilles Verschwinden.

| # | Arbeit | Done when | Stand |
|---|--------|-----------|--------|
| S2.1 | Limits halten (pending/concurrent) — schon da, im Alltag prüfen | unter Last stabil | Limits im Code; Burst-Drain ok |
| S2.2 | NACK-Pfad beobachten (Free-LLM Spam) | keine Endlos-Retry-Stürme | NACK empty/ROUTER aktiv |
| S2.3 | Worker dürfen sich nicht gegenseitig volldispatchen | nur GeneralAG auto-@ (schon) | ✅ |
| S2.4 | Hub-Claim-API (Default `GNOM_QUEUE_MODE=hub`) | Claim/Ack/Nack nur im Hub | ✅ live + README/Ops |
| S2.5 | `@@queue clear` / admin clear als Ops-Routine | dokumentiert, 1 Befehl | ✅ README + Chat-Befehl |

**Exit:** 1 h Dauerbetrieb: Chat ok, Queue nicht permanent &gt; Limits, 8 Agenten nicht zombie.

---

### Phase S3 — Antworten brauchbar (Qualität ohne Provider-Zwang)

**Ziel:** Weniger Müll-Antworten, ohne MiniMax zu erzwingen.

| # | Arbeit | Done when |
|---|--------|-----------|
| S3.1 | Anti-Spam (Länge/Think-only) halten | Chat nicht mit 50k Tokens voll |
| S3.2 | User wählt Provider in UI/`routing.txt` | Defaults nur dorthin schreiben, wo User es will |
| S3.3 | System-Meldungen bei Fail klar | User weiß „nochmal senden / Key prüfen“ |

---

### Phase S4 — Code-Hygiene am bestehenden System

**Ziel:** Weniger Fallstricke, kein Feature-Zuwachs.

| # | Arbeit | Done when |
|---|--------|-----------|
| S4.1 | Tote Chat-Pfade mergen/löschen | ein Chat-Pfad |
| S4.2 | Ein Agent-Startstil überall | kein agents.*AG-Doppelstart |
| S4.3 | CI-Ignore-Liste schrumpfen (nur echte Live-Tests draußen) | weniger blinde Flecken |
| S4.4 | ARCHITECTURE.md = Default GeneralAG | Doku = Code |

---

### Phase S5 — Später / nur auf expliziten Wunsch

- Frontend TypeScript / Rewrite  
- TKG tiefer in den Agent-Loop  
- Externe Queue/DB  
- Sandbox, Docker, Broker  

**Default:** nicht anfangen.

---

## 5. Explizite Nicht-Ziele (Checkliste vor jeder Änderung)

Vor jedem PR/Commit fragen:

- [ ] Macht es Chat/Queue/Agenten **schneller oder zuverlässiger**?  
- [ ] Bleibt es **ohne** Docker/Sandbox/neuen Daemon?  
- [ ] Ändert es Provider-Defaults **ohne** User-OK? → dann **nicht**  
- [ ] Ist es ein neues Feature statt Fix? → nur mit User-OK  

---

## 6. Betriebs-Checkliste (täglich / nach Restart)

```bash
./scripts/start_gnom_hub.sh   # oder start_gnom_hub.sh im Root
curl -s http://127.0.0.1:3002/api/health
curl -s http://127.0.0.1:3002/api/stats   # queue pending/processing

# Im Chat:
@@queue stats
@@queue clear          # bei Storm
```

Erwartung: `healthy: 8`, `pending` klein, Chat-Send &lt; 1 s.

---

## 7. Nächste konkrete Schritte (Reihenfolge)

1. ~~**S0** README~~ ✅  
2. ~~**S1** Chat-Latenz unter Last~~ ✅ (siehe Tabelle; p95 ≪ 300 ms)  
3. ~~**S2.4/S2.5** hub-claim + @@queue~~ ✅  
4. **S2.1–S2.2** Queue-Limits + NACK unter Free-LLM weiter im Live-Betrieb absichern  
5. **S4** Tote Chat-Pfade / Startstil (Watchdog-Restart = `run_agent`) / ARCHITECTURE (GeneralAG schon)  
6. Quarantäne-Recovery ✅ (Commit `b810741`); Claim-HTTP-Timeout Agent ≥ Claim-Wartezeit

---

## 8. Beziehung zu älteren Docs

| Doc | Rolle jetzt |
|-----|-------------|
| `docs/PLAN_STABILITAET.md` (dieses) | **Arbeitsplan** |
| `docs/STRATEGY_PLAN_2026.md` | Randbedingungen (kein Docker/Sandbox); Details hier |
| `docs/TECHNICAL_STATUS_REPORT_2026-07.md` | Ist-Probleme / Kritikalität |
| `docs/README_CODE_ALIGNMENT_2026-07.md` | README vs Code |
| Root `README.md` / Branch `main` | Marketing/Memory — **nicht** Spec ohne Abgleich |

---

## 9. Für eine andere KI (Copy-Paste)

```
Gnom-Hub Arbeitsplan: docs/PLAN_STABILITAET.md
User-Priorität: schnell + fehlerfrei, nur Vorhandenes fixen.
Local-first nativ. KEIN Docker, KEINE Sandbox, KEIN erzwungener Provider.
Funktionen größtenteils schon im Code. Nächste Arbeit: S1 Chat/Locks, S2 Queue,
dann Doku-Drift README. Keine Wave-B-Broker/Migration ohne expliziten User-Auftrag.
```

---

*Ende Plan. Änderungen an diesem Plan nur mit User-OK bei Scope-Erweiterung.*
