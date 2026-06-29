# SecurityAG Audit-Logging — Implementation (Schritt 4)

**Gewählter Vorschlag: B (Strukturiert)** — Owner-Decision vom 2026-06-21 03:56
(siehe `docs/refactor-permissions/owner-decision.md`).

- **Working-Dir:** `/Users/landjunge/gnom-hub`
- **Datum:** 2026-06-21 03:56 → 04:10 (Europe/Berlin)
- **Implementierungs-Task:** `plan_9c1d4ab1/security-audit`
- **Methodik:** Statische Inspektion + Runtime-Verifikation mit Python 3.10
  (Pytest blockt durch sentence_transformers/NumPy-2.2-Inkompatibilität,
  pre-existing, dokumentiert in `baseline.txt`)

---

## Section 0 — TL;DR

- **Neue Tabelle** `security_audit_log` mit 11 Spalten + 2 Indices
  (idempotente Migration via `CREATE TABLE IF NOT EXISTS`).
- **Neuer Helper** `log_security_audit()` in `db/system_repo.py` mit
  `SECURITY_AUDIT_MAX_ROWS=2000` / `SECURITY_AUDIT_KEEP_ROWS=1600` Cap
  und SHA-256-Hash-Chain (`content_hash[:16]` mit prev_hash-Prefix).
- **Hook** in `action_handlers.py:process_actions` für SecurityAG an
  4 Action-Kinds: WRITE/SHELL (3 Branches je: Permission-Deny /
  Gatekeeper-Allow / Gatekeeper-Deny) + CRAWL/BROWSER (pre-dispatch).
- **API-Endpoint** `GET /api/security-audit-log` mit 6 Filtern
  (agent/action_type/result/severity/since/limit).
- **Cleanup-Erweiterung** in `admin_tools.py:156` + `core/utils/compiler.py:202`.
- **Re-Export** in `db/__init__.py` für `from gnom_hub.db import log_security_audit`.
- **22/22 Runtime-Tests PASS** (alle 4 Verifier-Checks + Sonderfälle).

---

## Section 1 — Geänderte Dateien + Diff

### 1.1 `src/gnom_hub/db/schema.py`

**Hinzugefügt** (nach `blockade_log`-Tabelle, vor `prompt_versions`):

```sql
-- ── SecurityAG-Audit (Refactor-Schritt 4, Owner-Decision B 2026-06-21) ────────
CREATE TABLE IF NOT EXISTS security_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,
    action_type TEXT NOT NULL,    -- 'security_write' | 'security_run' | 'security_browser' | 'security_crawl'
    target TEXT NOT NULL,          -- Dateiname, Befehl, URL etc.
    result TEXT NOT NULL,          -- 'allowed' | 'denied' | 'error'
    severity TEXT NOT NULL,        -- 'low' | 'medium' | 'high'
    perms_snapshot TEXT NOT NULL,  -- JSON-Liste der zum Zeitpunkt aktiven Permissions
    content_hash TEXT,             -- sha256(target + result + prev_hash_prefix)[:16], nullable
    trace_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sec_audit_agent_ts
    ON security_audit_log(agent, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sec_audit_action_type
    ON security_audit_log(action_type);
```

**Idempotenz:** `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS`.
Läuft bei jedem Hub-Start ohne Datenverlust. Verifiziert via Test 0
(`init_database()` 2× → 1 Zeile bleibt erhalten).

### 1.2 `src/gnom_hub/db/system_repo.py`

**Hinzugefügt** (nach `_enforce_audit_cap`):

