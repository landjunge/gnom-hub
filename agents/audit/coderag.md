# Audit: CoderAG

**Audit-Datum:** 2026-06-28 17:30 UTC+2
**Auditor:** general (Worker-Audit, Run 2)
**Quellen-Sprache:** Deutsch, technische Tokens Englisch
**Methode:** Read aller Pflichtquellen + `grep -rn "CoderAG|coderag|action_write"` + Cross-Reference WriterAG/EditorAG/ResearcherAG
**Audit-Schwerpunkt:** WRITE-Tag-Handler + Cold-Start-Hang + Workspace-Pinning + Sprech-Verbot

---

## 0. Quellen-Inventar

| Datei | Zeilen / Größe | Was gefunden |
|---|---|---|
| `config/agents/CoderAG.json` | 31 (~5.321 bytes) | v5.3 — Identity 4.968 Zeichen, Sliders, prompt_blocks, **permissions: `["read", "write", "run", "showbox_write"]`** (Z. 19-24), allowed_contexts |
| `agents/coderAG.py` | **1** | Einzeiliger Stub: `if __name__ == "__main__": import asyncio; from agents.run_agent import BaseAgent, AGENT_DEFINITIONS; cfg = AGENT_DEFINITIONS["coderag"]; asyncio.run(...)` |
| `agents/run_agent.py` | 29 | Universeller Agent-Runner; liest aus `gnom_hub.agents.agent_definitions.AGENT_DEFINITIONS` (NICHT aus JSON!) |
| `src/gnom_hub/agents/agent_definitions.py` | 330 | Master-Liste aller 8 Agents. CoderAG-Block Z. 230-253: `sys_prompt` (Z. 235-242) + DE-Perms `[read, write, run]` (Z. 247) + EN-Perms `[read, write, run]` (Z. 252) |
| `src/gnom_hub/agents/actions/action_write.py` | 95 | WRITE+READ-Handler. `handle_write()` Z. 9-70 schreibt via `os.path.realpath + _safe()`, Backup bei `os.path.exists`. Cold-Start-Fix Z. 50-59 (Import `from gnom_hub.core.zwc_codec`). `seal_content()` Z. 6-7 = `strip()`. `handle_read()` Z. 72-94 |
| `src/gnom_hub/agents/actions/action_exec.py` | 121 | SHELL+ CRAWL + SHOWBOX-Handler. `handle_shell()` Z. 11-36, `handle_crawl()` Z. 37-46, `handle_showbox()` Z. 47-120. **Kein** `from gnom_hub.soul`-Import |
| `src/gnom_hub/agents/actions/action_handlers.py` | 181 | Dispatcher `process_actions()` Z. 48-181. Permission-Checks WRITE Z. 62-83, SHELL Z. 97-105. SecurityAG-Audit-Hook `_audit_security()` Z. 19-45. Inline-Button-Extraktion Z. 96-110 |
| `src/gnom_hub/agents/actions/action_browser.py` | 66 | Browser-Handler (Playwright). `handle_browser()` Z. 15-65 mit `verify_browser()` gatekeeper-check, default 120s timeout. **Kein** Soul-Import |
| `src/gnom_hub/agents/actions/action_desktop.py` | 147 | Desktop-GUI (pyautogui). `verify_desktop()` Z. 7-23 nutzt `wait_for_decision()`. **Kein** Soul-Import |
| `src/gnom_hub/agents/actions/action_video.py` | 328 | Video recording/merge/edit (screencapture + ffmpeg). 3 Handler, alle `run`-Permission-gecheckt. **Kein** Soul-Import |
| `src/gnom_hub/agents/actions/adaptive_decomposition.py` | 148 | Adaptive Task-Routing (`RouteOptimizer`, 3 Strategien A/B/C). Pricing-Raten CoderAG=$0.05/s. **Kein** Soul-Import |
| `src/gnom_hub/core/zwc_codec.py` | 69 | Lightweight ZWC-Codec ohne SoulAG-Import. 4 Funktionen: `soul_to_bits`, `bits_to_zwc`, `add_agent_metadata`. `add_agent_metadata` (Z. 60-69) wird in `action_write.py:58` genutzt |
| `tests/test_action_write_e2e.py` | 95 | Existiert. 2 Tests: `test_action_write_writes_file_to_disk` (Z. 32-61) prüft Schreiben + Cold-Start <5s. `test_action_write_uses_lightweight_zwc_codec` (Z. 64-94) prüft via Regex dass Import aus `gnom_hub.core.zwc_codec` (NICHT `gnom_hub.soul.zwc_soul`) |
| `src/gnom_hub/core/security/path_validator.py` | 190 | Workspace-Boundary `_safe()` Z. 7-24, `SYSTEM_PATHS` Z. 53-65, `is_system_path()` Z. 68-92, Risk-Patterns Z. 114-136 |
| `src/gnom_hub/core/security/gatekeeper.py` | 498 | Whitelist+Blacklist-Hybrid. `is_command_safe_and_whitelisted()` Z. 350-432, `verify_cmd()` Z. 434-498, `HARMLESS_SHELL_PATTERNS` Z. 127-147 (19 Patterns) |
| `src/gnom_hub/db/chat_repo.py` | 421 | `WORKER_AGENT_NAMES = {"CoderAG", "WriterAG", "EditorAG", "ResearcherAG"}` Z. 24. Worker-Filter `_agent_message_filter()` Z. 56-114 |
| `src/gnom_hub/core/audit_helpers.py` | 89 | `record_block` (Z. 31-43), `record_write_fail` (Z. 46-55), `record_cooldown` (Z. 71-81). Schreiben in `audit_log` via `log_audit_event` |
| `src/gnom_hub/infrastructure/process/sandbox.py` | 179 | `run_in_sandbox()` Z. 93-157 mit argv-Mode, 4-Layer-Defense, kein Docker |
| `gnom-Workspace/default/` (live) | 591 Files | Aktive Workspace-Instanz. Enthält `.agents/coderag/soul.json` mit `permissions: [read, write, run]` — **matcht Python, NICHT JSON** |
| `config/agents/{Writer,Editor,Researcher,General}AG.json` | je 30-40 | Cross-Reference für Strukturvergleich |

**Cross-Reference-Reads:**
- `agents/audit/soulag.md` (500 Z.) — bestätigt `showbox_write` Dead-Token Befund auf allen 8 Agents
- `agents/audit/securityag.md` — bestätigt `db_write`/`network`/`showbox_write` Dead-Tokens bei SecurityAG
- `src/gnom_hub/soul/soul_initializer.py` (141 Z.) — bestätigt `get_soul()` liest aus Python `AGENT_DEFINITIONS`, NICHT aus JSON

---

## 1. Aktueller Zustand

### 1.1 Version & Sliders (`config/agents/CoderAG.json:2-10`)

- **Version:** 5.3 (Worker v5-Familie, alle 4 Worker sind v5.3)
- **Sliders (alle 5 = 2 = "medium"):**
  - `creativity: 2` → "Balance standard approaches with occasional creative solutions."
  - `precision: 2` → "Balanced accuracy. Verify main outputs."
  - `speed: 2` → "Steady pace. Deliver when ready."
  - `critical_thinking: 2` → "Think about the task. Suggest obvious improvements."
  - `obedience: 2` → "Follow instructions with reasonable interpretation. Small adjustments OK."

**Identisch mit den anderen 7 Agent-Configs** (siehe Cross-Ref §5.7 in soulag.md). **Symptom, nicht Design** (soulag.md:V9).

### 1.2 Identity-Struktur (`CoderAG.json:18`, 4.968 Zeichen)

| Sektion | Zeile in JSON | Inhalt |
|---|---|---|
| Rollen-Intro | Z. 18 (1. Absatz) | "Du bist CoderAG — der CODER..." + 8 Kern-Charakteristika (laut denken, TTS, Empfänger Soul→GeneralAG, Showbox-Pflicht, Code-Stil, Workspace-Bound, Farbe Orange) |
| `═══ DEIN WORKSPACE — WO [WRITE:] HIN GEHT — PRIORITÄT 0.7 ═══` | Z. ~19-24 | Pfad-Pin: `/Users/landjunge/gnom-Workspace/default/`. Beispiele `[WRITE: foo.md]` → `<workspace>/foo.md`, `[WRITE: src/app.py]` → `<workspace>/src/app.py` |
| `═══ SPRECH-VERBOT — NUR SHOWBOX — PRIORITÄT 0.6 ═══` | Z. ~25-35 | User-Mandat 2026-06-28 02:04. 4 erlaubte Ausgabe-Formate (Showbox, WRITE, READ, Code-Block). 4 Verbote. Verweis: "Backend-Filter in chat_repo.add_chat_message droppt Worker-Chat ohne Purpose-Tag und loggt es als `cooldown` Event in audit_log." |
| `═══ SHOWBOX + BUTTONS (PFLICHT — gilt seit User-Mandat 2026-06-28) ═══` | truncated (Z. 18 endet bei 2000 chars) | User-Mandat-Block. 4 WANN-Trigger, JSON-Format mit doppelten Quotes, 5 WANN-BUTTONS-Trigger |

