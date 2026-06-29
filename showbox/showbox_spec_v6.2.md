# Showbox v6.2 — Spezifikation

> *Das Antwort-Format des Schwarms. Tag-Syntax, Buttons-Registry, Dynamic-Patterns.*  
> *Sprint B — Härtung des Doku-Layers.*

---

## 1. Übersicht

**Showbox** ist das zentrale Ausgabe-Format aller 8 Agents. Jede Antwort des Schwarms erfolgt über mindestens eine Showbox-Slide — niemals als reiner Fließtext.

**Grundregel:**  
> *Jede Antwort = ≥ 1 Showbox-Slide. Buttons IMMER im `buttons[]`-Array, niemals als Pseudo-HTML im Content.*

---

## 2. `[SHOWBOX:]`-Tag-Syntax

### 2.1 Grundgerüst

```json
[SHOWBOX:<name>]{"slides":[{"title":"...","content":"...","buttons":[...]}]}
```

| Feld       | Typ     | Pflicht | Beschreibung                                    |
|------------|---------|---------|-------------------------------------------------|
| `name`     | string  | ✅      | kebab-case Identifier, z. B. `welcome`, `agent_status` |
| `slides`   | array   | ✅      | 1-n Slide-Objekte                                |
| `title`    | string  | ✅      | Slide-Überschrift (kurz, prägnant)              |
| `content`  | string  | ✅      | Slide-Body (Markdown-fähig, keine `<button>`-Tags!) |
| `buttons`  | array   | ⬜      | 0-n Button-Objekte                               |

### 2.2 Multi-Slide

```json
[SHOWBOX:pipeline_status]{
  "slides":[
    {"title":"Slide 1","content":"...","buttons":[...]},
    {"title":"Slide 2","content":"...","buttons":[...]}
  ]
}
```

### 2.3 Verbotene Patterns

- ❌ `<button>` im Content (immer in `buttons[]`)
- ❌ Inline-JS oder Event-Handler im Tag
- ❌ Externe Ressourcen-URLs in Buttons ohne Whitelist
- ❌ Agent-Farben außerhalb der definierten Palette

---

## 3. Buttons-Registry

### 3.1 Button-Schema

```json
{
  "label":  "Angezeigter Text",
  "action": "namespace.action_id",
  "style":  "primary | warn | agent | secondary"
}
```

| Style      | Verwendung                                      | Farbe   |
|------------|-------------------------------------------------|---------|
| `primary`  | Standard-Aktion (Start, OK, Bestätigen)        | 🟢 Grün |
| `warn`     | Risiko / Pause / Stop                           | 🟡 Gelb |
| `agent`    | Direkt-Call an Agent (`@call:writer` usw.)      | 🔵 Blau |
| `secondary`| Zurück / Wiederholen / Status                   | ⚪ Grau |

### 3.2 Preset-Whitelist (`showbox/buttons/*.json`)

| Datei                     | Zweck                                      | Beispiele                    |
|---------------------------|--------------------------------------------|------------------------------|
| `nav.json`                | Navigation                                 | ◀ Zurück · ▶ Weiter · ✕ Close |
| `actions.json`            | Approve / Reject / Stop                    | Approve · Reject · Stop       |
| `agents.json`             | Direkt-Calls an alle 8 Agents              | `@call:soul`, `@call:writer`  |
| `workflow.json`           | Brainstorm / Vote / Pipeline               | Start Vote · Open Pipeline    |
| `dynamic/` *(Archiv)*     | Vom Kontext abhängige Buttons              | on-the-fly, niemals löschen! |

> **Regel:** Existierende Presets **nutzen**, nicht erfinden. Eigene Buttons nur, wenn kein Preset passt — dann in `dynamic/` archivieren.

---

## 4. Dynamic-Patterns

### 4.1 Agent-Calls (`@call:`)

```json
{"label":"@WriterAG direkt","action":"@call:writer","style":"agent"}
```

Verfügbare Agents: `soul`, `general`, `writer`, `editor`, `coder`, `researcher`, `watchdog`, `security`.

### 4.2 Pipeline-Aktionen

```json
{"label":"🚀 Sprint A starten","action":"writer.start_manifest","style":"primary"}
{"label":"⏸ Pause","action":"general.pause","style":"warn"}
{"label":"🔄 Status abfragen","action":"general.status","style":"primary"}
```