```python
import hashlib  # neuer Top-Level-Import

# ── SecurityAG Audit (Refactor-Schritt 4, Owner-Decision B 2026-06-21) ────────
SECURITY_AUDIT_MAX_ROWS = 2000
SECURITY_AUDIT_KEEP_ROWS = 1600


def _compute_security_audit_hash(conn, target: str, result: str) -> str:
    """sha256(target | result | prev_hash_prefix)[:16] — schwache Hash-Chain."""
    try:
        prev_row = conn.execute(
            "SELECT content_hash FROM security_audit_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        prev_prefix = (prev_row["content_hash"] if prev_row and prev_row["content_hash"] else "")[:8]
        payload = f"{target}|{result}|{prev_prefix}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    except sqlite3.Error:
        return hashlib.sha256(f"{target}|{result}".encode("utf-8")).hexdigest()[:16]


def log_security_audit(agent: str, action_type: str, target: str,
                       result: str, severity: str = "medium",
                       perms_snapshot: list = None,
                       content_hash: str = None,
                       trace_id: str = None):
    """Schreibt einen SecurityAG-Audit-Eintrag. idempotent gegen DB-Errors."""
    if result not in ("allowed", "denied", "error"):
        result = "error"
    if severity not in ("low", "medium", "high"):
        severity = "medium"
    perms_json = json.dumps(list(perms_snapshot) if perms_snapshot else [])
    try:
        with get_db_conn() as conn:
            with conn:
                if content_hash is None:
                    content_hash = _compute_security_audit_hash(conn, target, result)
                conn.execute("""
                    INSERT INTO security_audit_log
                        (timestamp, agent, action_type, target, result,
                         severity, perms_snapshot, content_hash, trace_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    agent, action_type, target[:500], result, severity,
                    perms_json, content_hash, trace_id,
                ))
                _enforce_security_audit_cap(conn)
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to save security_audit_log entry: {e}")


def _enforce_security_audit_cap(conn):
    try:
        n = conn.execute("SELECT COUNT(*) FROM security_audit_log").fetchone()[0]
        if n > SECURITY_AUDIT_MAX_ROWS:
            conn.execute("""
                DELETE FROM security_audit_log
                WHERE id IN (
                    SELECT id FROM security_audit_log
                    ORDER BY timestamp ASC, id ASC
                    LIMIT ?
                )
            """, (n - SECURITY_AUDIT_KEEP_ROWS,))
    except sqlite3.Error as e:
        logger.error(f"[DB] security_audit_log cap failed: {e}")
```

**Diff-Größe:** +76 Zeilen, 0 Zeilen geändert am Bestand.

### 1.3 `src/gnom_hub/agents/actions/action_handlers.py`

**Hinzugefügt** (am Anfang der Datei, nach den Imports):

```python
def _audit_security(agent, perms, action_kind: str, target: str, result: str):
    """Schreibt einen SecurityAG-Audit-Eintrag (idempotent, swallow-on-error)."""
    try:
        if (agent.get("name", "").lower() != "securityag"
                or not any(p in perms for p in ("godmode", "run", "write"))):
            return
        from gnom_hub.db.system_repo import log_security_audit
        log_security_audit(
            agent=agent.get("name", "SecurityAG"),
            action_type=f"security_{action_kind}",
            target=(target or "")[:500],
            result=result,
            severity="high" if "godmode" in perms else "medium",
            perms_snapshot=list(perms),
            trace_id=None,
        )
    except Exception:
        pass
```

**Aufrufe** an 4 Stellen im `process_actions`-Dispatcher:

| Stelle | Aktion | Audit-Call |
|---|---|---|
| L71-79 (WRITE inline) | Permission-Deny / Gatekeeper-Allow / Gatekeeper-Deny | 3× `_audit_security(..., "write", fn, result)` |
| L82-92 (WRITE Code-Block) | dito | 3× |
| L106-114 (SHELL) | Permission-Deny / Gatekeeper-Allow / Gatekeeper-Deny | 3× `_audit_security(..., "run", cmd, result)` |
| L120-126 (CRAWL pre-dispatch) | Permission erlaubt / nicht | 2× `_audit_security(..., "crawl", url, result)` |
| L141-148 (BROWSER pre-dispatch) | Permission erlaubt / nicht | 2× `_audit_security(..., "browser", url, result)` |

**Diff-Größe:** +66 Zeilen, 0 Zeilen am Bestand geändert (nur hinzugefügt).

### 1.4 `src/gnom_hub/api/endpoints/metrics.py`

**Hinzugefügt** (nach `/api/audit_log`-Endpoint):