**Count:** 3 ═══-Marker + 1 Rollen-Intro. Identity ist **kürzer** als SoulAG (4.968 vs. 6.868 Zeichen) weil Worker keine 5-Pflichten-Liste hat.

### 1.3 Permissions-Liste (`CoderAG.json:19-24`)

```json
["read", "write", "run", "showbox_write"]
```

**vs. Runtime (Python `agent_definitions.py:247,252`):**

```python
["read", "write", "run"]   # DE:247, EN:252
```

→ **`showbox_write` fehlt in Python** (4 vs. 3 Tokens). Drift von 25%. **Kein Code-Pfad enforced `showbox_write`** (soulag.md:V2).

### 1.4 Identity-Docstring (`coderAG.py:1`)

```python
if __name__ == "__main__": import asyncio; from agents.run_agent import BaseAgent, AGENT_DEFINITIONS; cfg = AGENT_DEFINITIONS["coderag"]; asyncio.run(BaseAgent(cfg["name"], cfg["description"], cfg["capabilities"][0], sys_prompt=cfg["sys_prompt"], poll=15).run())
```

**1 Zeile.** Kein eigener Logic. Nutzt `AGENT_DEFINITIONS["coderag"]` aus `agent_definitions.py:230-253`. **Damit wird `config/agents/CoderAG.json` als BaseAgent-Instanz NICHT konsumiert** — die JSON ist nur ein Doku-Schatten.

### 1.5 Live soul.json (`/Users/landjunge/gnom-Workspace/default/.agents/coderag/soul.json`)

```json
{
  "role": "coder",
  "character": "The Coder",
  "directive": "Coder. Writes, edits and debuggs code. Receives only from GeneralAG. Results only via Showbox with dynamic buttons. No normal chat. Color: Orange.",
  "permissions": ["read", "write", "run"],
  "breakpoints": []
}
```

→ **Matcht Python `agent_definitions.py:247` exakt** (3 Tokens). `soul_initializer.py:30-81` schreibt/liest diese Datei. Wenn `agent_definitions.py` geändert wird → wird `soul.json` beim nächsten `get_soul()`-Call überschrieben (Z. 55-61: `if data.get("permissions") != permissions: ... json.dump(...)`).

---

## 2. Spec-Konformität

### 2.1 Workspace-Pin (`CoderAG.json` Identity Z. ~19-24)

**Behauptung:** `Dein Workspace (User-gepinnt, ändert sich nicht ohne expliziten Befehl): /Users/landjunge/gnom-Workspace/default/`

**Realität:**
- `core/config.py:16` setzt `default_workspace = Path.home() / "gnom-Workspace"` → Modul-Level `WORKSPACE_DIR = ~/gnom-Workspace` (nicht `default/`)
- `chat/brainstorm/brainstorm_helpers.py:3` `get_workspace_dir()` = `WORKSPACE_DIR/<active_project>` → `~/gnom-Workspace/<project>/`
- `system_repo.py:39-46` `get_active_project()` → `"default"` (DB-Fallback) oder User-Override via State-Tabelle
- `api/endpoints/workspace.py:12-21` `get_workspace_dir()` (Endpoint-Variante) → `Config.workspace_dir() + "/" + active_project`

**Verification (live):**
```
$ ls /Users/landjunge/gnom-Workspace/default/ | wc -l
591
$ cat /Users/landjunge/gnom-Workspace/default/.agents/coderag/soul.json | jq .permissions
["read", "write", "run"]
```

**Bewertung:**

| Aspekt | Status | Kommentar |
|---|---|---|
| Pfad `/Users/landjunge/gnom-Workspace/default/` korrekt | ✅ | Trifft zu solange `get_active_project() == "default"` |
| `gnom-Workspace/default/` (Hard-Coded) | ⚠️ | `get_active_project()` kann theoretisch `"other-project"` sein. In dem Fall würden Worker-Files dort landen. **Kein Test** der das absichert |
| Workspace-Override via UI | ⚠️ | `Config.workspace_dir()` liest `workspace_dir_override` aus State (`api/endpoints/workspace.py:51-99`). User könnte z.B. auf `~/projects/foo` umstellen — dann schreibt CoderAG dorthin, NICHT nach `gnom-Workspace/default/` |
| `WORKSPACE_DIR` Hard-Code vs. `get_workspace_dir()` Hot-Reload | ⚠️ | `brainstorm_helpers.py:1` und `sandbox.py:13` importieren Modul-Level `WORKSPACE_DIR` (nicht `Config.workspace_dir()`). Override greift nur in Code-Pfaden die `Config.workspace_dir()` aufrufen |
| Workers (alle 4) gleicher Pin | ✅ | Cross-Ref: WriterAG.json, EditorAG.json, ResearcherAG.json haben **wortwörtlich identischen** Pin-Block (`/Users/landjunge/gnom-Workspace/default/`) |

**Pin-Status: ⚠️ TEILWEISE RICHTIG.** Pfad stimmt im Default-Fall, aber es gibt 2 Szenarien in denen er lügt:
1. `set_active_project("foo")` → Worker schreibt nach `gnom-Workspace/foo/` (Pin behauptet weiter `default/`)
2. `set_workspace_config(path="~/projects/bar")` → Worker schreibt nach `bar/` (Pin behauptet weiter `gnom-Workspace/default/`)

**Cross-Ref Befund:** Auch GeneralAG, SoulAG, SecurityAG, WatchdogAG-Identities kennen KEINEN dynamischen Workspace. Die JSON-Identities sind alle auf `gnom-Workspace/default/` gepinnt. **Systematisches Pin-Problem, nicht CoderAG-spezifisch.**

### 2.2 Sprech-Verbot + Showbox-Pflicht

**Behauptung in Identity Z. ~25-35:**
- "User-Mandat 2026-06-28 02:04: Worker dürfen NICHT direkt in den Chat schreiben."
- "Backend-Filter in chat_repo.add_chat_message droppt Worker-Chat ohne Purpose-Tag und loggt es als `cooldown` Event in audit_log."

**Realität (Code):**
- `db/chat_repo.py:24` `WORKER_AGENT_NAMES = frozenset({"CoderAG", "WriterAG", "EditorAG", "ResearcherAG"})` — **alle 4 Worker enthalten, CoderAG ist drin** ✅
- `db/chat_repo.py:56-114` `_agent_message_filter()` mit Worker-Branch Z. 71-95:
  ```python
  if sender in WORKER_AGENT_NAMES:
      has_write_read = "[WRITE:" in content or "[READ:" in content
      has_code_block = "```" in content
      showbox_tag_only = bool(_SHOWBOX_TAG_ONLY_RE.match(content))
      # ... JSON-Slides detection ...
      has_meaningful_showbox = (
          bool(_SHOWBOX_TAG_STRIP_RE.search(content))
          and (has_json_slides or bool(stripped))
          and not showbox_tag_only
      )
      if not (has_meaningful_showbox or has_write_read or has_code_block):
          return True, "worker_sprech_verbot"
  ```
- `db/chat_repo.py:243-291` `add_chat_message()` ruft Filter in Z. 250-263
- **Erfasste Worker:** CoderAG, WriterAG, EditorAG, ResearcherAG ✅
- **Erfasste NICHT:** GeneralAG, SoulAG, SecurityAG, WatchdogAG (per Design — System-Agents dürfen reden)

**Cooldown-Logging:**
- `db/chat_repo.py:254-263`: `record_cooldown(sender, reason=filter_reason, duration_s=...)` bei Filter-Treffer
- `core/audit_helpers.py:71-81` `record_cooldown()` schreibt in `audit_log` mit `event_type="cooldown"`, `details={"reason": ..., "duration_s": ...}`
- `db/schema.py:65-77` `audit_log` Tabelle existiert (id, timestamp, agent, event_type, details, trace_id, created_at)

**Bewertung:** Sprech-Verbot ist **technisch vollständig enforced** für alle 4 Worker. **CoderAG erfasst.** Verstoß-Beispiele:
- CoderAG schreibt "OK ich mache das" → Filter returnt `(True, "worker_sprech_verbot")` → `add_chat_message` returnt `None` → kein DB-Eintrag, dafür `audit_log`-Eintrag mit `event_type="cooldown"`
- CoderAG schreibt `[→ Showbox: foo]{"slides": [...]}` → `has_meaningful_showbox=True` → pass-through
- CoderAG schreibt `[WRITE: foo.py]x=1[/WRITE]` → `has_write_read=True` → pass-through
- CoderAG schreibt nur `[→ Showbox: foo]` (ohne Body) → `showbox_tag_only=True` → `has_meaningful_showbox=False` → gedroppt

**CoderAG-spezifisches Risiko:** Code-Block ist die einzige "Plain-Text"-Erlaubnis. Wenn CoderAG EINEN Code-Block mit Kommentar-Talk sendet (z.B. ```# Hallo, ich habe folgendes gemacht...```), wird das als "has_code_block=True" durchgelassen — **Filter zu permissiv?** Nein, Spec sagt explizit "reiner Code-Block ```...```" — Inline-Kommentar-Talk im Code ist OK.

