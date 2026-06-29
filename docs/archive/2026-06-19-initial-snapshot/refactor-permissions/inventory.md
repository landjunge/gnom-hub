# Inventory: Permission-Touchpoints in Gnom-Hub

**Schritt 1 der Agent-Permission-Refactor — Reine Bestandsaufnahme, keine Code-Änderungen.**

- **Working-Dir:** `/Users/landjunge/gnom-hub`
- **Datum:** 2026-06-21 03:03 (Europe/Berlin)
- **Branch/Commit:** working tree (kein git-repo laut User-Profile)
- **Methodik:** Statische Inspektion via `grep` + `Read` (Read-only)

> **Wichtigste Erkenntnis vorab:** Es existieren **zwei konkurrierende Permission-Vokabulare** im Codebase:
>
> 1. **Vocabulary A — AKTIV/RUNTIME:** Token-Liste (`read, write, run, godmode, desktop, crawl, evolve, web_search, browser, @job, @soul, @watchdog, @security, @code, @write, @research, @edit`) — hartcodiert in `agent_definitions.py` (16 Inline-Vorkommen), zur Laufzeit gelesen von `tool_registry.py`, `action_handlers.py`, `soul_initializer.py`, `router.py`, `agents_status.py`.
> 2. **Vocabulary B — DORMANT:** Schema `PermissionsConfig` (`preset_schema.py:308-314`) + befüllte Datei `data/presets/default/permissions.json` mit Tokens `read, write, exec, network, memory, admin`. Schema existiert, Loader validiert Keys — **aber kein einziger Runtime-Pfad liest diese Matrix für tatsächliche Permission-Entscheidungen.** Siehe Section 4 für Beleg.
>
> Für den Refactor heißt das: Vocabulary B ist die naheliegende Single-Source-of-Truth, aber die Migration muss die 16+ Runtime-Stellen in Vocabulary A entweder umstellen oder beide Vokabulare dauerhaft synchron halten.

---

## Section 1 — Grep-Rohausgaben

Alle Befehle wurden am 2026-06-21 03:03 in `/Users/landjunge/gnom-hub` ausgeführt. Output verbatim.

### 1.1 `grep -rn "godmode" src/gnom_hub/ --include="*.py" | head -50`

```
src/gnom_hub/agents/tool_registry.py:5:        "read_file": "Read files (also outside workspace with godmode)",
src/gnom_hub/agents/tool_registry.py:28:    if "godmode" in p or "run" in p: a += ["run_command", "sys_cmd", "screen_record", "video_merge", "video_edit"]
src/gnom_hub/agents/tool_registry.py:29:    if "godmode" in p: a += ["browser"]
src/gnom_hub/agents/tool_registry.py:38:    if "read_file" in t: syn += "\n  [READ: filename] — Read file (godmode: any absolute path)"
src/gnom_hub/agents/actions/action_handlers.py:11:    if "godmode" in perms and "run" not in perms: perms.append("run")
src/gnom_hub/agents/agent_definitions.py:33:            "permissions": ["read", "godmode", "evolve", "crawl"]
src/gnom_hub/agents/agent_definitions.py:38:            "permissions": ["read", "godmode", "evolve", "crawl"]
src/gnom_hub/agents/agent_definitions.py:83:            "permissions": ["read", "run", "godmode"]
src/gnom_hub/agents/agent_definitions.py:88:            "permissions": ["read", "run", "godmode"]
src/gnom_hub/agents/agent_definitions.py:99:            "Du hast godmode auf dem Dateisystem. "
src/gnom_hub/agents/agent_definitions.py:110:            "permissions": ["read", "write", "run", "godmode", "desktop", "crawl", "evolve"]
src/gnom_hub/agents/agent_definitions.py:115:            "permissions": ["read", "write", "run", "godmode", "desktop", "crawl", "evolve"]
src/gnom_hub/agents/agent_definitions.py:135:            "permissions": ["read", "write", "run", "godmode"]
src/gnom_hub/agents/agent_definitions.py:140:            "permissions": ["read", "write", "run", "godmode"]
src/gnom_hub/agents/agent_definitions.py:210:            "permissions": ["read", "write", "run", "godmode"]
src/gnom_hub/agents/agent_definitions.py:215:            "permissions": ["read", "write", "run", "godmode"]
```

**16 Treffer.** Davon **8 Inline-Permissionslisten** (8 Agents, je de+en) und **5 Runtime-Checks** in `tool_registry.py` + `action_handlers.py` + **1 sys_prompt-Erwähnung** in `agent_definitions.py:99`.

### 1.2 `grep -rn "capabilities" src/gnom_hub/agents/agent_definitions.py`

```
src/gnom_hub/agents/agent_definitions.py:10:        "capabilities": ["@soul"],
src/gnom_hub/agents/agent_definitions.py:45:        "capabilities": ["@job"],
src/gnom_hub/agents/agent_definitions.py:71:        "capabilities": ["@watchdog"],
src/gnom_hub/agents/agent_definitions.py:95:        "capabilities": ["@security"],
src/gnom_hub/agents/agent_definitions.py:122:        "capabilities": ["@code"],
src/gnom_hub/agents/agent_definitions.py:147:        "capabilities": ["@write"],
src/gnom_hub/agents/agent_definitions.py:172:        "capabilities": ["@research"],
src/gnom_hub/agents/agent_definitions.py:197:        "capabilities": ["@edit"],
```

**8 Treffer — exakt einer pro Agent.** Capabilities-Tokens sind **Role-Marker** (`@soul, @job, @watchdog, @security, @code, @write, @research, @edit`), nicht funktionale Capabilities. Ein Such-Query über `caps.get('run')` o.ä. liefert 0 Treffer (siehe 1.5).

### 1.3 `grep -rn "permissions" src/gnom_hub/ --include="*.py" | head -50`