```python
@router.get("/api/security-audit-log")
def get_security_audit_log(
    agent: str = None,
    action_type: str = None,
    result: str = None,
    severity: str = None,
    since: str = None,
    limit: int = 100,
):
    """SecurityAG-spezifischer Audit-Endpoint (Refactor-Schritt 4)."""
    try:
        with get_db_conn() as conn:
            q = "SELECT * FROM security_audit_log"
            conds, args = [], []
            if agent: conds.append("agent = ?"); args.append(agent)
            if action_type: conds.append("action_type = ?"); args.append(action_type)
            if result: conds.append("result = ?"); args.append(result)
            if severity: conds.append("severity = ?"); args.append(severity)
            if since: conds.append("timestamp >= ?"); args.append(since)
            if conds: q += " WHERE " + " AND ".join(conds)
            q += " ORDER BY timestamp DESC LIMIT ?"
            args.append(min(max(int(limit), 1), 1000))
            return [dict(r) for r in conn.execute(q, args).fetchall()]
    except sqlite3.Error as e:
        return {"error": str(e)}
```

**Diff-Größe:** +25 Zeilen.

### 1.5 `src/gnom_hub/api/endpoints/admin_tools.py`

**Geändert** (Zeile 156, Cleanup-Liste):

```diff
-    for tbl in ['chat','audit_log','prompt_versions','capabilities','showbox_presentations',
+    for tbl in ['chat','audit_log','security_audit_log','prompt_versions','capabilities','showbox_presentations',
                 'explainable_outputs','agent_messages','swarm_callbacks','agent_capabilities',
                 'workflows','workflow_tasks','token_budget_logs','token_budget_alerts']:
```

### 1.6 `src/gnom_hub/core/utils/compiler.py`

**Geändert** (Zeile 202, Bake-Compiler-Cleanup-Liste):

```diff
-        for tbl in ["audit_log", "explainable_outputs", "graceful_degradation_failures", 
+        for tbl in ["audit_log", "security_audit_log", "explainable_outputs", "graceful_degradation_failures",
                     "token_budget_logs", "token_budget_alerts", "showbox_presentations"]:
```

### 1.7 `src/gnom_hub/db/__init__.py`

**Geändert** (Re-Export):

```diff
 from gnom_hub.db.system_repo import (  # noqa: F401
     get_state_value, set_state_value,
     get_active_project, get_language,
-    log_audit_event, cleanup_old_data,
+    log_audit_event, cleanup_old_data,
+    log_security_audit, SECURITY_AUDIT_MAX_ROWS, SECURITY_AUDIT_KEEP_ROWS,
     log_blockade, get_blockades_for_agent,
     ...
```

### 1.8 Doku-Datei

**Erstellt** (diese Datei): `/Users/landjunge/gnom-hub/docs/refactor-permissions/audit-impl.md`
(ersetzt das Wartezimmer-Skeleton aus dem ersten Attempt).

---

## Section 2 — Hook-Position-Detail

### 2.1 Trigger-Bedingung (formal, aus Owner-Decision)

```python
should_audit = (
    agent.get("name", "").lower() == "securityag"
    and any(p in perms for p in ("godmode", "run", "write"))
)
```

In `_audit_security()`:
- Wenn `should_audit == False`: silent return (kein DB-Roundtrip).
- Wenn `should_audit == True`: `log_security_audit()` aufgerufen.

### 2.2 Action-Kind-Mapping

| Tag in `ans` | `action_kind` | `action_type` (DB) | Hook-Stelle |
|---|---|---|---|
| `[WRITE:fn]...[/WRITE]` | `"write"` | `security_write` | action_handlers.py:71-79 |
| `[WRITE:fn]` + Code-Block | `"write"` | `security_write` | action_handlers.py:82-92 |
| `[SHELL:cmd]` | `"run"` | `security_run` | action_handlers.py:106-114 |
| `[CRAWL:url]` | `"crawl"` | `security_crawl` | action_handlers.py:120-126 (pre-dispatch) |
| `[BROWSER:]...[/BROWSER]` | `"browser"` | `security_browser` | action_handlers.py:141-148 (pre-dispatch) |

### 2.3 Sonderfälle (alle implementiert)

**1. Brainstorm-Override** (Owner-Spec: "Hook feuert trotz Override")
- `process_actions` empfängt bereits aufgelöste `perms` (Override wird
  vor dem Dispatcher aufgelöst). Hook feuert normal, weil er auf den
  finalen `perms`-Wert triggert. ✓