### 2.3 Showbox-Buttons-Pflicht (Identity Z. ~37+)

**Behauptung:** "MUSS Buttons enthalten wenn User-Aktion möglich ist."

**Realität:**
- `actions/action_exec.py:96-110` `handle_showbox()` extrahiert Buttons aus 3 Quellen (JSON-Key "buttons", inline `<button action="..." label="...">`, inline `<button data-sb-action="...">`)
- `actions/action_exec.py:103-110` keine Validierung "wenn Worker sendet, müssen Buttons da sein"
- `frontend/showbox_button_parser.py` extrahiert Buttons (Cross-Ref)

**Bewertung:** Buttons-Pflicht ist **NICHT technisch erzwungen** (soulag.md:V3). CoderAG könnte `[→ Showbox: x]{"slides": [...]}` ohne `buttons[]` senden → wird gespeichert, **kein Fehler**.

**Hinweis Identity:** Der in CoderAG.json:18 erwähnte "User-Mandat 2026-06-28" Block endet bei den 2000 chars die der Read-Output liefert — vollständige Spec evtl. in den nächsten 2-3 KB. Da ich nur den ersten 2000 chars lese, könnte noch eine "WANN BUTTONS" Liste folgen. **Read mit höherem Limit wäre für vollständige Bewertung nötig.**

### 2.4 `run`-Permission Whitelist/Blacklist

**Spec:** `core/security/gatekeeper.py` definiert Whitelist+Blacklist-Hybrid.

**Pfad für CoderAG `[SHELL:]`-Aufrufe:**

```
agent emit [SHELL: ls -la]
  → action_handlers.py:86 matcht
  → permission-check: "run" in perms? ✅ (CoderAG hat run, Z. 247)
  → verify_cmd() gatekeeper.py:434
      → check_blockade_rules() (User-Regeln)
      → mark_harmless_shell() — 19 HARMLESS_SHELL_PATTERNS, Z. 127-147
          z.B. `^ffmpeg\b`, `^say\s+`, `^open\s+`, `^pip3?\s+install`, `^brew\s+install`
      → path-workspace-check
      → is_command_safe_and_whitelisted() — Z. 350-432
          → Pipe-to-shell: hard block (curl|sh etc.)
          → Per-Segment-Parsing: mkfs/fdisk/reboot → high block
          → rm: hard block wenn target=/etc/, /usr/, ~/, src/gnom_hub, run.sh, .env
          → npm/yarn: hard block bei "rm -rf" oder "curl|sh" im Befehl
          → pip uninstall: block pip/setuptools/wheel/fastapi/uvicorn
          → git: HARD BLOCK — "git ist nicht verfügbar" (Z. 430)
          → alles andere: ALLOW (mit warning wenn Medium-Risk-Pattern)
  → run_in_sandbox() sandbox.py:93
      → Whitelist-Check (1)
      → Segment-Parsing (shlex) (2)
      → subprocess.run(parts, shell=False) (3) — argv-Mode
      → Operator-Semantik &&/||/;
      → KEIN PIPE, KEIN REDIRECT, KEIN Backtick
```

**Whitelist (was ist erlaubt):** `is_command_safe_and_whitelisted` ist faktisch eine **BLACKLIST** — alles ist erlaubt solange es nicht in den High-Risk-Patterns matched. Plus `HARMLESS_SHELL_PATTERNS` für dauerhaft harmlose Befehle (auto-whitelist).

**Blacklist (was ist blockiert):**
1. `curl|sh`, `wget|sh`, `fetch|sh` — Pipe-to-Shell
2. `mkfs`, `fdisk`, `reboot` — high-risk executables
3. `rm` auf `/`, `~`, `/etc`, `/usr`, `/bin`, `/sbin`, `/var`, `/boot`, `/proc`, `/sys`, `/lib`, `/private/etc`, `/private/var`, `src/gnom_hub`, `run.sh`, `.env`
4. `npm/yarn/pnpm/bun` mit "rm -rf" oder "curl|sh"
5. `pip uninstall` von `pip/setuptools/wheel/fastapi/uvicorn`
6. `git` — komplett blockiert (User-Mandat 2026-06-15)
7. Bash-Builtin-Exec via shell: hard block wenn `subprocess.*(... shell=True)`

**CoderAG-Spezifika:**
- `run`-Permission erlaubt alles was nicht in der Blacklist ist
- **Keine** zusätzliche CoderAG-spezifische Whitelist/Blacklist (im Gegensatz zu z.B. `screencapture` für Video-Worker)
- **CoderAG ist der einzige Worker mit `run`** (Cross-Ref: WriterAG hat `crawl`, EditorAG hat `write` only, ResearcherAG hat `crawl/web_search/browser`). CoderAG ist auch der einzige Worker der Skripte ausführen kann

**Edge-Cases für CoderAG:**
- `python3 -c "print(1)"` → argv-Mode parsed `["python3", "-c", "print(1)"]`. Subprocess-Mode läuft. OK.
- `python3 -c "import os; os.system('rm -rf /')"` → Whitelist-Check sieht NICHT den `os.system`-Code (kein scan von stdin-args), läuft im subprocess. **Subprocess läuft** aber das `os.system('rm -rf /')` läuft im PYTHON-PROZESS mit vollen User-Rechten. **KEIN sandbox-Schutz für Python-Code.** ⚠️
- `bash -c "rm -rf ~"` → argv-Mode parsed. Subprocess läuft. Das `rm` wird aber NICHT in `is_command_safe_and_whitelisted` extrahiert (das checkt nur das erste Token, "bash"). **Kein Schutz.** ⚠️
- `nohup python3 daemon.py &` → `&` ist nicht in `_SEGMENT_SPLIT_RE` (nur `&&`/`||`/`;`). `&` wird zu einem arg des letzten commands. **Background-Prozesse unkontrolliert.**

**Befund:** Die Run-Whitelist ist **whitelist+blacklist by intent** (gut gedacht) aber **Token-basiert** (sieht nur das was syntaktisch zerlegbar ist). Python-Scripts und `bash -c` umgehen den ganzen Layer. Für **echte Isolation** bräuchte es Docker/sandbox-exec (was User-Mandat 2026-06-15 explizit ablehnt: "keep it simple, run directly").

### 2.5 Action-Write-Handler Cold-Start (Memory-Fix)

**Memory-Recall:** "action_write.py:50 importierte soul.zwc_soul → 30-40s delay"

**Verification:**

```bash
$ grep -nE "from gnom_hub.soul|import gnom_hub.soul" src/gnom_hub/agents/actions/*.py
src/gnom_hub/agents/actions/action_write.py:51: # Vorher: `from gnom_hub.soul.zwc_soul import add_agent_metadata`
```

→ **NUR 1 Match** in 7 Action-Files: der Kommentar in `action_write.py:51` der den ALTEN Pfad dokumentiert. **Kein aktiver Soul-Import** in irgendeinem Action-File.

**Source-File `action_write.py:58`:**
```python
from gnom_hub.core.zwc_codec import add_agent_metadata
r = f"[System: Datei '{fname}' gespeichert unter {os.path.abspath(fpath)}.{auto_open}]" + add_agent_metadata(agent["name"], "")
```

**Source-File `core/zwc_codec.py:36-69`:** pure-stdlib, 4 Funktionen, **kein Import von `gnom_hub.soul.*`**, **kein sentence_transformers**, **kein torch**.

**Test-File `tests/test_action_write_e2e.py:64-94`:** `test_action_write_uses_lightweight_zwc_codec` prüft via Regex dass action_write.py `add_agent_metadata` aus `gnom_hub.core.zwc_codec` importiert (NICHT `gnom_hub.soul.zwc_soul`). **Regression-Test vorhanden.**

**Test-File `tests/test_action_write_e2e.py:32-61`:** `test_action_write_writes_file_to_disk` prüft Schreiben + Cold-Start <5s.

