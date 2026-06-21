# Schema-Migration: presets.json (Layer A → Layer A v2)

**Stand:** 2026-06-21
**Task:** `plan_ec22311c/extend-schema`
**Datei:** `src/gnom_hub/core/utils/presets.json`
**Schema-Generation:** 1
**Abwärtskompatibel:** ja (Layer-A-Code lädt ohne Änderung weiter)

## Motivation

Layer A (`presets.json`) hat heute nur die **vier Worker-Agents**
(`coderag`/`researcherag`/`writerag`/`editorag`) abgebildet. Die vier
**System-Agents** (SoulAG/WatchdogAG/GeneralAG/SecurityAG) waren nur
über Layer B (`data/presets/default/system_agents.json`) verfügbar und
nicht über die UI-Presets schaltbar. Das neue Schema bildet alle 8 Agents
mit per-Agent-Feldern ab und hält das alte Format als Fallback
bereitstellen — Loader (`preset_service.load_presets()`) und alle
Konsumenten bleiben unverändert funktionsfähig.

Quelle der Anforderungen: `~/.mavis/plans/plan_ec22311c/workspace/inventory.md`
§4 ("Schema-Erweiterung-Vorschlag").

## Vorher-Schema (verbatim aus `presets.json:1-54`, Stand vor Migration)

```json
{
  "prompts": {
    "Web Development": {
      "coderag": "SYSTEM-ROLLE: WEB DEVELOPER CODER. ...",
      "researcherag": "SYSTEM-ROLLE: WEB DEV RESEARCHER. ...",
      "writerag": "SYSTEM-ROLLE: WEB DEV WRITER. ...",
      "editorag": "SYSTEM-ROLLE: WEB DEV EDITOR. ..."
    },
    "Graphic Design": { "coderag": "...", "researcherag": "...", "writerag": "...", "editorag": "..." },
    "Audio Production": { ... },
    "Video Production": { ... },
    "Content Creation": { ... },
    "Research & Analysis": { ... }
  },
  "focus": {
    "Web Development": "Fokus auf sauberen HTML, CSS, JavaScript Code, ...",
    "Graphic Design": "Fokus auf visuelle Ästhetik, ...",
    "Audio Production": "Fokus auf Sound-Synthese, ...",
    "Video Production": "Fokus auf Video-Streaming, ...",
    "Content Creation": "Fokus auf überzeugende Texte, ...",
    "Research & Analysis": "Fokus auf tiefgehende Recherche, ..."
  },
  "targets": {
    "Web Development": ["coderag", "qwen/qwen3-coder:free"],
    "Graphic Design": ["coderag", "meta-llama/llama-3.3-70b-instruct:free"],
    "Content Creation": ["writerag", "meta-llama/llama-3.3-70b-instruct:free"],
    "Research & Analysis": ["researcherag", "meta-llama/llama-3.3-70b-instruct:free"]
  }
}
```

**Limitierungen des Vorher-Schemas:**

1. Nur **4 von 8 Agents** abgedeckt — System-Agents komplett fehlend.
2. Pro Worker nur **ein einziges Feld** (`prompt`) im `prompts`-Dict.
   Keine `focus`/`target`/`creativity`/`obedience`/`enabled`-Felder pro Agent.
3. `focus` und `targets` sind **pro Kategorie**, nicht pro Agent.
   Worker-Agents derselben Kategorie teilen sich focus implizit.
4. **Keine Versions-Marker.** Schema-Änderungen sind nicht detektierbar.
5. `targets` ist eine 2-Tupel-Liste `[agent_name, model]` — Limit auf
   einen einzigen Routing-Override pro Kategorie.

## Nachher-Schema

### Top-Level-Keys (in stabiler Reihenfolge)

