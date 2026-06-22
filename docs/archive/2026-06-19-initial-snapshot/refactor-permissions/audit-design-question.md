# Design-Entscheidung: SecurityAG-Audit-Log (Schritt 4)

**Schritt 4 des Agent-Permission-Refactor.** Diese Datei enthält **keinen Code** — sie ist eine
Design-Frage an den User (Owner). Erst nach Deiner Entscheidung wird die Implementierung in Task
`security-audit` gestartet.

- **Working-Dir:** `/Users/landjunge/gnom-hub`
- **Datum:** 2026-06-21 03:11 (Europe/Berlin)
- **Methodik:** Statische Inspektion via `Read` + `grep` (Read-only, keine Code-Änderungen)
- **Input:** `docs/refactor-permissions/inventory.md` (Schritt 1, abgeschlossen 2026-06-21 03:08)
- **Bezug:** `plan_9c1d4ab1/design-decision` (diese Task), `plan_9c1d4ab1/security-audit` (Implementierung NACH Approval)

> **Wichtigste Erkenntnis vorab:** Der **bereits existierende** `audit_log`-Mechanismus (Tabelle +
> Helper `log_audit_event` + API + Cap) ist funktional, aber er **kennt keine SecurityAG-
> Spezifika** — SecurityAG-Aktionen werden wie die jedes anderen Agents protokolliert. Schritt 4
> verlangt jetzt eine **dedizierte** Auditierung von SecurityAG-Aktionen mit `godmode`/`run`/`write`.
> Die Frage ist: **wie dediziert?**

---

## Section 1 — Ist-Zustand (was heute schon da ist)

### 1.1 `audit_log`-Tabelle

```sql
51: CREATE TABLE IF NOT EXISTS audit_log (
52:     id INTEGER PRIMARY KEY AUTOINCREMENT,
53:     timestamp TEXT NOT NULL,
54:     agent TEXT NOT NULL,
55:     event_type TEXT NOT NULL,
56:     details TEXT NOT NULL,         -- JSON-String
57:     trace_id TEXT,
58:     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
59: );
```
(Quelle: `src/gnom_hub/db/schema.py:51-59`)

**Indizes:** `idx_agent_event` (agent, event_type) + `idx_timestamp` (timestamp DESC) — `db/schema.py:139-140`.
**Cap-Mechanismus:** `AUDIT_LOG_MAX_ROWS = 1000`, `AUDIT_LOG_KEEP_ROWS = 800` — `db/system_repo.py:100-101`.
**Cleanup:** In `admin_tools.py:156` (DB-Reset) und `compiler.py:202` (State-Reset).

### 1.2 Schreib-Helper

```python
86: def log_audit_event(agent: str, event_type: str, details: dict, trace_id: str = None):
87:     try:
88:         with get_db_conn() as conn:
89:             with conn:
90:                 conn.execute("""
91:                     INSERT INTO audit_log (timestamp, agent, event_type, details, trace_id)
92:                     VALUES (?, ?, ?, ?, ?)
93:                 """, (datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
94:                        agent, event_type, json.dumps(details), trace_id))
95:                 _enforce_audit_cap(conn)
96:     except sqlite3.Error as e:
97:         logger.error(f"[DB] Failed to save audit log: {e}")
```
(Quelle: `src/gnom_hub/db/system_repo.py:86-97`)

**Wrapper-Klasse** (optional, mit trace_id-Tracking): `AgentLogger` in
`src/gnom_hub/core/structured_log.py:19-25`. Setzt eine `contextvars.ContextVar` für trace_id.

### 1.3 Wer ruft `log_audit_event` heute auf?

Belegt durch `grep -rn "log_audit_event" src/gnom_hub/` (6 produktive Aufrufer, exklusive Re-Exports):

| Datei:Zeile | Event-Type | Wann? |
|---|---|---|
| `core/utils/pvm_activate.py:12` | `"prompt_activated"` | Prompt-Version aktiviert |
| `core/utils/pvm_rollback.py:12` | `"prompt_auto_rollback"` | Prompt-Rollback |
| `core/utils/gd_fallback.py:33` | `"degradation_fallback"` | Graceful-Degradation |
| `core/utils/evolution_v2.py:156,182` | (Evolution-Events) | Agent-Evolution |
| `agents/specialization_monitor.py:36` | (via `log_audit_event(...)`) | Specialization-Tracking |
| `core/structured_log.py:24` | (allgemein via `AgentLogger`) | Strukturierte Logs |

**Befund:** Es gibt **keinen** dedizierten SecurityAG-Audit-Aufrufer. SecurityAG-Aktionen
landen heute nur dann in `audit_log`, wenn ein Evolution-Event oder ein Graceful-Degradation-
Event ihn tangential betrifft — **nicht** für jeden godmode-/run-/write-Vorgang.

### 1.4 Lesepfad / API