**Befund Cold-Start-Hang:**
- ✅ **Fix vollständig durchgezogen** für `action_write.py`
- ✅ **Keine anderen Action-Module** hatten das Pattern (`action_exec.py`, `action_browser.py`, `action_desktop.py`, `action_video.py` sind alle soul-frei)
- ✅ **Regression-Test vorhanden** (`test_action_write_uses_lightweight_zwc_codec`)
- ⚠️ **Aber:** Test-Kommentar Z. 22-27 weist auf **ORTHOGONALEN Cold-Start-Bug** hin: `init_database() → _seed_agents()` triggert `from gnom_hub.soul import soul_instance` → torch. Das ist NICHT Teil des Write-Handler-Fixes. **Bestehender Bug, separat zu fixen.**

**Andere Soul-Imports im Hub (für CoderAG-Kontext relevant):**

```
src/gnom_hub/agents/agent_base.py:1,100,106,140,156,178,202 — viele Imports
src/gnom_hub/agents/swarm/swarm_comms.py:205
src/gnom_hub/agents/swarm/workflow_engine.py:128
src/gnom_hub/agents/swarm/swarm_coordinator.py:11,141
src/gnom_hub/agents/role_tools.py:11
```

**Aber:** das sind alles Imports in `agent_base.py` / `swarm/`, NICHT in `actions/`. Beim Worker-Run wird `agent_base.py` geladen (jedes Mal) — das triggert `gnom_hub.soul` Import. **Cold-Start des WORKERS selbst** ist also nicht weg, nur der Cold-Start des WRITE-HANDLERS. Beim ersten Worker-Message-Processing wird `agent_base.py` geladen → sentence_transformers/torch geladen → 30-40s. **Schrift-Aktion danach ist schnell** (weil schon gecacht), aber die erste Aktion hängt.

**Befund:** Memory-Recall war präzise — der **Write-Handler-spezifische** Hang ist gefixt. Der **allgemeine** Cold-Start (über `agent_base.py`) bleibt. Tests grün, aber User-Wahrnehmung "Worker startet langsam" bleibt.

### 2.6 `showbox_write` Dead-Token (CoderAG-spezifisch)

**Verification `grep "showbox_write" src/`:**

```
config/agents/{CoderAG,WriterAG,EditorAG,ResearcherAG,GeneralAG,SoulAG,SecurityAG,WatchdogAG}.json — JSON-Defs
src/gnom_hub/db/generalag_repo.py:7 — Kommentar (Doku)
plans/agent_comm_showbox.yaml:231 — Test-Config (nutzt `perms = ['read', 'write', 'showbox_write']`)
tests/test_action_write_e2e.py:38 — Test-Perms
```

**KEIN Production-Code-Pfad** der `if "showbox_write" in perms:` checkt. Bestätigt soulag.md:V2 (HIGH-Befund).

**CoderAG-Auswirkung:** CoderAG hat in Python `["read", "write", "run"]` (3 Tokens). Im JSON hätte er 4. Aber weil der Runtime-Pfad sowieso nicht `showbox_write` enforced, ist die Diskrepanz **funktional irrelevant** — CoderAG schreibt IMMER in Showbox (siehe action_exec.py:115 `save_showbox_presentation(...)`).

---

## 3. Code-Realität (Write-Pfad)

### 3.1 Was passiert mit dem File bei `[WRITE: foo.md]x=1[/WRITE]`?

**Vollständiger Trace:**

```
1. agent_base.py:115-121 (für CoderAG via swarm_comms)
   r = await ask_router(...)
   processed = await _to_thread(process_actions, r.content, {"name": "CoderAG"}, perms, False, wd)

2. action_handlers.py:48-181 process_actions()
   - Matcht [WRITE: foo.md]x=1[/WRITE] via regex Z. 51
   - Permission-Check Z. 62: "write" in perms? ✅ (CoderAG hat write)
   - verify_write() gatekeeper.py:291-324:
     * check_blockade_rules() (User-Regeln)
     * is_worker_blocked() — `src/gnom_hub` etc. blockiert
     * is_security_block() — high-risk patterns blockiert
     * request_capability() — logged
   - Wenn ✅: append zu w_ms

3. action_handlers.py:118
   ans = handle_write(ans, w_ms, agent, perms, bs_mode, wd)

4. action_write.py:9-70 handle_write()
   - fname = "foo.md", content = "x=1"
   - Markdown-Fence-Stripping Z. 12: re.sub(r"^```\w*\n", ...) und r"\n```$"
   - _safe(wd, "foo.md", perms) — Path-Validator: prüft ob foo.md im Workspace
   - os.makedirs(os.path.dirname(fpath), exist_ok=True) — legt subdir an
   - Wenn fpath existiert UND base == "index.html": counter-loop für index1.html etc.
   - Wenn fpath existiert: shutil.copy2(fpath, fpath + ".bak") — BACKUP
   - seal_content(content) = content.strip()
   - **open(fpath, "w").write(sealed_content)** — WRITE PASSIERT HIER (Z. 38-39)
   - Wenn base.startswith("index") UND "run" in perms: `open` auf macOS öffnet Browser
   - add_agent_metadata(...) aus gnom_hub.core.zwc_codec → ZWC-Block mit agent+timestamp
   - return: ans mit "[System: Datei 'foo.md' gespeichert unter /abs/path]"

5. Rückgabe an action_handlers.py → ersetzt im Antwort-Text
6. agent_base.py:121-130
   raw = processed or r.content
   self._req("post", "/api/chat", {"content": think_display, "sender": "CoderAG"})
```

**Write-Pfad ist robust.** Zwei Sicherheits-Layer vor Disk-Write:
1. Permission-Check (action_handlers.py:62)
2. Path-Validator (action_handlers.py:65 → gatekeeper.py:311-313)

**Write-Pfad ist NICHT atomar.** Backup wird VOR Write gemacht (action_write.py:34-35), Write passiert Z. 38-39. Bei Crash zwischen Backup und Write: Datei fehlt, Backup vorhanden. **Akzeptabel.**

**Write-Pfad ist NICHT transaktional für mehrere Dateien.** Worker kann `[WRITE: a.md]...[/WRITE] [WRITE: b.md]...[/WRITE]` senden. Jeder wird einzeln verarbeitet. Wenn a.md klappt und b.md failt (z.B. weil quota) → **inkonsistenter Zustand.**

### 3.2 In welche DB-Tabelle wird das geloggt?

**3 Logs entstehen pro Write:**

1. **`audit_log`** (via `_audit_security()` action_handlers.py:19-45):
   - **NUR** wenn `name=='securityag' AND ('godmode'|'run'|'write') in perms`
   - **Für CoderAG: NEIN** — CoderAG ist nicht SecurityAG
   - Aber: bei jedem Write wird `_audit_security(agent, perms, "write", fn, "allowed")` aufgerufen (Z. 66) → Early-Return weil `agent.get("name") != "securityag"`

2. **`capability_log`** (via `request_capability()` gatekeeper.py:323):
   - Schreibt in `capability_requests` Tabelle (nicht audit_log)
   - agent=agent_name, capability="WRITE", resource=fn, status="AutoApprovedSafePath"

3. **`audit_log` write_fail** (via `record_write_fail()` action_write.py:62-66):
   - **NUR** bei Exception im try-Block (Z. 18-59)
   - event_type="write_fail", details={path, error}
   - Bei Erfolg: **KEIN expliziter audit_log-Eintrag für "write_success"**

**Befund: Erfolgreiche Writes werden NICHT zentral in `audit_log` geloggt.** Nur `capability_log` (für Auto-Approve) und `security_audit_log` (nur SecurityAG-Aktionen). **Lücke:** "CoderAG hat foo.md geschrieben" ist nicht direkt in audit_log abfragbar — nur via capability_log + JOIN mit agents-Tabelle.

**Bei Fehlschlag:** `record_write_fail` schreibt `event_type="write_fail"` in `audit_log`. Plus `chat_repo.record_cooldown` würde zuschlagen wenn der Write-Tag gefiltert würde (was er nicht wird — `[WRITE:...]` ist erlaubte Ausgabe).

### 3.3 CoderAG's Workspace — was passiert wo?

**Bei `[WRITE: foo.md]x=1[/WRITE]` mit wd=`/Users/landjunge/gnom-Workspace/default/`:**
- fpath = `os.path.realpath(os.path.join("/Users/landjunge/gnom-Workspace/default/", "foo.md"))` = `/Users/landjunge/gnom-Workspace/default/foo.md`
- _safe() check: ist der pfad im WORKSPACE_DIR (~/gnom-Workspace)? Ja ✅
- Datei wird in `/Users/landjunge/gnom-Workspace/default/foo.md` geschrieben