| Key | Typ | Zweck |
|---|---|---|
| `_schema_version` | `int` | Date-Format-Version (aktuell: 1) |
| `_schema_generation` | `int` | Zähl-Variable für Migrationen (aktuell: 1) |
| `_deprecation_notice` | `str` | Erklärt, dass alte Top-Level-Keys (`prompts`/`focus`/`targets`) bewusst erhalten bleiben |
| `_deprecation_layer` | `str` | `"A"` (Layer A ist die UI-aktive Schicht) |
| `_supersedes` | `dict` | Mapping alt → neu für Migrations-Skripte |
| `agent_groups` | `dict[str, list[str]]` | `{"system": [...], "worker": [...]}` (siehe §agent_groups) |
| `presets` | `dict[str, Preset]` | Neue strukturierte Form (siehe §presets) |
| `prompts` | `dict[str, dict[str, str]]` | **DEPRECATED**, Layer-A-Fallback — bit-identisch zum Vorher-Schema |
| `focus` | `dict[str, str]` | **DEPRECATED**, Layer-A-Fallback — bit-identisch zum Vorher-Schema |
| `targets` | `dict[str, list[str]]` | **DEPRECATED**, Layer-A-Fallback — bit-identisch zum Vorher-Schema |

### `agent_groups` (neu)

```json
"agent_groups": {
  "system": ["soulag", "watchdogag", "generalag", "securityag"],
  "worker": ["coderag", "researcherag", "writerag", "editorag"]
}
```

**Lowercase-Norm:** Layer A benutzt bereits `coderag` etc.
(`presets.json:49` im Vorher-Schema), Layer B CamelCase (`soul`,
`watchdog`, ... in `data/presets/default/system_agents.json`). Lowercase
ist die gemeinsame Norm und matched die Layer-A-Konvention. Die
Mapping-Tabelle CamelCase → Lowercase lebt in
`gnom_hub/core/agent_names.py` (frozen contract).

### `presets.<slug>` — Beispiel JSON

**Slug-Konvention:** `name.lower().replace(' ', '_').replace('&', 'and')`
(siehe `preset_service.py:_slugify`). Aus "Web Development" wird
`web_development`, aus "Research & Analysis" wird `research_and_analysis`.

```json
"presets": {
  "web_development": {
    "name": "Web Development",
    "slug": "web_development",
    "description": "Fokus auf sauberen HTML, CSS, JavaScript Code, Responsive Design, Barrierefreiheit, Performance und moderne Web-APIs.",
    "created_at": "2026-06-21T12:00:00Z",
    "updated_at": "2026-06-21T12:00:00Z",
    "schema_generation": 1,
    "agents": {
      "soulag":      { "prompt": "...", "focus": "...", "target": "auto:stage_5", "creativity": 3, "obedience": 3, "model_override": null, "model_locked": true,  "priority": "highest", "enabled": true },
      "watchdogag":  { "prompt": "...", "focus": "...", "target": "auto:stage_2", "creativity": 3, "obedience": 4, "model_override": null, "model_locked": false, "priority": "high",    "enabled": true },
      "generalag":   { "prompt": "...", "focus": "...", "target": "auto:stage_2", "creativity": 3, "obedience": 3, "model_override": null, "model_locked": false, "priority": "normal",  "enabled": true },
      "securityag":  { "prompt": "...", "focus": "...", "target": "auto:stage_2", "creativity": 3, "obedience": 4, "model_override": null, "model_locked": false, "priority": "high",    "enabled": true },
      "coderag":     { "prompt": "SYSTEM-ROLLE: WEB DEVELOPER CODER. ...", "focus": "Fokus auf sauberen HTML, ...", "target": "openrouter:qwen/qwen3-coder:free", "creativity": 3, "obedience": 3, "model_override": "qwen/qwen3-coder:free", "model_locked": false, "priority": "normal", "enabled": true },
      "researcherag":{"prompt": "SYSTEM-ROLLE: WEB DEV RESEARCHER. ...","focus": "Fokus auf sauberen HTML, ...", "target": "auto:stage_2",                     "creativity": 3, "obedience": 3, "model_override": null,                                  "model_locked": false, "priority": "normal", "enabled": true },
      "writerag":    { "prompt": "SYSTEM-ROLLE: WEB DEV WRITER. ...",    "focus": "Fokus auf sauberen HTML, ...", "target": "auto:stage_2",                     "creativity": 3, "obedience": 3, "model_override": null,                                  "model_locked": false, "priority": "normal", "enabled": true },
      "editorag":    { "prompt": "SYSTEM-ROLLE: WEB DEV EDITOR. ...",    "focus": "Fokus auf sauberen HTML, ...", "target": "auto:stage_2",                     "creativity": 3, "obedience": 3, "model_override": null,                                  "model_locked": false, "priority": "normal", "enabled": true }
    }
  }
}
```

