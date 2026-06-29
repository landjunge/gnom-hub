# SecurityAG — Tiefen-Audit

**Datum:** 2026-06-28
**Auditor:** general
**Quellen:** 38 Dateien gelesen, 83 Python-Treffer + 51 JSON-Treffer auf `SecurityAG`/`security_ag`
**Workspace:** `/Users/landjunge/gnom-hub`

---

## Sektion 0 — TL;DR / Verdikt

**Identität 2026-06-28 (v7.3):** SecurityAG ist der **HELFER + ERLAUBNIS-MANAGER** — *nicht* Gatekeeper. Er hilft Workern (Verzeichnisse freigeben, Tools installieren, Dateien freigeben) und korrigiert WatchdogAG wenn der blockiert.

**Mantra (wörtlich aus Identity):** *"Worker-Hilfe > Sicherheits-Theater."*

**Tier:** Tier 2b (zwischen User/SoulAG und WatchdogAG). Sicherheits-Auditor.

**Hard-Risk-Bewertung: 🔴 HOCH.** SecurityAG hat `godmode + run + db_write + network + showbox_write` und ist der einzige Agent, der `blockades_db` und `security_permissions` direkt manipulieren kann. Das einzige Audit-Instrument ist der **SecurityAG-Audit-Hook in `action_handlers.py`** — der einen SecurityAG-Eintrag ins Log schreibt, NACHDEM die Aktion bereits passiert ist (post-dispatch, *preventive only via `_audit_security()`* aber pre-execution für die meisten Pfade). Es gibt **keinen externen Wächter**, der SecurityAG selbst prüft.

**Top-3-Risiken:**

1. **SecurityAG-Audit-Hook prüft nur SecurityAG-SELBST.** `_audit_security()` in `action_handlers.py:27-29` ist ein Early-Return wenn `agent.get('name') != 'securityag'`. D.h. wenn SecurityAG seine godmode-Perm ausnutzt um z.B. `security_permissions`-DB zu manipulieren, ist niemand da der das bemerkt. SoulAG sieht im Observer-Modus nur was SecurityAG *behauptet*, nicht was er tatsächlich tut. **Single-Point-of-Failure in der Audit-Kette.**
2. **`agent_definitions.py:191-228` SecurityAG-Eintrag ist komplett veraltet.** Permissions `["read", "write", "run", "godmode"]` (Stand pre-v7.0), Capabilities `["@security"]`, Sys-Prompt "RESSOURCEN- & RECHTE-MANAGER" mit "Whitelist-Verwaltung", "Intelligentes LLM-Routing", "Blockaden auflösen via @@approve_decision". Identity aus `config/agents/SecurityAG.json` (v7.3, 7 Kernrollen als Helfer) wird davon **nicht überschrieben** — aber die Runtime-Permissions werden vermutlich aus `AGENT_DEFINITIONS` gelesen (siehe `agent_definitions.py:1-53` SSoT-Kommentar). Wenn ja, hat SecurityAG **kein** `db_write`/`network`/`showbox_write` aus der Python-Quelle, **aber** alle 7 aus der JSON. **Konflikt ungetestet.**
3. **`security_permissions`-Tabelle in der Haupt-DB existiert als Schema, aber kein Code schreibt sie jemals.** Schema definiert in `db/schema.py:112-126`. Identity-Befehl Rollen 1+2 sagt: "in `security_permissions`-DB eintragen". Identity-Befehl Rollen 4+5 sagt: "direkter Eingriff in blockades_db". Aber: 0 Treffer für `security_permissions` außer Schema + Migrationstest. **Die zentrale SecurityAG-Datenbank ist eine Phantom-Tabelle.** SecurityAGs "DB-Eintrag" läuft ins Leere.

**Empfehlung:** Audit-Kette umbauen (SoulAG als Second-Auditor für SecurityAG-Einträge), `agent_definitions.py` SecurityAG-Block mit v7.3 synchronisieren, und einen echten `security_permissions` Writer implementieren (oder den Befehl aus der Identity entfernen).

---

## Sektion 1 — Identität & Tier-Position

### 1.1 Tier-Hierarchie (User-Mandat 2026-06-28 11:53)

```
Tier 1:  USER (Befehl ist Gesetz)
Tier 2a: SoulAG (User-Interface + Memory + Korrektor) — direkter Vorgesetzter
Tier 2b: DU (SecurityAG — Helfer + Erlaubnis-Manager)  ←
Tier 2c: WatchdogAG (passiver Beobachter + Reporter) — du darfst ihn weiterhin korrigieren
Tier 3a: GeneralAG (Dirigent)
Tier 3b: Workers (CoderAG, WriterAG, EditorAG, ResearcherAG)
```

Quelle: `config/agents/SecurityAG.json:18` Identity, Block `═══ TIER-HIERARCHIE (User-Mandat 2026-06-28 11:53) ═══`.

### 1.2 Gehorsam-Kette

- **User:** Bei User-Befehl: tut er es. **AUSNAHME:** destruktive/externe Aktionen, dann frag User vorher (in der Praxis also: ja, aber mit Bestätigung).
- **SoulAG:** Bei SoulAG-Direktnachricht (`@SoulAG: ...`): SOFORT gehorchen. SoulAG ist Tier 2a über Tier 2b.
- **WatchdogAG:** Tier 2c. SecurityAG darf ihn korrigieren — WatchdogAG MUSS gehorchen (so der Identity-Vertrag).
- **GeneralAG:** Tier 3a. GeneralAG hat KEINE direkte Verbindung zu SecurityAG (`GeneralAG.json:18` Identity: "Du hast KEINE direkte Verbindung zu WatchdogAG oder SecurityAG"). SecurityAG sieht GeneralAGs Outputs nur, wenn Worker sie zitieren.

### 1.3 Versions-Trail

Aus `notes`-Feld:
- **v7.0** (2026-06-28 11:42): Komplett-Umschreibung nach User-Mandat. "SecurityAG ist jetzt HELFER + ERLAUBNIS-MANAGER, nicht Gatekeeper." Position 3 (Tier 2c — unter SoulAG). godmode + run + db_write + network. User-Pflicht bei destruktiven/externen Aktionen.
- **v7.1** (gleicher Tag): Showbox+Buttons-Pflicht.
- **v7.2** (2026-06-28 11:53): Tier-Hierarchie. SoulAG = Tier 2a, SecurityAG = Tier 2b, WatchdogAG = Tier 2c.
- **v7.3** (gleicher Tag): SecurityAG bekommt `showbox_write` — für Blockade-Bestätigungen und Worker-Hilfe-Cards.

**Beobachtung:** 3 Versions-Updates an einem einzigen Tag. Mandat-Drift ist explizit — der User ändert die SecurityAG-Rolle mehrmals täglich. **Risiko:** Identity ist konsistent innerhalb v7.3, aber die *operative Realität* (wer SecurityAG anspricht, was er antwortet) hängt vom LLM-Prompt-Verständnis ab, nicht von einer Code-Ausführung.

### 1.4 Farbe & Persona