```python
22: @router.get("/api/audit-log")
23: def get_audit_log(agent: str = None, event: str = None, limit: int = 50):
24:     try:
25:         with get_db_conn() as conn:
26:             q = "SELECT * FROM audit_log"
27:             conds, args = [], []
28:             if agent: conds.append("agent = ?"); args.append(agent)
29:             if event: conds.append("event_type = ?"); args.append(event_type)
30:             if conds: q += " WHERE " + " AND ".join(conds)
31:             q += " ORDER BY timestamp DESC LIMIT ?"
32:             args.append(limit)
33:             return [dict(r) for r in conn.execute(q, args).fetchall()]
34:     except sqlite3.Error: return []
```
(Quelle: `src/gnom_hub/api/endpoints/metrics.py:22-34`)

**Filter vorhanden** (agent + event_type + limit). Eine `WHERE agent = "SecurityAG"`-Query
funktioniert heute schon — aber das **Ergebnis ist leer**, weil kein SecurityAG-spezifischer
Event-Type geschrieben wird.

### 1.5 `blockade_log` (verwandt, aber nicht ausreichend)

```sql
61: CREATE TABLE IF NOT EXISTS blockade_log (
62:     id INTEGER PRIMARY KEY AUTOINCREMENT,
63:     timestamp TEXT NOT NULL,
64:     agent_name TEXT NOT NULL,
65:     blocked_by TEXT DEFAULT 'Gatekeeper',
66:     action_type TEXT NOT NULL,
67:     detail TEXT NOT NULL,
68:     reason TEXT NOT NULL,
69:     content_snippet TEXT DEFAULT '',
70:     status TEXT DEFAULT 'blocked'
71: );
```
(Quelle: `src/gnom_hub/db/schema.py:61-71`)

**Wird in `gatekeeper.py:316, 321, 324, 458, 491, 497, 500` befüllt** — aber **nur für
verhinderte** Aktionen (Status `blocked` oder `warning`). Erfolgreiche SecurityAG-Aktionen
landen **hier nicht**. Selbst wenn wir die `blocked_by="SecurityAG"`-Spalte als Indiz nutzen
würden (Zeile 321, 324 sind Beispiele), erfassen wir nur `is_security_block(sev=high|medium)`-
Treffer — nicht alle godmode-Aktionen.

### 1.6 Hook-Punkt: `action_handlers.py`

`process_actions(ans, agent, perms, bs_mode, wd)` ist der zentrale Dispatcher. Er sieht:

- Zeile 10: `perms = list(perms)` — die komplette Permissions-Liste des Agents
- Zeile 11: `if "godmode" in perms and "run" not in perms: perms.append("run")` — die godmode-Auto-Inferenz
- Zeile 13-30: `[WRITE:...]...[/WRITE]`-Matcher (zwei Varianten) + `verify_write()`-Aufruf
- Zeile 33-40: `[SHELL:...]`-Matcher + `verify_cmd()`-Aufruf
- Zeile 41-42: `[DESKTOP:...]`-Matcher
- Zeile 46: `[CRAWL:...]`-Matcher
- Zeile 50-56: Video-Tool-Matcher
- Zeile 57: `[BROWSER:...]...[/BROWSER]`-Matcher

**Alle Action-Typen** laufen hier durch — das ist der **natürliche Hook-Punkt** für
SecurityAG-Audit. Der Agent-Name ist via `agent.get("name", "")` verfügbar
(Zeile 16, 26, 36 sehen das schon).

### 1.7 SecurityAG-Permissions heute

Aus `agent_definitions.py:110,115` (DE/EN-Block):

```python
"permissions": ["read", "write", "run", "godmode", "desktop", "crawl", "evolve"]
```

Schritt 2 des Refactors (Task `change-definitions`) wird das auf
`["read", "write", "run", "godmode"]` reduzieren (desktop/evolve/crawl RAUS). Das ist
**nicht Teil dieser Design-Frage** — aber die Audit-Logik muss für die Permissions
**nach Schritt 2** korrekt funktionieren.

Die zu überwachenden **Aktionen** (gemäß Schritt 4-Spec) sind:
- Alle `[WRITE:...]`-Aktionen (gated by `write`-Permission in `action_handlers.py:15, 25`)
- Alle `[SHELL:...]`-Aktionen (gated by `run`-Permission in `action_handlers.py:35`)
- Alle Aktionen mit `godmode` im Permission-Set (impliziert run via Zeile 11, schaltet
  `browser` frei via `tool_registry.py:29`)

**Trigger-Bedingung (Vorschlag — unabhängig von A/B/C):**
```python
if (agent.get("name", "").lower() == "securityag"
    and ("godmode" in perms or "run" in perms or "write" in perms)):
    # ... audit log
```

---

## Section 2 — Die 3 Design-Vorschläge

### Option A — Minimal: Bestehende `audit_log`-Tabelle wiederverwenden

**Kernidee:** Eine einzige Code-Stelle in `action_handlers.py` ruft `log_audit_event()` mit
einem **neuen Event-Type** `"security_action"` (oder spezifischer `"security_godmode"`,
`"security_run"`, `"security_write"`) und allen relevanten Details auf. **Kein Schema-
Change**, **kein neuer Helper**, **keine Migration**.

#### A.1 Hook-Position

In `src/gnom_hub/agents/actions/action_handlers.py:9-30` (WRITE-Block) und
Zeile 33-40 (SHELL-Block). Beispiel-Snippet (illustrativ, **nicht** zur sofortigen
Implementierung):