```
src/gnom_hub/core/utils/test_agent_self_diagnosis.py:13:        permissions = ["read"] # No "write"
src/gnom_hub/core/utils/test_agent_self_diagnosis.py:15:        result = process_actions(ans, agent, permissions, False, "/tmp")
src/gnom_hub/core/utils/test_agent_self_diagnosis.py:25:            "permissions": ["read"], # No "write"
src/gnom_hub/core/preset_schema.py:309:    """``permissions.json`` — Berechtigungs-Matrix Agent → Capabilities."""
src/gnom_hub/core/preset_schema.py:344:    "permissions.json",
src/gnom_hub/core/preset_schema.py:369:    permissions: PermissionsConfig
src/gnom_hub/core/preset_loader.py:53:    "permissions": PermissionsConfig,
src/gnom_hub/core/preset_loader.py:195:        "permissions": bundle.permissions,
src/gnom_hub/core/preset_loader.py:269:      * ``permissions.json``-Keys müssen Union aus system+workers sein.
src/gnom_hub/core/preset_loader.py:302:    for agent_id in bundle.permissions.matrix.keys():
src/gnom_hub/core/preset_loader.py:305:                f"permissions.matrix hat unbekannten agent '{agent_id}'"
src/gnom_hub/chat/brainstorm/brainstorm_helpers.py:11:    soul = get_soul(ag["name"]) or {"role": ag.get('description', ''), "permissions": ["read"]}
src/gnom_hub/chat/brainstorm/brainstorm_helpers.py:28:        processed = process_actions(eo.content, ag, soul.get("permissions", []), bs_mode, wd)
src/gnom_hub/agents/agent_base.py:161:                    soul = get_soul(self.n) or {"permissions": ["read"]}
src/gnom_hub/agents/agent_base.py:162:                    perms = soul.get("permissions", [])
src/gnom_hub/agents/swarm/swarm_coordinator.py:106:    if gen: post(gen.name, process_actions(ans, {"name": gen.name}, (get_soul(gen.name) or {}).get("permissions", []), False, get_workspace_dir()))
src/gnom_hub/agents/tool_registry.py:4:    p, tm = soul.get("permissions", []), {
src/gnom_hub/agents/agent_definitions.py:33:            "permissions": ["read", "godmode", "evolve", "crawl"]
src/gnom_hub/agents/agent_definitions.py:38:            "permissions": ["read", "godmode", "evolve", "crawl"]
src/gnom_hub/agents/agent_definitions.py:59:            "permissions": ["read", "@job"]
src/gnom_hub/agents/agent_definitions.py:63:            "directive": "Conductor – pure orchestrator. Receives only from SoulAG, delegates only to the 4 workers. No write permissions. No communication with system agents. Color: Blue.",
src/gnom_hub/agents/agent_definitions.py:64:            "permissions": ["read", "@job"]
src/gnom_hub/agents/agent_definitions.py:83:            "permissions": ["read", "run", "godmode"]
src/gnom_hub/agents/agent_definitions.py:88:            "permissions": ["read", "run", "godmode"]
src/gnom_hub/agents/agent_definitions.py:110:            "permissions": ["read", "write", "run", "godmode", "desktop", "crawl", "evolve"]
src/gnom_hub/agents/agent_definitions.py:115:            "permissions": ["read", "write", "run", "godmode", "desktop", "crawl", "evolve"]
src/gnom_hub/agents/agent_definitions.py:160:            "permissions": ["read", "write", "crawl"]
src/gnom_hub/agents/agent_definitions.py:165:            "permissions": ["read", "write", "crawl"]
src/gnom_hub/agents/agent_definitions.py:185:            "permissions": ["read", "crawl", "web_search", "browser"]
src/gnom_hub/agents/agent_definitions.py:190:            "permissions": ["read", "crawl", "web_search", "browser"]
src/gnom_hub/agents/agent_definitions.py:210:            "permissions": ["read", "write", "run", "godmode"]
src/gnom_hub/agents/agent_definitions.py:215:            "permissions": ["read", "write", "run", "godmode"]
src/gnom_hub/api/endpoints/agents_status.py:287:    perm_soul = {"role": defn.get("role", "normal"), "permissions": lang_block.get("permissions", []),
src/gnom_hub/api/endpoints/agents_status.py:422:    """One-shot endpoint: permissions, tools, LLM routing, soul summary."""
src/gnom_hub/api/endpoints/agents_status.py:434:    permissions = lang_block.get("permissions", [])
src/gnom_hub/api/endpoints/agents_status.py:436:    soul = {"role": defn.get("role", "normal"), "permissions": permissions,
src/gnom_hub/api/endpoints/agents_status.py:474:        "permissions": permissions,
src/gnom_hub/soul/soul_initializer.py:44:    permissions = lang_data.get("permissions", ["read"])
src/gnom_hub/soul/soul_initializer.py:55:                if data.get("permissions") != permissions: data["permissions"] = permissions; dirty = True
src/gnom_hub/soul/soul_initializer.py:71:        "permissions": permissions,
src/gnom_hub/infrastructure/router/router.py:102:        perms = soul_data.get("permissions", [])
```

### 1.4 `grep -rln "AGENT_DEFINITIONS" src/gnom_hub/`

```
src/gnom_hub/core/utils/compiler.py
src/gnom_hub/core/utils/evolution_v2.py
src/gnom_hub/agents/agent_definitions.py
src/gnom_hub/db/schema.py
src/gnom_hub/api/endpoints/registry.py
src/gnom_hub/api/endpoints/agents_status.py
src/gnom_hub/api/app.py
src/gnom_hub/soul/soul_initializer.py
src/gnom_hub/soul/soul.py
src/gnom_hub/infrastructure/process/process_manager.py
src/gnom_hub/infrastructure/router/router.py
```

**11 .py-Dateien importieren `AGENT_DEFINITIONS`.** Davon permission-relevant: `soul_initializer.py:33`, `agents_status.py:285,432`, `router.py:58` (für Role-Lookup, nicht Permissions), `soul.py` (Soul-Loader), `evolution_v2.py` (Evolution-Regeln). Die anderen nutzen wahrscheinlich nur die `sys_prompt`/Slider-Werte.

### 1.5 `grep -rn "\"run\" in caps\|'run' in caps\|caps.get(.run.)\|in permissions" src/gnom_hub/ --include="*.py"`

```
(kein Output)
```

**Nicht gefunden.** Es gibt KEINE Variable namens `caps` im Codebase, die via `caps.get("run")` o.ä. abgefragt wird. Alle Capability-Checks arbeiten direkt auf der `permissions`-Liste (`if "run" in perms`, `if "godmode" in p`, `if "write" in perms`).

### 1.6 `grep -rn "\"write\" in caps\|'write' in caps" src/gnom_hub/ --include="*.py"`

```
(kein Output)
```

**Nicht gefunden** — bestätigt 1.5. Capabilities heißen im Code `permissions` (nicht `caps`).

### 1.7 `ls -la config/agents/`