**Namensschema:** `<agent-namespace>.<verb>`  
- Beispiele: `writer.start_manifest`, `editor.review_standby`, `general.dispatch_ab`

### 4.3 Dynamic-Buttons (on-the-fly)

Wenn der Kontext eine Aktion erfordert, die **kein Preset** abdeckt:

1. Button wird vom Agent on-the-fly erzeugt.
2. **Sofort archivieren** unter `showbox/buttons/dynamic/`.
3. Niemals Auto-Cleanup — User hat 2026-06-27 expliziert verboten, Presets zu löschen.

**Beispiel-Archiv-Eintrag:**

```json
// showbox/buttons/dynamic/sprint_dispatch.json
[
  {"label":"🚀 WriterAG · Sprint A starten","action":"writer.start_manifest","style":"primary"},
  {"label":"🚀 WriterAG · Sprint B starten","action":"writer.start_docs","style":"primary"}
]
```

---

## 5. Agent-Farbpalette

| Agent         | Farbe      | Hex (approx.) |
|---------------|------------|---------------|
| SoulAG        | 🩷 Magenta  | `#E91E63`     |
| GeneralAG     | 🔵 Blau     | `#2196F3`     |
| WriterAG      | 🟢 Grün     | `#4CAF50`     |
| EditorAG      | 🩷 Pink     | `#FF4081`     |
| CoderAG       | 🟠 Orange   | `#FF9800`     |
| ResearcherAG  | 🟡 Gelb     | `#FFC107`     |
| WatchdogAG    | 🩷 Rosa     | `#F48FB1`     |
| SecurityAG    | 🔷 Türkis   | `#26A69A`     |

---

## 6. Beispiele

### 6.1 Minimal (Welcome)

```json
[SHOWBOX:welcome]{
  "slides":[{
    "title":"👋 Willkommen im Schwarm",
    "content":"Acht Agents, ein Klang. **Wähle eine Aktion.**",
    "buttons":[
      {"label":"🚀 Schwarm starten","action":"general.start","style":"primary"},
      {"label":"📜 Manifest lesen","action":"open.manifest","style":"secondary"}
    ]
  }]
}
```

### 6.2 Multi-Slide (Status)

```json
[SHOWBOX:schwarm_status]{
  "slides":[
    {
      "title":"🟢 Schwarm online",
      "content":"Alle 8 Agents auf Position. Token-Stand: 12.480.",
      "buttons":[{"label":"🔄 Refresh","action":"general.status","style":"primary"}]
    },
    {
      "title":"📊 Worker-Stats",
      "content":"| Agent | Jobs | Quote |\n|-------|------|-------|\n| WriterAG | 225 | 100% |",
      "buttons":[{"label":"@WriterAG","action":"@call:writer","style":"agent"}]
    }
  ]
}
```

### 6.3 File-Delivered (mit Dynamic-Button)

```json
[SHOWBOX:file_delivered]{
  "slides":[{
    "title":"✅ Datei geschrieben",
    "content":"**`manifest_v6.2.md`** wurde in `/gnom-hub/showbox/` abgelegt.",
    "buttons":[
      {"label":"📂 Öffnen","action":"open.file","style":"primary"},
      {"label":"🩷 EditorAG review","action":"editor.review_manifest","style":"agent"}
    ]
  }]
}
```

---

## 7. Versionshistorie

| Version | Datum       | Änderung                                      |
|---------|-------------|-----------------------------------------------|
| v6.0    | 2026-01     | Initiale Tag-Syntax                           |
| v6.1    | 2026-04     | Buttons-Registry eingeführt                   |
| v6.2    | 2026-06     | Dynamic-Buttons-Archiv, Agent-Farbpalette     |

---

## Signatur

```
Showbox Spec v6.2
─────────────────
Sprint:       B (Härtung)
Sequenz:      A → B
Autor:        WriterAG · Grün
Output:       /gnom-hub/showbox/showbox_spec_v6.2.md
Reviewer:     EditorAG (Standby)
Manifest:     manifest_v6.2.md (Sprint A)
```

*Showbox v6.2 ist spezifiziert. Der Doku-Layer steht.*