```python
# Pseudo-Hook (Zeile 16 nach 'else if verify_write')
if (agent.get("name", "").lower() == "securityag"
    and "write" in perms and "godmode" in perms):
    log_audit_event(
        agent=agent["name"],
        event_type="security_write",
        details={"file": fn, "verdict": "allowed",
                 "content_len": len(content), "bs_mode": bs_mode},
        trace_id=get_trace_id(),
    )
```

Analog für SHELL (Zeile 38) und ggf. CRAWL/BROWSER (Zeile 46/57).

#### A.2 SQL-Schema-Skizze

**Kein Schema-Change.** Bestehende Tabelle wird genutzt. Neue Event-Types:

| `event_type` | Wann? | `details`-Felder |
|---|---|---|
| `"security_write"` | SecurityAG mit `write`+`godmode` und `[WRITE:...]` | `file`, `verdict`, `content_len`, `bs_mode` |
| `"security_run"` | SecurityAG mit `run`+`godmode` und `[SHELL:...]` | `cmd`, `verdict`, `whitelisted` |
| `"security_browser"` | SecurityAG mit `godmode` und `[BROWSER:...]` | `url_count`, `verdict` |
| `"security_desktop"` | SecurityAG mit `desktop` und `[DESKTOP:...]` | `action`, `verdict` |

(Schemata post-Schritt-2: `desktop` fällt weg — dann gibt es nur `security_write`,
`security_run`, `security_browser`.)

#### A.3 Aufwand (Std)

- **Implementierung:** 0.5–1.5 Std
  - 2 kleine Edit-Stellen in `action_handlers.py` (WRITE-Block + SHELL-Block)
  - 1–2 optionale Stellen für BROWSER/CRAWL/DESKTOP (je 5 Min)
- **Tests:** 1 Std
  - Neuer Test `test_security_audit_log.py`: triggert eine `process_actions`-Aufruf mit
    `agent={"name": "SecurityAG", "role": "security"}`, `perms=["read","write","run","godmode"]`,
    prüft dass `audit_log` einen Eintrag mit `event_type="security_write"` enthält.
- **Docs:** 0.5 Std
- **Total:** **2–3 Std**

#### A.4 Trade-offs

| Pro | Contra |
|---|---|
| **Null Schema-Migration** — sofort umsetzbar | SecurityAG-Events **vermischen** sich mit Prompt-Versionen, Degradation, Evolution in derselben Tabelle |
| **Bestehender Helper** (`log_audit_event`) — kein neuer Code-Pfad | Cap-Mechanismus (1000/800) teilt sich SecurityAG mit allen anderen Events — bei viel SecurityAG-Aktivität droht Verlust älterer Sicherheits-Events |
| **Bestehende API** (`/api/audit-log?agent=SecurityAG`) funktioniert sofort | Kein dedizierter Event-Type-Filter in API; muss man Client-seitig nach `event_type` filtern |
| **Bestehende Indizes** (`idx_agent_event`, `idx_timestamp`) sind passend | Kein Hash für Tamper-Evidence (nur Plain-JSON in `details`) |
| **Bestehende Tests** (`test_audit_log_cap.py`) bleiben grün | SecurityAG-Audit ist **nicht** optisch von anderen Events trennbar im Frontend |
| **Kleinste Diff-Fläche** (eine Datei) | Bei späterem Bedarf (z.B. SIEM-Export) muss die Tabelle partitioniert werden |

#### A.5 Test-Implikationen

- **Bestehende Tests:** Null Reibung. `test_audit_log_cap.py` testet Cap-Mechanismus
  unabhängig vom Event-Inhalt.
- **Neue Tests:**
  1. `test_security_write_creates_audit_entry` — SecurityAG + `[WRITE:...]` →
     `audit_log` enthält Zeile mit `event_type="security_write"`.
  2. `test_security_shell_creates_audit_entry` — dito für `[SHELL:...]`.
  3. `test_non_security_agent_no_audit_entry` — CoderAG mit `godmode` schreibt
     **keinen** `security_*`-Event (Negativ-Test, schützt vor Versehentlich-Alles-Loggen).
  4. `test_audit_log_contains_security_audit_filterable` — Filter
     `event_type LIKE 'security_%'` liefert SecurityAG-Events.

---

### Option B — Strukturiert: Dedizierte `security_audit_log`-Tabelle

**Kernidee:** Eine **neue** Tabelle `security_audit_log` mit **strukturierten Spalten** (statt
JSON-Blob) + **Hash-Spalte** für Tamper-Evidence. Eigener Schreib-Helper
`log_security_audit()`, eigene Lesepfad-API `/api/security-audit-log`. **Migration nötig**
(aber idempotent via `CREATE TABLE IF NOT EXISTS`).

#### B.1 Hook-Position

In `src/gnom_hub/agents/actions/action_handlers.py:9-40` — **gleiche Stelle wie Option A**,
aber Aufruf geht an den neuen Helper:

```python
# Pseudo-Hook (illustrativ)
if (agent.get("name", "").lower() == "securityag"
    and ("godmode" in perms or "write" in perms or "run" in perms)):
    from gnom_hub.db import log_security_audit
    log_security_audit(
        agent=agent["name"],
        action_type="write" if "[WRITE:" in m.group(0) else "shell",
        target=fn if "[WRITE:" in m.group(0) else cmd[:200],
        result="allowed" if verdict else "denied",
        content_hash=sha256(content or cmd).hexdigest()[:16],
        perms_snapshot=list(perms),
    )
```

#### B.2 SQL-Schema-Skizze

**Neue Tabelle** in `db/schema.py` (idempotent):

```sql
CREATE TABLE IF NOT EXISTS security_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,                    -- "SecurityAG"
    action_type TEXT NOT NULL,              -- "write" | "run" | "crawl" | "browser" | "desktop"
    target TEXT NOT NULL,                   -- filename / cmd / url
    result TEXT NOT NULL,                   -- "allowed" | "denied" | "error"
    severity TEXT,                          -- "low" | "medium" | "high" | NULL
    perms_snapshot TEXT NOT NULL,           -- JSON-Array der Permissions zum Zeitpunkt
    content_hash TEXT,                      -- sha256[:16] für Tamper-Evidence
    trace_id TEXT,                          -- Korrelation mit normalem audit_log
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sec_audit_agent_ts
    ON security_audit_log(agent, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sec_audit_result
    ON security_audit_log(result, timestamp DESC);
```

**Neuer Helper** in `db/system_repo.py`:

```python
SECURITY_AUDIT_MAX_ROWS = 5000
SECURITY_AUDIT_KEEP_ROWS = 4500

def log_security_audit(agent, action_type, target, result,
                       severity=None, perms_snapshot=None,
                       content_hash=None, trace_id=None):
    """Schreibt in security_audit_log. Eigener Cap (5000/4500)."""
    # ... analog zu log_audit_event
```

**Neue API** in `api/endpoints/metrics.py` (oder neue Datei
`api/endpoints/security_audit.py`):

```python
@router.get("/api/security-audit-log")
def get_security_audit_log(agent: str = None, result: str = None, limit: int = 50):
    # ... analog zu get_audit_log
```

#### B.3 Aufwand (Std)

- **Implementierung:** 2.5–3.5 Std
  - 1. Schema-Migration in `db/schema.py` (~30 Zeilen: CREATE TABLE + 2 Indizes)
  - 2. `log_security_audit()`-Helper in `db/system_repo.py` (~40 Zeilen inkl. Cap)
  - 3. Hook in `action_handlers.py` (~15 Zeilen für WRITE + SHELL + BROWSER)
  - 4. API-Endpoint `/api/security-audit-log` (~25 Zeilen)
  - 5. Export in `db/__init__.py` und ggf. `db/legacy_db.py` (~5 Zeilen)
- **Tests:** 1.5 Std
  - Schema-Migration-Test (idempotent, existierende DBs überleben)
  - Cap-Mechanismus-Test
  - Hook-Tests (analog zu A.5, aber auf neue Tabelle)
  - API-Filter-Test
- **Docs:** 0.5 Std
- **Total:** **4.5–5.5 Std**

#### B.4 Trade-offs

| Pro | Contra |
|---|---|
| **Saubere Trennung** — SecurityAG-Audit ist visuell & query-mäßig isoliert | **Schema-Migration** nötig (wenn auch idempotent) |
| **Strukturierte Spalten** — `result`, `severity`, `action_type` als ENUM-ähnliche Felder, querybar ohne JSON-Parsing | **Zwei Audit-Tabellen** zu pflegen (Cap, Cleanup, Admin-Reset) |
| **Tamper-Evidence** via `content_hash` (sha256) | Hash deckt nur den **einzelnen** Eintrag ab — keine Hash-Chain (Option C ist stärker) |
| **Eigener Cap** (5000/4500) — SecurityAG-Events gehen nicht im Prompt-Event-Rauschen unter | Mehr Code-Fläche → mehr Test-Aufwand |
| **Eigene API** — Frontend kann dediziertes Dashboard bauen | Frontend muss ggf. angepasst werden (wenn `/api/audit-log` reicht, ist B oversized) |
| **Saubere Indexierung** auf `(agent, result)` für schnelle "alle verhinderten SecurityAG-Aktionen" | Hash-Spalte bringt nur etwas, wenn man Audit-Trail-Echtheit **separat verifiziert** (z.B. Export + Verify-Script) |
| **Saubere perms_snapshot** — bei Post-Mortem klar, welche Permissions zum Zeitpunkt der Aktion galten | |

#### B.5 Test-Implikationen

