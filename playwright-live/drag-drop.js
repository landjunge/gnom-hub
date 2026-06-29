// drag-drop.js — Erweiterte Drag & Drop Steuerung
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 50 });
  const page = await browser.newPage();

  // Interaktive Demo-Seite mit Drag & Drop
  await page.goto('https://the-internet.herokuapp.com/drag_and_drop');

  // Methode 1: Manuell mit Maus-Events
  const source = page.locator('#column-a');
  const target = page.locator('#column-b');

  const sourceBox = await source.boundingBox();
  const targetBox = await target.boundingBox();

  if (sourceBox && targetBox) {
    const sourceX = sourceBox.x + sourceBox.width / 2;
    const sourceY = sourceBox.y + sourceBox.height / 2;
    const targetX = targetBox.x + targetBox.width / 2;
    const targetY = targetBox.y + targetBox.height / 2;

    // Realistisches Drag mit Zwischenschritten
    await page.mouse.move(sourceX, sourceY);
    await page.mouse.down();
    await page.mouse.move(sourceX + 10, sourceY + 10, { steps: 5 });
    await page.mouse.move(targetX, targetY, { steps: 20 });
    await page.mouse.up();
  }

  // Methode 2: Drag mit Locator (einfacher)
  // await source.dragTo(target);

  // Methode 3: Force-Drag (ignoriert Sichtbarkeits-Checks)
  // await source.dragTo(target, { force: true });

  await browser.close();
})();