```
total 64
drwxr-xr-x@ 10 landjunge  staff  320 Jun 19 01:28 .
drwxr-xr-x@  8 landjunge  staff  256 Jun 21 03:01 ..
-rw-r--r--@  1 landjunge  staff  562 Jun 19 01:28 CoderAG.json
-rw-r--r--@  1 landjunge  staff  563 Jun 19 01:28 EditorAG.json
-rw-r--r--@  1 landjunge  staff  563 Jun 19 01:28 GeneralAG.json
-rw-r--r--@  1 landjunge  staff  567 Jun 19 01:28 ResearcherAG.json
-rw-r--r--@  1 landjunge  staff  565 Jun 19 01:28 SecurityAG.json
-rw-r--r--@  1 landjunge  staff  560 Jun 19 01:28 SoulAG.json
-rw-r--r--@  1 landjunge  staff  565 Jun 19 01:28 WatchdogAG.json
-rw-r--r--@  1 landjunge  staff  563 Jun 19 01:28 WriterAG.json
```

**8 JSON-Dateien** — exakt einer pro Agent. Inhalt identisch (siehe Section 4).

### 1.8 `grep -rn "config/agents" src/gnom_hub/ --include="*.py"`

```
(kein Output)
```

**Nicht gefunden.** Keine `.py`-Datei referenziert den Pfad `config/agents/`. Die JSON-Dateien sind statisch und werden **nirgendwo zur Laufzeit gelesen**. Section 4 belegt: Inhalt ist nur Slider/Prompt-Blöcke (`creativity`, `precision`, `obedience` …) — keine Permissions.

### 1.9 `grep -rn "sys_role" src/gnom_hub/ --include="*.py" | head -20`

```
src/gnom_hub/db/agent_repo.py:85:    sys_roles = {"soul", "general", "watchdog", "security"}
src/gnom_hub/db/agent_repo.py:86:    is_sys = role in sys_roles
src/gnom_hub/db/agent_repo.py:90:        was_sys = existing["role"] in sys_roles
src/gnom_hub/db/agent_repo.py:93:    count = sum(1 for r in rows if (r["role"] in sys_roles) == is_sys and r["name"].lower() != name.lower())
```

**Eine einzige Datei** (`db/agent_repo.py`) definiert und nutzt `sys_roles`. Das Set ist hartcodiert: `{"soul", "general", "watchdog", "security"}`. Konsistent mit `agent_definitions.py`-Role-Feldern (siehe Section 2).

### 1.10 `grep -rn "audit_log" src/gnom_hub/ --include="*.py" | head -20`

```
src/gnom_hub/core/utils/compiler.py:202:        for tbl in ["audit_log", "explainable_outputs", "graceful_degradation_failures",
src/gnom_hub/db/system_repo.py:91:                    INSERT INTO audit_log (timestamp, agent, event_type, details, trace_id)
src/gnom_hub/db/system_repo.py:106:        n = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
src/gnom_hub/db/system_repo.py:109:                DELETE FROM audit_log
src/gnom_hub/db/system_repo.py:111:                    SELECT id FROM audit_log
src/gnom_hub/db/system_repo.py:117:        logger.error(f"[DB] audit_log cap failed: {e}")
src/gnom_hub/db/schema.py:51:CREATE TABLE IF NOT EXISTS audit_log (
src/gnom_hub/db/schema.py:139:CREATE INDEX IF NOT EXISTS idx_agent_event ON audit_log(agent, event_type);
src/gnom_hub/db/schema.py:140:CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp DESC);
src/gnom_hub/api/endpoints/metrics.py:23:def get_audit_log(agent: str = None, event: str = None, limit: int = 50):
src/gnom_hub/api/endpoints/metrics.py:26:            q = "SELECT * FROM audit_log"
src/gnom_hub/api/endpoints/admin_tools.py:156:    for tbl in ['chat','audit_log','prompt_versions','capabilities','showbox_presentations',
```

audit_log ist eine **echte SQLite-Tabelle** mit Schema (`db/schema.py:51-59`), Schreibpfad (`db/system_repo.py:86-97` via `log_audit_event`), Lesepfad (API `metrics.py:22-34`), Indizes und Cleanup. Siehe Section 5.

---

## Section 2 — 8-Agent-Aktuell-Tabelle

Quelle: `src/gnom_hub/agents/agent_definitions.py`, jeweils `capabilities` (Zeile N1) und `permissions` aus dem `de`-Block (Zeile N2). Englische `en`-Blöcke sind 1:1-Kopien der deutschen Permissions (siehe 1.3) — Ausnahme ist **keine**, daher nur die DE-Spalte.

| # | Agent (key) | Display-Name | Role | capabilities (Zeile) | permissions — `de`-Block (Zeile) | Datei:Zeile |
|---|---|---|---|---|---|---|
| 1 | `soulag` | SoulAG | `soul` | `["@soul"]` (10) | `["read", "godmode", "evolve", "crawl"]` (33) | `agent_definitions.py:6-40` |
| 2 | `generalag` | GeneralAG | `general` | `["@job"]` (45) | `["read", "@job"]` (59) | `agent_definitions.py:41-66` |
| 3 | `watchdogag` | WatchdogAG | `watchdog` | `["@watchdog"]` (71) | `["read", "run", "godmode"]` (83) | `agent_definitions.py:67-90` |
| 4 | `securityag` | SecurityAG | `security` | `["@security"]` (95) | `["read", "write", "run", "godmode", "desktop", "crawl", "evolve"]` (110) | `agent_definitions.py:91-117` |
| 5 | `coderag` | CoderAG | `coder` | `["@code"]` (122) | `["read", "write", "run", "godmode"]` (135) | `agent_definitions.py:118-142` |
| 6 | `writerag` | WriterAG | `writer` | `["@write"]` (147) | `["read", "write", "crawl"]` (160) | `agent_definitions.py:143-167` |
| 7 | `researcherag` | ResearcherAG | `researcher` | `["@research"]` (172) | `["read", "crawl", "web_search", "browser"]` (185) | `agent_definitions.py:168-192` |
| 8 | `editorag` | EditorAG | `editor` | `["@edit"]` (197) | `["read", "write", "run", "godmode"]` (210) | `agent_definitions.py:193-218` |

**Beobachtungen:**

- **Capabilities** sind reine Role-Marker (alle starten mit `@`), keine funktionalen Capabilities.
- **Permissions** sind Token-Strings (kein `@`-Prefix). `read` ist bei allen 8 Agents vorhanden. Nur **GeneralAG** hat kein `write` (Zeile 59, 64).
- **GeneralAG** hat `["read", "@job"]` — der `@job`-Token ist eine Permission, die laut `tool_registry.py:26` die `war_room_chat` + `create_agent`-Tools freischaltet. **Aber** der `permissions`-Check in `action_handlers.py:15,35` macht **keine Sonderbehandlung** für `@job` — d.h. `@job` wird zur Laufzeit NUR als Tool-Flag interpretiert, nicht als Schreib-/Run-Erlaubnis.
- **`godmode`** ist bei 6 von 8 Agents vorhanden (alle außer GeneralAG und ResearcherAG). ResearcherAG hat stattdessen `crawl + web_search + browser` für expliziten Web-Zugriff.
- **`desktop`** gibt's nur bei SecurityAG (Zeile 110, 115). Es schaltet `screenshot + desktop_action + browser + screen_record` frei (`tool_registry.py:30`).
- **`evolve`** haben nur SoulAG und SecurityAG — Self-Improvement ist explizit auf diese zwei beschränkt.
- Die `en`-Permissions (Zeilen 38, 64, 88, 115, 140, 165, 190, 215) sind **byte-genau identisch** mit den `de`-Permissions. Keine i18n-Abweichung im Permission-Vokabular.