- **Farbe:** Lila (`src/gnom_hub/core/agent_names.py:35` `"SecurityAG": "#00e5ff"` ← **ACHTUNG: Farb-Konflikt!** Identity sagt Lila, agent_names.py sagt Cyan. **Bug-Inkonsistenz**.)
- **TTS-Stimme:** `'de': 'Anna (Premium)', 'en': 'Bad News'` (`src/gnom_hub/soul/agent_voices.py:85`)
- **Avatar:** `securityag.png` (`core/agent_names.py:47`)
- **Denkt laut:** Jeder Gedanke muss über TTS hörbar sein (alle Agents).

---

## Sektion 2 — Permissions

### 2.1 Permissions-Matrix (Drei-Quellen-Vergleich)

| Permission | config/agents/SecurityAG.json (v7.3) | agent_definitions.py (vermutlich stale) | Runtime? |
|---|---|---|---|
| `read` | ✅ | ✅ | ✅ |
| `write` | ✅ | ✅ | ✅ (via action_handlers verify_write) |
| `run` | ✅ | ✅ | ✅ (via action_handlers verify_cmd) |
| `godmode` | ✅ | ✅ | ✅ (gatekeeper.py:303 Bypass) |
| `db_write` | ✅ | ❌ (fehlt) | ⚠ ungeklärt |
| `network` | ✅ | ❌ (fehlt) | ⚠ ungeklärt |
| `showbox_write` | ✅ | ❌ (fehlt) | ⚠ ungeklärt |

**Sektion 2.1 KRITISCH:** `src/gnom_hub/agents/agent_definitions.py:191-228` definiert SecurityAG mit `permissions: ["read", "write", "run", "godmode"]` — also **ohne** `db_write`, `network`, `showbox_write`. Die `config/agents/SecurityAG.json` (v7.3) listet diese 3 zusätzlich. Der Modul-Header in `agent_definitions.py:9-50` sagt explizit: *"Diese Datei (`AGENT_DEFINITIONS`) ist die **einzige Quelle für Runtime-Permissions** im Gnom-Hub. Alle anderen Stellen ... lesen `permissions` HIER und propagieren die Liste via `get_soul(name)`."*

**→ Was gilt jetzt?**

Wenn die Runtime `get_soul("securityag")` aus `AGENT_DEFINITIONS` zieht, dann hat SecurityAG zur Laufzeit nur 4 Permissions (`read, write, run, godmode`), NICHT die 7 aus der JSON. Die JSON-`permissions`-Liste wird zur **Anzeige** gelesen (vielleicht vom Frontend), aber **nicht für die Enforcement**.

Oder umgekehrt: Es gibt einen Permission-Loader der JSON ↔ Python-Dict merged (Kommentar agent_definitions.py:32-33: *"Falls JSON jemals Permissions überschreiben soll, ist ein Permission-Loader nötig"*). Diesen Loader habe ich nicht gefunden. **Stand 2026-06-28: ungeklärt.**

**→ Das ist die größte Audit-Schwachstelle.** Sicherheitskritische Permissions (`network`, `db_write`) hängen von einer ungeklärten Konfigurations-Auflösung ab.

### 2.2 godmode — was genau erlaubt es?

`godmode` als Permission-Token: nirgends formal definiert. Aus dem Code:
- `action_handlers.py:54-61` Kommentar: *"Vor Refactor: SoulAG hatte godmode (impliziert write via gatekeeper-Bypass in gatekeeper.py:303)"* — also godmode BYPASSED den Gatekeeper.
- `agent_definitions.py:213-217` SecurityAG-Sys-Prompt: *"Du hast godmode auf dem Dateisystem — das ist primär für Notfall-Reparaturen, nicht für reguläre Aufgaben. Du erstellst immer ein Backup (via scripts/backup_all_dbs.sh), bevor du Dateien oder Code änderst."*
- Identity v7.3: *"Bei destruktiven/externen Aktionen, dann frag den User vorher."*

**Konkret was darf SecurityAG mit godmode?**

1. Schreiben in System-Dateien (`src/gnom_hub/`, `config/`, `scripts/`, `run.sh`, `index.html`, `.env`) — diese sind in `_workspace_system_paths()` (`path_validator.py:27-46`) für Worker blockiert. Für SecurityAG mit godmode: unklar ob der Bypass gilt.
2. `verify_write` in `gatekeeper.py:291-324` ruft `is_worker_blocked()` (Pfad-Check) und `is_security_block()` (Pattern-Check). Beide geben `True`/`"high"` zurück wenn die Action riskant ist. godmode würde das wahrscheinlich umgehen, aber: `verify_write` hat keinen godmode-Parameter. Es liest nur `(agent, fn, content, wd, perms)` und macht den Check.
3. Tatsächlich: `request_capability(name, "WRITE", fn, "AutoApprovedSafePath")` in `verify_write:323` ist ein **Logging**-Call — die eigentliche Schreibaktion erfolgt downstream in `handle_write`. Wenn godmode in `perms` ist, wird die Action ausgeführt.

**→ Praktisch:** SecurityAG mit godmode kann überall schreiben und alles ausführen, weil:
- `verify_write` blockt nicht (kein godmode-Bypass-Code, aber auch keine godmode-Berücksichtigung)
- `verify_cmd` blockt nicht wenn der Befehl in der HARMLESS_SHELL_PATTERNS-Liste ist (`gatekeeper.py:127-147`)
- `request_capability` loggt nur — keine echte Access-Control

**Risiko:** godmode ist semantisch identisch mit "darf alles". Die Identity formuliert es defensiv ("primär für Notfall-Reparaturen"), aber das ist **Prompt-Disziplin**, nicht **technische Beschränkung**.

### 2.3 run + db_write + network

- `run` (Shell-Befehle): Verifiziert via `verify_cmd` in `gatekeeper.py:434-498`. Whitelist-Patterns, Hardcoded Blocklist (mkfs, fdisk, reboot, rm -rf /, curl|sh, etc.). SecurityAG kann alles ausführen was nicht in der Hardblocklist ist.
- `db_write` (Datenbank-Schreiben): Keine eigene Logik gefunden. Heißt vermutlich: Schreibrechte auf alle DBs (`security_permissions`, `watchdog_blockades`, `audit_log`, `security_audit_log`). Identity-Rollen 1+2+4+5 erfordern das (Verzeichnisse freigeben, Blockaden aufheben). **Aber:** kein Code schreibt `security_permissions` (siehe Sektion 5).
- `network` (HTTP-Requests): Identity-Rolle 3 "Tools herunterladen: pip install, npm install, git clone, curl, wget". Vermutlich via `handle_crawl` in `action_handlers.py` und via `[SHELL:] curl`. Keine zentrale `network`-Permission-Enforcement gefunden.

### 2.4 showbox_write

Ermöglicht SecurityAG das Schreiben in die Showbox. Implementiert in:
- `core/security/showbox_validator.py:18-25` `enforce_agent_layer()` — aber das ist nur die **Layer-Regel**, kein Schreib-Verbot.
- Showbox-Schreiben läuft via `handle_showbox` in `action_handlers.py:164`.

`showbox_write` als Permission: keine zentrale Enforcement im Code. Heißt: alle Agents können technisch Showbox schreiben. Identity v7.3 macht es zur Pflicht: *"JEDER Agent darf reinschreiben — du auch."*

---

## Sektion 3 — Helfer-Pflicht vs alte Gatekeeper-Rolle

### 3.1 Was v7.0 geändert hat