**Bei `[WRITE: ../escape.txt]x=1[/WRITE]`:**
- fpath = `os.path.realpath(os.path.join("/Users/landjunge/gnom-Workspace/default/", "../escape.txt"))` = `/Users/landjunge/gnom-Workspace/escape.txt`
- _safe() check: fpath == ws_real? Nein. `startswith(ws_real + os.sep)`? Ja (es IST in `gnom-Workspace/`, nur nicht in `default/`)
- _safe() returnt fpath (erlaubt) — Worker kann in `gnom-Workspace/` schreiben, aber nicht in `gnom-hub/` oder `/etc/`

**Bewertung:** `path_validator.py:21-22` hat **off-by-one Schutz** (`startswith(ws_real + os.sep)`) gegen `<workspace>-evil/` Sibling-Dirs. Aber Worker können mit `../` eine Ebene hoch (von `default/` zu `gnom-Workspace/`). **Böswilliger Worker könnte Files in `gnom-Workspace/` schreiben.** Für die 4 Worker (CoderAG, WriterAG, EditorAG, ResearcherAG) ist das vermutlich OK, weil der User-Workspace eh `gnom-Workspace/` ist.

**Bei `[WRITE: /etc/passwd]x=1[/WRITE]`:**
- fpath ist absolut. `_safe(wd, "/etc/passwd", perms)` mit perms=["read", "write", "run"]
- perms truthy → perms=True branch in `_safe()` Z. 23-24: returnt fpath
- **Würde durchgehen** ohne `is_system_path` Check im `_safe()` selbst
- ABER: `is_worker_blocked()` in `verify_write()` ruft `is_system_path(f)` Z. 146 → returnt True für `/etc/passwd`
- → `verify_write()` returnt False → nicht in w_ms → ans bekommt `[Gatekeeper: Schreibzugriff auf '/etc/passwd' verweigert.]`

**Bewertung:** Defense-in-depth funktioniert. `_safe()` ist nur Pfad-Normalisierung + Workspace-Check, NICHT die finale Authorisierung. `verify_write()` ist die Authorisierung. `is_system_path()` ist der System-Pfad-Check.

---

## 4. Widersprüche INTERN

### 4.1 CoderAG Identity vs. Live-soul.json

| Quelle | CoderAG-Inhalt |
|---|---|
| `CoderAG.json:18` (Identity) | 4.968 Zeichen, 4 Sektionen, Workspace-Pin, Sprech-Verbot, Showbox-Buttons-Pflicht |
| `agent_definitions.py:235-242` (sys_prompt) | ~400 Zeichen, nur 1 Absatz Rollen-Intro. **KEIN** Workspace-Pin, **KEIN** Sprech-Verbot, **KEIN** Showbox-Buttons-Pflicht |
| `agent_definitions.py:247` (DE perms) | `["read", "write", "run"]` |
| `agent_definitions.py:252` (EN perms) | `["read", "write", "run"]` |
| `CoderAG.json:19-24` (JSON perms) | `["read", "write", "run", "showbox_write"]` |
| Live `soul.json` | `["read", "write", "run"]` (matcht Python) |

**Drift:**
- Identity: JSON hat 4.968 Zeichen mit allen Pflichten; Python hat ~400 Zeichen ohne Pflichten
- Permissions: JSON hat 4, Python hat 3, Live-Disk hat 3
- Workspace-Pin: nur in JSON erwähnt
- Sprech-Verbot: nur in JSON erwähnt
- Showbox-Buttons-Pflicht: nur in JSON erwähnt

**Welche Quelle gewinnt?**
- `coderAG.py:1` und `run_agent.py:19` lesen aus `agent_definitions.py` (Python)
- `agent_base.py:118` liest aus `get_soul(self.n)` → `soul_initializer.py:30-81` → liest aus `agent_definitions.py` (Python)
- `core/prompt/builder.py:136` baut [TOOLS]-Block aus JSON-Perms (für System-Prompt-Text, nicht für Runtime)

→ **Python ist SSOT für Runtime, JSON ist SSOT für Prompt-Text.** Beide driften stark. Worker-Prompts haben die volle Identity; Runtime-Perms sind abgespeckt.

**Befund:** CoderAG als BaseAgent-Instanz bekommt den **abgespeckten sys_prompt** (nur Rollen-Intro). Die detaillierte Identity (Workspace-Pin, Sprech-Verbot, Showbox-Buttons) wird **NICHT injiziert** über den `coderAG.py`-Pfad. Wird sie woanders injiziert?

**Verifikation — `tool_registry.format_tools_prompt()`:** nicht gelesen, aber der Aufruf in `agent_base.py:12` `t_p = format_tools_prompt(get_soul(name), name); self.sys = (self.sys + "\n\n" + t_p) if self.sys else t_p` — kombiniert nur den soul-`get_soul()`-Output mit sys_prompt. `get_soul()` returnt das `directive` aus `agent_definitions.py:243-246` (1 Satz). **NICHT die ganze JSON-Identity.**

→ **CoderAG als BaseAgent hat faktisch nur ~400 Zeichen sys_prompt + 1-Satz-Direktive.** Die 4.968-Zeichen JSON-Identity ist **DOKUMENTATION, nicht Runtime.** SoulAG-Audit §3.1 hat das gleiche Phänomen gefunden.

### 4.2 CoderAG Identity Hardcoded Pfad vs. dynamischer Workspace

(siehe §2.1 für Details)

CoderAG Identity sagt "Workspace ist `/Users/landjunge/gnom-Workspace/default/`". `Config.workspace_dir()` löst zur Laufzeit dynamisch auf (mit Hot-Reload via State-Override). **CoderAG's hardcoded Pin ist eine Lüge wenn der User den Workspace wechselt.**

### 4.3 `run`-Permission Whitelist-Intent vs. Token-basierte Realität

**Spec in Identity:** "Workspace + Chat-History reichen für Tool-Auswahl" (CoderAG.json:30 notes).

**Realität:** CoderAG hat `run` UND `write` UND `read`. Mit `run` kann er:
- `python3 -c "import os; os.system('rm -rf ~)'"` ← wird NICHT von Whitelist erkannt (Token-basiert)
- `bash -c "evil-stuff"` ← wird NICHT von Whitelist erkannt
- `nohup background-daemon &` ← wird unkontrolliert gestartet
- `pip install malicious-package` ← Whitelist erlaubt pip install (gatekeeper.py:419-425 prüft nur uninstall)

**Defense-in-depth ist ILLUSION** für Python/Bash-Stuffing. Die Whitelist funktioniert nur für **top-level commands** die syntaktisch sauber sind.

### 4.4 Workspace-Boundary Lücke: Worker schreibt mit `..` hoch

`path_validator._safe()` Z. 21-22:
```python
return p if p == ws_real or p.startswith(ws_real + os.sep) else None
```

`ws_real = ~/gnom-Workspace` (nicht `~/gnom-Workspace/default/`). `wd` (vom Caller) ist `~/gnom-Workspace/default/`. Worker schreibt `[WRITE: ../foo.md]`:
- `os.path.join("~/gnom-Workspace/default/", "../foo.md")` = `~/gnom-Workspace/default/../foo.md`
- `os.path.realpath(...)` = `~/gnom-Workspace/foo.md`
- Startswith `ws_real + os.sep` (`~/gnom-Workspace/`) → True
- → **erlaubt, schreibt nach `~/gnom-Workspace/foo.md` (SIBLING von `default/`)**

**Kein Schutz** dass Worker in seinem `default/`-Subdir bleibt. Sie können `gnom-Workspace/` selbst zumüllen.

---

## 5. Widersprüche ZU ANDEREN AGENTS

### 5.1 Struktureller Vergleich der 4 Worker

| Aspekt | CoderAG | WriterAG | EditorAG | ResearcherAG |
|---|---|---|---|---|
| JSON-Version | v5.3 | v5.3 | v5.3 | v5.3 |
| Workspace-Pin | `gnom-Workspace/default/` | `gnom-Workspace/default/` | `gnom-Workspace/default/` | `gnom-Workspace/default/` |
| Sprech-Verbot-Block | ✅ | ✅ | ✅ | ✅ |
| Showbox+Buttons-Block | ✅ | ✅ | ✅ | ✅ |
| Color | Orange | Grün | Pink | Gelb |
| JSON-Perms | `[read, write, run, showbox_write]` | `[read, write, crawl, showbox_write]` | `[read, write, showbox_write]` | `[read, crawl, web_search, browser, showbox_write]` |
| Python-Perms | `[read, write, run]` | `[read, write, crawl]` | `[read, write]` | `[read, crawl, web_search, browser]` |
| `run` in Python? | ✅ | ❌ | ❌ | ❌ |
| `crawl` in Python? | ❌ | ✅ | ❌ | ✅ |
| `web_search` in Python? | ❌ | ❌ | ❌ | ✅ |
| `browser` in Python? | ❌ | ❌ | ❌ | ✅ |
| Special Capability | nur CoderAG | nur WriterAG | nur EditorAG | nur ResearcherAG |
| Sliders | identisch | identisch | identisch | identisch |
| prompt_blocks | wortwörtlich identisch | wortwörtlich identisch | wortwörtlich identisch | wortwörtlich identisch |
| sys_prompt (Python) | ~400 chars, alle strukturell identisch | identisch | identisch | identisch |
| Worker-Name in WORKER_AGENT_NAMES | ✅ | ✅ | ✅ | ✅ |
| Brainstorm-Rate (`adaptive_decomposition.py:27-33`) | $0.05/s | $0.03/s | $0.025/s | $0.03/s |
| Default-Duration (`adaptive_decomposition.py:44-48`) | 25s | 15s | 10s | 12s |

