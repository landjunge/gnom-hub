# Dynamische Buttons

Dynamische Buttons sind **on-the-fly vom Agent erzeugt**, basierend auf dem Kontext der User-Anfrage.
Sie sind **kein Theater** — sie sind funktional und werden archiviert.

## Wann dynamische Buttons?

- User stellt offene Frage → Agent bietet kontextspezifische Antwort-Buttons an
- Workflow hat mehrere Branches → Agent exponiert alle als Buttons
- Daten sind da → Agent macht Quick-Action-Buttons ("Sortieren", "Filtern", "Exportieren")

## Beispiele

```json
{
  "buttons": [
    {"label": "📊 Tabelle anzeigen", "action": "nav_to_slide", "slide_id": "table"},
    {"label": "📈 Diagramm generieren", "action": "run_script", "path": "scripts/chart.py"},
    {"label": "💾 Als CSV speichern", "action": "run_script", "path": "scripts/csv.py"},
    {"label": "🔊 Vorlesen", "action": "tts_speak", "text": "..."}
  ]
}
```

## Archivierung

Jeder dynamische Button, den ein Agent erzeugt, wird unter
`showbox/buttons/dynamic/<agent>_<timestamp>_<slug>.json` abgelegt.

Beispiel: `showbox/buttons/dynamic/coderag_20260627_1132_quick_sort.json`

**Regel:** Dynamische Buttons werden **nie** gelöscht — der User hat das explizit
verlangt (2026-06-27, "die sollen nicht gelöscht werden einen ordner im gnom-hub
selber erstellen mit buttons preasets da wird dann nichts einfach so gelöscht").

## Wo der Agent das lernt

In jedem Agent-Prompt steht:
```
═══ DYNAMIC BUTTONS ═══
Wenn du Buttons erzeugst die nicht in showbox/buttons/*.json sind:
1. Lege sie in showbox/buttons/dynamic/<agent>_<slug>.json ab
2. Nutze sie EINMAL in deiner Antwort
3. Sie bleiben für die Ewigkeit im Repo (User-Anweisung 2026-06-27)
```