- **Bestehende Tests:** Null Reibung. `audit_log`-Tabelle bleibt unangetastet.
- **Neue Tests:**
  1. `test_security_audit_table_migration_idempotent` — `init_database()` läuft 2x ohne
     Fehler, Tabelle ist nach Run 2 immer noch da mit korrektem Schema.
  2. `test_security_audit_cap` — analog zu `test_audit_log_cap.py:1-97`, aber auf
     `security_audit_log` mit 5000/4500.
  3. `test_security_write_creates_structured_entry` — SecurityAG + `[WRITE:...]` →
     Zeile in `security_audit_log` mit `action_type="write"`, `target=fn`,
     `result="allowed"`, `content_hash` 16 Hex-Chars.
  4. `test_security_audit_content_hash_stable` — gleicher Input → gleicher Hash;
     anderer Content → anderer Hash.
  5. `test_non_security_agent_no_security_audit_entry` — CoderAG mit `godmode`
     schreibt **nichts** in `security_audit_log` (Negativ-Test).
  6. `test_security_audit_api_filter_by_result` — `GET /api/security-audit-log?result=denied`
     liefert nur denied-Einträge.
  7. `test_admin_reset_clears_security_audit` — `admin_tools.py:156` muss um
     `security_audit_log` erweitert werden — neuer Regressions-Test.

#### B.6 Migrationsbedarf

**Idempotent via `CREATE TABLE IF NOT EXISTS`.** Bestehende `init_database()`-Funktion
(aufgerufen in `system_repo.py:13-17` und in `db/schema.py`) ergänzt die neue Tabelle
+ Indizes. **Kein Datenverlust** in der bestehenden `audit_log`-Tabelle. Bei der
`admin_tools.py:156`-Cleanup-Liste muss `security_audit_log` ergänzt werden (sonst
überlebt die Tabelle einen DB-Reset).

---

### Option C — Outbox-Pattern: Asynchrone Audit-Persistierung

**Kernidee:** SecurityAG-Aktionen werden **zuerst** in eine `security_audit_outbox`-Tabelle
geschrieben (im selben Transaktions-Kontext wie die eigentliche Aktion). Ein
**Watcher-Thread** leert die Outbox **asynchron** in `security_audit_log` (oder direkt in
ein append-only Log-File). **Erhöhte Komplexität**, dafür **audit-fest**: wenn die
audit-Insert fehlschlägt, **schlägt auch die Aktion fehl** (synchroner Outbox-Write als
Commit-Gate).

#### C.1 Hook-Position

In `src/gnom_hub/agents/actions/action_handlers.py` (gleiche Stelle wie A/B), aber der
Write geht in die Outbox-Tabelle — **nicht** direkt in den finalen Audit-Log:

```python
# Pseudo-Hook (illustrativ)
if (agent.get("name", "").lower() == "securityag"
    and ("godmode" in perms or "write" in perms or "run" in perms)):
    from gnom_hub.db import enqueue_security_audit
    enqueue_security_audit(
        agent=agent["name"],
        action_type=...,
        target=...,
        result=...,
        outbox_status="pending",  # wird vom Watcher auf "committed" gesetzt
    )
```

**Watcher** (neuer Thread in `gnom_hub/infrastructure/security_audit_watcher.py`):

```python
# Pseudo-Watcher (illustrativ)
def security_audit_watcher_loop():
    while not stop_event.is_set():
        rows = conn.execute(
            "SELECT * FROM security_audit_outbox WHERE status='pending' LIMIT 50"
        ).fetchall()
        for row in rows:
            try:
                # Schreibe in security_audit_log (oder append-only File)
                log_security_audit(...)
                conn.execute("UPDATE outbox SET status='committed', committed_at=?", ...)
            except Exception:
                conn.execute("UPDATE outbox SET status='failed', error=?", ...)
        time.sleep(1.0)
```

#### C.2 SQL-Schema-Skizze

**Zwei neue Tabellen** in `db/schema.py`:

```sql
-- Outbox: wird synchron im selben Transaktions-Kontext wie die Aktion geschrieben
CREATE TABLE IF NOT EXISTS security_audit_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target TEXT NOT NULL,
    result TEXT NOT NULL,
    perms_snapshot TEXT NOT NULL,
    content_hash TEXT,
    trace_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | committed | failed
    attempts INTEGER DEFAULT 0,
    last_error TEXT,
    committed_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_outbox_status_ts
    ON security_audit_outbox(status, timestamp);

-- Finaler Audit-Log (append-only)
CREATE TABLE IF NOT EXISTS security_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outbox_id INTEGER NOT NULL,              -- referenziert outbox.id
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target TEXT NOT NULL,
    result TEXT NOT NULL,
    content_hash TEXT,
    trace_id TEXT,
    FOREIGN KEY (outbox_id) REFERENCES security_audit_outbox(id)
);
CREATE INDEX IF NOT EXISTS idx_sec_audit_agent_ts
    ON security_audit_log(agent, timestamp DESC);
```

**Optional — Hash-Chain** für stärkere Tamper-Evidence: jede Zeile enthält
`prev_hash = sha256(vorgaenger.content_hash)`. Damit ist Manipulation an einer Zeile
detektierbar (sie würde die gesamte nachfolgende Chain brechen). **Aufpreis:** ~2 Std
zusätzlich.

#### C.3 Aufwand (Std)