**Befund:** Die 4 Worker sind **Copy-Paste-Templates** mit Domain-spezifischen Variationen:
- **Sinnvolle Variation:** Python-Perms (run vs crawl vs web_search/browser) — passt zur Rolle
- **Sinnvolle Variation:** Color — UI-Differenzierung
- **Sinnvolle Variation:** Pricing/Duration im AdaptiveDecomposition — passt zur erwarteten Task-Komplexität
- **Copy-Paste ohne Wert:** Sliders (alle 5 = 2), prompt_blocks (wortwörtlich identisch), Workspace-Pin (alle gleich), Sprech-Verbot-Block (alle gleich), Showbox-Buttons-Block (alle gleich)

**Cross-Ref Befund:** Alle 4 Worker haben **IDENTISCHE** Sprech-Verbot-Sektion. Das ist **gewollt** (User-Mandat 2026-06-28 02:04 gilt für ALLE Worker). Copy-Paste ist hier OK weil der Verbot einheitlich sein muss.

Aber: **Worker-spezifische Sprech-Verbot-Beispiele unterscheiden sich** (CoderAG: "Datei geschrieben unter...", WriterAG: "Hier ist der Text...", EditorAG: "QA-Review fertig...", ResearcherAG: "Recherche abgeschlossen..."). Das ist sinnvoll — jeder Worker hat andere typische "Talk-Versuchungen".

### 5.2 `run`-Permission: CoderAG ist der einzige Worker mit Shell

**Warum sinnvoll:**
- CoderAG schreibt Code → muss Code ausführen können (`python3 script.py`, `pytest`, `pip install`)
- WriterAG schreibt nur Texte/Markdown → keine Shell nötig
- EditorAG refactored → könnte Shell wollen (z.B. `ruff check`), aber Perms lassen es nicht zu
- ResearcherAG crawlt Web → nutzt `crawl_smart()`, `web_search`, `browser` statt Shell

**Warum problematisch:**
- CoderAG mit `run` kann **auch destruktive Befehle** ausführen (siehe §4.3)
- Andere Worker (z.B. EditorAG) die refactored → müssten auch `run` haben, kriegen es aber nicht
- **Asymmetrie:** EditorAG kann Code-QA machen aber nicht `python -m pytest` ausführen

**EditorAG-Spec-Verify:** EditorAG-Python-Perms = `["read", "write"]` (agent_definitions.py:322). `action_handlers.py:97-99`: `if "run" not in perms: ... [System: EditorAG hat keine SHELL-Berechtigung.]`. **EditorAG kann KEIN pytest ausführen.** Bug oder Feature?

**Bewertung:** Bug. EditorAG soll "refactored und qualitätssichert" (Identity), aber kann keine Linter/Tests laufen lassen. **Spec-Lücke oder bewusste Einschränkung?**

### 5.3 Worker-Prompts (Python) sind fast identisch

```python
# CoderAG sys_prompt agent_definitions.py:235-242
"Du bist CoderAG — der CODER. Du denkst laut. Jeder Gedanke muss über TTS hörbar sein. "
"Du erhältst Aufträge aus der Soul→GeneralAG-Delegationskette. Der User kennt dich NICHT direkt — deine Outputs erreichen ihn nur via SoulAG. "
"Du kommunizierst niemals direkt mit dem User. Alle Ausgaben erfolgen ausschließlich über die Showbox mit Buttons. "
"Du schreibst sauberen, gut dokumentierten Code. "
"Du hast nur Schreibrechte in deinem Workspace. "
"Deine Farbe ist immer Orange."

# WriterAG sys_prompt agent_definitions.py:261-267 — wortwörtlich identisch bis auf:
#   SCHREIBER statt CODER, "schreibst klar..." statt "schreibst sauberen Code", GRÜN statt ORANGE
```

**Befund:** Template. Domain-spezifische Substitution von 3 Feldern. **Aber:** Das Template ist ~85% des JSON-Identity-Inhalts was fehlt. BaseAgent-Instanzen bekommen nur das Template.

**CoderAG vs. WriterAG funktional:**
- CoderAG darf `run` (Code ausführen) — WriterAG nicht
- Beide dürfen `write` (Files schreiben)
- WriterAG hat `crawl` — CoderAG nicht
- Beide haben `read`

**Praktisch:** CoderAG kann `[SHELL: pytest]` → Worker schreibt `test_foo.py` und führt Tests aus. WriterAG kann nur `[WRITE: doc.md]...[/WRITE]`. **Asymmetrie ist konsistent mit Rollen.**

### 5.4 Brainstorm-Routing-Default: CoderAG vor WriterAG

`core/utils/gd_fallback.py:20`:
```python
opts = {"CoderAG": ["GeneralAG", "WriterAG"], "WriterAG": ["GeneralAG", "EditorAG"]}
```

→ **Bei CoderAG-Failure fällt System auf WriterAG zurück** (Text statt Code). Sinnvoll als degraded-mode.

`adaptive_decomposition.py:84-97`:
```python
if "code" in task_lower or "landingpage" in task_lower:
    return route_a  # Coder + Writer parallel
elif "blog" in task_lower or "text" in task_lower:
    return route_b  # Writer → Editor serial
else:
    return route_c  # Single General
```

→ **Code-Tasks → Coder+Writer parallel.** Sinnvoll.
→ **Text-Tasks → Writer→Editor serial.** Sinnvoll.
→ **Andere → General solo.** Fallback.

**CoderAG ist der "primary" für Code-Tasks** im Adaptive-Routing. Cross-Validation: `soul_tasks.py:465-470` listet CoderAG als Default für "code" task_type.

### 5.5 Workspace-Pin ist bei ALLEN 8 Agents identisch

(siehe §2.1 und §4.2)

**Cross-Ref Befund:** SoulAG.json, GeneralAG.json, CoderAG.json, WriterAG.json, EditorAG.json, ResearcherAG.json, SecurityAG.json, WatchdogAG.json — **alle** haben entweder:
- Den wortwörtlich identischen `gnom-Workspace/default/` Pin (Worker)
- ODER gar keinen Pin (System-Agents — verlassen sich auf andere Mechanismen)

**Kein Agent-Config** kennt den dynamischen Workspace. **Systematisches Pin-Problem.**

---

## 6. Lücken

### 6.1 Was CoderAG können sollte, aber undefiniert ist

1. **Dynamischer Workspace-Pin:** Identity sagt `gnom-Workspace/default/`, User kann in UI umstellen auf z.B. `~/projects/foo`. CoderAG würde in `foo/` schreiben — Identity behauptet weiter `default/`. **Lüge.**
2. **EditorAG-spezifische Berechtigungen:** EditorAG soll Code-QA machen (laut Identity) aber hat kein `run` (siehe §5.2). **Asymmetrie ohne Begründung.**
3. **Cold-Start der Worker-BaseAgent-Instanz:** `agent_base.py:1,100,106,140,156,178,202` importiert mehrfach `gnom_hub.soul.*`. **Erste Worker-Message hängt 30-40s.** Memory-Recall war Write-Handler-only — der allgemeine Cold-Start bleibt. test_action_write_e2e.py:22-27 dokumentiert den orthogonalen Bug.
4. **Bash-Stuffing-Schutz:** `bash -c "..."` und `python -c "..."` umgehen die Token-basierte Whitelist. **Defense-in-depth ist Illusion für embedded Code.** Siehe §4.3.
5. **Workspace-`..`-Flucht:** Worker kann mit `../` aus `default/` in `gnom-Workspace/` schreiben. **Kein Subdir-Lock.** Siehe §4.4.
6. **Multi-Write-Transaktionalität:** Mehrere `[WRITE:]` in einer Antwort sind nicht atomar. Halb-failure möglich. Siehe §3.1.
7. **Audit-Log für erfolgreiche Writes:** `record_write_fail` loggt nur Failures. Erfolgreiche Writes sind nur in `capability_log`. **Lücke in der Audit-Trail-Vollständigkeit.** Siehe §3.2.
8. **Showbox-Buttons-Pflicht erzwungen?** `handle_showbox()` enforced keine Buttons. CoderAG könnte `[→ Showbox: x]{"slides": [...]}` ohne Buttons senden — wird gespeichert. **Kein technischer Zwang.**

