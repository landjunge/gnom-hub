## Showbox-Format-Facts (Kanonische Referenz)

### Tag-Syntax
- Jede Agent-Antwort = mindestens 1 `[SHOWBOX:name]{...}`-Tag
- Format: `[SHOWBOX:slide_id]{"slides":[...],"buttons":[...]}`
- `slide_id` MUSS eindeutig sein (z.B. `agent-action-context-timestamp`)

### Button-Regeln (HART)
- Buttons IMMER im `buttons[]`-Array — niemals als Pseudo-HTML im Content
- Existierende Presets aus `showbox/buttons/*.json` NUTZEN, nicht erfinden
- Dynamische Buttons (Kontext-abhängig) in `showbox/buttons/dynamic/` archivieren
- **User-Verbot 2026-06-27**: Buttons-Presets dürfen NICHT gelöscht werden (kein Auto-Cleanup)

### Slide-Struktur
- `slides[]` = Title + Content + optional Meta
- Title = kurz, prägnant (Emoji + Kernaussage)
- Content = Bullet-freundlich, max ~5 Zeilen pro Slide
- Meta = Quellen/IDs für Rückverfolgbarkeit

### Workflow-Kontext
- 8 Agents kommunizieren via Showbox
- Tier-Hierarchie: User > SecurityAG/SoulAG > Worker
- Tier-3 Agents (CoderAG, WriterAG, EditorAG, ResearcherAG, WatchdogAG) hören NICHT aufeinander ohne User-Dispatch