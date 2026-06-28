# Showbox Flash Module

1px Agent-Farben-Flash beim Showbox-Insert. 8 Agents gemappt, ~600ms × 2 Iterationen.

## Dateien

- `flash.css` — 8 @keyframes (eines pro Agent)
- `flash.js` — MutationObserver + Trigger-Logik

## Integration

```html
<link rel="stylesheet" href="showbox/flash/flash.css">
<script src="showbox/flash/flash.js" defer></script>
```

Voraussetzung: Slide-Element hat `data-author="<agent>"` (z.B. `general`, `soul`, `coder`, ...).

## Agent-Mapping

| Agent | Animation | Farbe |
|-------|-----------|-------|
| general | `flash-general` | `#3b82f6` blau |
| soul | `flash-soul` | `#8b5cf6` lila |
| coder | `flash-coder` | `#10b981` grün |
| writer | `flash-writer` | `#f97316` orange |
| editor | `flash-editor` | `#ef4444` rot |
| researcher | `flash-researcher` | `#06b6d4` cyan |
| security | `flash-security` | `#6b7280` grau |
| watchdog | `flash-watchdog` | `#f59e0b` bernstein |

## Reduced Motion

`@media (prefers-reduced-motion: reduce)` deaktiviert die Animation und zeigt eine statische Outline stattdessen.

## API

```javascript
window.ShowboxFlash.trigger(slideElement); // manuell triggern
window.ShowboxFlash.scan(rootElement);     //子树 scannen
window.ShowboxFlash.map;                   // {general:'flash-general', ...}
```

## Reviewer-Notizen

- 1px `outline` mit `outline-offset: -1px` → kein Layout-Shift
- Cleanup via `animationend` + 1400ms-Safety-Timeout
- `data-showboxFlashed="true"` verhindert Re-Flash bei Re-Render
- Color-Mapping folgt dem User-Dispatch (general=blau, …, watchdog=bernstein)