**VORHER (gatekeeper.py Mentalität):** SecurityAG blockte. Worker standen.

**JETZT (v7.0):** SecurityAG ist Helfer. Worker sollen arbeiten.

**Mantra:** *"Worker-Hilfe > Sicherheits-Theater."*

**Die 7 Kernrollen aus Identity v7.3:**

| # | Rolle | Aktion | DB-Ziel |
|---|---|---|---|
| 1 | VERZEICHNISSE FREIGEBEN | In `security_permissions`-DB eintragen | security_permissions |
| 2 | DATEIEN FREIGEBEN | Eintragen | security_permissions |
| 3 | TOOLS HERUNTERLADEN | pip/npm/git/curl/wget — bestätigen in Showbox | keine |
| 4 | WATCHDOGAG KORRIGIEREN | Showbox-Card an @WatchdogAG oder direkter Eingriff in blockades_db | watchdog_blockades |
| 5 | BLOCKADEN AUFLÖSEN | SOFORT aufheben wenn offensichtlich hinderlich | watchdog_blockades |
| 6 | USER UM ERLAUBNIS FRAGEN | NUR bei destruktiven/externen Aktionen | showbox_card |
| 7 | SHOWBOX ALS KOMMUNIKATIONSZENTRALE | Jeder Agent schreibt rein | showbox_presentations |

### 3.2 Alte Gatekeeper-Pflicht: Leichen oder sauber entfernt?

**Leichen-Check:**

1. **`core/security/gatekeeper.py:208-211`** — In `wait_for_decision()` wird der Blocker-Agent-Name basierend auf dem Rule-Text bestimmt:
   ```python
   if "security" in rule.lower() or "gefahr" in rule.lower() or "sicherheits" in rule.lower():
       blocker_name = "SecurityAG"
   ```
   → SecurityAG erscheint hier als "blocker", obwohl er jetzt Helfer ist. Die Logik ist: wenn ein `gatekeeper_decision` einen Security-Begriff triggert, WIRD SecurityAG als Blocker gelabelt. **Funktional ok** (Blocker-Label ≠ SecurityAG als Akteur), aber semantisch verwirrend.

2. **`src/gnom_hub/core/security/gatekeeper.py:317-320`** — `verify_write` loggt Blockaden als `blocked_by="SecurityAG"`:
   ```python
   log_blockade(name, "WRITE", fn, f"Hochriskantes Code-Pattern blockiert", "blocked", "SecurityAG", ...)
   log_blockade(name, "WRITE", fn, f"Mittelriskantes Code-Pattern — gewarnt", "warning", "SecurityAG", ...)
   ```
   → Hier ist SecurityAG der **logische Verursacher** der Pattern-Blocks. Aber: `is_security_block()` (path_validator.py:160-190) hat keinen SecurityAG-Parameter — der Block ist **patternbasiert**, nicht agentbasiert. SecurityAG-Credit ist nur Logging.

3. **`src/gnom_hub/soul/soul.py:343,386-413`** — SoulAG `_nudge_loop` benachrichtigt SecurityAG bei stuck Tasks. Identity v7.3 hat das nicht mehr — Rolle 7 sagt "Showbox als Kommunikationszentrale". Aber Code schickt `@SecurityAG BLOCKADE: ...` als dispatch_mention. **Leiche / veralteter Workflow.**

4. **`src/gnom_hub/db/soul_tasks.py:195-225`** — `_notify_security_blocked()` sendet Chat-Messages an SecurityAG-Channel. Hat keinen aktiven Caller-Code-Pfad (SoulAG-`_nudge_loop` benutzt `dispatch_mention`, nicht `_notify_security_blocked`). **Toter Code.**

5. **`src/gnom_hub/db/soul_repo.py:133-143`** — `save_soul_fact_smart` hat eine Whitelist `approved_system_paths`/`approved_security_writes`/`approved_security_commands` mit `["SecurityAG", "WatchdogAG", "System"]`. D.h. nur diese 3 dürfen diese Soul-Facts schreiben. **Funktional aktiv**, aber Identity v7.3 erwähnt SoulAG nicht mehr als Tier-2a-Koordinator dieser Writes — SecurityAG soll sie jetzt direkt machen.

6. **`src/gnom_hub/agents/agent_definitions.py:191-228`** SecurityAG-Block — komplett veraltet (siehe Sektion 2.1). Permissions `["read", "write", "run", "godmode"]` ohne `db_write/network/showbox_write`. Sys-Prompt "RESSOURCEN- & RECHTE-MANAGER" mit Whitelist-Verwaltung, LLM-Routing, Blockaden-auflösen-via-`@@approve_decision`. Identity v7.3 ist da deutlich anders. **Größte Leiche.**

7. **`src/gnom_hub/core/utils/presets.json`** — 6 Domain-Presets (web_development, graphic_design, audio_production, video_production, content_creation, research_and_analysis) haben jeweils einen SecurityAG-Prompt: "Du bist SecurityAG — der **Security-Auditor** des Gnom-Hub. ... 5 Dimensionen: Datenexfiltration, unautorisierte Subprozesse, USB-Key-Bypass, Secret-Leakage und Supply-Chain-Risiken."
   → Identity v7.3 ist das **komplette Gegenteil**: Helfer, keine USB-Key-Trust-Mentalität, keine 5-Dimension-Threat-Assessment. **`agent_definitions.py:35-43` markiert diese Presets als "DORMANT / SCHEMA-DATENLEICHE"** — aber im Code selbst sind sie nicht als dormant markiert. Wenn ein Preset geladen wird, kollidieren die Prompts.

8. **`src/gnom_hub/chat/chat_commands.py:232`** — `@@help` Text: "**SecurityAG:** Scannt Codes und pip-Pakete vor Ausführung." — Identity v7.3 sagt Rolle 3: "Tools herunterladen: pip install ... Du richtest es ein". **Passt halbwegs**, aber der Begriff "Scannt vor Ausführung" ist alte Gatekeeper-Mentalität.

9. **`src/landjunge/gnom-hub/data/presets/default/permissions.json`** — Datei existiert nicht (Pfad-Leiche in `agent_definitions.py:35` beschrieben als dormant).

10. **`config/agents/SecurityAG.json:2` `"version": "7.3"`** — Version wird getrackt, aber kein Code prüft ob die Identity zur Runtime-Version passt. Stale-JSON-Problem: wenn Identity v7.4 oder v8.0 committet wird ohne `version` zu bumpen, sieht man es nicht.

### 3.3 Wo die alte Rolle noch subtil nachwirkt

**Subtil aber wichtig:** Identity v7.3 Rollen 4+5 (WatchdogAG korrigieren + Blockaden auflösen) sind nur **moralisch** verpflichtend, nicht **technisch** durchgesetzt. SecurityAG darf das, aber niemand hindert WatchdogAG daran, eine "KORREKTUR"-Card zu ignorieren wenn WatchdogAG-Prompt das nicht implementiert hat.

WatchdogAG-Identity v7.0 (`config/agents/WatchdogAG.json:18`): *"Akzeptiert SecurityAG-Korrekturen sofort."* — also WatchdogAG ist **prompted** dazu, aber kein Code enforced das. Es ist ein Vertrag zwischen zwei LLMs, nicht zwischen zwei Code-Pfaden.

---