---

## Section 3 — Touchpoint-Liste

Die 10 wichtigsten Stellen, die `permissions` lesen/schreiben — geordnet nach Refactor-Relevanz.

### TP-1: `src/gnom_hub/agents/agent_definitions.py:5-218` — Source of Truth

```python
  5: AGENT_DEFINITIONS = {
  6:     "soulag": {
  7:         "name": "SoulAG",
  8:         "description": "The Sovereign – sole user interface",
  9:         "role": "soul",
 10:         "capabilities": ["@soul"],
 ...
 30:         "de": {
 31:             "character": "Der Souverän",
 32:             "directive": "Souverän – einziger User-Ansprechpartner. ...",
 33:             "permissions": ["read", "godmode", "evolve", "crawl"]
 34:         },
```

**Warum refactor-relevant:** Dies ist die einzige Quelle für runtime-Permissions. Jede Änderung am Permission-Vokabular (Schritt 2+3 des Refactors) MUSS hier anfangen. Wenn die `data/presets/default/permissions.json` zur Single-Source-of-Truth wird, muss `agent_definitions.py` sie konsumieren (z.B. via `soul_initializer.py`-Pattern).

### TP-2: `src/gnom_hub/soul/soul_initializer.py:30-81` — Persistente Soul-Mirror

```python
 30: def get_soul(agent_name: str) -> dict:
 31:     import os, json
 32:     from gnom_hub.db import get_language
 33:     from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
 34:
 35:     lang = get_language()
 36:     name_lower = agent_name.lower()
 37:
 38:     default_def = AGENT_DEFINITIONS.get(name_lower, {})
 39:     role = default_def.get("role", "default")
 40:
 41:     lang_data = default_def.get(lang, default_def.get("de", {}))
 42:     character = lang_data.get("character", "Agent")
 43:     directive = lang_data.get("directive", "Hilf dem Schwarm." if lang == "de" else "Help the swarm.")
 44:     permissions = lang_data.get("permissions", ["read"])
 45:
 46:     path = get_agent_soul_path(agent_name)
 47:     if os.path.exists(path):
 48:         try:
 49:             with open(path, "r", encoding="utf-8") as f:
 50:                 data = json.load(f)
 ...
 55:                 if data.get("permissions") != permissions: data["permissions"] = permissions; dirty = True
 ...
 67:     default_soul = {
 68:         "role": role,
 69:         "character": character,
 70:         "directive": directive,
 71:         "permissions": permissions,
 72:         "breakpoints": []
 73:     }
```

**Warum refactor-relevant:** `get_soul()` ist der **primäre Runtime-Zugriffspunkt** für Permissions — alle 6 anderen TP-Stellen (TP-3 bis TP-8) rufen `get_soul(name)` auf und lesen `.get("permissions", [])`. Die Funktion spiegelt Permissions persistent nach `<workspace>/.agents/<name>/soul.json` und committed per Git (Zeile 9-28). Refactor-Risiko: Wenn `agent_definitions.py` die Werte ändert, werden alle bestehenden soul.json-Files überschrieben (Zeile 55).

### TP-3: `src/gnom_hub/agents/tool_registry.py:1-32` — Tool-Vergabe nach Permission

```python
  1: def get_tools_for_agent(soul: dict):
  2:     if soul.get("role") == "general":
  3:         return {}
  4:     p, tm = soul.get("permissions", []), {
  5:         "read_file": "Read files (also outside workspace with godmode)",
  6:         "write_file": "Write files",
 ...
 24:     # ── DAUERHAFT FREIGESCHALTET für ALLE Agenten ──
 25:     a = ["read_file", "web_search", "crawl_url"]
 26:     if "@job" in p: a += ["war_room_chat", "create_agent"]
 27:     if "write" in p: a += ["write_file", "generate_image"]
 28:     if "godmode" in p or "run" in p: a += ["run_command", "sys_cmd", "screen_record", "video_merge", "video_edit"]
 29:     if "godmode" in p: a += ["browser"]
 30:     if "desktop" in p: a += ["screenshot", "desktop_action", "browser", "screen_record"]
 31:     if "evolve" in p: a += ["evolve"]
 32:     return {t: tm.get(t, t) for t in dict.fromkeys(a)}
```

**Warum refactor-relevant:** **GeneralAG-Hardcode** (Zeile 2-3) gibt GeneralAG ein leeres Tool-Set, BEVOR die Permission-Logik greift — das ist eine Spezialregel. Wenn das neue Vokabular ein "Orchestrator"-Bit hat, muss diese Sonderbehandlung ggf. erhalten bleiben. Die Permission-zu-Tool-Mapping-Tabelle (Zeile 25-31) muss 1:1 in die neue Welt übersetzt werden, sonst verlieren Agents Tools (oder bekommen welche, die sie nicht haben sollten).

### TP-4: `src/gnom_hub/agents/actions/action_handlers.py:9-11` — Permission-Inferenz

```python
  9: def process_actions(ans, agent, perms, bs_mode, wd):
 10:     perms = list(perms)
 11:     if "godmode" in perms and "run" not in perms: perms.append("run")
```

**Warum refactor-relevant:** **Implizite Auto-Erweiterung**: Wenn ein Agent `godmode` aber nicht `run` hat, wird `run` automatisch hinzugefügt. Heute hat jeder Agent mit `godmode` (siehe 1.1) **bereits** auch `run` in der Liste, daher ist diese Inferenz ein **No-Op** für die aktuelle Konfiguration. Trotzdem: Wenn der Refactor Permission-Vokabulare ändert, könnte diese Inferenz-Regel brechen oder doppelte Wirkung entfalten.

### TP-5: `src/gnom_hub/infrastructure/router/router.py:88-117` — Permissions landen im System-Prompt

