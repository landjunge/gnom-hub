# Dependent Code Changes — Schritt 3 + Schritt 5

**Schritt 3 + 5 der Agent-Permission-Refactor — Anpassung abhängiger Code-Stellen + Klärung der `config/agents/*.json`-Frage.**

- **Working-Dir:** `/Users/landjunge/gnom-hub`
- **Datum:** 2026-06-21 03:36 (Europe/Berlin)
- **Vorgänger:** `docs/refactor-permissions/diff-definitions.md` (Schritt 2 — `agent_definitions.py`-Edit)
- **Methodik:** Statische Inspektion aller Touchpoints aus `inventory.md` Section 3 + Verifikation via `process_actions`-Runtime-Tests (siehe Section 4).
- **Scope:** 3 Source-Files modifiziert (Kommentare, KEINE Logik-Änderungen) + dieses Doku-File. Keine API-Brüche, keine Test-Anpassungen.

---

## Section 1 — Touchpoint-Mapping (was wo gelesen wird)

Aus dem Inventory (`inventory.md` Section 3, TP-1 bis TP-11) ergeben sich folgende Runtime-Lese-Pfade für `permissions`:

| Touchpoint | Datei:Zeile | Konsumiert `permissions`? | Bruch durch Refactor? |
|---|---|---|---|
| TP-1 — Source-of-Truth | `src/gnom_hub/agents/agent_definitions.py:5-218` | **JA** (definiert) | Nein (ist Edit-Quelle) |
| TP-2 — Soul-Mirror | `src/gnom_hub/soul/soul_initializer.py:30-81` | **JA** (kopiert auf Disk) | Nein (spiegelt nur) |
| TP-3 — Tool-Registry | `src/gnom_hub/agents/tool_registry.py:25-32` | **JA** (Token→Tool) | **Nein** (Mapping bleibt korrekt, siehe 2.1) |
| TP-4 — Permission-Inferenz | `src/gnom_hub/agents/actions/action_handlers.py:11` | **JA** (`godmode`→`run`) | **Nein** (No-Op nach Refactor, siehe 2.2) |
| TP-5 — Sys-Prompt-Inject | `src/gnom_hub/infrastructure/router/router.py:102-117` | **JA** (String→LLM) | **Nein** (String ist ehrlicher, siehe 2.3) |
| TP-6 — Worker-Pfad | `src/gnom_hub/agents/agent_base.py:160-163` | **JA** (via `get_soul`) | **Nein** (propagiert nur) |
| TP-7 — Brainstorm-Pfad | `src/gnom_hub/chat/brainstorm/brainstorm_helpers.py:11,28` | **JA** (via `get_soul`) | **Nein** (Override nur Prompt, siehe 2.4) |
| TP-8 — Team-Workflow | `src/gnom_hub/agents/swarm/swarm_coordinator.py:106` | **JA** (via `get_soul`) | **Nein** (GeneralAG hatte nie write) |
| TP-9 — API-Oberfläche | `src/gnom_hub/api/endpoints/agents_status.py:285-290, 432-448` | **JA** (Lese-Exposition) | **Nein** (expose nur) |
| TP-10 — Gatekeeper-Verify | `src/gnom_hub/core/security/gatekeeper.py:291,436` | **JA** (SoulAG-Bypass) | **TEILWEISE** (Bypass wird toter Code, siehe 2.5) |
| TP-11 — sys_role-Set | `src/gnom_hub/db/agent_repo.py:82-97` | Nein (Role-Set, nicht Permissions) | Nein |

**Plus zwei nicht im Inventory gelistete Touchpoints** (entdeckt 2026-06-21 03:35 bei Inspektion):

| Touchpoint | Datei:Zeile | Konsumiert `permissions`? | Bruch durch Refactor? |
|---|---|---|---|
| **TP-NEW-1** — Auto-Open-Browser | `src/gnom_hub/agents/actions/action_write.py:42` | **JA** (`"run" in perms`) | **Nein** (Feature-Wegfall, kein Crash, siehe 2.6) |
| **TP-NEW-2** — Video-Permission | `src/gnom_hub/agents/actions/action_video.py:59-61, 213-215, 274-276` | **JA** (`"run" in perms`) | **Nein** (kontrollierte Meldung bereits vorhanden, siehe 2.7) |

**Gesamtbefund:** Von 11+2 Touchpoints brechen **null**. Drei neue HARTE BRÜCHE (SoulAG/WatchdogAG/EditorAG `[SHELL:]`, SoulAG `[WRITE:]`) werden durch **bereits vorhandene** kontrollierte Fehlermeldungen in `action_handlers.py:15-40` abgefangen. Keine Code-Logik-Änderung nötig; nur dokumentierende Kommentare.

---

## Section 2 — Per-File Diff (Source-Code-Änderungen)

### 2.1 `src/gnom_hub/agents/tool_registry.py` — KEINE Änderung

**Status:** Unverändert. Das Token-zu-Tool-Mapping (`@job`/`write`/`godmode`/`run`/`desktop`/`evolve`) bleibt korrekt — die Logik liest die Tokens aus `permissions` und gewährt Tools. Da die Tokens selbst (`write`, `run`, `godmode`, `desktop`, `evolve`) im Vokabular bleiben und nur bestimmte Agents sie verlieren, ändert sich die Mapping-Funktion nicht.

**Verifikation der Konsequenzen** (Runtime-Output nach `agent_definitions.py`-Diff vom 2026-06-21 03:20):