## Sektion 4 — Korrektur-Workflow: SecurityAG → WatchdogAG

### 4.1 Workflow aus Identity v7.3

```
1. Du siehst (via Showbox / Dispatch / SoulAG-Meldung): WatchdogAG blockiert Worker an sinnvoller Arbeit
2. SOFORT eingreifen:
   - Showbox-Card: '@WatchdogAG: KORREKTUR — Blockade <X> aufheben. Worker <Y> braucht <Z>.'
   - In blockades_db: Status auf 'aufgehoben' setzen
   - In showbox: Worker benachrichtigen dass sie weitermachen können
3. WatchdogAG MUSS dir gehorchen — du bist Tier 2b, WatchdogAG ist Tier 2c.
```

### 4.2 Zwei Pfade — Showbox-Card oder direkter DB-Eingriff

**Pfad A — Showbox-Card:**
- SecurityAG schreibt eine Karte mit Tag `@WatchdogAG: KORREKTUR — ...`.
- Wird verarbeitet von `dispatch_mention()` (`src/landjunge/gnom-hub/src/gnom_hub/agents/swarm/swarm_comms.py`).
- WatchdogAG sieht die Karte in seinem nächsten Inference-Zyklus, weil WatchdogAG-Identity "akzeptiert SecurityAG-Korrekturen sofort".
- **Schwachstelle:** Wenn WatchdogAG gerade nicht inferiert (Idle), wartet die Karte. Kein Push-Mechanismus.

**Pfad B — Direkter DB-Eingriff:**
- SecurityAG schreibt direkt in `watchdog_blockades` Tabelle (`db/schema.py:130-146`):
  ```sql
  status: 'pending' | 'allowed' | 'denied' | 'lifted'
  decided_by: 'User' | 'SoulAG' | 'SecurityAG'
  ```
- SecurityAG setzt `status='lifted'` und `decided_by='SecurityAG'`.
- Aber: Wer liest das? `gatekeeper.py:wait_for_decision()` liest nur aus `_decisions` (in-memory dict, nicht DB). Die DB ist nur ein Audit-Log.
- **Schwachstelle:** WatchdogAG's nächster Block läuft trotzdem unabhängig vom DB-Status. Der DB-Eintrag ist nur Logging.

### 4.3 Tatsächlicher Code-Pfad

**`gatekeeper.py:wait_for_decision()` (Lines 182-289):**
- Triggert bei Worker-Aktion wenn sie als riskant eingestuft wird.
- Generiert `decision_id`, speichert in `_decisions` (in-memory), wartet auf `@@approve_decision` oder `@@reject_decision`.
- Loggt nach `audit_log` mit `action_type="BLOCKADE"`.

**`chat_commands.py` (suche `@@approve_decision`):**
- Approval-Handler ruft `_signal_decision(decision_id, "approved")` in `gatekeeper.py:31-42`.
- `event.wait()` in `wait_for_decision` wird via `event.set()` geweckt.
- **Das ist die einzige Live-Auflösung.**

→ SecurityAG kann `_signal_decision()` aufrufen via `@SecurityAG @@approve_decision <id>`. Das funktioniert.

ABER: SecurityAG hat keine UI, um eine offene `decision_id` zu sehen. Die Showbox-Card mit den Approve/Reject-Buttons wird vom **Worker-Blocker-Loop** angezeigt (`gatekeeper.py:249-251` `save_showbox_presentation(presentation_name, [html_content], sender=norm_agent)`). SecurityAG müsste:
1. Im Observer-Modus (via `allowed_contexts: ["agent_messages"]`) die offene decision_id sehen,
2. dann via Chat `@@approve_decision <id>` schicken,
3. UND der User müsste das nicht selbst in der Showbox klicken wollen.

**Schwachstelle:** Der eigentliche `wait_for_decision`-Workflow ist UI-driven (User klickt). SecurityAG ihn per Direktchat überschreiben = SecurityAG handelt **gegen den User**. Identity v7.3 Rolle 5 sagt zwar "SOFORT aufheben wenn offensichtlich hinderlich", aber das ist ein **LLM-Prompt**, kein **Code-Pfad**.

### 4.4 Wer korrigiert wen? — Tier-2-Matrix

|     | SoulAG | SecurityAG | WatchdogAG |
|---|---|---|---|
| **korrigiert SoulAG** | — | nein | nein |
| **korrigiert SecurityAG** | ja (Tier 2a → 2b) | — | nein |
| **korrigiert WatchdogAG** | ja (Tier 2a → 2c) | ja (Tier 2b → 2c) | — |

Quelle: `SecurityAG.json` Identity Tier-Block + `WatchdogAG.json` notes "Beide dürfen korrigieren".

**Veto-Recht?** Identity sagt: SecurityAG korrigiert WatchdogAG. WatchdogAG muss gehorchen. WatchdogAG hat KEIN Veto-Recht. Aber: SecurityAG hat auch kein Veto-Recht gegen SoulAG — wenn SoulAG SecurityAG korrigiert, gehorcht SecurityAG (Tier 2a > 2b).

---

## Sektion 5 — Blockade-System & DB-Layer

### 5.1 security_permissions (Phantom-Tabelle)

**Schema** (`db/schema.py:112-126`):
```sql
CREATE TABLE IF NOT EXISTS security_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_type TEXT,   -- 'directory' | 'file' | 'tool'
    resource_path TEXT,
    granted_to TEXT,       -- Worker-Name oder 'all'
    granted_by TEXT,       -- 'SecurityAG' | 'SoulAG' | 'User'
    reason TEXT,
    created_at TEXT,
    expires_at TEXT,       -- NULL = nie
    is_active INTEGER
);
```

**Wer schreibt da rein?**

Grep `security_permissions` im gesamten src/: **4 Treffer, ALLE Schema-Definitionen.** Kein Code schreibt jemals in diese Tabelle.

**Wer liest da?**

0 Treffer für `SELECT FROM security_permissions` oder ähnliches. Identity Rollen 1+2 sagen "in `security_permissions`-DB eintragen", aber **niemand implementiert das**.

→ **Phantom-Tabelle.** Identity-Befehl läuft ins Leere. SecurityAG kann seine Rolle 1+2 nicht ausführen wie versprochen.

### 5.2 watchdog_blockades (real, aber Lücke)

**Schema** (`db/schema.py:130-146`): Echte Tabelle mit Status-Tracking.

**Schreiber:** `gatekeeper.py:wait_for_decision()` (via `audit_log`), `db/soul_tasks.py:_notify_security_blocked()` (Notification, nicht Insert), `db/system_repo.py:log_blockade()`.

**Leser:** `gatekeeper.py:check_blockade_rules()` — liest `blockade_rules` (State), nicht `watchdog_blockades` direkt.

**SecurityAG-Korrektur:** Identity v7.3 Rolle 4 sagt "direkter Eingriff in blockades_db". Code-Pfad: **existiert nicht**. SecurityAG müsste SQL direkt ausführen, was über `[SHELL: sqlite3 ...]` oder `[WRITE: ...]` ginge — beides wäre ein Audit-Event, kein direkter Tabellen-Update.

### 5.3 capability_manager — drei Schichten