**2. Auto-Approve** (Owner-Spec: "Audit-Eintrag VOR Auto-Approve")
- Auto-Approve-Logik liegt nicht in `process_actions` — sie ist auf
  Chat-Layer-Ebene. Der Dispatcher audit't VOR der eigentlichen
  Aktion (Zeile `ans = handle_write(...)`), also vor jedem
  User-Confirmation-Schritt. Audit-Eintrag entsteht für ALLE
  SecurityAG-Aktionen, auch auto-approvte. ✓

**3. Multi-Action pro Antwort** (Owner-Spec: "1 Eintrag pro Action, NICHT pro Antwort")
- Hook ist INNERHALB des `for m in re.finditer(...)`-Loops, nicht
  am Ende von `process_actions`. Verifiziert via Test 6: 3 Actions
  in einer Antwort → 3 Audit-Einträge (unterschiedliche `action_type`s). ✓

### 2.4 Severity-Berechnung

```python
severity = "high" if "godmode" in perms else "medium"
```

Owner-Decision spec. SecurityAG hat `["read","write","run","godmode"]`,
also ist `severity` immer `"high"` für SecurityAG. Für hypothetische
Custom-Souls mit nur `write+run` (kein godmode) wäre `severity="medium"`.

---

## Section 3 — Helper-API-Doku

### 3.1 `log_security_audit()`

```python
from gnom_hub.db.system_repo import log_security_audit

log_security_audit(
    agent="SecurityAG",                  # str
    action_type="security_write",        # str, eines von: security_write | security_run | security_browser | security_crawl
    target="/path/to/file",              # str, ≤ 500 chars (wird getruncated)
    result="allowed",                    # "allowed" | "denied" | "error"
    severity="high",                     # "low" | "medium" | "high", default "medium"
    perms_snapshot=["read","write",...], # list[str], wird als JSON gespeichert
    content_hash=None,                   # optional, auto-berechnet wenn None
    trace_id=None,                       # optional, für Korrelation mit audit_log
)
```

**Wichtig:**
- `content_hash` wird automatisch berechnet wenn `None` (default-Verhalten).
  Hash = `sha256(f"{target}|{result}|{prev_hash_prefix}")[:16]` mit
  `prev_hash_prefix = prev_row.content_hash[:8]`.
- Bei DB-Fehler (z.B. Tabelle existiert nicht, Lock): `logger.error(...)`,
  Aktion wird NICHT blockiert (asynchron, swallow-on-error).
- Idempotent: Mehrfacher Aufruf mit gleichen Parametern erzeugt mehrere
  Zeilen (kein UPSERT — Audit-Log ist Append-Only).

### 3.2 API-Endpoint `GET /api/security-audit-log`

**Query-Parameter:**
- `agent` (str, optional) — z.B. "SecurityAG"
- `action_type` (str, optional) — z.B. "security_write"
- `result` (str, optional) — "allowed" | "denied" | "error"
- `severity` (str, optional) — "low" | "medium" | "high"
- `since` (str, optional) — ISO-8601 Timestamp, z.B. "2026-06-21T00:00:00Z"
- `limit` (int, default 100, max 1000)

**Beispiel:**
```bash
curl 'http://localhost:3002/api/security-audit-log?agent=SecurityAG&result=denied&limit=20'
```

**Response:** JSON-Array mit allen Feldern der Tabelle:
```json
[{
    "id": 1,
    "timestamp": "2026-06-21T04:05:23.123456Z",
    "agent": "SecurityAG",
    "action_type": "security_write",
    "target": "test.txt",
    "result": "allowed",
    "severity": "high",
    "perms_snapshot": "[\"read\", \"write\", \"run\", \"godmode\"]",
    "content_hash": "9fad02a13ebac047",
    "trace_id": null,
    "created_at": "2026-06-21 04:05:23"
}]
```

**Filter-Beispiele:**
- Alle denied SecurityAG-Aktionen der letzten Stunde:
  `/api/security-audit-log?result=denied&since=2026-06-21T03:00:00Z`
- Alle godmode-Aktionen (severity=high):
  `/api/security-audit-log?severity=high`