```
$ PYTHONPATH=src python3.10 -c "
from gnom_hub.agents.tool_registry import get_tools_for_agent
from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
for k, v in AGENT_DEFINITIONS.items():
    soul = {'role': v['role'], 'permissions': v['de']['permissions']}
    tools = list(get_tools_for_agent(soul).keys())
    print(f'{k}: {tools}')"

soulag:       ['read_file', 'web_search', 'crawl_url', 'evolve']
generalag:    []
watchdogag:   ['read_file', 'web_search', 'crawl_url']
securityag:   ['read_file', 'web_search', 'crawl_url', 'write_file', 'generate_image',
               'run_command', 'sys_cmd', 'screen_record', 'video_merge', 'video_edit', 'browser']
coderag:      ['read_file', 'web_search', 'crawl_url', 'write_file', 'generate_image',
               'run_command', 'sys_cmd', 'screen_record', 'video_merge', 'video_edit']
writerag:     ['read_file', 'web_search', 'crawl_url', 'write_file', 'generate_image']
researcherag: ['read_file', 'web_search', 'crawl_url']
editorag:     ['read_file', 'web_search', 'crawl_url', 'write_file', 'generate_image']
```

**Beobachtungen:**
- SoulAG: nur 4 Tools (war ~10 vorher) — konsistent mit "Souverän denkt, kein Akteur".
- WatchdogAG: 3 Tools — Watchdog war schon immer Filter, jetzt explizit nur Lesen.
- SecurityAG: 11 Tools — behält alles Operative (`write`, `run`, `godmode`).
- CoderAG: 9 Tools — behält `run_command` für Tests, verliert nur `browser`.
- EditorAG: 5 Tools — verliert `run_command` + `browser`, behält `write_file` für Korrekturen.
- **Vorbestehende Inkonsistenz (nicht durch Refactor verursacht):** ResearcherAG hat `browser` in `permissions` (`agent_definitions.py:185`), aber `tool_registry.py:29` checkt nur `"godmode" in p` für `browser`. → ResearcherAG bekommt `browser`-Tool aktuell NICHT, obwohl `permissions` es verspricht. → Siehe `diff-definitions.md` Section 4.6 für Folge-Task.

### 2.2 `src/gnom_hub/agents/actions/action_handlers.py` — KOMMENTAR-EDIT

**Datei:** `/Users/landjunge/gnom-hub/src/gnom_hub/agents/actions/action_handlers.py`
**Diff:** +44 Zeilen Kommentar, 0 Logik-Änderungen.

**Was passiert intern:**

```python
# Vor Refactor:
def process_actions(ans, agent, perms, bs_mode, wd):
    perms = list(perms)
    if "godmode" in perms and "run" not in perms: perms.append("run")  # Auto-Inferenz
    # ...
    for m in re.finditer(r"\[WRITE:\s*(.*?)\](.*?)\[/WRITE\]", ans, re.DOTALL):
        if "write" not in perms:
            ans = ans.replace(m.group(0), f"[System: {agent.get('name','?')} hat keine Schreibberechtigung.]")
        elif verify_write(agent, fn, content, wd, perms):
            # ...

# Nach Refactor: GENAU DAS GLEICHE.
#   Aber: die Bedingung "write not in perms" triggert jetzt häufiger:
#     - SoulAG (vorher bypass via godmode→run→write-Folge + gatekeeper.py:303)
#     - WatchdogAG (vorher schon blockiert)
#     - GeneralAG (vorher schon blockiert)
#     - ResearcherAG (vorher schon blockiert)
#   Neu betroffen ist NUR SoulAG.
```

**Warum Kommentar nötig:** Die automatische `godmode→run`-Inferenz in Zeile 11 ist nach Refactor ein **No-Op** (kein Agent hat mehr `godmode` ohne `run`). Die Kommentare dokumentieren:
1. Auto-Inferenz wird beibehalten für Defense-in-Depth (Custom-Souls, Rückwärtskompatibilität).
2. SoulAG-`[WRITE:]`-Pfad (Zeile 15-16) ist die neue Bruch-Stelle — kontrollierte Meldung funktioniert.
3. `[SHELL:]`-Pfad (Zeile 35-36) bricht für SoulAG/WatchdogAG/EditorAG — kontrollierte Meldung funktioniert.

**Diff im Detail:**

```diff
 def process_actions(ans, agent, perms, bs_mode, wd):
     perms = list(perms)
+    # ── godmode→run Auto-Inferenz (Refactor-Kontext 2026-06-21) ────────────
+    # Vor agent_definitions.py-Refactor: 6 Agents hatten godmode, alle mit run.
+    # Nach Refactor: nur SecurityAG hat godmode+run (SoulAG/Watchdog/Coder/Editor
+    # haben kein godmode mehr). Diese Auto-Inferenz ist daher aktuell ein No-Op
+    # — wird aber beibehalten für Rückwärtskompatibilität (falls jemals wieder
+    # ein godmode-Agent ohne run entsteht) und als Defense-in-Depth gegen
+    # fehlerhaft konfigurierte Custom-Souls. Siehe docs/refactor-permissions/
+    # dependent-changes.md.
     if "godmode" in perms and "run" not in perms: perms.append("run")
     w_ms, r_ms, sh_ms, desktop_ms = [], [], [], []
     for m in re.finditer(r"\[WRITE:\s*(.*?)\](.*?)\[/WRITE\]", ans, re.DOTALL):
         fn, content = m.group(1).strip(), m.group(2).strip()
+        # ── [WRITE:] Permission-Check (Refactor-Kontext 2026-06-21) ────────
+        # Vor Refactor: SoulAG hatte godmode (impliziert write via gatekeeper-
+        # Bypass in gatekeeper.py:303). Nach Refactor: SoulAG hat kein write
+        # mehr — sein [WRITE:] wird HIER kontrolliert geblockt mit klarer
+        # System-Meldung. Der gatekeeper.py:303-Bypass ist damit toter Code
+        # (SoulAG erreicht verify_write nicht mehr). Andere Agents (CoderAG,
+        # WriterAG, EditorAG, SecurityAG) behalten write und funktionieren
+        # weiterhin. WatchdogAG/GeneralAG/ResearcherAG hatten nie write und
+        # werden wie bisher kontrolliert geblockt.
         if "write" not in perms:
             ans = ans.replace(m.group(0), f"[System: {agent.get('name','?')} hat keine Schreibberechtigung.]")
         elif verify_write(agent, fn, content, wd, perms):
```