### 6.2 Welche Übergaben fehlen

- **CoderAG → SoulAG:** Worker hat keinen Pfad um SoulAG über "Code-Deliverable" zu informieren außer Showbox. SoulAG müsste alle Worker-Showbox-Ausgaben pollen.
- **CoderAG → User:** Worker darf nicht direkt mit User reden. Bei User-Frage "ist mein Code gut?" muss CoderAG → GeneralAG → SoulAG → User.
- **CoderAG Error-Reporting:** Bei `[SHELL:]` failure wird `[Shell blockiert ...]` oder `[Shell-Fehler ...]` generiert. Werden diese Errors dem User sichtbar? Geht via `add_chat_message("CoderAG", ...)` durch den Worker-Sprech-Verbot-Filter. `has_code_block` oder `has_write_read` ist nicht da. **`[Shell-Fehler: ...]` würde gedroppt!** ⚠️

**Verifikation `chat_repo._agent_message_filter` für CoderAG-SHELL-Fehler:**
- Inhalt: `[Shell blockiert (high): rm -rf / nicht erlaubt.]`
- `has_write_read` = `"[WRITE:" in content or "[READ:" in content` → False
- `has_code_block` = `"```" in content` → False
- `has_meaningful_showbox` = False (kein Showbox-Tag)
- → **GEDROPpt** mit reason="worker_sprech_verbot"
- → **CoderAG kann nicht über Shell-Fehler berichten!**

Das ist ein **BUG**: CoderAG's Shell-Fehler werden vom Worker-Filter geschluckt. User sieht nur den leeren `processed` String, der per `r.content` fallback geladen wird (agent_base.py:124). Aber dann ist der `[Shell blockiert ...]` Teil nicht im Frontend sichtbar (war im `processed` enthalten, wurde aber gedroppt).

**Workaround:** CoderAG müsste Shell-Errors in Showbox wrappen (`[→ Showbox: shell-error]{"slides": [...]}`). Ist das im Identity-Prompt vorgesehen? Nein, in CoderAG.json ist das nicht spezifiziert.

### 6.3 Edge-Cases nicht abgedeckt

1. **Backup-Konflikt:** `action_write.py:35` `shutil.copy2(fpath, fpath + ".bak")` — überschreibt vorheriges `.bak` ohne Warnung. Bei 3× Write auf dieselbe Datei geht die 1. Generation verloren.
2. **Concurrent Writes:** Zwei Worker schreiben gleichzeitig dieselbe Datei. Kein Lock. Race-Condition. SQLite hat Lock, aber File-Write ist außerhalb der DB.
3. **Disk-Quota:** `os.write` ohne Check ob noch Platz. Worker könnte `/Users` vollschreiben.
4. **Symlink-Attacke:** `[WRITE: foo.md]...[/WRITE]` mit `foo.md` als Symlink auf `/etc/passwd` → `_safe()` macht `realpath()` Z. 18, resolved to `/etc/passwd`, BUT `verify_write()` `is_worker_blocked` checkt `is_system_path(f)` (mit `f` = originaler fname, NICHT realpath). **Möglich Bug.** ⚠️
5. **Worker schreibt Binary:** `[WRITE: foo.png]\x89PNG...[/WRITE]` — JSON-Payload ist UTF-8, aber Content könnte non-UTF8 sein. `open(fpath, "w", encoding="utf-8")` würde fehlschlagen. Kein binary-mode Fallback.
6. **Path-Traversal mit encoded chars:** `%2e%2e/foo` (URL-encoded) — wird von `_safe` NICHT decoded. Aber `os.path.realpath` macht das normalerweise nicht. Edge case.
7. **Workspace-Quota:** Kein Tracking wie viel Worker geschrieben hat. Disk-Full-Modus möglich.

---

## 7. Konkrete Verbesserungsvorschläge (priorisiert)

### V1 [HOCH] Workspace-Pin Dynamisierung

- **Was:** CoderAG Identity (und alle 4 Worker) soll nicht `gnom-Workspace/default/` hardcoden, sondern den **live** Workspace-Pfad aus `Config.workspace_dir() + active_project` referenzieren.
- **Warum:** Identity lügt in mindestens 2 Szenarien (User-Override, Project-Wechsel). Systematisches Pin-Problem über alle 8 Agents.
- **Datei:** `config/agents/CoderAG.json:18` Identity Z. ~19-24 + 3 weitere Worker-Configs
- **Vorschlag:** Identity-Section ersetzen durch:
  ```
  Dein Workspace-Pfad wird dir bei jedem Auftrag als [WORKSPACE: /abs/path | Dateien: ...] injiziert
  (siehe brainstorm_helpers.py:15-16). NIEMALS nach /Users/landjunge/gnom-hub/ schreiben.
  ```
- **Risiko:** Niedrig. Agent-Prompts funktionieren weiterhin, weil der Workspace eh per `[WORKSPACE: ...]`-Injection im System-Prompt steht.

### V2 [HOCH] Worker-Sprech-Verbot-Lücke für Shell-Errors fixen

