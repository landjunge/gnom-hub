# Showbox Progress-Protokoll

## Zweck
Worker emittieren **zwischendurch** Showbox-Slides, nicht nur am Ende. User sieht Fortschritt live.

## Trigger (WANN eine Progress-Slide)
- **CoderAG:** nach jedem Bauabschnitt (V1 fertig, V2 fertig, V3 fertig, CSS-Keyframe live, Browser-Preview offen)
- **WriterAG:** nach jedem Copy-Block (Hero, Features, CTA, Variante X fertig)
- **EditorAG:** nach jedem Review-Schritt (Brief validiert, Review laeuft, Verdict steht)
- **ResearcherAG:** nach jedem Fakt-Check (Facts-Block 1/3, 2/3, 3/3)
- **Bei Blockern / Rückfragen an User** — immer Progress-Slide
- **Bei signifikanten Zwischen-Ergebnissen**

## Format (Slide-Schema)
```json
{
  "slide_id": "{agent}-progress-{schritt}-{kuerzel}",
  "type": "progress",
  "color": "{agent-farbe}",
  "icon": "{emoji}",
  "title": "{Emoji} {Agent} — {Schritt-Name}",
  "content": "**Status:** {1-Satz-Beschreibung}\n\n**Fortschritt:** {X}/{Y}\n\n**Naechster Schritt:** {was kommt als naechstes}",
  "buttons": [
    {"label": "Status pruefen", "action": "@generalag.status", "style": "primary"},
    {"label": "Worker-Liste", "action": "nav.workers", "style": "secondary"}
  ]
}
```

## Agent-Farben (zur Erinnerung)
- CoderAG: #10b981
- WriterAG: #f59e0b
- EditorAG: #ef4444
- ResearcherAG: #3b82f6
- GeneralAG: #6366f1
- SoulAG: #7c3aed
- WatchdogAG: #ff3344
- SecurityAG: #dc2626

## Don'ts
- Nicht spammen — max 1 Progress-Slide pro signifikantem Schritt
- Keine Pseudo-Buttons im Content-Feld
- Echte `buttons[]` immer als Array, nicht inline
- Bei FINAL-Deliverable: type="deliverable", nicht "progress"

## Beispiel
```json
{
  "slide_id": "coderag-progress-v1-skeleton-2026-07-28",
  "type": "progress",
  "color": "#10b981",
  "icon": "🟢",
  "title": "CoderAG — V1 Skelett steht",
  "content": "**Status:** HTML-Geruest + CSS-Variablen gesetzt.\n\n**Fortschritt:** 1/3 Varianten\n\n**Naechster Schritt:** V2 (technical tone) bauen."
}