# Delegation: Browser-Open-Chain nach Demo-Finalisierung

## Trigger
User-Dispatch via SoulAG: "wenn die seite fertig ist gleich im broowser zeigen"

## Kette
1. **CoderAG** — `demo.html` finalisieren (3 Fixes: aria-label auf TTS-Buttons, prefers-reduced-motion Guard, intros[3] Padding). Nach Commit: `open /Users/landjunge/gnom-Workspace/default/demo.html`
2. **EditorAG** — Re-Review auf finale Version, PASS/FAIL signalisieren
3. **GeneralAG** — Pipeline-Close, Bestätigung an SoulAG

## Mac-Open-Befehl
```bash
open /Users/landjunge/gnom-Workspace/default/demo.html