- **Was:** `chat_repo._agent_message_filter()` Worker-Branch soll auch `[SHELL ...]` / `[Browser ...]` / `[Desktop ...]` / `[Video ...]` System-Meldungen als "Purpose-Tag" akzeptieren.
- **Warum:** CoderAG kann aktuell nicht über Shell-Errors berichten — werden gedroppt. User sieht Fehler nicht.
- **Datei:** `src/gnom_hub/db/chat_repo.py:71-94` Worker-Filter. Substanz-Marker erweitern:
  ```python
  _SUBSTANCE_MARKERS = ("```", "[WRITE:", "[READ:", '"slides":', '"slide_id":',
                        "[Shell", "[Browser", "[Desktop", "[Video", "[System:")
  ```
- **Risiko:** Niedrig. Substanz-Marker sind ohnehin schon recht breit.

### V3 [HOCH] Cold-Start des agent_base.py Imports fixen

- **Was:** `agent_base.py:1` importiert `from gnom_hub.soul import get_soul` und `from gnom_hub.infrastructure.router.router import ask_router` — beides ist Heavy-Weight. Lazy-Loading in den `__init__`/`run` Methoden verschieben.
- **Warum:** Memory-Recall war Write-Handler-only. **Erste Worker-Message hängt 30-40s.** test_action_write_e2e.py:22-27 dokumentiert den Bug.
- **Datei:** `src/gnom_hub/agents/agent_base.py:1,100,106,140,156,178,202`
- **Vorschlag:** 
  ```python
  # statt: from gnom_hub.soul import get_soul
  # in __init__:
  def _get_soul(self):
      from gnom_hub.soul import get_soul
      return get_soul(self.n)
  ```
- **Risiko:** Mittel. Mehrere `await _to_thread` Calls brauchen lazy imports. Regression-Risiko bei race conditions.

### V4 [HOCH] Write-Success in audit_log loggen

- **Was:** Bei erfolgreichem `[WRITE:]` einen `event_type="write_success"` Eintrag in `audit_log` schreiben.
- **Warum:** Aktuell nur Failures werden geloggt. Audit-Trail unvollständig. SecurityAG-Audit-Hook (`_audit_security()`) ist nur für SecurityAG aktiv.
- **Datei:** `src/gnom_hub/agents/actions/action_write.py:38-39` (nach open().write()) + `src/gnom_hub/core/audit_helpers.py` (neue `record_write_success()` Funktion).
- **Risiko:** Niedrig. Volume-Increase in `audit_log` (CAP-Mechanismus existiert schon in `system_repo.py:107-118`).

### V5 [MITTEL] EditorAG `run`-Permission Diskussion

- **Was:** Klären ob EditorAG `run` braucht (für pytest/ruff) oder ob das per CoderAG-Sub-Delegation läuft.
- **Warum:** EditorAG soll Code-QA/refactor, kann aber keine Tests laufen lassen. Asymmetrie zu CoderAG (der `run` hat).
- **Datei:** `src/gnom_hub/agents/agent_definitions.py:322` (EditorAG-Perms) + `config/agents/EditorAG.json:19-23` (JSON-Perms).
- **Vorschlag:** Entweder `run` zu EditorAG-Python-Perms hinzufügen ODER in EditorAG-Identity explizit sagen "für Tests delegiere an CoderAG".
- **Risiko:** Niedrig wenn Klarstellung, mittel wenn echte Permission-Erweiterung (mehr Sandbox-Risiko).

### V6 [MITTEL] Bash/Python-Stuffing-Schutz

- **Was:** `is_command_safe_and_whitelisted()` erweitern um Risk-Check auf `python -c` / `bash -c` Argumente (Suche nach `os.system`, `subprocess.*shell=True`, `eval`, `exec` in args).
- **Warum:** Token-basierte Whitelist umgehbar durch embedded Code.
- **Datei:** `src/gnom_hub/core/security/gatekeeper.py:350-432`.
- **Risiko:** Mittel. False positives möglich (z.B. `python3 -c "print('eval is dangerous')"` würde triggern). Kalibrierung nötig.

### V7 [MITTEL] Workspace-Subdir-Lock

- **Was:** `path_validator._safe()` soll verhindern dass Worker mit `../` aus seinem `default/`-Subdir rausklettern. Workspace-Boundary auf `<workspace>/<active_project>/` festlegen, nicht `<workspace>/`.
- **Warum:** Aktuell kann Worker in `gnom-Workspace/` selbst schreiben (Sibling des `default/`-Projekt-Dirs).
- **Datei:** `src/gnom_hub/core/security/path_validator.py:7-24` (Parameter für Subdir-Project-Boundary).
- **Risiko:** Niedrig. Subdir-Lock ist restriktiver — Worker können weniger, aber sicherer.

### V8 [MITTEL] Backup-Strategie verbessern

- **Was:** Statt `fpath + ".bak"` (überschreibt vorheriges Backup) ein rotierendes Backup-System: `fpath.bak1`, `.bak2`, `.bak3`.
- **Warum:** Aktuell geht Backup-Historie bei mehrfachem Write verloren.
- **Datei:** `src/gnom_hub/agents/actions/action_write.py:34-35`.
- **Risiko:** Niedrig. Mehr Disk-Verbrauch.

### V9 [NIEDRIG] Multi-Write-Transaktionalität

- **Was:** Worker-Outputs mit mehreren `[WRITE:]` Tags als atomar behandeln. Alle Files schreiben oder keine. Pre-Allocate alle Files in temp, dann umbenennen.
- **Warum:** Halb-failure Zustand möglich.
- **Datei:** `src/gnom_hub/agents/actions/action_handlers.py:48-181` process_actions().
- **Risiko:** Hoch. Komplex, race conditions, nicht-trivialer Test-Aufwand.

### V10 [NIEDRIG] Symlink-Attacke Fix

- **Was:** `is_system_path()` mit `realpath()` (nicht `f`) checken. Aktuell `path_validator.py:146` `if f and is_system_path(f):` — `f` ist original, nicht realpath.
- **Warum:** Symlink kann Workspace-Bypass erlauben.
- **Datei:** `src/gnom_hub/core/security/path_validator.py:139-157`.
- **Risiko:** Niedrig. Defense-in-depth, nicht Hauptvektor.

### V11 [NIEDRIG] showbox_write Dead-Token Konsolidierung

- **Was:** Entweder Implementierung in `action_handlers.py` (Showbox-Check `"showbox_write" in perms`) ODER aus allen 8 JSONs entfernen.
- **Warum:** `showbox_write` ist in 8/8 JSON-Configs, kein Code enforced es. Täuschend echte Spec.
- **Risiko:** Niedrig wenn Entfernen, mittel wenn echte Implementierung.

### V12 [NIEDRIG] Sliders für CoderAG individualisieren

- **Was:** Mindestens `precision: 3` ("Verify everything carefully. Output must be correct.") für CoderAG.
- **Warum:** Code-Generierung braucht höhere Precision als die "medium" Stufe 2.
- **Datei:** `config/agents/CoderAG.json:4-10`.
- **Risiko:** Niedrig (Slider sind aktuell inert — siehe soulag.md:V9).

### V13 [NIEDRIG] Binary-Write-Support

- **Was:** `[WRITE: foo.png]<base64>[/WRITE]` als Alternative für Binary-Files.
- **Warum:** Aktuell nur UTF-8 Text-Writes. Worker kann keine Bilder direkt schreiben.
- **Datei:** `src/gnom_hub/agents/actions/action_write.py:9-70` + neuer Marker `[BINARY: ...]`.
- **Risiko:** Mittel. Base64-Decode-Fehler, große Files in LLM-Context.

### V14 [NIEDRIG] Write-Disk-Quota

- **Was:** Per-Worker-Quota (z.B. max 100MB pro Stunde). Überschritten → Worker blockiert.
- **Warum:** Disk-Full-Schutz.
- **Datei:** Neue `worker_disk_usage` Tabelle + Cron-Reset.
- **Risiko:** Mittel. Quota-Verwaltung komplex.

---

## 8. Cross-Check-Notes für die Synthese

Diese Stichpunkte sollte der Cross-Synthesis-Verifier aufgreifen:

1. **CoderAG ist der EINZIGE Worker mit `run`-Permission** (siehe §5.2). Andere Worker (WriterAG, EditorAG, ResearcherAG) haben kein `run`. **Asymmetrie ohne klare Begründung** in Cross-Ref.
2. **EditorAG fehlt `run` möglicherweise als Bug:** Identity sagt "refactored und qualitätssichert" (siehe §5.2), aber Python-Perms = `["read", "write"]`. Editor kann kein pytest/ruff laufen lassen.
3. **`coderAG.py` ist 1-Zeilen-Stub** identisch zu `soulAG.py` (soulag.md:495). Beide nutzen `AGENT_DEFINITIONS["<name>"]` aus Python. **JSON-Configs sind für BaseAgent-Instanzen unsichtbar.**
4. **Workspace-Pin `gnom-Workspace/default/` ist systematisch gefälscht** für alle 4 Worker + alle 4 System-Agents. Lügt bei Project-Wechsel oder User-Override (siehe §2.1).
5. **Worker-Sprech-Verbot-Lücke für System-Tags** (siehe V2, §6.2): CoderAG kann aktuell nicht über Shell-Errors berichten — `[Shell blockiert ...]` wird vom Filter gedroppt. **Akuter Bug.**
6. **Cold-Start-Hang ist nur HALB gefixt** (siehe §2.5): Write-Handler ist clean, aber `agent_base.py:1` importiert noch `gnom_hub.soul` → erste Worker-Message hängt 30-40s. **Memory-Recall "Cold-Start-Hang" war Write-Handler-spezifisch.**
7. **`showbox_write` Dead-Token über alle 8 Agents** (Cross-Validation mit soulag.md:362): in 8/8 JSONs vorhanden, in keinem Code enforced. **System-weit, nicht CoderAG-spezifisch.**
8. **Backup-Strategie überschreibt** bei mehrfachem Write (siehe §6.3.1): `.bak` wird ohne Rotation überschrieben.
9. **Workspace-`..`-Flucht** erlaubt Worker in `gnom-Workspace/`-Sibling (siehe §4.4, V7). Subdir-Lock fehlt.
10. **Audit-Log-Lücke für Write-Success** (siehe §3.2, V4): nur Failures werden in `audit_log` geschrieben, nicht Erfolge.
11. **Alle 4 Worker haben identische Sliders/prompt_blocks** (Cross-Ref soulag.md:368-374): symptomatisch, nicht Design. Vorschlag: CoderAG `precision: 3`.
12. **`brainstorm_helpers.get_workspace_dir()` und `sandbox.py:13` importieren Modul-Level `WORKSPACE_DIR`** (nicht `Config.workspace_dir()`). User-Override greift in diesen Code-Pfaden nicht. **Inkonsistente Hot-Reload-Coverage.**

---

## 9. Test-Coverage-Befund

| Test | Existenz | Deckt ab | Cold-Start-Check? |
|---|---|---|---|
| `tests/test_action_write_e2e.py` (95 Z.) | ✅ | Schreiben auf Disk, ZWC-Import-Source | ✅ ja (5s cap) |
| `tests/test_browser_action.py` | ✅ | Browser-Handler | ❌ nein |
| `tests/test_security_suite.py` | ✅ | Whitelist/Blacklist | ❌ nein |
| `tests/test_path_validator_security.py` | ✅ | Path-Validator | ❌ nein |
| `tests/test_permission_refactor.py` | ✅ | Permission-Refactor | ❌ nein |
| `tests/test_audit_log_cap.py` | ✅ | Audit-Log-Cap | n/a |

**Befund:** Test für Action-Write deckt Cold-Start ab. **Aber:** orthogonaler Cold-Start (über `init_database() → _seed_agents()`) ist NICHT getestet — test_action_write_e2e.py:22-27 dokumentiert das. **Bestehender Bug, kein Test.**

**Lücke:** Kein Test für Worker-Sprech-Verbot-Filter mit System-Tags (siehe V2). Wenn meine Hypothese stimmt dass `[Shell blockiert ...]` gedroppt wird, gibt es keinen Test der das entdecken würde.

**Lücke:** Kein Test für Workspace-Pin-Drift (User-Override, Project-Wechsel). `test_admin_system.py`/`test_admin_auth.py` sind vorhanden, aber ich habe nicht gelesen was sie genau testen.