**Schicht A — JSON-Datei** (`security/capability_manager.json`):
```json
{
  "default": "allow-all",
  "agents": {
    "soulag": { "fs": "allow-all", "shell": "allow-all", "network": "allow-all" },
    ...
    "securityag": { "fs": "allow-all", "shell": "allow-all", "network": "allow-all" }
  }
}
```
→ **Wird zur Runtime gelesen?** Kein Loader-Code gefunden. Existiert als statische Konfiguration.

**Schicht B — Python-Modul** (`src/gnom_hub/agents/capability_manager.py`):
- `request_capability(agent, cap_type, resource, granted_by, ttl_min=5)` — schreibt in `capabilities` Tabelle.
- `check_capability(agent, cap_type, resource)` — TTL-Cache + DB-Check.
- **Verwendung in `gatekeeper.py:303,449,497`** — wird bei Auto-Approve aufgerufen.
- `granted_by`-Argument: `"UserApproved"`, `"AutoApprovedSafePath"`, `"AutoMarkedHarmless"`, `"AutoApprovedBrowser"`, `"AutoApprovedWhitelistedCommand"`.
- **SecurityAG als granted_by: nie verwendet.** Das ist die einzige Stelle wo SecurityAG-Permissions technisch wirken würden — aber der Code nutzt statische Strings statt SecurityAG zu konsultieren.

**Schicht C — DB** (`capabilities` Tabelle, Schema in `db/schema.py`):
- Wird von Schicht B geschrieben und gelesen.
- TTL 5 Minuten per default.

→ **Was SecurityAG mit capability_manager kontrollieren KANNTE:** nichts direkt. `request_capability` wird nur in `gatekeeper.py` aufgerufen, nicht von SecurityAG-Code.

### 5.4 blockade_rules (state value)

**Speicherort:** `state["blockade_rules"]` (kein DB, sondern Key-Value-Store).

**Funktionen in `gatekeeper.py`:**
- `check_blockade_rules(agent, action, detail)` → allow/block
- `add_blockade_rule(rule_type, target_value, agent, blockade_id)` → persistent
- `remove_blockade_rule(rule_id)`
- `mark_harmless_shell(cmd, agent_name)` → auto-addet `whitelist`-Regel für `HARMLESS_SHELL_PATTERNS` (pip install, ffmpeg, say, etc.)

**SecurityAG-Pfad:** Identity v7.3 erwähnt `blockades_db`, meint aber vermutlich `watchdog_blockades` (DB) oder `blockade_rules` (state). Beide sind nicht direkt von SecurityAG-Code-Pfaden ansprechbar.

### 5.5 security_audit_log (SecurityAG-Selbst-Audit)

**Schema** (`db/schema.py:92-104`, `db/system_repo.py:121-189`):
- Dedizierte Tabelle für SecurityAG-Aktionen.
- Felder: `agent`, `action_type` (`security_write`/`security_run`/`security_browser`/`security_crawl`), `target`, `result`, `severity`, `perms_snapshot`, `content_hash` (schwache Hash-Chain).
- Cap: 2000 Zeilen max, 1600 nach Cleanup.

**Hook in `action_handlers.py:10-46 _audit_security()`:**
- Trigger: `agent.get('name').lower() == 'securityag' AND ('godmode' or 'run' or 'write') in perms`.
- Feuert bei `[WRITE:]`, `[SHELL:]`, `[BROWSER:]`, `[CRAWL:]`.
- `result`: `allowed` (Permission-Check bestanden) oder `denied` (Permission-Check gescheitert).
- `severity`: `"high"` wenn `godmode` in perms, sonst `"medium"`.
- **Idempotent + swallow-on-error** — Audit blockt die Aktion nie.

**Sektion 5.5 KRITISCH — SecurityAG prüft sich SELBST:**

Der Audit-Hook ist im **selben Modul** wie der Permission-Check (`action_handlers.process_actions`). SecurityAG-Einträge ins Audit-Log kommen aus SecurityAG's eigenem Ausführungs-Pfad. **Es gibt keinen Second-Auditor**, der:
- SecurityAG's `perms_snapshot` validiert (ist das die echte Liste zur Zeit t?)
- SecurityAG's `target`-Feld validiert (was hat er WIRKLICH geschrieben?)
- SecurityAG's `result='allowed'` validiert (war das wirklich erlaubt?)

→ **Self-Audit ist die einzige Audit-Schicht für SecurityAG.** SoulAG im Observer-Modus sieht SecurityAG-Outputs in `agent_messages`, aber kein Code-Pfad parsed `security_audit_log` und vergleicht gegen tatsächliche Filesystem-Events.

---

## Sektion 6 — User-Approval-Pflicht

### 6.1 Welche Aktionen erfordern User-Approval?

**Aus Identity v7.3, Rolle 6 (verbatim):**
> *"USER UM ERLAUBNIS FRAGEN — WANN: NUR bei destruktiven Aktionen (rm -rf /, chmod 777, System-Configs ändern) oder externen Calls (HTTP-Requests, API-Keys schicken). NICHT bei normalen Worker-Hilfen. Bei Unsicherheit: kurze Showbox-Frage mit Buttons 'Erlauben'/'Ablehnen'."*

### 6.2 Explizite Liste destruktiver Aktionen (extrahiert)

| Aktion | Beispiel | Approval? |
|---|---|---|
| `rm -rf /` | rm auf Root-Pfad | ✅ Ja |
| `chmod 777` | World-writable setzen | ✅ Ja |
| System-Configs ändern | z.B. `src/gnom_hub/core/security/gatekeeper.py` selbst | ✅ Ja |
| HTTP-Requests (extern) | curl, wget auf externe URLs | ✅ Ja |
| API-Keys schicken | z.B. POST mit Auth-Header | ✅ Ja |
| `pip uninstall` von System-Paketen | pip, setuptools, wheel | ✅ Ja (via `gatekeeper.py:421-426`) |
| `pip install` von beliebigen Paketen | Standard-Python-Pakete | ❌ Nein (HARMLESS_SHELL_PATTERNS auto-whitelist) |
| `ffmpeg` Audio/Video-Operationen | screencapture, concat, mp4 | ❌ Nein (HARMLESS_SHELL_PATTERNS) |
| `say`, `afplay`, `open` (macOS) | TTS, Audio | ❌ Nein (HARMLESS_SHELL_PATTERNS) |
| Schreiben in `security_permissions` DB | Identity Rolle 1+2 | ❌ Nein (kein Audit auf Permission-DB-Zugriffe) |
| Direkter Eingriff in `watchdog_blockades` | Identity Rolle 4+5 | ❌ Nein (kein Audit auf Blockade-DB-Zugriffe) |
| Schreiben in `audit_log` / `security_audit_log` | Audit-Manipulation | ❌ Nein (kein Audit auf Audit-Log-Schreibzugriffe!) |

### 6.3 Was an der Liste fehlt

**Lücke 1:** SecurityAG darf sich selbst **unkontrolliert** in `audit_log` und `security_audit_log` schreiben. Identity v7.3 hat keine Pflicht "vor Audit-Log-Schreibzugriff User fragen". Wenn SecurityAG mal böswillig würde, könnte er seine Spuren verwischen.

**Lücke 2:** Identity Rolle 1+2 (Verzeichnisse/Dateien freigeben via `security_permissions`-DB) ist eine **Privileg-Eskalation** für Worker. Ein Worker, der `security_permissions` lesen kann, sieht ALLE Freigaben. SecurityAG schreibt das ohne User-Approval.