```python
 88: def _build_sys(n, sys, agent_name):
 89:     """Inject slider config + evolution rules into system prompt."""
 ...
  96:         from gnom_hub.core.utils.slider_prompt import build_system_prompt
  97:         from gnom_hub.agents.tool_registry import get_tools_for_agent as _tf
  98:         from gnom_hub.soul import get_soul as _gs
  99:
 100:         # Tools-Block bauen
 101:         soul_data = _gs(agent_name) or {}
 102:         perms = soul_data.get("permissions", [])
 103:         perms_str = ", ".join(perms) if perms else "read, write, run"
 104:
 105:         # Security-Block
 106:         sec = "Systemdateien+Gefährliche Patterns geblockt. Shell via Whitelist."
 ...
 111:         sys = build_system_prompt(
 112:             agent_identity_block=sys,
 113:             agent_name=agent_name or "Agent",
 114:             soul_facts=soul_facts,
 115:             agent_tools_block=f"Perms: {perms_str}",
 116:             agent_security_block=sec,
 117:         )
```

**Warum refactor-relevant:** Die Permission-Liste wird **als String ins LLM-System-Prompt** geschrieben (`agent_tools_block=f"Perms: {perms_str}"`). Wenn das neue Vokabular längere Tokens hat (z.B. `network` statt `crawl`) oder eine andere Struktur (Bitfeld, JSON), muss `perms_str` neu generiert werden. Außerdem: Default-Fallback `"read, write, run"` (Zeile 103) — wenn `perms` leer ist, bekommt der LLM die **Maximalrechte** suggeriert. Security-relevant.

### TP-6: `src/gnom_hub/agents/agent_base.py:160-163` — Worker-Pfad: get_soul → process_actions

```python
158:                     processed = ""
159:                     if r.content and not r.content.startswith("[ROUTER-FEHLER]"):
160:                         from gnom_hub.agents.actions.action_handlers import process_actions
161:                         soul = get_soul(self.n) or {"permissions": ["read"]}
162:                         perms = soul.get("permissions", [])
163:                         processed = await _to_thread(process_actions, r.content, {"name": self.n}, perms, False, wd)
```

**Warum refactor-relevant:** **Worker-Pfad** für alle 4 Worker (CoderAG, WriterAG, ResearcherAG, EditorAG). Liest Permissions aus Soul, übergibt an `process_actions` (das TP-4-Inferenz + Gatekeeper macht). Fallback `["read"]` ist sicher — kein Default-Elevation wie in TP-5.

### TP-7: `src/gnom_hub/chat/brainstorm/brainstorm_helpers.py:11,28` — Brainstorm-Pfad

```python
  9: def ask_llm(ag, q, ctx, bs_mode=False, depth=0):
 10:     from gnom_hub.agents.tool_registry import format_tools_prompt; from gnom_hub.soul import get_soul; from gnom_hub.agents.actions.action_handlers import process_actions; from gnom_hub.db import set_agent_status, update_agent_active_job
 11:     soul = get_soul(ag["name"]) or {"role": ag.get('description', ''), "permissions": ["read"]}
 12:     sys = format_tools_prompt(soul, ag["name"])
 ...
 26:     eo = ask_router(u_msg, sys, agent_name=ag.get("name", ""), depth=depth)
 27:     if not eo.content: return post(ag["name"], f"[Fehler: Keine Antwort vom LLM]", depth=depth)
 28:     processed = process_actions(eo.content, ag, soul.get("permissions", []), bs_mode, wd)
```

**Warum refactor-relevant:** Brainstorm-Modus (Debatte/Roundtable). **Wichtig:** Zeile 17 setzt im Brainstorm-Modus zusätzlich `[MODUS: BRAINSTORM — ... [WRITE:] und [SHELL:] sind erlaubt.]` ins System-Prompt, **unabhängig von Permissions**. Das ist ein **Override-Pfad** — Permissions werden umgangen, wenn `bs_mode=True`. Refactor-Risiko: Wenn der Modus dokumentierter werden soll, ist das eine zweite Permission-Schiene.

### TP-8: `src/gnom_hub/agents/swarm/swarm_coordinator.py:106` — Team-Workflow-Pfad

```python
102: def _eval(ar, task, history):
103:     sys_p = "Du bist GeneralAG. Führe Ergebnisse des Team-Workflows zusammen. ..."
104:     ans = _llm(sys_p, f"Hauptaufgabe: {task}\n\nWorker-Ergebnisse:\n{history}")
105:     gen = next((a for a in ar.get_all() if a.role == "general" or a.name.lower() == "generalag"), None)
106:     if gen: post(gen.name, process_actions(ans, {"name": gen.name}, (get_soul(gen.name) or {}).get("permissions", []), False, get_workspace_dir()))
```

**Warum refactor-relevant:** **GeneralAG schreibt am Ende des Team-Workflows** — aber GeneralAG hat nur `["read", "@job"]`. `@job` schaltet nur `war_room_chat + create_agent` frei (`tool_registry.py:26`), kein `write_file`. Wenn GeneralAG per `[WRITE:]` etwas persistieren will, **schlägt process_actions das mit `[System: ... keine Schreibberechtigung.]`**. Security-Korrekt, aber Refactor-Überlegung: Soll Team-Workflow-Output speziell behandelt werden?

### TP-9: `src/gnom_hub/api/endpoints/agents_status.py:285-290, 432-448` — API-Oberfläche

```python
285:     defn = AGENT_DEFINITIONS.get(key, {})
286:     lang_block = defn.get("de") or defn.get("en") or {}
287:     perm_soul = {"role": defn.get("role", "normal"), "permissions": lang_block.get("permissions", []),
288:                  "character": "", "directive": ""}
289:     def_tools = list(get_tools_for_agent(perm_soul).keys())
```

```python
420: @router.get("/api/agents/{a_id}/profile")
421: def get_agent_profile(a_id: str):
422:     """One-shot endpoint: permissions, tools, LLM routing, soul summary."""
423:     from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
 ...
 432:     defn = AGENT_DEFINITIONS.get(key, {})
 433:     lang_block = defn.get("de") or defn.get("en") or {}
 434:     permissions = lang_block.get("permissions", [])
 435:     # Build soul dict for tool_registry (mirrors what agent_base uses)
 436:     soul = {"role": defn.get("role", "normal"), "permissions": permissions,
 437:             "character": lang_block.get("character", ""), "directive": lang_block.get("directive", "")}
 438:     tools = list(get_tools_for_agent(soul).keys())
```

```python
471:     return {
472:         "name": agent.name,
473:         "role": defn.get("role", agent.role or "normal"),
474:         "permissions": permissions,
475:         "tools": tools,
476:         "llm_provider": llm_provider,
477:         "llm_model": llm_model,
478:         "soul_fact_count": total,
479:         "top_soul_facts": top_facts,
```