**Per-Agent-Felder:**

| Feld | Typ | Zweck | Default |
|---|---|---|---|
| `prompt` | `str` | System-Prompt für den Agent in dieser Preset-Kategorie | (aus altem `prompts[cat][agent]`) |
| `focus` | `str` | Einzeiler zur Anzeige in UI | (aus altem `focus[cat]`, agent-adaptiert) |
| `target` | `str` | `"<provider>:<model>"` oder `"auto:<stage>"` | (auto:stage_2/3/5 je nach Agent) |
| `creativity` | `int` (1-5) | Slider für response_style | 3 |
| `obedience` | `int` (1-5) | Slider für Disziplin/Konsistenz | 3 (System: 4) |
| `model_override` | `str\|null` | Pin auf bestimmtes Modell (null = Router entscheidet) | null |
| `model_locked` | `bool` | Router ignoriert Override (SoulAG: true) | false (SoulAG: true) |
| `priority` | `str` | Routing-Priorität (`"highest"`/`"high"`/`"normal"`) | "normal" (System: "high"/"highest") |
| `enabled` | `bool` | Agent ist im Preset aktiv | true |
| `_source` | `str` | Provenienz-Marker für Audit (welche Datei/Zeile hat den Wert geliefert) | (s. Migration-Schritte) |

## Migration-Schritte

Ausgeführt via `~/.mavis/plans/plan_ec22311c/workspace/build_presets_v2.py`
(kann re-runnen werden, idempotent solange die Eingabedatei unverändert ist):

1. **Quellen einlesen:**
   - `src/gnom_hub/core/utils/presets.json` (alt) → `old.prompts`,
     `old.focus`, `old.targets`.
   - `data/presets/default/system_agents.json` → `sys_defaults`
     (CamelCase-Keys: soul/watchdog/general/security).

2. **System-Agent-Pool mappen:** CamelCase → Lowercase.
   `{"soul": ..., "watchdog": ..., "general": ..., "security": ...}` →
   `{"soulag": ..., "watchdogag": ..., "generalag": ..., "securityag": ...}`.
   Prompt-Inhalt bleibt 1:1.

3. **Default-Target pro Agent** (spiegelt `preset_service._get_preset_agents`):
   - `coderag` → `"auto:stage_3"` (Stage 3 hat die Coding-Modelle)
   - `soulag` → `"auto:stage_5"` (SoulAG ist model_locked auf Top-Modell)
   - Alle anderen (`researcherag`, `writerag`, `editorag`,
     `watchdogag`, `generalag`, `securityag`) → `"auto:stage_2"`

4. **Pro Kategorie (= Preset) `agents`-Block bauen:**
   - **System-Agents (4):** Prompt aus `sys_defaults`, focus adaptiert
     via `adapt_focus(agent, cat_name, cat_focus)`, target aus
     Schritt 3, `model_locked`/`priority` aus `sys_defaults`,
     `creativity=3`, `obedience=4` (für watchdog/security), 3 sonst,
     `enabled=true`, `_source="data/presets/default/system_agents.json#<role>"`.
   - **Worker-Agents (4):** Prompt aus `old.prompts[cat][agent]`, focus =
     adaptierte `cat_focus`, target entweder `"openrouter:<model>"`
     (wenn dieser Worker der `targets[cat]`-Agent ist) oder
     `"auto:stage_3"` für coderag / `"auto:stage_2"` sonst,
     `model_override=model` nur wenn `targets[cat]` matched,
     `creativity=3`, `obedience=3`, `enabled=true`,
     `_source="presets.json#prompts.<cat>.<agent>"`.

5. **Slug-Generierung:** `slugify(name)` —
   `"Web Development"` → `"web_development"`,
   `"Research & Analysis"` → `"research_and_analysis"`.

6. **Top-Level-Assembly:** `presets.<slug>` einsetzen + die alten
   `prompts`/`focus`/`targets` bit-identisch übernehmen.