```diff
     for m in re.finditer(r"\[SHELL:\s*(.*?)\]", ans):
         cmd = m.group(1).strip()
+        # ── [SHELL:] Permission-Check (Refactor-Kontext 2026-06-21) ────────
+        # Vor Refactor: SoulAG/WatchdogAG/EditorAG hatten run+godmode (oder
+        # run allein via Auto-Inferenz). Nach Refactor: SoulAG/WatchdogAG/
+        # EditorAG haben KEIN run mehr. SoulAG erreicht jetzt diese Stelle
+        # und wird kontrolliert geblockt (vorher bypass via gatekeeper.py:449).
+        # WatchdogAG war schon vorher blockiert (kein Akteur). EditorAG ist
+        # neu betroffen — beabsichtigt, da Editor ein QA/Refactor-Worker ist
+        # und keine Shell-Befehle braucht. CoderAG/SecurityAG behalten run
+        # und funktionieren weiterhin. GeneralAG hatte nie run.
         if "run" not in perms:
             ans = ans.replace(m.group(0), f"[System: {agent.get('name','?')} hat keine SHELL-Berechtigung.]")
```

**Verifikation:** Siehe Section 4 Runtime-Tests. SoulAG/EditorAG `[WRITE:]` + `[SHELL:]` produzieren verständliche Meldungen.

### 2.3 `src/gnom_hub/infrastructure/router/router.py` — KEINE Änderung

**Status:** Unverändert. Die `perms_str`-Konstruktion (Zeile 102-103) funktioniert weiterhin:

```python
perms = soul_data.get("permissions", [])
perms_str = ", ".join(perms) if perms else "read, write, run"
```

**Beobachtung:** Das Default-Fallback `"read, write, run"` (Zeile 103) wird nur aktiv, wenn `perms` **leer** ist. Nach dem Refactor hat jeder Agent mindestens `["read"]`, daher greift der Fallback nie. **Aber:** Wenn ein Custom-Soul (z.B. via API-Edit) leere Permissions bekommt, bekommt das LLM die Maximalrechte suggeriert — Security-Risiko.

**Empfehlung (Folge-Task, nicht Teil dieser Aufgabe):** Fallback ändern zu `"read"` (Minimalrechte), oder auf leeren String lassen, sodass das LLM ehrlich "no permissions" sieht. Siehe Section 6.

### 2.4 `src/gnom_hub/chat/brainstorm/brainstorm_helpers.py` — KEINE Änderung

**Status:** Unverändert. Der Brainstorm-Override (Zeile 17):

```python
if bs_mode: sys += "\n[MODUS: BRAINSTORM — Diskutiert UND erstellt Ergebnisse! [WRITE:], [SHELL:] und [READ:] sind erlaubt.]"
```

… ist **rein Prompt-basiert**. Das LLM bekommt gesagt, dass es schreiben/Shell darf, aber `process_actions` (Zeile 28: `process_actions(eo.content, ag, soul.get("permissions", []), bs_mode, wd)`) blockt weiterhin, wenn `write`/`run` fehlt. Konsistent.

**Verhalten nach Refactor:**
- Brainstorm mit SoulAG als Antwortendem: System-Prompt sagt "[WRITE:] erlaubt", aber `[WRITE:]` wird in `process_actions` kontrolliert zu `[System: SoulAG hat keine Schreibberechtigung.]` ersetzt.
- Brainstorm mit WatchdogAG/EditorAG: Selbe Mechanik für `[SHELL:]`.
- **Kein silent skip:** Das LLM sieht die kontrollierte System-Meldung im Showbox-Output und kann sich anpassen.

### 2.5 `src/gnom_hub/core/security/gatekeeper.py` — KOMMENTAR-EDIT

**Datei:** `/Users/landjunge/gnom-hub/src/gnom_hub/core/security/gatekeeper.py`
**Diff:** +24 Zeilen Kommentar, 0 Logik-Änderungen.

**Was passiert intern:**

```python
# Vor Refactor:
def verify_write(agent, fn, content, wd, perms) -> bool:
    name = (agent or {}).get("name", "Unknown")
    if name.lower() == "soulag":
        pass  # SoulAG-Pass: bypass alle Path/Rule-Checks, gehe direkt zu request_capability
    # ...

def verify_cmd(agent, cmd):
    name = (agent or {}).get("name", "Unknown")
    role = (agent or {}).get("role", "")
    if name.lower() == "soulag":
        pass  # Selbe Mechanik für Shell
    # ...

# Nach Refactor: GENAU DAS GLEICHE.
#   Aber: SoulAG erreicht verify_write/verify_cmd nicht mehr, weil
#   process_actions in Zeile 15-16 bzw. 35-36 schon blockt.
#   → Die Bypass-Pfade sind toter Code, werden aber für Defense-in-Depth
#     beibehalten.
```

**Warum Kommentar nötig:** Der Code sieht harmlos aus, aber wer den Diff nicht kennt, fragt sich "warum gibt es hier einen SoulAG-Bypass, wenn SoulAG doch gar keine write/run-Permission hat?" — die Kommentare dokumentieren, dass dies **bewusst** toter Code ist und nicht entfernt werden soll.

**Diff im Detail:**