**Warum refactor-relevant:** API-Endpoints `/api/agents/{id}/profile` (Zeile 420) und `/api/agents/{id}/tools/toggle` (Zeile 280) exposen Permissions + Tools im JSON-Response. Wenn das neue Vokabular eingeführt wird, **müssen die API-Felder weiterhin stabil bleiben** (oder migriert werden) — sonst bricht das Frontend.

### TP-10: `src/gnom_hub/core/security/gatekeeper.py:291,436` — Verify-Funktionen

```python
291: def verify_write(agent, fn, content, wd, perms) -> bool:
292:     """
293:     Risikobasierte Prüfung vor Schreibaktionen.
294:     - Benutzerregeln (whitelist/block) haben Vorfahrt
295:     - Workspace-Dateien → Auto-Approve
296:     - System-Dateien (src/gnom_hub, config/, .env, ...) → Hard Block
297:     - Hochriskante Code-Patterns → Hard Block
298:     - Mittelriskante Code-Patterns → Warning (log + allow)
299:     """
300:     name = (agent or {}).get("name", "Unknown")
301:
302:     # SoulAG darf Dateien schreiben (User erlaubt)
303:     if name.lower() == "soulag":
304:         pass
 ...
307:     rule_result = check_blockade_rules(name, "WRITE", fn)
 ...
315:     if is_worker_blocked(agent, fn, wd, perms):
316:         log_blockade(name, "WRITE", fn, f"System-Pfad blockiert: {fn}", "blocked", "PathValidator")
317:         return False
 ...
```

```python
436: def verify_cmd(agent, cmd):
437:     """
438:     Nicht-blockierende Prüfung vor Shell-Befehlen.
439:     - Benutzerregeln (whitelist/block) haben Vorfahrt
440:     - GeneralAG (role=general): KEINE Shell-Befehle erlaubt
441:     - Whitelist-Prüfung (erlaubte Befehle)
442:     - System-Pfad-Schutz (kein Zugriff auf src/gnom_hub, config/, .env, ...)
443:     - Keine Warte-Dialoge.
444:     """
445:     name = (agent or {}).get("name", "Unknown")
446:     role = (agent or {}).get("role", "")
447:
448:     # SoulAG darf Shell-Befehle ausführen (User erlaubt)
449:     if name.lower() == "soulag":
450:         pass
```

**Warum refactor-relevant — WICHTIG:** Die `verify_write` und `verify_cmd` sind die **eigentliche Sicherheitslinie** — sie haben **zwei Hardcoded-Ausnahmen** (SoulAG, Zeile 303/449; GeneralAG, Zeile 440-Doc). Sie konsumieren das `perms`-Argument, geben es aber an `is_worker_blocked(agent, fn, wd, perms)` weiter — die detaillierte Permission-Logik lebt in `path_validator.py` und `policy.py`. Refactor-Relevanz: Diese Hardcodes (SoulAG-Pass + GeneralAG-Deny) müssen mitwandern, wenn sich Rollen-Namen oder das Role-Vokabular ändern.

### TP-11 (Bonus): `src/gnom_hub/db/agent_repo.py:82-97` — sys_role-Liste

```python
 82: def validate_agent_limit_db(conn, role: str, name: str) -> bool:
 83:     if is_testing():
 84:         return True
 85:     sys_roles = {"soul", "general", "watchdog", "security"}
 86:     is_sys = role in sys_roles
 87:     rows = conn.execute("SELECT name, role FROM agents").fetchall()
 88:     existing = next((r for r in rows if r["name"].lower() == name.lower()), None)
 89:     if existing:
 90:         was_sys = existing["role"] in sys_roles
 91:         if was_sys == is_sys:
 92:             return True
 93:     count = sum(1 for r in rows if (r["role"] in sys_roles) == is_sys and r["name"].lower() != name.lower())
 94:     if count >= 4:
 95:         from gnom_hub.core.exceptions import ValidationError
 96:         raise ValidationError(f"Limit von 4 {'System' if is_sys else 'Worker'}-Agenten überschritten.")
```

**Warum refactor-relevant:** Set `{"soul", "general", "watchdog", "security"}` ist die **4-System-Rollen-Konstante** (siehe konsistent mit Section 2 Roles). Wenn das Refactor die Role-Namen ändert (z.B. `security` → `admin`), MUSS dieses Set mitgeändert werden, sonst bricht die Limit-Validierung.

---

## Section 4 — Konfigurationsdateien

### 4.1 `config/agents/*.json` — 8 statische Dateien, **NIRGENDS gelesen**

Existenz belegt (1.7). Vollinhalt **aller 8 Dateien** ist **identisch bis auf das `agent`-Feld**:

```json
{
  "agent": "SoulAG",        // ← variiert pro Datei (CoderAG, EditorAG, ...)
  "version": "3.0",
  "sliders": {
    "creativity": 2,
    "precision": 2,
    "speed": 2,
    "critical_thinking": 2,
    "obedience": 2
  },
  "prompt_blocks": {
    "creativity": "Balance standard approaches with occasional creative solutions.",
    "precision": "Balanced accuracy. Verify main outputs.",
    "speed": "Steady pace. Deliver when ready.",
    "critical_thinking": "Think about the task. Suggest obvious improvements.",
    "obedience": "Follow instructions with reasonable interpretation. Small adjustments OK."
  }
}
```

Quelle: Read auf `SoulAG.json` (18 Zeilen), `SecurityAG.json`, `CoderAG.json`, `GeneralAG.json`, `ResearcherAG.json`, `WriterAG.json`, `WatchdogAG.json`, `EditorAG.json`. **Keine der Dateien enthält `permissions` oder `capabilities` als Feld.**

**Wer liest diese Dateien?** Belegt durch 1.8: **`grep -rn "config/agents" src/gnom_hub/ --include="*.py"` liefert 0 Treffer.** Die Dateien sind statisch und werden **nicht** zur Laufzeit konsumiert. Sie sind offensichtlich ein älteres Konfig-Format (oder für die UI gedacht, die einen anderen Loader hat).

### 4.2 `data/presets/default/permissions.json` — Befüllt, aber DORMANT

Existenz und Inhalt (Read am 2026-06-21 03:03):

```json
{
  "description": "Berechtigungs-Matrix für alle 8 Agenten. Capabilities: read, write, exec, network, memory, admin.",
  "matrix": {
    "SoulAG": ["read", "write", "memory", "network"],
    "WatchdogAG": ["read", "write", "exec", "network", "memory"],
    "GeneralAG": ["read", "network", "memory"],
    "SecurityAG": ["read", "write", "exec", "network", "memory", "admin"],
    "WriterAG": ["read", "write", "network"],
    "CoderAG": ["read", "write", "exec", "network"],
    "ResearcherAG": ["read", "exec", "network", "memory"],
    "EditorAG": ["read", "write", "network"]
  }
}
```