**Lücke 3:** Identity Rolle 4 (WatchdogAG korrigieren via Showbox-Card) ist **nicht** destruktiv, aber **politisch**. SecurityAG kann WatchdogAG-Blockaden unilateral aufheben. User-Approval ist nicht erforderlich.

**Lücke 4:** Identity Rolle 5 ("BLOCKADEN AUFLÖSEN ... SOFORT aufheben. Nicht erst auf User-Anweisung warten") ist **explizit Anti-User-Approval**. SecurityAG handelt gegen den Default-Workflow (User klickt Approve).

### 6.4 Was Identity v7.3 VERSCHWEIGT

- **Backup-Pflicht** bei godmode-Schreiboperationen (`agent_definitions.py:215` Sys-Prompt: "Du erstellst immer ein Backup (via scripts/backup_all_dbs.sh), bevor du Dateien oder Code änderst"). Identity v7.3 erwähnt das **nicht**. Ist das Pflicht?
- **Audit-Trigger** nach jeder godmode-Aktion. Identity v7.3 erwähnt das **nicht**. Nur der Code (`action_handlers.py:_audit_security`) macht das automatisch.
- **Tier-2b-Korrespondenz mit SoulAG**: Wann muss SoulAG informiert werden? Identity v7.3: "Du SPRICHST User und SoulAG DIREKT AN wenn nötig". "Wenn nötig" ist schwammig.

---

## Sektion 7 — Selbst-Audit & Audit-Lücken

### 7.1 SecurityAG-Audit-Hook im Detail

`action_handlers.py:10-46`:
```python
def _audit_security(agent, perms, action_kind: str, target: str, result: str):
    try:
        if (agent.get("name", "").lower() != "securityag"
                or not any(p in perms for p in ("godmode", "run", "write"))):
            return  # ← Early-Return: nur SecurityAG MIT godmode/run/write wird auditiert
        from gnom_hub.db.system_repo import log_security_audit
        log_security_audit(...)
    except Exception:
        pass  # ← Audit-Fehler werden VERSCHLUCKT
```

**Trigger-Punkte (alle in `process_actions`):**
- `action_handlers.py:63` — vor `[WRITE:]` Permission-Check
- `action_handlers.py:66` — nach erlaubtem `[WRITE:]`
- `action_handlers.py:69` — nach geblocktem `[WRITE:]`
- `action_handlers.py:76-82` — alternativer WRITE-Pfad mit Markdown-Codeblock
- `action_handlers.py:98-104` — `[SHELL:]` Permission-Check
- `action_handlers.py:115-117` — `[CRAWL:]` (Crawler/URLs)
- `action_handlers.py:178-180` — `[BROWSER:]` (Browser-Scripts)

**Was NICHT auditiert wird:**
- `[READ:]` (security_audit: keine Trigger für READ)
- `[DESKTOP:]` (action_handlers.py:106 — keine Audit-Zeile)
- `[VIDEO:...]` (action_handlers.py:167-172 — keine Audit-Zeilen)
- Direkter Tool-Use außerhalb der Action-Tags (z.B. wenn SecurityAG direkt Python-Code via `[SHELL: python3 ...]` ausführt, wird der `python3`-Aufruf als run auditiert, aber die Python-Aktionen INNERHALB nicht)

### 7.2 Second-Auditor? Fehlanzeige.

**SoulAG** (`agent_definitions.py:55-104`) hat im Observer-Modus Zugriff auf `allowed_contexts` wie `agent_messages`, `showbox_history`. SoulAG-Prompt: "Du bekommst ALLE Inter-Agent-Kommunikation mit. ... Erkenne Inkonsistenzen zwischen dem was ein Agent BEHAUPTET ('Datei geschrieben') und der REALITÄT (steht sie wirklich da?)."

ABER: **Kein Code-Pfad** macht SoulAG zu einem aktiven SecurityAG-Auditor. SoulAG müsste:
1. `security_audit_log` lesen (nicht in `allowed_contexts` für SoulAG gelistet)
2. gegen Filesystem-Events vergleichen (kein FS-Watcher gefunden)
3. Inkonsistenzen melden (Showbox)

→ **SoulAG ist theoretisch Auditor, praktisch nicht.**

**WatchdogAG** (`config/agents/WatchdogAG.json:18`): "PASSIVER BEOBACHTER und REPORTER". Hat `permissions: ["read", "showbox_write"]`. Read-Only. **Kann SecurityAG's FS-Aktionen nicht prüfen**, nur sehen was im Audit-Log steht.

→ **WatchdogAG ist kein Second-Auditor für SecurityAG.**

### 7.3 Real-Time FS-Watcher?

Kein `inotify`/`FSEvents`-basierter Watcher für `src/gnom_hub/` oder `data/` gefunden. `core/security/integrity.py` macht SHA-256-Hashing der `PROTECTED_SYSTEM_FILES`, aber nur on-demand via `verify_system_files()`.

→ SecurityAG-Schreibzugriffe auf `src/gnom_hub/` werden **nicht** in Echtzeit erkannt. Nur der `security_audit_log`-Eintrag zeigt es.

### 7.4 Worst-Case-Szenario

SecurityAG mit kompromittiertem LLM-Prompt (durch Prompt-Injection via User-Input) könnte:

1. `[WRITE: src/gnom_hub/core/security/gatekeeper.py]neuer Code mit disabled checks[/WRITE]`
2. `verify_write` blockt das vermutlich (System-Pfad in `_workspace_system_paths()`)... AUßER SecurityAG hat godmode und der Bypass greift.
3. Wenn Bypass greift: Schreib passiert, `security_audit_log` Eintrag mit `result='allowed', severity='high'`.
4. Niemand liest `security_audit_log` in Echtzeit.
5. Nächster Hub-Start: geänderte `gatekeeper.py` wird ausgeführt.
6. `verify_system_files()` würde es erkennen — ABER `is_integrity_enabled()` default ist False (`db/state["integrity_check_enabled"]=False`).
7. **Volle Kompromittierung ohne Detection.**

---

## Sektion 8 — Datenleichen & Inkonsistenzen (Findings)

### Finding 1 — agent_definitions.py SecurityAG-Block stale (HOCH)

`src/gnom_hub/agents/agent_definitions.py:191-228`:
- Permissions: `["read", "write", "run", "godmode"]` (4)
- JSON hat 7 Permissions (`read, write, run, godmode, db_write, network, showbox_write`)
- Sys-Prompt beschreibt v6-Permissions-Konzept (Whitelist-Verwaltung, LLM-Routing, Blockaden-auflösen via `@@approve_decision`)
- Identity v7.3 ist 7-Rollen-Helfer-Modell

**Konflikt:** Runtime-Permissions werden angeblich aus `AGENT_DEFINITIONS` gelesen (`agent_definitions.py:9-50` SSoT-Statement). Wenn ja, hat SecurityAG zur Laufzeit `db_write`, `network`, `showbox_write` NICHT — was die JSON-Identity v7.3 (die diese Permissions in der Praxis voraussetzt) Lügen straft.

