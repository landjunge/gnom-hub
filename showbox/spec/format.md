# Showbox · Format-Spec

## Container
- Tag: `[SHOWBOX:<name>]`
- Body: JSON (single line or pretty-printed)
- Pflicht-Keys: `type:"slide"`, `slides[]`
- Optional: `buttons[]` (Array, NIEMALS Pseudo-HTML im Content)

## Slide-Shape
```json
{
  "title": "string",
  "icon": "emoji",
  "color": "#hex",
  "content": "string|markdown|html",
  "buttons": ["button_id", "..."]
}
```

## Code-Blocks · ERLAUBT (alle Sprachen)

Renderer MUSS folgende Fences ohne Filter durchlassen:

| Fence        | Inhalt           | Use-Case                  |
|--------------|------------------|---------------------------|
| ` ```json `  | JSON-Payloads    | Slide-Bodies, Buttons     |
| ` ```html `  | HTML-Snippets    | Demos, Renderer-Tests     |
| ` ```css `   | CSS-Blocks       | Style-Diffs, Themes       |
| ` ```js `    | JavaScript       | Snippets, Renderer-Patch  |
| ` ```ts `    | TypeScript       | Type-Demos                |
| ` ```bash `  | Shell-Commands   | Scouting, Crawls          |
| ` ```diff `  | Diff-Blocks      | Patch-Reviews             |
| ` ```md `    | Markdown in MD   | Nested-Format             |
| ` ```yaml `  | YAML-Configs     | Pipeline-Definition       |
| ` ```python`| Python           | Script-Snippets           |

## Verboten
- KEINE Sprach-Whitelist (nicht auf `json` allein beschränken)
- KEINE Auto-Escapes für Backticks in Code-Blöcken
- KEIN Pseudo-HTML für Buttons — immer `buttons[]`-Array
- KEIN `stripCodeBlocks` / `sanitizeCode` / `replace(/```/g, '')` mehr

## Buttons
- IDs aus `buttons/*.json` referenzieren
- Custom-Buttons: in `buttons/dynamic/` archivieren
- Inline-Definition in `buttons[]` erlaubt wenn nicht als Preset existiert

## Validation
- JSON.parse MUSS fehlschlagen bei kaputten Payloads (laut sein, nicht silent)
- Unbekannte Sprachen: als Plain-Codeblock durchreichen, nicht ablehnen