Datei: `/Users/landjunge/gnom-hub/data/presets/default/permissions.json` (586 Bytes).

**Schema-Definition:**

```python
308: class PermissionsConfig(BaseModel):
309:     """``permissions.json`` — Berechtigungs-Matrix Agent → Capabilities."""
310:
311:     model_config = ConfigDict(extra="allow")
312:
313:     matrix: dict[str, list[str]] = Field(default_factory=dict)
314:     description: str = Field(default="")
```
(Quelle: `src/gnom_hub/core/preset_schema.py:308-314`)

**Wer liest diese Datei?**

- `preset_loader.py:195` — schreibt die Matrix zurück auf Disk (`"permissions": bundle.permissions,`)
- `preset_loader.py:302-305` — validiert, dass alle Matrix-Keys in `bundle.all_agent_ids` enthalten sind (Cross-File-Validierung)
- `preset_loader.py:53` — registriert `PermissionsConfig` im Bundle-Schema
- `preset_loader.py:269` — Doku-Kommentar: `permissions.json-Keys müssen Union aus system+workers sein.`

**Was passiert zur Laufzeit damit?** Belegt durch:
```
grep -rn "permissions.matrix\|bundle.permissions\|preset.permissions" src/gnom_hub/ --include="*.py"
→ src/gnom_hub/core/preset_loader.py:195
→ src/gnom_hub/core/preset_loader.py:302
→ src/gnom_hub/core/preset_loader.py:305
```

Die drei Treffer sind **alle im Loader selbst** (Schreiben + Validieren). Kein einziger Runtime-Pfad — weder `agent_base.py`, `tool_registry.py`, `action_handlers.py`, `router.py`, `brainstorm_helpers.py`, `swarm_coordinator.py`, `agents_status.py` — liest `permissions.matrix` für tatsächliche Permission-Entscheidungen.

`get_preset_prompt()` in `src/gnom_hub/core/utils/preset_service.py:23` ist die einzige Runtime-Funktion, die Preset-Daten liest — sie greift aber nur auf das `prompt`-Feld pro Agent zu, nicht auf `permissions`. (`grep -rn "permissions" /Users/landjunge/gnom-hub/data/presets/` lieferte 0 Treffer in den anderen Preset-Dateien.)

### 4.3 Befund: Zwei-Vokabular-Konflikt

| Aspekt | Vocabulary A (`agent_definitions.py`) | Vocabulary B (`permissions.json`) |
|---|---|---|
| Datei | `src/gnom_hub/agents/agent_definitions.py` | `data/presets/default/permissions.json` |
| Schema | inline Python-Dict | `preset_schema.py:308` + `preset_loader.py:53` |
| Tokens | `read, write, run, godmode, desktop, crawl, evolve, web_search, browser, @job` | `read, write, exec, network, memory, admin` |
| Runtime gelesen? | **JA** (6+ Stellen) | **NEIN** (nur Schema-Validation) |
| Persistenz | pro Agent: `<workspace>/.agents/<name>/soul.json` (via `soul_initializer.py:46-79`) | pro Preset: `data/presets/<id>/permissions.json` (via `preset_loader.py:195`) |

**Schlüsselbefund für den Refactor:** Vocabulary B ist die **zukünftige Single-Source-of-Truth**, existiert aber als reine Schema-Datenleiche ohne Runtime-Anbindung. Vocabulary A funktioniert, ist aber hartcodiert und nur über `soul_initializer.py` mutationsfähig (was bei Agent-Death wieder auf Defaults zurücksetzt). Der Refactor muss entscheiden: (a) beide synchron halten, (b) Vocabulary A durch Vocabulary B ersetzen und alle 6 Runtime-Stellen umstellen, oder (c) eine Mapping-Tabelle zwischen den Vokabularen definieren.

---

## Section 5 — Audit-Log-Status

### 5.1 Schema existiert

```sql
51: CREATE TABLE IF NOT EXISTS audit_log (
52:     id INTEGER PRIMARY KEY AUTOINCREMENT,
53:     timestamp TEXT NOT NULL,
54:     agent TEXT NOT NULL,
55:     event_type TEXT NOT NULL,
56:     details TEXT NOT NULL,
57:     trace_id TEXT,
58:     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
59: );
```
(Quelle: `src/gnom_hub/db/schema.py:51-59`)

```sql
139: CREATE INDEX IF NOT EXISTS idx_agent_event ON audit_log(agent, event_type);
140: CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp DESC);
```
(Quelle: `src/gnom_hub/db/schema.py:139-140`)

### 5.2 Schreibpfad: `db/system_repo.py:86-97`

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

**Cap-Mechanismus:** `AUDIT_LOG_MAX_ROWS = 1000`, `AUDIT_LOG_KEEP_ROWS = 800` (`system_repo.py:100-101`). Älteste Einträge werden abgeschnitten, sobald > 1000 Rows.

### 5.3 Wer ruft `log_audit_event` auf?

Belegt durch `grep -rn "log_audit_event" src/gnom_hub/`:

| Datei:Zeile | Event-Type | Wann? |
|---|---|---|
| `db/system_repo.py:86` | (Definition) | — |
| `db/__init__.py:7`, `db/legacy_db.py:12` | (Re-Export) | — |
| `agents/specialization_monitor.py:36` | (via `log_audit_event(...)`) | Specialization-Tracking |
| `core/utils/pvm_activate.py:12` | `"prompt_activated"` | Prompt-Version aktiviert |
| `core/utils/gd_fallback.py:33` | `"degradation_fallback"` | Graceful-Degradation |
| `core/utils/evolution_v2.py:156,182` | (Evolution-Events) | Agent-Evolution |
| `core/utils/pvm_rollback.py:12` | `"prompt_auto_rollback"` | Prompt-Rollback |
| `core/structured_log.py:24` | (allgemein via `AgentLogger`) | Strukturierte Logs |

**Total: 6 produktive Aufrufer** in src/gnom_hub (exklusive Re-Exports).

### 5.4 Lesepfad: API

```python
22: @router.get("/api/audit-log")
23: def get_audit_log(agent: str = None, event: str = None, limit: int = 50):
24:     try:
25:         with get_db_conn() as conn:
26:             q = "SELECT * FROM audit_log"
27:             conds, args = [], []
28:             if agent: conds.append("agent = ?"); args.append(agent)
29:             if event: conds.append("event_type = ?"); args.append(event)
30:             if conds: q += " WHERE " + " AND ".join(conds)
31:             q += " ORDER BY timestamp DESC LIMIT ?"
32:             args.append(limit)
33:             return [dict(r) for r in conn.execute(q, args).fetchall()]
34:     except sqlite3.Error: return []
```
(Quelle: `src/gnom_hub/api/endpoints/metrics.py:22-34`)