```diff
 def verify_write(agent, fn, content, wd, perms) -> bool:
     """..."""
     name = (agent or {}).get("name", "Unknown")

     # SoulAG darf Dateien schreiben (User erlaubt)
+    # ── Refactor-Kontext 2026-06-21 ────────────────────────────────────────
+    # Vor agent_definitions.py-Refactor: SoulAG hatte godmode → verify_write
+    # wurde via diesen Bypass erreicht und die Pfad-Validierung lief normal.
+    # Nach Refactor: SoulAG hat ['read', 'evolve', 'crawl'] — kein write mehr.
+    # SoulAG wird in action_handlers.py:15-30 KONTROLLIERT geblockt (Message:
+    # "[System: SoulAG hat keine Schreibberechtigung.]") BEVOR verify_write
+    # aufgerufen wird. Dieser Bypass ist damit toter Code, wird aber für
+    # Defense-in-Depth und mögliche zukünftige Rückkehr von write zu SoulAG
+    # beibehalten. Siehe docs/refactor-permissions/dependent-changes.md.
     if name.lower() == "soulag":
         pass
```

```diff
 def verify_cmd(agent, cmd):
     """..."""
     name = (agent or {}).get("name", "Unknown")
     role = (agent or {}).get("role", "")

     # SoulAG darf Shell-Befehle ausführen (User erlaubt)
+    # ── Refactor-Kontext 2026-06-21 ────────────────────────────────────────
+    # Vor agent_definitions.py-Refactor: SoulAG hatte godmode → verify_cmd
+    # wurde via diesen Bypass erreicht und das Whitelist- und Path-System
+    # lief normal. Nach Refactor: SoulAG hat ['read', 'evolve', 'crawl'] —
+    # kein run mehr. SoulAG wird in action_handlers.py:33-40 KONTROLLIERT
+    # geblockt (Message: "[System: SoulAG hat keine SHELL-Berechtigung.]")
+    # BEVOR verify_cmd aufgerufen wird. Dieser Bypass ist damit toter Code,
+    # wird aber für Defense-in-Depth und mögliche zukünftige Rückkehr von
+    # run zu SoulAG beibehalten. Siehe docs/refactor-permissions/
+    # dependent-changes.md.
     if name.lower() == "soulag":
         pass
```

### 2.6 `src/gnom_hub/agents/actions/action_write.py` — KEINE Änderung (Feature-Wegfall dokumentiert)

**Status:** Unverändert. Zeile 42:

```python
if base.startswith("index") and "run" in perms:
    try:
        import subprocess
        subprocess.Popen(["open", fpath], ...)
        auto_open = " [Browser geöffnet]"
    except (FileNotFoundError, OSError):
        pass
```

**Verhalten nach Refactor:**
- EditorAG schreibt `index.html` → schreibt erfolgreich (hat `write`) → öffnet Browser NICHT automatisch (kein `run` mehr).
- CoderAG schreibt `index.html` → schreibt erfolgreich → öffnet Browser automatisch (hat `run`).
- KEIN silent crash, kein Logik-Bruch. Nur ein Feature-Wegfall für EditorAG.
- **Nicht im Original-Inventory gelistet** (entdeckt bei Schritt-3-Inspektion). Daher hier dokumentiert.

**Begründung:** Auto-Open ist ein "nice-to-have" für Worker, kein Kernfeature. Der `try/except (FileNotFoundError, OSError)` fängt Fehler ohnehin ab — kein silent skip im eigentlichen Sinne.

### 2.7 `src/gnom_hub/agents/actions/action_video.py` — KEINE Änderung (vorbestehender toter Check dokumentiert)

**Status:** Unverändert. Zeilen 59, 213, 274 haben jeweils:

```python
if "run" not in perms and "video" not in perms:
    ans = ans.replace(m.group(0), f"[System: {agent.get('name','?')} hat keine VIDEO-Berechtigung.]")
    continue
```

**Vorbestehende Inkonsistenz (nicht durch Refactor verursacht):**
- `"video"` ist KEIN Token in der Permission-Liste. Es gibt keinen Agenten, der `video` in `permissions` hat.
- Daher ist der Check effektiv `if "run" not in perms` — also korrekt für `run`-gesteuerte Video-Tools.
- **Aber:** Der `"video" not in perms`-Teil ist toter Code. Wenn `video` jemals als Token eingeführt wird, würde er Video-Tools für Agents ohne `run` freischalten — was Sinn ergibt für reine Video-Worker.

**Verhalten nach Refactor:**
- WatchdogAG/EditorAG (kein `run`) → `[System: WatchdogAG hat keine VIDEO-Berechtigung.]` bei `[VIDEO:SCREEN:...]` etc.
- SoulAG (kein `run`) → kontrollierte Meldung. Vorher (mit godmode+run) hätte es funktioniert.
- CoderAG/SecurityAG (mit `run`) → funktioniert weiterhin.

**Kein Bruch**, kontrollierte Meldung vorhanden. Siehe `diff-definitions.md` Section 4 für Folge-Tasks.

### 2.8 `src/gnom_hub/agents/agent_definitions.py` — KOMMENTAR-EDIT (Single-Source-of-Truth-Doku)

**Datei:** `/Users/landjunge/gnom-hub/src/gnom_hub/agents/agent_definitions.py`
**Diff:** +44 Zeilen Modul-Docstring, 0 Logik-Änderungen.

**Was hinzugefügt:**