7. **Sanity-Checks (laufen VOR dem Write):**
   - `prompts == old.prompts` (Bit-Identität)
   - `focus == old.focus` (Bit-Identität)
   - `targets == old.targets` (Bit-Identität)
   - Jede Kategorie hat genau 8 Agents
   - Alle per-Agent-Required-Fields vorhanden
   - Preset-Slugs == `slugify(cat)` für alle Kategorien

8. **Schreiben:** 61942 Bytes JSON, `indent=2`, `ensure_ascii=False`.

## Beispiel-JSON pro Agent-Type

### Worker-Agent (`coderag` in `web_development`)

```json
{
  "prompt": "SYSTEM-ROLLE: WEB DEVELOPER CODER. Write highly clean, modular, and modern HTML/CSS/JS. Use vanilla CSS and native web APIs. Focus on semantic HTML5 tags, responsive layouts, accessibility (ARIA), and smooth transitions.",
  "focus": "Fokus auf sauberen HTML, CSS, JavaScript Code, Responsive Design, Barrierefreiheit, Performance und moderne Web-APIs.",
  "target": "openrouter:qwen/qwen3-coder:free",
  "creativity": 3,
  "obedience": 3,
  "model_override": "qwen/qwen3-coder:free",
  "model_locked": false,
  "priority": "normal",
  "enabled": true,
  "_source": "presets.json#prompts.Web Development.coderag"
}
```

**Charakteristisch:** Prompt ist die ursprüngliche Worker-Rolle (unverändert).
`target` und `model_override` kommen aus dem alten `targets["Web Development"] =
["coderag", "qwen/qwen3-coder:free"]`. `model_locked=false` weil Worker
überschreibbar sind.

### System-Agent (`soulag` in `web_development`)

```json
{
  "prompt": "Du bist SoulAG — der Identitäts-, Persönlichkeits- und Werte-Agent des Gnom-Hub. ... (siehe data/presets/default/system_agents.json)",
  "focus": "Identitäts-Anker im Modus »Web Development« — Fokus auf sauberen HTML, CSS, JavaScript Code, Responsive Design, Barrierefreiheit, Performance und moderne Web-APIs.",
  "target": "auto:stage_5",
  "creativity": 3,
  "obedience": 3,
  "model_override": null,
  "model_locked": true,
  "priority": "highest",
  "enabled": true,
  "_source": "data/presets/default/system_agents.json#soul"
}
```

**Charakteristisch:** Prompt ist die SoulAG-Identitätsdefinition
(Layer-B-Default, unverändert übernommen). `focus` ist die Kombination
aus Rolle ("Identitäts-Anker") + Kategorie-Kontext
("im Modus »Web Development«") + Kategorie-Focus. `model_locked=true`
und `priority="highest"` weil SoulAG niemals überschreibbar ist.

### Gegenüberstellung (System vs. Worker)

| Aspekt | Worker (`coderag`) | System (`soulag`) |
|---|---|---|
| Prompt-Quelle | `presets.json` (Layer A) | `data/presets/default/system_agents.json` (Layer B) |
| Prompt-Variation pro Kategorie | ja (6 verschiedene Prompts) | nein (immer identisch) |
| Focus | = Kategorie-Focus | Rolle + Kategorie-Kontext |
| Target | aus altem `targets` oder Stage-Default | Stage-Default (Stage 5 für Soul) |
| Model-Lock | false | true (SoulAG) / false (andere) |
| Routing-Override | ja (aus `targets`) | nein (`null`) |

## Abwärtskompatibilitäts-Garantie

### Layer A (alte Konsumenten) — bit-identisch

`preset_service.load_presets()` (`preset_service.py:25-43`) liest
`prompts`/`focus`/`targets` weiterhin direkt aus dem Top-Level. Diese
Keys bleiben **bit-identisch** zum Vorher-Schema (verifiziert via
`assert new_doc["prompts"] == old["prompts"]` im Build-Script). Folge:

- `get_preset_prompt("Web Development", "coderag")` liefert weiterhin
  den exakt gleichen String wie vor der Migration.
- `_get_preset_agents(conn, preset, custom)` (`preset_service.py:192-214`)
  liest `load_presets().get("targets", {})` weiterhin korrekt.
- `handle_preset_change()` (`preset_service.py:217-254`) ruft
  `load_presets().get("focus", {}).get(preset, "Allgemeine Unterstützung.")`
  auf — funktioniert unverändert.