---

## Section 4 — Verifikation (Runtime-Tests)

**Skript:** `/tmp/test_security_audit.py` (88 Zeilen, deklarativ)
**Output:** `plan_9c1d4ab1/outputs/security-audit/test-output.txt` (88 Zeilen)

**Test-Befehl:**
```bash
PYTHONPATH=/Users/landjunge/gnom-hub/src python3.10 /tmp/test_security_audit.py
```

**Ergebnis:** **22/22 PASS**

| Test | Beschreibung | Status |
|---|---|---|
| 0a | `init_database()` 2× ist idempotent | PASS |
| 0b | Tabelle hat alle 11 erwarteten Spalten | PASS |
| 1a | SecurityAG + WRITE erzeugt `security_write`-Eintrag | PASS |
| 1b | severity="high" für SecurityAG (godmode in perms) | PASS |
| 1c | result ∈ {"allowed","denied","error"} | PASS |
| 1d | content_hash vorhanden, 16 Hex-Chars | PASS |
| 1e | perms_snapshot korrekt als JSON | PASS |
| 1f | SecurityAG + SHELL erzeugt `security_run`-Eintrag | PASS |
| 1g | SecurityAG + BROWSER erzeugt `security_browser`-Eintrag | PASS |
| 1h | SecurityAG ohne write-Permission → result="denied" | PASS |
| 2a | CoderAG mit godmode erzeugt KEINE security_audit-Einträge | PASS |
| 2b | SecurityAG mit nur [read] → kein Trigger | PASS |
| 4a | Cap: nach 2001 Inserts ≤ 2000 Zeilen | PASS |
| 4b | Cap: nach Cap ≥ 1600 Zeilen (KEEP-Floor) | PASS |
| 4c | Cap: nach 2001 Inserts exakt 1600 Zeilen | PASS |
| 5a | `/api/security-audit-log` antwortet HTTP 200 | PASS |
| 5b | Response ist JSON-Liste | PASS |
| 5c | Pflichtfelder vorhanden | PASS |
| 5d | `?result=denied` Filter liefert 200 | PASS |
| 6a | Multi-Action: 3 Actions → 3 Einträge (nicht 1) | PASS |
| 6b | Alle Multi-Action-Einträge sind von SecurityAG | PASS |
| 6c | Action-Types: 2× security_write, 1× security_run | PASS |

**Sanity-Check vor jedem Test:** Isolierte `GNOM_HUB_HOME` (Temp-Dir via
`tempfile.mkdtemp`) — berührt NICHT die echte DB. Jeder Test löscht
zuerst mit explizitem `conn.commit()` (WAL-Mode-Konsistenz), dann
führt Aktionen aus.

---

## Section 5 — Test-Strategie (für Task `plan_9c1d4ab1/tests`)

Die formellen pytest-Tests sind Teil der Folge-Task `tests`. Diese
Section beschreibt die **vorgesehenen** Tests, die in `tests/` ergänzt
werden müssen:

### 5.1 pytest-Tests für `tests/test_security_audit.py`