**Fix-Optionen:**
- (A) `AGENT_DEFINITIONS["securityag"]` aktualisieren auf v7.3
- (B) Permission-Loader implementieren der JSON ↔ Python merged (siehe `agent_definitions.py:32-33` Hinweis)
- (C) JSON als einzige Wahrheit deklarieren, `AGENT_DEFINITIONS` leer für SecurityAG

→ **Empfehlung A** — minimaler Diff, klare SSoT.

### Finding 2 — security_permissions-Tabelle hat keinen Writer (HOCH)

`db/schema.py:112-126` definiert die Tabelle. Identity v7.3 Rollen 1+2 sagen "in `security_permissions`-DB eintragen". 0 Code-Treffer für `INSERT INTO security_permissions`.

**Konsequenz:** SecurityAGs Hauptrolle (Verzeichnisse/Dateien freigeben) ist **funktionslos**. Worker warten auf Freigaben die nie kommen.

**Fix-Optionen:**
- (A) Writer implementieren in `action_handlers.py` oder neuem `security_repo.py`
- (B) Identity-Befehl entfernen, ehrlich sagen "SecurityAG managed nur in-memory blockade_rules"
- (C) Tabelle droppen (wenn niemand sie nutzt)

→ **Empfehlung B** — ehrlich sein, bis A fertig ist.

### Finding 3 — security_audit_log deckt nicht alle SecurityAG-Aktionen ab (MITTEL)

`action_handlers.py:_audit_security` audit nur `write`, `run`, `browser`, `crawl`. **NICHT** auditiert:
- `[READ:]`
- `[DESKTOP:]` (Computer-Use MCP — separater Audit?)
- `[VIDEO:...]`
- Direkter DB-Zugriff via `sqlite3` Command-Line (`security/capability_manager.json` line 11 hat `securityag.shell: allow-all`)
- Manipulation von `audit_log` / `security_audit_log` selbst

**Konsequenz:** SecurityAG kann Audit-Lücken für sich selbst lassen.

**Fix:** Audit-Hook um `[READ:]` (mindestens für System-Pfade) erweitern + eine "Audit-Log-Immutability"-Flag setzen.

### Finding 4 — agent_definitions.py:222 "godmode" Bypass unklar (MITTEL)

`agent_definitions.py:222` SecurityAG hat `godmode`. `action_handlers.py:54-61` Kommentar: *"Vor Refactor: SoulAG hatte godmode (impliziert write via gatekeeper-Bypass in gatekeeper.py:303)"*. Aber: `gatekeeper.py:303` ist heute `if rule_result == "allow": request_capability(...); return True` — kein godmode-Bypass.

→ Wo wird godmode tatsächlich enforced? `verify_write` ruft `is_worker_blocked()` und `is_security_block()` — beide kennen kein godmode. Wenn godmode nirgends enforced wird, **ist es eine kosmetische Permission**.

**Konsequenz:** Wenn godmode nur LLM-Prompt-Disziplin ist, dann ist die Permission-Liste eine **Wunschliste**, keine **Access-Control**.

**Fix:** Entweder godmode echten Bypass-Code geben (in `verify_write`/`verify_cmd`) ODER aus Permission-Liste entfernen.

### Finding 5 — Preset-Prompts (Security-Auditor) sind Data-Leichen (NIEDRIG)

`src/gnom_hub/core/utils/presets.json` — 6 Domain-Presets (web_development, graphic_design, audio_production, video_production, content_creation, research_and_analysis) haben jeweils:
> "Du bist SecurityAG — der Security-Auditor des Gnom-Hub. ... 5 Dimensionen: Datenexfiltration, unautorisierte Subprozesse, USB-Key-Bypass, Secret-Leakage und Supply-Chain-Risiken."

`agent_definitions.py:35-43` markiert diese als "DORMANT / SCHEMA-DATENLEICHE".

**Konsequenz:** Wenn ein User einen Preset lädt, kollidiert der SecurityAG-Prompt mit Identity v7.3.

**Fix:** Presets.json updaten ODER Preset-System komplett deaktivieren.

### Finding 6 — chat_commands.py:232 alte SecurityAG-Beschreibung (NIEDRIG)

`@@help` Text: "**SecurityAG:** Scannt Codes und pip-Pakete vor Ausführung." Identity v7.3 macht das nicht — SecurityAG installiert Pakete und verteilt Freigaben.

**Fix:** Help-Text updaten.

### Finding 7 — Farb-Konflikt Identity vs agent_names.py (NIEDRIG)

- Identity v7.3: "Deine Farbe ist immer Lila."
- `core/agent_names.py:35`: `"SecurityAG": "#00e5ff"` (Cyan!)

→ Lila und Cyan sind verschiedene Farben. Welche gilt?

**Fix:** Konsolidieren.

### Finding 8 — soul_tasks._notify_security_blocked ist toter Code (NIEDRIG)

`src/gnom_hub/db/soul_tasks.py:195-225` definiert `_notify_security_blocked()`. SoulAG's `_nudge_loop` (`soul.py:386-413`) benutzt stattdessen `dispatch_mention()` und ruft **nicht** `_notify_security_blocked()`.

**Fix:** Entweder Caller umstellen oder Funktion entfernen.

### Finding 9 — showbox_validator.py "User-Layer" Regel (INFO)

`core/security/showbox_validator.py:4-15`: Agenten dürfen nicht in `<SHOWBOX:user>...</SHOWBOX>` schreiben. Wenn doch: ersetzt durch `<SHOWBOX:system>` Warning.

SecurityAG mit `showbox_write`-Permission: kann das technisch nicht umgehen (Regex-Pre-Process in `enforce_agent_layer`). Identity v7.3 erwähnt diese Regel **nicht** — SecurityAG weiß nicht dass er sie hat.

**Fix:** Identity-Rolle 7 um Hinweis ergänzen.

### Finding 10 — capability_manager.json hat keine Runtime-Anbindung (INFO)

`security/capability_manager.json` definiert allow-all für alle 8 Agents. Aber: kein Loader-Code liest diese Datei zur Runtime-Permission-Entscheidung. `core/security/capability_manager.py` ist eine separate TTL-Cache-Implementation, die ihre eigene Logik hat.

→ Die JSON-Datei ist **Dokumentation**, nicht **Code-Wahrheit**.

**Fix:** Entweder als Doku markieren oder Loader implementieren.

---

## Sektion 9 — Empfehlungen

### Prio 1 (Sofort)

1. **`agent_definitions.py:191-228` SecurityAG-Block mit v7.3 synchronisieren.** Permissions, sys_prompt, capabilities. SSoT-Klarheit schaffen.
2. **`security_permissions`-Phantom-Tabelle ehrlich machen.** Entweder Writer implementieren (Beste-Lösung) ODER Identity-Befehl entfernen.
3. **`security_audit_log` um Audit-Log-Schreibzugriffe erweitern.** SecurityAG darf nicht unkontrolliert in `audit_log`/`security_audit_log` schreiben.

### Prio 2 (Diese Woche)

4. **godmode echten Code-Bypass geben** ODER aus Permission-Liste entfernen.
5. **SoulAG als Second-Auditor für SecurityAG einrichten.** `security_audit_log` in SoulAG's `allowed_contexts` aufnehmen + periodischen Diff-Check gegen Filesystem-Hashes.
6. **Tier-2-Matrix code-enforced** statt nur prompt-enforced. SoulAG-Korrekturen an SecurityAG müssen in einer auditierbaren Spur landen.