- **Implementierung:** 5–7 Std
  - 1. Schema: Outbox + Log-Tabelle + Indizes (~50 Zeilen)
  - 2. `enqueue_security_audit()`-Helper (~30 Zeilen, **synchroner** Write in Outbox)
  - 3. `security_audit_watcher.py` — Thread-Loop mit graceful shutdown (~80 Zeilen)
  - 4. Watcher-Lifecycle: Start in `app.py` lifespan, Stop in shutdown (~30 Zeilen)
  - 5. Hook in `action_handlers.py` (~15 Zeilen)
  - 6. Optional: Hash-Chain + Verify-Script (~2 Std)
  - 7. Reconciler / Health-Check (Outbox-pending-Counter) (~30 Zeilen)
  - 8. API `/api/security-audit-log` + Outbox-Status-Endpoint (~40 Zeilen)
- **Tests:** 2–3 Std
  - Watcher-Start/Stop-Test (kein Thread-Leak)
  - Outbox-zu-Log-Promotion-Test (synchroner Test mit `wait_for_outbox_drain()`-Helper)
  - Failure-Recovery-Test (Audit-Insert fail → outbox.status="failed", retry)
  - Cap-Tests für Outbox + Log
  - Thread-Safety-Test (10 SecurityAG-Aktionen parallel → alle in Log, keine doppelt)
  - Schema-Migration-Test (idempotent)
- **Docs:** 1 Std
  - Watcher-Lifecycle-Doku
  - Failure-Mode-Doku (was passiert, wenn Watcher crasht? Outbox pendelt → Recovery beim Restart)
- **Total:** **8–11 Std** (mit Hash-Chain: 10–13 Std)

#### C.4 Trade-offs

| Pro | Contra |
|---|---|
| **Audit-Fest** — Outbox-Write ist synchron zur Aktion; wenn Audit fehlschlägt, schlägt Aktion fehl | **Watcher-Thread** ist eine neue langlaufende Komponente → Lifecycle, Monitoring, Restart-Szenarien |
| **Async-Persistierung** — SecurityAG-Aktionen werden nicht durch langsame DB-Writes ausgebremst | **Komplexität** — Outbox + Log + Watcher + Reconciler = 4 neue bewegliche Teile |
| **Append-Only mit Outbox-ID-FK** — `security_audit_log` ist echt immutable, `outbox` zeigt Verarbeitungs-Status | **Test-Komplexität** — Thread-Tests sind flaky; `wait_for_outbox_drain()` braucht Timeouts |
| **Hash-Chain möglich** (Aufpreis) — stärkste Tamper-Evidence | **Fehlerszenarien komplexer** — was, wenn Outbox voll? Was, wenn Watcher hängt? |
| **Failure-Recovery** — Restart des Watchers fährt Outbox-pending-Items fort | **Debug-Komplexität** — Outbox-Eintrag ≠ Log-Eintrag; bei "warum sehe ich das Event nicht" muss man beide Tabellen prüfen |
| **Reconciliation-fähig** — Outbox ist Self-Healing | **Overkill für die aktuelle Anforderung** — Schritt 4 verlangt nur "Eintrag erzeugen", nicht "garantiert persistiert" |

#### C.5 Test-Implikationen

- **Bestehende Tests:** Eventuell Concurrency-Tests in `test_concurrency.py:1` oder
  `test_queue_stability.py:1` müssen um "Watcher-Thread läuft" erweitert werden.
- **Neue Tests:**
  1. `test_outbox_to_log_promotion` — SecurityAG-Aktion → Outbox-Eintrag
     `status='pending'` → nach Watcher-Tick → Log-Eintrag + Outbox `status='committed'`.
  2. `test_outbox_failure_recovery` — Log-Insert wirft Exception → Outbox `status='failed'`,
     `attempts=1` → nächster Tick bei nicht-mehr-failendem Log → `status='committed'`.
  3. `test_watcher_graceful_shutdown` — `stop_event.set()` → Thread beendet sauber
     in <2s, keine hängenden Promotions.
  4. `test_outbox_schema_idempotent` — `init_database()` 2x → Outbox-Tabelle + Indizes
     unverändert.
  5. `test_audit_failure_blocks_action` — wenn Outbox-Write fehlschlägt (DB locked),
     schlägt auch die SecurityAG-Aktion fehl (sicherer Pfad).
  6. `test_optional_hash_chain` — wenn implementiert: 10 Aktionen → 10 verkettete
     Hashes, Manipulation an Zeile 5 → Zeile 6-10 `verify_chain()` returns False.
  7. `test_outbox_drain_helper` — `wait_for_outbox_drain(timeout=2.0)` funktioniert
     für Last-Test-Szenarien.

#### C.6 Migrationsbedarf

**Idempotent via `CREATE TABLE IF NOT EXISTS`.** Zwei neue Tabellen + Indizes. Watcher-
Start beim App-Bootstrap (`app.py` lifespan). **Kein Datenverlust** in `audit_log` oder
`blockade_log`. Bei `admin_tools.py:156` müssen **beide** neuen Tabellen in die Cleanup-
Liste.

---

## Section 3 — Vergleichstabelle