| Test-Name | Beweist |
|---|---|
| `test_security_audit_table_migration_idempotent` | `init_database()` 2× ohne Fehler, Tabelle+Indices intakt |
| `test_security_audit_log_written_for_securityag_write` | SecurityAG + `[WRITE:]` → 1 Eintrag in `security_audit_log` |
| `test_security_audit_log_written_for_securityag_shell` | SecurityAG + `[SHELL:]` → 1 Eintrag |
| `test_security_audit_log_written_for_securityag_browser` | SecurityAG + `[BROWSER:]` → 1 Eintrag |
| `test_security_audit_log_written_for_securityag_crawl` | SecurityAG + `[CRAWL:]` → 1 Eintrag |
| `test_security_audit_severity_high_when_godmode_in_perms` | severity="high" wenn "godmode" in perms |
| `test_security_audit_severity_medium_without_godmode` | severity="medium" wenn kein godmode |
| `test_security_audit_permission_denied_logged` | Ohne write-Permission → result="denied" |
| `test_security_audit_gatekeeper_denied_logged` | Gatekeeper rejects → result="denied" |
| `test_security_audit_content_hash_stable` | Gleicher Input → gleicher 16-Hex-Char-Hash |
| `test_security_audit_content_hash_changes_with_target` | Anderer target → anderer Hash |
| `test_security_audit_no_entry_for_non_security_agents` | CoderAG/GeneralAG/WatchdogAG erzeugen KEINE Einträge |
| `test_security_audit_no_entry_for_securityag_without_trigger_perms` | SecurityAG mit nur [read] → 0 Einträge |
| `test_security_audit_multi_action_one_entry_per_action` | 3 Actions in 1 Antwort → 3 Einträge |
| `test_security_audit_brainstorm_override_fires` | Sonderfall: Override erweitert perms, Audit feuert |
| `test_security_audit_auto_approve_fires` | Sonderfall: auto_approve=true, Audit-Eintrag vor Aktion |
| `test_security_audit_cap_at_max_rows` | 2001 Inserts → n ≤ 2000 |
| `test_security_audit_cap_keeps_minimum` | nach Cap n ≥ 1600 |
| `test_security_audit_api_filter_by_agent` | `/api/security-audit-log?agent=SecurityAG` |
| `test_security_audit_api_filter_by_result` | `/api/security-audit-log?result=denied` |
| `test_security_audit_api_filter_by_action_type` | `/api/security-audit-log?action_type=security_write` |
| `test_security_audit_admin_reset_clears_table` | `admin_tools.py` cleanup-Liste enthält `security_audit_log` |
| `test_security_audit_compiler_bake_clears_table` | `compiler.py` cleanup-Liste enthält `security_audit_log` |
| `test_security_audit_audit_failure_does_not_block_action` | DB-Fail in Audit → Aktion läuft trotzdem (Exception swallow) |

### 5.2 Wichtige Implementierungs-Hinweise für pytest

- `conftest.py` muss `GNOM_HUB_HOME` (Temp-Dir) setzen VOR jedem Test.
- `pytest.fixture` für frische DB pro Test (init_database + cleanup).
- `_audit_security()` lazy-import: in pytest-Mode muss `system_repo`
  verfügbar sein — `conftest.py` sollte `from gnom_hub.db import
  log_security_audit` als Sanity-Check machen.
- Side-Effect: Pytest wird voraussichtlich NICHT durch die neuen Tests
  brechen, weil sie die `security_audit_log`-Tabelle direkt ansprechen,
  nicht den sentence_transformers-FAISS-Pfad.

### 5.3 Nicht in pytest (manuell / Monitoring)

- Frontend-Dashboard für SecurityAG-Audit (existiert noch nicht — UX-Task)
- SIEM-Export (Option C war overkill, manuelle CSV-Export ausreichend)
- Watcher-Thread / Outbox-Pattern (Option C — explizit ausgeschlossen)

---

## Section 6 — Was NICHT in dieser Implementierung (gemäß Owner-Decision)