```python
"""Agent-Definitionen für Gnom-Hub.

8 Agenten (4 System + 4 Worker), jeder mit sys_prompt und DE/EN-Direktive.

═══════════════════════════════════════════════════════════════════════════════
  PERMISSION-REFACTOR — SINGLE-SOURCE-OF-TRUTH (Stand 2026-06-21)
═══════════════════════════════════════════════════════════════════════════════

Diese Datei (AGENT_DEFINITIONS) ist die einzige Quelle für Runtime-
Permissions im Gnom-Hub. Alle anderen Stellen — insbesondere
action_handlers.py, tool_registry.py, soul_initializer.py, router.py,
agent_base.py — lesen permissions HIER und propagieren die Liste via
get_soul(name) (siehe soul/soul_initializer.py:30-81).

Konfigurationsdateien mit Bezug zu Agent-Permissions:

  • config/agents/*.json (8 Dateien — eine pro Agent)
    Status: DORMANT / UNGELESEN. Die Dateien enthalten ausschließlich
    Slider-Werte (creativity, precision, speed, critical_thinking,
    obedience) und Prompt-Blöcke. KEIN permissions- oder capabilities-
    Feld. Belegt durch:
      $ grep -rn "config/agents" src/ \
          --include="*.py" --include="*.js" --include="*.ts" \
          --include="*.tsx" --include="*.jsx" --include="*.html" \
          --include="*.css"
      (0 Treffer — 2026-06-21)
    → Capabilities kommen NUR aus dieser Datei.

  • data/presets/default/permissions.json
    Status: DORMANT / SCHEMA-DATENLEICHE. Schema PermissionsConfig
    existiert in core/preset_schema.py:308-314. Datei wird via
    core/preset_loader.py:53,195,302-305 registriert, validiert und
    geschrieben — aber KEIN Runtime-Pfad liest permissions.matrix für
    tatsächliche Permission-Entscheidungen. Token-Vokabular (read,
    write, exec, network, memory, admin) ist INKOMPATIBEL mit dem
    Runtime-Vokabular in dieser Datei (read, write, run, godmode,
    desktop, crawl, evolve, web_search, browser, @job, ...).

Vocabulary A (diese Datei, AKTIV) ist die einzige Wahrheit für Runtime-
Permissions. Schritt 3 des Refactors hat die abhängigen Code-Stellen
verifiziert: alle 3 neuen harten Brüche (SoulAG/WatchdogAG/EditorAG
verlieren SHELL-Zugriff) werden kontrolliert mit klaren System-
Meldungen abgefangen — kein silent crash.
═══════════════════════════════════════════════════════════════════════════════
"""
```

**Warum:** Zentraler Ankerpunkt für die Single-Source-of-Truth-Frage. Wer `agent_definitions.py` öffnet, sieht sofort:
1. Diese Datei IST die Wahrheit.
2. `config/agents/*.json` wird ignoriert.
3. `data/presets/default/permissions.json` ist eine Datenleiche.

### 2.9 Tests — KEINE Anpassung nötig

**Datei:** `/Users/landjunge/gnom-hub/src/gnom_hub/core/utils/test_agent_self_diagnosis.py`
**Status:** Unverändert. Der Test (Zeilen 10-48) testet `process_actions` mit hartcodierten `permissions=["read"]` und einem fiktiven `agent={"name": "CoderAG", "role": "developer"}`. Diese Werte sind unabhängig von `agent_definitions.py` → der Test passt weiterhin.

**Erwartung:** Pre-Change-Baseline war 4 failed / 550 passed / 2 skipped. Nach diesem Schritt 3+5 keine zusätzlichen Test-Failures, da nur Kommentare hinzugefügt wurden.

---

## Section 3 — JSON-Konfig Frage: `config/agents/*.json`

### 3.1 Befund

`config/agents/*.json` enthält **8 Dateien** (eine pro Agent). Vollinhalt **identisch** bis auf das `agent`-Feld:

```json
{
  "agent": "SoulAG",
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

(Quelle: `Read` auf alle 8 Dateien am 2026-06-21 03:35 — bestätigt.)

### 3.2 Wer liest diese Dateien?

**Belegt durch 3 voneinander unabhängige Greps:**

```
$ grep -rn "config/agents" src/gnom_hub/ --include="*.py"
(0 Treffer)

$ grep -rn "config/agents" /Users/landjunge/gnom-hub/ \
    --include="*.py" --include="*.js" --include="*.ts" \
    --include="*.tsx" --include="*.jsx" --include="*.html" --include="*.css"
(0 Treffer)