| Aspekt | A (Minimal) | B (Strukturiert) | C (Outbox) |
|---|---|---|---|
| **Aufwand** | 2–3 Std | 4.5–5.5 Std | 8–13 Std |
| **Schema-Migration** | Nein | Ja (idempotent) | Ja (2 Tabellen, idempotent) |
| **Neue Tabellen** | 0 | 1 | 2 |
| **Neue Helper** | 0 | 1 (`log_security_audit`) | 2 (`enqueue_security_audit` + Watcher) |
| **Watcher-Thread** | Nein | Nein | Ja |
| **Tamper-Evidence** | Nein (nur Plain-JSON) | `content_hash` (sha256) optional | Optional Hash-Chain |
| **Cap-Mechanismus** | shared (1000/800) | dediziert (5000/4500) | dediziert + Outbox-Cap |
| **Filter-Granularität** | `event_type LIKE 'security_%'` | Spalten `result`, `severity`, `action_type` | + Outbox-Status-Filter |
| **API-Endpoint** | bestehend (`/api/audit-log`) | neu (`/api/security-audit-log`) | neu + Outbox-Status-Endpoint |
| **Risiko bei DB-Lock** | niedrig (shared Tabelle, kurze Writes) | mittel (eigener Write) | mittel (2 Writes + Watcher) |
| **Test-Komplexität** | niedrig (5 Tests) | mittel (7 Tests) | hoch (7+ Tests + Threading) |
| **Debug-Komplexität** | trivial | trivial | mittel (2 Tabellen) |
| **Frontend-Impact** | keiner (bestehende API reicht) | optional (neues Dashboard) | optional (Outbox-Status) |
| **Production-Ready?** | Ja, aber Cap-geteilt | Ja, dediziert | Ja, aber Thread-Lifecycle testen |

---

## Section 4 — Hook-Position im Detail (für alle 3 Optionen identisch)

**Datei:** `src/gnom_hub/agents/actions/action_handlers.py`
**Zeilen:** 9-40 (WRITE-Block: 13-30; SHELL-Block: 33-40; weitere nach Bedarf)

**Trigger-Bedingung (für alle Optionen gleich):**
```python
def _is_security_audit_action(agent: dict, perms: list, action_kind: str) -> bool:
    """SecurityAG mit godmode/run/write führt eine sicherheitskritische Aktion aus."""
    if (agent.get("name") or "").lower() != "securityag":
        return False
    # godmode zählt als run+write-Surrogat (vgl. Zeile 11: godmode impliziert run)
    if action_kind == "write" and ("write" in perms or "godmode" in perms):
        return True
    if action_kind == "run" and ("run" in perms or "godmode" in perms):
        return True
    if action_kind == "browser" and "godmode" in perms:
        return True
    return False
```

**Vergleichbare Hardcodes** im Codebase (belegen, dass `name.lower() == "securityag"` ein
etabliertes Pattern ist):
- `gatekeeper.py:303, 449` — `if name.lower() == "soulag": pass` (SoulAG-Sonderfall)
- `agent_repo.py:85` — `sys_roles = {"soul", "general", "watchdog", "security"}`

**Kein anderer SecurityAG-spezifischer Audit-Hook existiert heute** — die SecurityAG-
Rolle hat **keine** dedizierte Code-Behandlung, die über die generische Permission-Logik
hinausgeht. Ausnahme: `is_security_block()`-Funktion in `path_validator.py` (vom
`gatekeeper.py:319` aufgerufen) — die ist aber ein **Risk-Scorer**, kein Audit-Hook.

---

## Section 5 — Was SecurityAG-spezifisch zu tracken ist

Schritt 4-Spec nennt drei Aktions-Kategorien. Hier die Konkretisierung mit Code-Quellen:

### 5.1 `godmode`-Aktionen

`godmode` ist eine **Permission**, kein Action-Tag. Es aktiviert:
- `run`-Permission automatisch (`action_handlers.py:11`)
- `browser`-Tool (`tool_registry.py:29`)
- `read_file` ohne Workspace-Beschränkung (`tool_registry.py:5`)

**Konkret zu tracken (wenn SecurityAG `godmode` hat):**
- `[WRITE:...]` mit Pfad außerhalb des Workspace (godmode-Feature)
- `[SHELL:...]` mit `run_in_sandbox`-Call (`action_exec.py:32`)
- `[BROWSER:...]`-Calls (`action_handlers.py:57`)

### 5.2 `run`-Aktionen

`run` wird explizit von `action_handlers.py:35` geprüft:
```python
for m in re.finditer(r"\[SHELL:\s*(.*?)\]", ans):
    cmd = m.group(1).strip()
    if "run" not in perms:
        ans = ans.replace(m.group(0), f"[System: ...]")
    elif verify_cmd(agent, cmd):
        sh_ms.append(m)
    else:
        ans = ans.replace(m.group(0), f"[Gatekeeper: ...]")
```

**Hook-Punkt:** Zeile 38 (nach `verify_cmd` True) und Zeile 40 (nach Gatekeeper-Deny).
Beide Stellen wissen, ob die Aktion **erfolgt** ist.

### 5.3 `write`-Aktionen

`write` wird explizit von `action_handlers.py:15, 25` geprüft:
```python
for m in re.finditer(r"\[WRITE:\s*(.*?)\](.*?)\[/WRITE\]", ans, re.DOTALL):
    fn, content = m.group(1).strip(), m.group(2).strip()
    if "write" not in perms:
        ans = ans.replace(m.group(0), f"[System: ...]")
    elif verify_write(agent, fn, content, wd, perms):
        w_ms.append(m)
    else:
        ans = ans.replace(m.group(0), f"[Gatekeeper: ...]")
```