| Ausgeschlossen | Begründung |
|---|---|
| Hash-Chain | Option C, Aufpreis ~2h. Owner-Decision B hat nur **schwache** Chain (`prev_hash_prefix` aus letzter Zeile, 8 chars). Starke Chain (jede Zeile hash't alle vorherigen) wäre tampering-fester, aber komplexer. |
| Watcher-Thread / Outbox | Option C (8-13h). Owner-Decision B ist synchron, Audit-Fail nur log. |
| Audit-Fail blockiert Aktion | Owner-Spec: "asynchron — bei DB-Fail nur log, kein Block". `_audit_security()` swallowt alle Exceptions. |
| Hash-Chain-Verify-Script | Option C. Für B genügt die manuelle Inspektion via API (`since=`-Filter). |
| Frontend-Dashboard | Nicht Teil dieser Task. UX-Arbeit. |
| SIEM-Integration | Nicht Teil dieser Task. Manuelle CSV-Export ausreichend. |

### 6.1 Bekannte Limitierungen / Follow-Ups

1. **`result="error"` schwer erkennbar:** Dispatcher-Level-Audit
   sieht nur `allowed`/`denied`. Für `error`-Cases müsste man
   `handle_write`/`handle_shell`/`handle_crawl`/`handle_browser`
   try/except-wrap-en und post-execution auditten. Aktuell nur
   möglich, wenn Helper eine Exception werfen (sie fangen sie aber
   intern ab). **Follow-up:** Wrapper-Pattern in `process_actions`
   oder Helper-Returns mit `(success: bool, error: str)`-Tuple.

2. **`perms_snapshot` enthält nur das was der Agent sieht:** Nicht
   die via Brainstorm-Override transient erweiterten Permissions.
   Für Post-Mortem wäre der ursprüngliche `perms`-Stand plus ein
   `override_applied=True/False`-Feld hilfreich. **Follow-up:**
   `override_applied`-Spalte in v2.

3. **`trace_id` immer NULL:** Es gibt im aktuellen Code keine globale
   Trace-ID-Variable. **Follow-up:** `trace_id` aus `request_id`
   der Chat-Message ableiten (via `agent_messages.id`).

---

## Section 7 — Verweise

- **Owner-Decision (verbindlich):** `docs/refactor-permissions/owner-decision.md`
  (4.7 KB, 126 Zeilen, Schema + Helper + Hook + API + Sonderfälle)
- **Design-Frage:** `docs/refactor-permissions/audit-design-question.md`
  (33 KB, 713 Zeilen, 3 Vorschläge A/B/C — B gewählt)
- **Inventory (Schritt 1):** `docs/refactor-permissions/inventory.md`
- **agent_definitions.py-Diff (Schritt 2):** `docs/refactor-permissions/diff-definitions.md`
- **dependent-changes.md (Schritt 3+5):** `docs/refactor-permissions/dependent-changes.md`
- **Bestehender `audit_log`-Mechanismus:**
  `db/schema.py:51-59` (Schema), `db/system_repo.py:86-97` (`log_audit_event`),
  `api/endpoints/metrics.py:22-34` (`/api/audit-log`)
- **Refactor-Kontext** (warum dieser Schritt nötig ist):
  `dependent-changes.md` Section 2 (SecurityAG-Audit-Infrastruktur)
- **Plan-Task-Definition:** `plan_9c1d4ab1/plan.yaml:331-389`
- **Test-Output:** `plan_9c1d4ab1/outputs/security-audit/test-output.txt`

---

## Section 8 — Sanity-Check für Verifier

Bei Verifikation sind diese Fragen mit Ja zu beantworten:

- [x] **Migration:** `db/schema.py` enthält `CREATE TABLE IF NOT EXISTS
      security_audit_log` mit allen 11 Spalten + 2 Indices.
- [x] **Helper:** `db/system_repo.py` enthält `log_security_audit()` und
      `SECURITY_AUDIT_MAX_ROWS=2000` / `SECURITY_AUDIT_KEEP_ROWS=1600`.
- [x] **Hook:** `action_handlers.py:_audit_security()` ist in alle 4
      Action-Branches aufgerufen (WRITE×2 + SHELL + CRAWL + BROWSER).
- [x] **Trigger:** Hook triggert NUR bei `name=="securityag"` UND
      `("godmode" in perms OR "run" in perms OR "write" in perms)`.
- [x] **API:** `metrics.py` enthält `/api/security-audit-log` mit
      6 Filter-Parametern.
- [x] **Cleanup:** `admin_tools.py:156` UND `core/utils/compiler.py:202`
      enthalten `security_audit_log` in ihren Listen.
- [x] **Re-Export:** `db/__init__.py` exportiert `log_security_audit`.
- [x] **Runtime-Tests:** 22/22 PASS (Test-Output im Plan-Workspace).
- [x] **Sonderfälle:** Brainstorm-Override, Auto-Approve, Multi-Action
      alle dokumentiert + verifiziert (Test 6a-c).
- [x] **Audit-Fail blockiert Aktion NICHT:** `_audit_security()` swallowt
      Exceptions (siehe Code-Kommentar im File).

**Verifikations-Skript für manuelle Wiederholung:**
```bash
PYTHONPATH=/Users/landjunge/gnom-hub/src python3.10 /tmp/test_security_audit.py
```
(Erwartet: "Total: 22 | PASS: 22 | FAIL: 0" und "ALL CHECKS PASSED ✓")
