# Showbox Button-Typen v1.0

## Action-Registry

| Action-Typ | Pflicht-Felder | Optionale Felder | Handler |
|---|---|---|---|
| `next_slide` | — | — | showbox.js:240 |
| `prev_slide` | — | — | showbox.js:245 |
| `close_showbox` | — | — | showbox.js:250 |
| `agent_call` | `target` | `message` | chat_legacy.py:206 |
| `approve` | `decision_id` | — | soul_actions.py:74 |
| `reject` | `decision_id` | `reason` | soul_actions.py:74 |
| `stop_agent` | `target` | — | chat_commands.py:339 |
| `open_url` | `url` | `target` ("_blank"/"_self") | showbox.js |
| `run_script` | `path` | `args` | action_exec.py |
| `tts_speak` | `text` | `lang`, `pitch`, `rate` | showbox.js Web Speech |
| `nav_to_slide` | `slide_id` | — | showbox.js |
| `custom` | `handler` (Funktionsname) | `args` | — |

## Standard-Presets

Die folgenden JSON-Dateien enthalten **fertige Button-Listen** zum Kopieren:

- [`nav.json`](../buttons/nav.json) — Navigation (next/prev/close)
- [`actions.json`](../buttons/actions.json) — Approve/Reject/Stop
- [`agents.json`](../buttons/agents.json) — Agent-Calls (@SoulAG, @CoderAG, …)
- [`workflow.json`](../buttons/workflow.json) — Brainstorm / Vote / Multi-Step
- [`dynamic/`](../buttons/dynamic/) — Agent-erzeugte Buttons (archiviert)

## Button-Format

```json
{
  "label": "Angezeigter Text",
  "action": "action_typ_aus_registry",
  "color": "#ff4d6d",              // optional, default = Agent-Farbe
  "icon": "🔥",                    // optional, Emoji
  "confirm": true,                 // optional, doppelte Bestätigung
  "target": "CoderAG",             // für agent_call / stop_agent
  "decision_id": "abc-123",        // für approve / reject
  "url": "https://...",            // für open_url
  "message": "ping",               // für agent_call (default = Button-Label)
  "args": {...}                    // für run_script / custom
}
```

## Best-Practices

1. **3-5 Buttons pro Showbox** — mehr verwirrt
2. **Immer ein "Schließen"-Button** dabei
3. **Approve/Reject nur wenn nötig** — kein Approval-Theater
4. **Agent-Calls mit klarem Message** — nicht nur "ping"
5. **TTS-Buttons für Audio-Demos** — Web Speech API ist eingebaut
6. **Dynamic Buttons archivieren** — Agent-erzeugte Buttons landen in `buttons/dynamic/`
