# Dynamic Buttons — Archiv

Hier landen alle **on-the-fly von Agenten erzeugten** Buttons.
Sie werden **nie gelöscht** (User-Anweisung 2026-06-27).

## Naming-Convention

`<agent_name>_<YYYYMMDD>_<HHMM>_<slug>.json`

Beispiel: `coderag_20260627_1132_quick_action.json`

## Schema

```json
{
  "_created_by": "CoderAG",
  "_created_at": "2026-06-27T11:32:00Z",
  "_context": "User fragte nach 'wie sortiere ich eine Liste' — Bot schlug 3 Quick-Actions vor",
  "buttons": [
    {"label": "...", "action": "...", ...}
  ]
}
```

## Workflow

1. Agent erzeugt Button in seiner Antwort (z.B. inline in showbox-Content)
2. Agent (oder Hintergrund-Task) persistiert die Button-Definition hier
3. Beim nächsten ähnlichen User-Input kann der Button wiederverwendet werden
4. Archiv wächst monoton — keine Cleanup-Jobs

## Aktueller Inhalt

_(noch leer — wird beim ersten Agent-Output gefüllt)_
