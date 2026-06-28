# Playwright Live Maus-Steuerung

Sichtbarer Chromium-Browser, der per Playwright ferngesteuert wird. Maus fährt über den Screen, klickt, scrollt, hovered — alles in Echtzeit sichtbar.

## Setup (30 Sekunden)

```bash
cd /Users/landjunge/gnom-hub/playwright-live
npm init -y
npm install playwright
npx playwright install chromium
```

## Starten

```bash
# 1. Alle Maus-Aktionen testen
node mouse-control.js

# 2. Drag & Drop Demo (the-internet.herokuapp.com)
node drag-drop.js

# 3. Live-Maus-Visualizer mit Trail
node live-mouse-tracker.js
```

## Was passiert

- Chromium öffnet sichtbar (headless: false)
- `slowMo: 50-100ms` macht jede Bewegung sichtbar
- Browser bleibt offen bis alle Aktionen durch sind

## Maus-Methoden (Cheat-Sheet)

| Methode | Effekt |
|---|---|
| `page.mouse.move(x, y, { steps: N })` | Maus bewegen, N Schritte = menschlich |
| `page.mouse.click(x, y)` | Linksklick |
| `page.mouse.click(x, y, { button: 'right' })` | Rechtsklick |
| `page.mouse.click(x, y, { button: 'middle' })` | Mittelklick |
| `page.mouse.click(x, y, { clickCount: 2 })` | Doppelklick |
| `page.mouse.click(x, y, { clickCount: 3 })` | Dreifachklick |
| `page.mouse.wheel(dx, dy)` | Scrollen (dy negativ = hoch) |
| `page.mouse.down() / .up()` | Taste drücken / loslassen |
| `page.locator(...).hover()` | Hover über Element |
| `page.locator(...).dragTo(other)` | Drag & Drop |

## Quelle

Code generiert von SoulAG via MiniMax M3 (`audit_log`: provider=minimax, model=MiniMax-M3, status=success).