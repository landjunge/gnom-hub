# Owner-Decision: SecurityAG-Audit-Log

**Gewählt: Option B (Strukturiert)**

Datum: 2026-06-21 03:56 (Europe/Berlin)
Owner: landjunge (via General-Session mvs_2634aa0788d2432890422dec4f5f6164)
Bezug: docs/refactor-permissions/audit-design-question.md (Schritt 4)

## Begründung

1. SecurityAG ist ein sicherheitskritischer Agent — eine dedizierte Audit-Tabelle ist
   das Mindeste.
2. Aufwand 4.5-5.5 Std ist im Verhältnis zur Risikoreduktion vertretbar.
3. Saubere Trennung von allgemeinen Audit-Events (Prompt-Versionen, Evolution,
   Degradation) und SecurityAG-spezifischen Events.
4. Dedizierte Cap (eigene Zeilenlimits) verhindert Verlust älterer
   Security-Events bei hohem allgemeinen Audit-Aufkommen.
5. Content-Hash ermöglicht Tamper-Detection auf Hash-Basis (ohne Chain-Overhead
   wie Option C).
6. API-Endpoint /api/security-audit-log ermöglicht späteren SIEM-Export ohne
   Schema-Change.

## Implementierungs-Spec (verbindlich für security-audit-Task)

**Schema-Migration** (idempotent in `db/schema.py`):
```sql
CREATE TABLE IF NOT EXISTS security_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,
    action_type TEXT NOT NULL,    -- 'security_write' | 'security_run' | 'security_browser' | 'security_crawl'
    target TEXT NOT NULL,          -- Dateiname, Befehl, URL etc.
    result TEXT NOT NULL,          -- 'allowed' | 'denied' | 'error'
    severity TEXT NOT NULL,        -- 'low' | 'medium' | 'high'
    perms_snapshot TEXT NOT NULL,  -- JSON-Liste der zum Zeitpunkt aktiven Permissions
    content_hash TEXT,             -- sha256(target + result + prev_hash_prefix), nullable
    trace_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sec_audit_agent_ts
    ON security_audit_log(agent, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sec_audit_action_type
    ON security_audit_log(action_type);
```

**Helper** in `db/system_repo.py` (neben `log_audit_event`):
```python
def log_security_audit(agent: str, action_type: str, target: str,
                       result: str, severity: str = 'medium',
                       perms_snapshot: list = None,
                       content_hash: str = None,
                       trace_id: str = None):
    """Schreibt einen SecurityAG-Audit-Eintrag. idempotent gegen DB-Errors."""
    ...
```

**Hook-Position:** `src/gnom_hub/agents/actions/action_handlers.py:9-40`
- WRITE-Block (Zeile 16): vor `verify_write` einfügen
- SHELL-Block (Zeile 38): vor `verify_cmd` einfügen
- CRAWL/BROWSER-Blöcke (Zeile 46/57): analog

**Trigger-Bedingung (für alle Actions identisch):**
```python
if (agent.get("name", "").lower() == "securityag"
    and any(p in perms for p in ("godmode", "run", "write"))):
    log_security_audit(
        agent=agent["name"],
        action_type=f"security_{action_kind}",  # write/run/browser/crawl
        target=target_str,
        result="allowed",  # oder "denied" wenn verweigert
        severity="high" if "godmode" in perms else "medium",
        perms_snapshot=list(perms),
        trace_id=get_trace_id(),
    )
```

**Sonderfälle (alle zu implementieren, siehe design-question.md Section 5.4):**
- Brainstorm-Override: Hook feuert trotz Override (Audit ist nicht teil der
  Override-Logik)
- Auto-Approve: Audit-Eintrag VOR Auto-Approve (Beweiskette)
- Multi-Action pro Antwort: ein Eintrag pro Action, NICHT ein Eintrag pro Antwort

**API-Endpoint** in `api/endpoints/metrics.py` (oder neues File):
```python
@router.get("/api/security-audit-log")
def get_security_audit_log(
    agent: str = None,
    action_type: str = None,
    since: str = None,
    limit: int = 100,
):
    ...
```

**Cap-Mechanismus** (analog zu audit_log):
- `SECURITY_AUDIT_MAX_ROWS = 2000`
- `SECURITY_AUDIT_KEEP_ROWS = 1600`
- Cleanup in `admin_tools.py:156` und `compiler.py:202` (zu beiden Listen
  hinzufügen)

**Migrations-Strategie:**
- Idempotent via `CREATE TABLE IF NOT EXISTS` — kann bei jedem Hub-Start laufen
- KEIN Datenverlust in `audit_log` oder `blockade_log`
- Cleanup-Listen in admin_tools.py und compiler.py erweitern

**Was NICHT in dieser Implementierung:**
- Keine Hash-Chain (das ist Option C)
- Kein Watcher-Thread / Outbox (das ist Option C)
- Keine Schreib-Beschränkung der SecurityAG-Aktion bei Audit-Fail (Aktionen
  werden weiter ausgeführt, Audit ist asynchron — bei DB-Fail nur log, kein
  Block)

## Verifikations-Pflicht

Der security-audit-Task MUSS nach Implementation:
1. Runtime-Test: 3 Szenarien (SecurityAG schreibt, SecurityAG führt aus,
   SecurityAG browser) → 3 Audit-Einträge mit korrekten Feldern
2. Negativ-Test: CoderAG mit godmode schreibt → KEIN security_audit-Eintrag
3. Migrations-Test: `init_database()` 2x → Tabelle unverändert
4. Cap-Test: 2001 Einträge → Cap greift bei 1600

## Owner-Signoff

Diese Datei ist die offizielle Owner-Entscheidung. Verweis in allen
Folge-Dokumenten: "Owner-Decision: B (Strukturiert) — see
docs/refactor-permissions/owner-decision.md".