### 5.5 Cleanup-Pfad

```python
156:     for tbl in ['chat','audit_log','prompt_versions','capabilities','showbox_presentations',
157:                 'explainable_outputs','agent_messages','swarm_callbacks','agent_capabilities',
158:                 'workflows','workflow_tasks','token_budget_logs','token_budget_alerts']:
159:         try: conn.execute(f'DELETE FROM {tbl}')
```
(Quelle: `src/gnom_hub/api/endpoints/admin_tools.py:156-158`)

`compiler.py:202` listet `audit_log` ebenfalls in einer Cleanup-Liste (für State-Reset).

### 5.6 SecurityAG-spezifisches Audit-Logging

**Existiert NICHT als dedizierter Pfad.** SecurityAG (Role=`security`) ist ein LLM-Agent mit `permissions=["read", "write", "run", "godmode", "desktop", "crawl", "evolve"]` — seine Aktionen werden über die **gleichen** `log_blockade` und `verify_*`-Funktionen auditiert wie die anderen Agents (siehe `gatekeeper.py:286, 316, 321, 324, 458, 491, 497, 500`).

Es gibt **keinen** Eintrag in `audit_log`, der SecurityAG als speziellen Auditor markiert, und **keinen** Event-Type wie `"security_audit"` oder `"security_decision"`. Die SecurityAG-Rolle ist im Audit-Log nur über das `agent`-Feld identifizierbar (gleiche Spalte wie alle anderen Agents).

### 5.7 Zusammenfassung

| Aspekt | Status |
|---|---|
| `audit_log`-Tabelle | ✅ Existiert, mit Indizes |
| Schreib-API `log_audit_event()` | ✅ Existiert, 6 Aufrufer |
| Lesepfad `/api/audit-log` | ✅ Existiert, mit Filter (agent, event_type, limit) |
| Cap-Mechanismus (1000/800 Rows) | ✅ Existiert |
| Cleanup-Pfad | ✅ In `admin_tools.py` (DB-Reset) und `compiler.py` |
| **SecurityAG-spezifisches Audit** | ❌ **Existiert NICHT** — SecurityAG wird wie jeder andere Agent auditiert |
| Event-Type für Security-Decisions | ❌ Nicht definiert |
| Approval-Workflow (User-Approve) | ⚠️ Nur via `gatekeeper.py`-Blockade-Log (`blockade_log`-Tabelle, nicht `audit_log`) |

**Befund für Refactor-Schritt 4:** Das `audit_log` ist eine **generische** Tabelle. Für ein dediziertes SecurityAG-Audit muss entweder (a) ein neuer Event-Type + strukturierte `details` erfunden werden, oder (b) eine eigene Tabelle `security_audit_log` mit Security-spezifischen Feldern (Severity, Finding-Type, Patch-Vorschlag) angelegt werden.

---

## Anhang A — Test-Touchpoints

`src/gnom_hub/core/utils/test_agent_self_diagnosis.py` testet explizit Permission-Verhalten:

```python
10:     def test_gatekeeper_permission_denial(self):
11:         # 1. Test that without "write" permission, process_actions replaces [WRITE] with a Gatekeeper warning
12:         agent = {"name": "CoderAG", "role": "developer"}
13:         permissions = ["read"] # No "write"
14:         ans = "[WRITE: output.txt] test code [/WRITE]"
15:         result = process_actions(ans, agent, permissions, False, "/tmp")
16:         self.assertTrue("keine WRITE-Berechtigung" in result or "Schreibzugriff" in result)
```

(Zeile 21-48 testet analog den Brainstorm-Pfad mit `permissions=["read"]` und Self-Diagnose-Loop.)

**Refactor-Risiko:** Der Test setzt fest, dass `["read"]` (ohne `write`) zu `[System: ... keine Schreibberechtigung.]` führt (Zeile 16) — dieser String muss stabil bleiben oder bewusst migriert werden.

---

## Anhang B — Was NICHT gefunden wurde

- **`"run" in caps` / `caps.get("run")` / `in caps`-Pattern:** 0 Treffer (1.5) — Capabilities heißen im Code `permissions`, keine separate `caps`-Variable.
- **Konsumenten von `config/agents/*.json`:** 0 .py-Treffer (1.8) — die Dateien sind statisch.
- **`permissions`-Feld in `data/presets/default/*.json` außerhalb von `permissions.json`:** 0 Treffer — die anderen 13 Preset-Dateien haben keine `permissions`-Sektion. `permissions.json` ist **die einzige** permissions-tragende Preset-Datei.
- **SecurityAG-spezifischer Audit-Log-Eintrag oder Event-Type:** Nicht gefunden (siehe 5.6).
- **Live-Editor für Permissions via API:** `agents_status.py` liest Permissions nur zur Anzeige (TP-9); keine PUT/POST-Endpoint setzt sie zurück — sie werden ausschließlich über `soul_initializer.py:55` (Soul-Sync) oder über `agent_definitions.py`-Edits geändert.

---

## Anhang C — Offene Fragen für Folge-Tasks (Schritte 2-7)

1. **Vocabulary-Wahl:** Bleibt es bei Vocabulary A, migrieren wir zu B, oder gibt es ein C (Hybrid)? → Schritt 2 (Definitions ändern)
2. **GeneralAG `@job`-Token:** Soll der `@job`-Token als "Orchestrator-Marker" erhalten bleiben oder ins neue Vokabular überführt werden? → Schritt 2
3. **godmode → run Auto-Inferenz (TP-4):** Soll die Regel bestehen bleiben? Heute No-Op. → Schritt 2/3
4. **Brainstorm-Override (TP-7):** Soll `[MODUS: BRAINSTORM]` weiterhin WRITE/SHELL unabhängig von Permissions erlauben? → Schritt 3
5. **SoulAG-Hardcode in Gatekeeper (TP-10):** Wie migrieren wir die zwei `if name.lower() == "soulag": pass`-Ausnahmen? → Schritt 3
6. **SecurityAG-Audit (5.6):** Neuer Event-Type oder neue Tabelle? → Schritt 4 (nach Owner-Decision)
7. **Config/agents-Dateien (4.1):** Löschen, migrieren, oder als UI-Config belassen? → Schritt 3 oder Off-Task

---

**Ende der Bestandsaufnahme. Bereit für Verifier-Review und Folge-Schritte.**