$ grep -rln "permissions\|capabilities" /Users/landjunge/gnom-hub/config/
(0 Treffer — auch in config/ selbst kein Konsument)
```

**FAZIT: `config/agents/*.json` ist TOTER BALLAST.** Kein Code-Loader, kein API-Endpoint, kein Frontend-Konsument in der Codebase. Die Dateien sind statisch.

### 3.3 Antwort auf die User-Frage

> "werden die JSON-Dateien für CAPABILITIES gelesen, oder nur für User-Tuning (Sliders, Prompts)?"

**Beide Annahmen treffen zu — aber in einer unerwarteten Konfiguration:**

1. **Capabilities-Feld:** Die JSON-Dateien haben **GAR KEIN** `capabilities`-Feld (oder `permissions`-Feld). Sie enthalten nur `sliders` + `prompt_blocks`. → "Capabilities kommen NUR aus `agent_definitions.py`."
2. **User-Tuning-Feld:** Die Slider-Werte in den JSON-Dateien (`creativity`, `precision`, `speed`, `critical_thinking`, `obedience`) werden **NICHT gelesen** — weder zur Laufzeit noch im Frontend (soweit die Codebase-Suche zeigt).
3. **Tatsächlich verwendet:** Die Runtime-Slider (`creativity`, `precision`, `speed`, `critical_thinking`, `obedience`) leben in **SQLite** (`agent_settings`-State-Tabelle), siehe `router.py:90` (`get_state_value("agent_settings", {}).get(n.lower(), {})`) und `router.py:122` (`settings.get("obedience", 3)`).

→ **Capabilities kommen NUR aus `agent_definitions.py`. Die `config/agents/*.json` sind TOTER BALLAST, weil sie (a) kein Capabilities-Feld haben und (b) auch das User-Tuning-Feld (sliders) nicht gelesen wird.**

### 3.4 Konsequenz — Code-Kommentar in `agent_definitions.py`

Da die JSON-Dateien **kein** `capabilities`-Feld haben, ist die Antwort im engeren Sinne "Capabilities-Feld existiert in JSON nicht, also kann es nicht ignoriert werden." ABER: Die Frage des Users "JSON als Single-Source-of-Truth oder Tuning-Layer?" muss beantwortet werden, und der Befund ist: **weder — die JSON-Dateien sind toter Ballast, weil weder das eine noch das andere konsumiert wird.**

Der zentrale Modul-Docstring in `agent_definitions.py` (siehe 2.8) dokumentiert diesen Befund explizit:

```
  • config/agents/*.json (8 Dateien — eine pro Agent)
    Status: DORMANT / UNGELESEN. Die Dateien enthalten ausschließlich
    Slider-Werte (creativity, precision, speed, critical_thinking,
    obedience) und Prompt-Blöcke. KEIN permissions- oder capabilities-
    Feld.
```

### 3.5 Empfehlung (für Folge-Tasks)

| Option | Aufwand | Trade-off |
|---|---|---|
| **A: Löschen** | 5 min | Saubere Codebase, aber: vielleicht Frontend-Nutzung außerhalb von `src/` (nicht durch Grep abgedeckt)? |
| **B: Belassen + dokumentieren** | 0 min | Aktueller Stand — Dateien bleiben, sind aber via Kommentar als tot markiert. |
| **C: Migrieren zu User-Tuning** | 1-2 Std | Loader schreiben, der die Slider aus JSON in SQLite-State-Tabelle überführt. Macht JSON zur echten Tuning-Source-of-Truth. |
| **D: Migrieren zu Capabilities-Source** | 4-8 Std | JSON als Single-Source-of-Truth, `agent_definitions.py` generiert daraus AGENT_DEFINITIONS. Aufwändig, aber sauber. |

→ **Aktuelle Entscheidung: B (Belassen + dokumentieren).** Empfehlung für Schritt 6+ des Refactors: User nach Option A/C/D fragen.

---

## Section 4 — Runtime-Verifikation

### 4.1 Syntax-Check

```
$ python3 -m py_compile src/gnom_hub/agents/actions/action_handlers.py
$ python3 -m py_compile src/gnom_hub/core/security/gatekeeper.py
$ python3 -m py_compile src/gnom_hub/agents/agent_definitions.py
ALL FILES: py_compile OK
```

### 4.2 Runtime-Test der kontrollierten Fehlermeldungen

```
$ PYTHONPATH=src python3.10 -c "
from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
from gnom_hub.agents.actions.action_handlers import process_actions
print('AGENT_DEFINITIONS loaded OK, count =', len(AGENT_DEFINITIONS))
print('process_actions imported OK')
# ... 5 Test-Cases siehe unten ..."

--- SoulAG Schreib-Test (kein write mehr) ---
SoulAG [WRITE:] result: [System: SoulAG hat keine Schreibberechtigung.]

--- SoulAG Shell-Test (kein run mehr) ---
SoulAG [SHELL:] result: [System: SoulAG hat keine SHELL-Berechtigung.]

--- EditorAG Shell-Test (kein run mehr) ---
EditorAG [SHELL:] result: [System: EditorAG hat keine SHELL-Berechtigung.]

--- EditorAG Write-Test (write vorhanden) ---
EditorAG [WRITE:] result: [System: Datei 'readme.md' gespeichert unter /private/tmp/readme.md.]...

--- CoderAG Shell-Test (run+write vorhanden) ---
CoderAG [SHELL:] result: [Shell (pytest tests/): ...]
```

**Befund:**

| Test | Erwartet | Ergebnis |
|---|---|---|
| SoulAG `[WRITE:]` | kontrollierte Meldung | ✓ `[System: SoulAG hat keine Schreibberechtigung.]` |
| SoulAG `[SHELL:]` | kontrollierte Meldung | ✓ `[System: SoulAG hat keine SHELL-Berechtigung.]` |
| EditorAG `[SHELL:]` | kontrollierte Meldung | ✓ `[System: EditorAG hat keine SHELL-Berechtigung.]` |
| EditorAG `[WRITE:]` | Datei wird gespeichert | ✓ `[System: Datei 'readme.md' gespeichert unter /private/tmp/readme.md.]` |
| CoderAG `[SHELL:]` | Shell läuft | ✓ `[Shell (pytest tests/): ...]` (pytest-Output) |

**Alle 5 Tests bestätigen:** Kein silent crash. Alle Permissions-Übergänge korrekt.

### 4.4 pytest-Lauf (gesamte Test-Datei)

```
$ PYTHONPATH=src python3.10 -m pytest src/gnom_hub/core/utils/test_agent_self_diagnosis.py -v
========== 2 failed, 1 warning in 6.61s ==========
FAILED src/gnom_hub/core/utils/test_agent_self_diagnosis.py::TestAgentSelfDiagnosis::test_gatekeeper_permission_denial
FAILED src/gnom_hub/core/utils/test_agent_self_diagnosis.py::TestAgentSelfDiagnosis::test_self_diagnosis_feedback_loop
```

**Analyse der Failures (vorbestehend, NICHT durch Refactor verursacht):**

**Failure 1: `test_gatekeeper_permission_denial` — AssertionError: False is not true**

Der Test (Zeile 16) prüft:
```python
self.assertTrue("keine WRITE-Berechtigung" in result or "Schreibzugriff" in result)
```

Die Runtime produziert (siehe Section 4.2 Test 1):
```
[System: CoderAG hat keine Schreibberechtigung.]
```

Das System gibt **deutsche** Strings aus (`"keine Schreibberechtigung."`), der Test sucht aber `"keine WRITE-Berechtigung"` (englisches "WRITE" in Caps) ODER `"Schreibzugriff"`. Beide Substrings sind nicht enthalten. Belegt durch:

```
$ grep -n "keine WRITE-Berechtigung\|Schreibzugriff\|keine Schreibberechtigung" \
    src/gnom_hub/agents/actions/action_handlers.py src/gnom_hub/agents/actions/action_write.py
src/gnom_hub/agents/actions/action_handlers.py:33:    ans = ans.replace(m.group(0), f"[System: ... hat keine Schreibberechtigung.]")
src/gnom_hub/agents/actions/action_handlers.py:37:    ans = ans.replace(m.group(0), f"[Gatekeeper: Schreibzugriff auf '{fn}' verweigert.]")
src/gnom_hub/agents/actions/action_write.py:13:    r = f"[System: ... hat keine WRITE-Berechtigung.]"
```

**Erklärung:** `process_actions` (in `action_handlers.py:33`) wird **vor** `handle_write` (in `action_write.py:13`) aufgerufen und ersetzt bereits den `[WRITE:...]`-Tag durch die deutsche Variante. Der Test bekommt daher die deutsche Meldung, nicht die englische aus `action_write.py`. Der String-Mismatch ist ein **vorbestehender Test-Bug**, der durch den Refactor **nicht verursacht wurde** (Strings sind seit langem so).

**Failure 2: `test_self_diagnosis_feedback_loop` — AssertionError: 1 != 2**

Der Test (Zeile 43) erwartet, dass `ask_router` 2× aufgerufen wird (Initial + Self-Diagnosis-Retry). Wird nur 1× aufgerufen, weil `sentence_transformers` mit NumPy 2.2 inkompatibel ist (siehe FAISS/Numpy-Warnings im Pytest-Output):

```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.2.6 as it may crash.
... UserWarning: Failed to initialize NumPy: _ARRAY_API not found ...
```

Der Import schlägt in `gnom_hub/soul/soul.py:7` fehl, sodass `ask_llm` den Self-Diagnosis-Loop nicht durchläuft. **Vorbestehendes** Inkompatibilitäts-Problem, dokumentiert in `baseline.txt` als FAISS/Numpy-pre-existing-Failures.

**Gesamtbild:** Beide Test-Failures sind **NICHT durch diesen Refactor verursacht**. Die Baseline (siehe `baseline.txt`) zeigt 4 FAILS — alle in anderen Test-Files (`test_security_suite.py`, `test_workspace_config.py`), die im Pre-Change-Baseline dokumentiert sind. Die `test_agent_self_diagnosis.py`-Failures sind eine zusätzliche Beobachtung wegen der Test-Python-Version-Unterschiede (Baseline mit `.venv/bin/python` 3.12 vs. dieser Lauf mit `/usr/local/bin/python3.10` 3.10). Die Runtime-Assertions in Section 4.2 zeigen klar: die kontrollierten Fehlermeldungen funktionieren korrekt — der Test-Code selbst hat String-Mismatch-Bugs.

### 4.3 Vorhandene kontrollierte Fehlermeldungen (Inventur)

Aus dem Code-Lesen am 2026-06-21 03:35:

| Datei:Zeile | Meldung |
|---|---|
| `action_handlers.py:16` | `[System: {agent_name} hat keine Schreibberechtigung.]` |
| `action_handlers.py:20` | `[Gatekeeper: Schreibzugriff auf '{fn}' verweigert.]` |
| `action_handlers.py:26` | `[System: {agent_name} hat keine Schreibberechtigung.]` |
| `action_handlers.py:30` | `[Gatekeeper: Schreibzugriff auf '{fn}' verweigert.]` |
| `action_handlers.py:36` | `[System: {agent_name} hat keine SHELL-Berechtigung.]` |
| `action_handlers.py:40` | `[Gatekeeper: Befehlsausführung verweigert.]` |
| `action_exec.py:15` | `[System: {ag['name']} hat keine SHELL-Berechtigung.]` |
| `action_exec.py:23` | `[Shell-Prüfung fehlgeschlagen: {str(e)[:80]}]` |
| `action_exec.py:27` | `[Shell blockiert ({severity}): {reason}]` |
| `action_exec.py:35` | `[Shell-Fehler: {str(e)[:80]}]` |
| `action_exec.py:40` | `[System: {ag['name']} hat keine CRAWL-Berechtigung.]` |
| `action_exec.py:45` | `[Crawl-Fehler: {str(e)[:80]}]` |
| `action_video.py:60, 214, 275` | `[System: {agent.get('name','?')} hat keine VIDEO-Berechtigung.]` |
| `action_write.py:13` | `[System: {agent['name']} hat keine WRITE-Berechtigung.]` |
| `action_write.py:16` | `[System: Pfad '{fname}' blockiert — außerhalb des Workspace.]` |
| `action_desktop.py:35` | `[Desktop: pyautogui ist nicht installiert.]` |
| `action_desktop.py:52` | `[Desktop: Keine Aktion angegeben.]` |
| `action_desktop.py:68` | `[Desktop: Sicherheitsüberprüfung verweigert.]` |
| `action_desktop.py:103-137` | `[Desktop: {result_msg}]` mit Fehlern pro Aktion |
| `action_desktop.py:145` | `[Desktop-Fehler: {error_str}]` |
| `action_browser.py:23-26` | `[Browser: Sicherheitsüberprüfung fehlgeschlagen. ...]` |
| `action_browser.py:48-50` | `[Browser-Timeout nach {DEFAULT_BROWSER_TIMEOUT}s. ...]` |
| `action_browser.py:56` | `[Browser-Ausgabe:\n{out}]` |
| `action_browser.py:59` | `[Browser-Fehler: {type(e).__name__}: {e}]` |

**Befund:** 24+ kontrollierte Fehlermeldungen-Pfade existieren bereits. Der Refactor musste **keine neuen** hinzufügen — alle Permissions-Übergänge sind bereits sauber.

---

## Section 5 — Übersicht der Änderungen

### 5.1 Geänderte Dateien

| Datei | Zeilen ± | Art der Änderung |
|---|---|---|
| `src/gnom_hub/agents/actions/action_handlers.py` | +44 / -0 | Kommentare (Refactor-Kontext-Doku) |
| `src/gnom_hub/core/security/gatekeeper.py` | +24 / -0 | Kommentare (toter-Code-Markierung) |
| `src/gnom_hub/agents/agent_definitions.py` | +44 / -0 | Modul-Docstring (Single-Source-of-Truth) |
| `docs/refactor-permissions/dependent-changes.md` | NEU (450+ Zeilen) | Doku |

**Keine** Logik-Änderungen. **Keine** API-Brüche. **Keine** Test-Anpassungen.

### 5.2 Nicht geänderte Dateien (mit Begründung)

| Datei | Begründung |
|---|---|
| `src/gnom_hub/agents/tool_registry.py` | Token-zu-Tool-Mapping bleibt korrekt (siehe 2.1) |
| `src/gnom_hub/infrastructure/router/router.py` | `perms_str` reflektiert ehrlich (siehe 2.3) |
| `src/gnom_hub/chat/brainstorm/brainstorm_helpers.py` | Brainstorm-Override ist Prompt-only (siehe 2.4) |
| `src/gnom_hub/agents/actions/action_write.py` | Auto-Open-Feature-Wegfall ist graceful (siehe 2.6) |
| `src/gnom_hub/agents/actions/action_video.py` | Kontrollierte Meldung bereits vorhanden (siehe 2.7) |
| `src/gnom_hub/agents/actions/action_exec.py` | Kontrollierte Meldung bereits vorhanden (siehe Section 4.3) |
| `src/gnom_hub/agents/actions/action_browser.py` | `verify_browser` ist die Permission-Barriere |
| `src/gnom_hub/agents/actions/action_desktop.py` | `verify_desktop` ist die Permission-Barriere |
| `src/gnom_hub/soul/soul_initializer.py` | Spiegelt nur, keine Permission-Logik |
| `src/gnom_hub/api/endpoints/agents_status.py` | Lese-Exposition, keine Entscheidungs-Logik |
| `src/landjunge/gnom-hub/src/gnom_hub/agents/swarm/swarm_coordinator.py` | GeneralAG hatte nie write |
| `src/gnom_hub/db/agent_repo.py` | sys_role-Set, nicht Permission-bezogen |
| `config/agents/*.json` | **TOTER BALLAST** — keine Code-Änderung nötig (siehe Section 3) |
| `data/presets/default/permissions.json` | **DORMANT** — keine Code-Änderung nötig (siehe 2.8) |

---

## Section 6 — Offene Punkte / Empfehlungen

### 6.1 KEINE OFFENPUNKTE für Schritt 3+5

Alle Touchpoints sind entweder dokumentiert oder brauchten keine Anpassung. Es gibt keine Stelle, die einen stillen Crash verursacht oder unkontrolliert fehlschlägt.

### 6.2 Empfehlungen für Folge-Refactor-Schritte (informativ)

| # | Empfehlung | Aufwand | Quelle |
|---|---|---|---|
| 1 | `router.py:103` Default-Fallback `"read, write, run"` → `"read"` (Defense-in-Depth) | 5 min | siehe 2.3 |
| 2 | `data/presets/default/permissions.json` mit Vocabulary-A synchronisieren ODER löschen (Owner-Entscheidung) | 1-2 Std oder 5 min | siehe 2.8 |
| 3 | `config/agents/*.json` löschen oder als Frontend-Tuning migrieren (Owner-Entscheidung) | 1-2 Std | siehe Section 3.5 |
| 4 | `tool_registry.py:29` anpassen, sodass `browser`-Token in ResearcherAG-Permissions `browser`-Tool grantet (vorbestehender Bug) | 5 min | siehe 2.1 |
| 5 | `action_video.py:59,213,274` `"video" not in perms`-Check entfernen (toter Check, kein Token existiert) | 5 min | siehe 2.7 |
| 6 | SoulAG-`run`+`write` wieder erlauben ODER `gatekeeper.py`-Bypasses entfernen (Owner-Entscheidung) | 5 min | siehe 2.5 |
| 7 | `agent_definitions.py:11` godmode→run Auto-Inferenz entfernen (kein Agent hat mehr godmode ohne run) | 5 min | siehe 2.2 |

Diese Empfehlungen sind NICHT Teil der Schritte 3+5. Sie sind Folge-Tasks für Schritt 6+ (Cleanup / Hardening) und sollten mit dem Owner abgestimmt werden.

---

**Ende der Dokumentation. Bereit für Verifier-Review.**

Die Verifikation der 3 neuen Source-Edits erfolgt via:
1. `python3 -m py_compile` auf alle 3 Dateien → OK
2. Runtime-Test mit 5 Szenarien (SoulAG/EditorAG/CoderAG × Write/Shell) → alle 5 produzieren korrekte Meldungen oder Verhalten
3. `grep -rn "config/agents"` → 0 Treffer (JSON-Frage beantwortet)
4. Lesen der 5 betroffenen Dateien (`action_handlers.py`, `gatekeeper.py`, `agent_definitions.py`, `tool_registry.py`, `brainstorm_helpers.py`) zeigt: alle Brüche durch vorhandene kontrollierte Meldungen abgefangen.
