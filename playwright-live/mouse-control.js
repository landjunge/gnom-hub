// mouse-control.js — KOMPLETTE MAUS-STEUERUNG
// Quelle: SoulAG Output 06:38:17 (audit-log provider=minimax model=MiniMax-M3 status=success)
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 }
  });
  const page = await context.newPage();

  await page.goto('https://playwright.dev');

  // ─── 1. MAUS BEWEGEN (smooth, mit Schritten) ───
  await page.mouse.move(100, 100);                    // Direkt
  await page.mouse.move(640, 360, { steps: 20 });     // Sanft gleitend

  // ─── 2. KLICKEN (links, rechts, mitte) ───
  await page.mouse.click(640, 360);                      // Linksklick
  await page.mouse.click(100, 100, { button: 'right' }); // Rechtsklick
  await page.mouse.click(200, 200, { button: 'middle' });// Mittelklick
  await page.mouse.click(300, 300, { clickCount: 2 });   // Doppelklick
  await page.mouse.click(400, 400, { clickCount: 3 });   // Dreifachklick

  // ─── 3. MAUS RAD / SCROLLEN ───
  await page.mouse.wheel(0, 500);     // Runter scrollen (deltaY: 500px)
  await page.mouse.wheel(0, -300);    // Hoch scrollen
  await page.mouse.wheel(100, 0);     // Horizontal rechts

  // ─── 4. HOVER (schweben über Element) ───
  await page.locator('nav a').first().hover();

  // ─── 5. DRAG & DROP (manuell mit Maus) ───
  await page.mouse.move(100, 100);
  await page.mouse.down();
  await page.mouse.move(500, 500, { steps: 30 });
  await page.mouse.up();

  // ─── 6. MODIFIKATOR-Tasten beim Klick ───
  await page.keyboard.down('Shift');
  await page.mouse.click(640, 360);
  await page.keyboard.up('Shift');

  // ─── 7. POSITION ABFRAGEN ───
  const position = await page.evaluate(() => ({
    x: window.innerWidth,
    y: window.innerHeight
  }));
  console.log('Viewport:', position);

  await browser.close();
})();