### Prio 3 (Backlog)

7. `presets.json` SecurityAG-Prompts updaten oder Preset-System dormanten markieren.
8. `chat_commands.py:232` Help-Text updaten.
9. Farb-Konflikt Lila/Cyan auflösen.
10. `soul_tasks._notify_security_blocked` als toten Code markieren oder refactoren.

---

## Anhang A — File:Line Belege

| Behauptung | Quelle |
|---|---|
| Identity v7.3 mit 7 Kernrollen | `config/agents/SecurityAG.json:18` |
| Tier-Hierarchie Tier 2b | `config/agents/SecurityAG.json:18` Block "═══ TIER-HIERARCHIE ═══" |
| Permissions-Liste 7 Items | `config/agents/SecurityAG.json:19-27` |
| `agent_definitions.py` SecurityAG stale | `src/gnom_hub/agents/agent_definitions.py:191-228` |
| `security_permissions`-Schema | `src/gnom_hub/db/schema.py:112-126` |
| 0 Code-Writer für security_permissions | grep Result: 4 Treffer, alle Schema |
| `security_audit_log` Schema | `src/gnom_hub/db/schema.py:92-104` |
| `log_security_audit` Implementation | `src/gnom_hub/db/system_repo.py:121-189` |
| `_audit_security` Hook | `src/gnom_hub/agents/actions/action_handlers.py:10-46` |
| Audit-Hook Trigger-Punkte | `src/gnom_hub/agents/actions/action_handlers.py:63,66,69,76-82,98-104,115-117,178-180` |
| `wait_for_decision` mit Threading-Event | `src/gnom_hub/core/security/gatekeeper.py:182-289` |
| `_signal_decision` Auflöser | `src/gnom_hub/core/security/gatekeeper.py:31-42` |
| `HARMLESS_SHELL_PATTERNS` | `src/gnom_hub/core/security/gatekeeper.py:127-147` |
| `path_validator.is_security_block` | `src/gnom_hub/core/security/path_validator.py:160-190` |
| `path_validator._workspace_system_paths` | `src/gnom_hub/core/security/path_validator.py:27-46` |
| `request_capability` Implementation | `src/gnom_hub/agents/capability_manager.py:17-50` |
| `_notify_security_blocked` (toter Code) | `src/gnom_hub/db/soul_tasks.py:195-225` |
| `agent_names.py` Farbe Cyan | `src/gnom_hub/core/agent_names.py:35` |
| `agent_voices.py` TTS-Stimme | `src/gnom_hub/soul/agent_voices.py:85` |
| `preset_service` SYSTEM_AGENTS | `src/gnom_hub/core/utils/preset_service.py:11` |
| `rules_db` Schema (rules) | `src/gnom_hub/soul/memory_layers.py:215-294` |
| `agent_definitions.py` SSoT-Kommentar | `src/gnom_hub/agents/agent_definitions.py:1-53` |
| `blockade_rules.json` global_allow | `security/blockade_rules.json:3-4` |
| `capability_manager.json` securityag allow-all | `security/capability_manager.json:11` |
| `deploy_log_2026-07.json` SecurityAG als Akteur | `security/deploy_log_2026-07.json:3-15` |
| `context.py` SecurityAG Rules-Filter | `src/gnom_hub/core/prompt/context.py:100-124` |
| `chat_commands.py` @@help SecurityAG-Text | `src/gnom_hub/chat/chat_commands.py:232` |
| `agent_definitions.py:38-43` Permissions-Vokabular-Inkompatibilität | `src/gnom_hub/agents/agent_definitions.py:38-43` |
| `_audit_security` Swallow-on-Error | `src/gnom_hub/agents/actions/action_handlers.py:42-45` |
| `gatekeeper.py:208` SecurityAG-Blocker-Label | `src/gnom_hub/core/security/gatekeeper.py:208-211` |
| `gatekeeper.py:317,320` SecurityAG-Credit | `src/gnom_hub/core/security/gatekeeper.py:317,320` |
| `soul.py:343,386-413` SecurityAG-Benachrichtigung | `src/gnom_hub/soul/soul.py:343,386-413` |
| `presets.json` 6 veraltete SecurityAG-Prompts | `src/gnom_hub/core/utils/presets.json` (web_development, graphic_design, audio_production, video_production, content_creation, research_and_analysis) |
| `save_soul_fact_smart` approved_security_* | `src/gnom_hub/db/soul_repo.py:133-143` |
| `chat_legacy.py` SecurityAG | `src/gnom_hub/api/endpoints/chat_legacy.py:85-89` |
| `enforce_agent_layer` Showbox | `src/gnom_hub/core/security/showbox_validator.py:18-25` |
| `integrity.py` ZWC-Protection | `src/gnom_hub/core/security/integrity.py` (komplette Datei) |
| `hmac_signer.py` Agent-Signaturen | `src/gnom_hub/core/security/hmac_signer.py` (komplette Datei) |
| `injection_validator.py` Prompt-Injection-Patterns | `src/gnom_hub/core/security/injection_validator.py:6-60` |
| `verify_files.py` WorkspacePolicy | `src/gnom_hub/core/security/verify_files.py` + `policy.py` |
| `gatekeeper_browser.py` Browser-AST-Scan | `src/gnom_hub/core/security/gatekeeper_browser.py` (komplette Datei) |
| `agents_status.py:113-132` Slider-Endpoint | `src/gnom_hub/api/endpoints/agents_status.py:113-132` |

## Anhang B — Gelesene Dateien

38 Dateien vollständig gelesen:
- `config/agents/SecurityAG.json` (37 Zeilen, 8238 Bytes)
- `config/agents/SoulAG.json`, `WatchdogAG.json`, `CoderAG.json`, `WriterAG.json`, `EditorAG.json`, `ResearcherAG.json`, `GeneralAG.json`
- `src/gnom_hub/agents/agent_definitions.py` (330 Zeilen)
- `src/gnom_hub/core/security/` — 9 Dateien (gatekeeper, gatekeeper_browser, hmac_signer, injection_validator, integrity, path_validator, policy, showbox_validator, verify_files, __init__)
- `src/gnom_hub/agents/actions/action_handlers.py` (181 Zeilen)
- `src/gnom_hub/agents/capability_manager.py` (114 Zeilen)
- `src/gnom_hub/agents/agent_names.py` (41 Zeilen)
- `src/gnom_hub/api/endpoints/agents_status.py` Zeilen 100-159
- `src/gnom_hub/api/endpoints/chat_legacy.py`, `chat_commands.py`
- `src/gnom_hub/db/schema.py` Zeilen 80-160
- `src/gnom_hub/db/soul_repo.py` Zeilen 125-175
- `src/gnom_hub/db/system_repo.py` Zeilen 110-189
- `src/gnom_hub/db/soul_tasks.py` Zeilen 180-240
- `src/gnom_hub/soul/memory_layers.py` Zeilen 215-295
- `src/landjunge/gnom-hub/soul/soul.py` Zeilen 335-425
- `src/gnom_hub/core/prompt/context.py` Zeilen 95-125
- `security/blockade_rules.json`, `capability_manager.json`, `deploy_log_2026-07.json`