### Layer C (`config/presets/test_preset.json` und ähnliche Custom-Files)

Custom-Preset-Files unter `config/presets/*.json` werden vom Loader in
die Top-Level-`prompts`/`focus`/`targets` der `load_presets()`-Antwort
gemerged (`preset_service.py:31-42`). Dieses Verhalten ist
unverändert.

`test_preset.json` selbst wurde mit Schema-Markern versehen
(`_schema_version`, `_schema_generation`, `_layer="custom"`,
`_deprecation_notice`), behält aber **alle bestehenden Felder**
(`name`/`description`/`model`/`prompt_modifier`/`allowed_tools`/
`ttl_minutes`) bit-identisch bei, sodass der Loader es ohne
Anpassung weiter akzeptiert. Verifiziert: `assert d2['name'] == 'Test
Preset'` und `assert 'TEST PRESET MODIFIER' in test_prompt`.

### Konsumenten-Tests

| Konsument | Datei | Erwartung | Status |
|---|---|---|---|
| `router.py:132` | `get_preset_prompt(active, agent_name)` | liefert Worker-Prompt | OK (Layer-A-Fallback) |
| `admin_config.py:38-44` | `handle_preset_change`, `load_presets` | Preset wird gewechselt | OK (Layer-A-Fallback) |
| `llm_keys.py:69`, `llm_agents.py:113,125` | `db.get_value("active_preset", "Web Development")` | Default-Preset | OK (DB-State unabhängig) |
| `soul/soul.py:157-159` | hardcoded Kategorie-Whitelist | "Web Development" etc. als Strings | OK (Display-Namen unverändert) |

### Smoke-Test (ausgeführt, OK)

```bash
.venv/bin/python -c "
import json
d = json.load(open('src/gnom_hub/core/utils/presets.json'))
assert d['_schema_version'] == 1
assert d['_schema_generation'] == 1
assert set(d['agent_groups']['system']) == {'soulag','watchdogag','generalag','securityag'}
assert set(d['agent_groups']['worker']) == {'coderag','researcherag','writerag','editorag'}
assert len(d['presets']) == 6
for slug, p in d['presets'].items():
    assert len(p['agents']) == 8
assert 'prompts' in d and len(d['prompts']) == 6
assert 'focus' in d and len(d['focus']) == 6
assert 'targets' in d and len(d['targets']) == 4
print('OK — 6 presets × 8 agents, schema_version=1, schema_generation=1')
"
```

**Output:** `OK — 6 presets × 8 agents, schema_version=1, schema_generation=1`.

## Migration-Pfad für Code-Konsumenten

Code, der heute `prompts[cat][agent]` liest → **bleibt funktional
unverändert** (Layer-A-Fallback). Empfehlung für neuen Code:

| Alt | Neu |
|---|---|
| `load_presets()["prompts"][cat][agent]` | `load_presets()["presets"][slugify(cat)]["agents"][agent]["prompt"]` |
| `load_presets()["focus"][cat]` | `load_presets()["presets"][slugify(cat)]["description"]` |
| `load_presets()["targets"][cat]` (2-Tupel) | `presets[slug]["agents"][agent_name]["target"]` (pro Agent) |
| `load_presets()["prompts"][cat][agent]` (System-Agent) | **NEU**: war vorher nicht abrufbar |

**Mapping-Helper:** `agent_names.py` exportiert `category_of(name)` und
`is_known_agent(name)` — neue Konsumenten sollten diese Funktionen
benutzen, statt hartcodiert `"system"`/`"worker"` zu prüfen.

## Nächste Schritte (für `backend-service`-Task)

- Service-Methoden `get_agent_groups()`, `list_presets()`,
  `get_preset(slug)`, `get_preset_agent(slug, agent)`,
  `update_preset_agent(slug, agent, fields)`,
  `create_preset()`/`clone_preset()`/`delete_preset()` sind im
  parallel laufenden `backend-service`-Task definiert. Diese Datei
  (Schema) ist deren **Daten-Voraussetzung** und nun vorhanden.
- API-Endpoints (`/api/presets/groups`, `/api/presets/{id}/agents/{name}`,
  `/api/presets/{id}/clone`) siehe `inventory.md` §5.2.