**Hook-Punkt:** Zeile 18 (nach `verify_write` True) und Zeile 20 (nach Gatekeeper-Deny).

### 5.4 Sonderfälle

- **Brainstorm-Override** (`brainstorm_helpers.py:17`): Wenn `bs_mode=True`, sind
  `[WRITE:]` und `[SHELL:]` unabhängig von Permissions erlaubt. **Soll SecurityAG auch
  im Brainstorm-Modus auditiert werden?** Vermutlich ja, aber explizit zu klären.
- **Auto-Approve-Pfad** (`gatekeeper.py:185`): Wenn `enable_confirmations=False` ist,
  werden alle Aktionen ohne User-Bestätigung durchgewunken. **Audit-Log muss diese
  Auto-Approvals markieren** (z.B. `result="auto_approved"`).
- **Mehrere Actions in einer Antwort** (`action_handlers.py:13-57`): Die Regex-Loop
  matcht **beliebig viele** `[WRITE:...]`/`[SHELL:...]`-Tags in einer einzigen LLM-
  Antwort. Der Audit-Hook muss **pro Match** feuern, nicht nur einmal pro Antwort.

---

## Section 6 — Owner-Entscheidung (Bitte ausfüllen)

> **Wähle genau eine Option:** A, B oder C.
>
> ☐ **Option A** — Minimal (bestehende `audit_log`-Tabelle, neuer Event-Type)
> ☐ **Option B** — Strukturiert (neue `security_audit_log`-Tabelle, dedizierter Helper)
> ☐ **Option C** — Outbox (Watcher-Pattern, async, audit-fest)
>
> **Optional — Sonderfälle explizit regeln:**
> - ☐ Audit auch im Brainstorm-Modus? (Default: ja)
> - ☐ `result="auto_approved"` als zusätzliches Result-Feld? (Default: ja)
> - ☐ Hash-Chain für Tamper-Evidence? (Default: nein — zu aufwendig für Stufe 1)
> - ☐ Neuer API-Endpoint `/api/security-audit-log`? (Default: ja für B/C, nein für A)
>
> **Antwort bitte an:** mavis communication send → General-Session (plan_9c1d4ab1)

---

## Section 7 — Verweise

- **Inventory-Task (Schritt 1):** `docs/refactor-permissions/inventory.md` Section 5.6
  dokumentiert die Ist-Situation des `audit_log` ausführlich (diese Datei fasst zusammen).
- **Bestehende API:** `src/gnom_hub/api/endpoints/metrics.py:22-34` (`/api/audit-log`).
- **Bestehender Schreib-Helper:** `src/gnom_hub/db/system_repo.py:86-97` (`log_audit_event`).
- **Bestehende Wrapper-Klasse:** `src/gnom_hub/core/structured_log.py:19-25` (`AgentLogger`).
- **Cap-Mechanismus:** `src/gnom_hub/db/system_repo.py:100-117` (AUDIT_LOG_MAX_ROWS=1000,
  AUDIT_LOG_KEEP_ROWS=800, `_enforce_audit_cap`).
- **Blockade-Log (verwandt):** `src/gnom_hub/db/schema.py:61-71` (Tabelle),
  `src/gnom_hub/db/system_repo.py:138-152` (Helper `log_blockade`).
- **Hook-Position:** `src/gnom_hub/agents/actions/action_handlers.py:9-40`.
- **Permission-Inferenz:** `src/gnom_hub/agents/actions/action_handlers.py:11`
  (godmode → run Auto-Erweiterung).
- **Verwandter Capability-Begriff:** `agent_capabilities`-Tabelle in `db/schema.py:176-181`
  + `find_best_agent_for("security_audit", conn)` in
  `src/gnom_hub/agents/swarm/swarm_comms.py:630` — SecurityAG ist bereits als
  `security_audit`-Agent registriert, aber **nur für Dispatch**, nicht für Self-Audit.
- **Implementierungs-Task (wartet auf diese Entscheidung):**
  `plan_9c1d4ab1/security-audit` — wird NACH User-Approval aktiv.
- **Cleanup-Liste (admin_tools.py:156-158):** Bei B/C muss `security_audit_log` und/oder
  `security_audit_outbox` ergänzt werden — sonst überleben sie einen DB-Reset.

---

## Section 8 — Was diese Datei NICHT enthält

- **Keine Code-Änderungen** an `src/` (verifiziert mit `git diff --stat src/` — siehe
  deliverable.md).
- **Keine Schema-Migrationen** — die kämen erst nach Owner-Approval in der
  Implementierungs-Task.
- **Keine Tests** — `tests/test_security_audit_log.py` etc. würden in der
  Implementierungs-Task entstehen, NICHT hier.
- **Keine Antwort des Owners** — die Entscheidung wird vom User via
  `mavis communication send` zurück an die General-Session gegeben.

**Ende der Design-Frage. STOPP — warte auf Owner-Entscheidung.**
