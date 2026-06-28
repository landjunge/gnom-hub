// live-mouse-tracker.js — Zeigt Mausposition in Echtzeit
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

  // HTML-Seite mit Live-Maus-Anzeige
  await page.setContent(`
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { margin: 0; background: #0a0a2e; font-family: monospace; color: #00ffcc; }
        #info { position: fixed; top: 10px; left: 10px; font-size: 24px; z-index: 100; }
        #box { position: fixed; width: 100px; height: 100px; background: #ff006e;
               border-radius: 50%; pointer-events: none; transition: 0.05s; }
        #canvas { width: 100vw; height: 100vh; }
      </style>
    </head>
    <body>
      <div id="info">🖱️ Bewege die Maus!</div>
      <div id="box"></div>
      <canvas id="canvas"></canvas>
      <script>
        const box = document.getElementById('box');
        const info = document.getElementById('info');
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        document.addEventListener('mousemove', (e) => {
          box.style.left = (e.clientX - 50) + 'px';
          box.style.top = (e.clientY - 50) + 'px';
          info.textContent = '🖱️ X: ' + e.clientX + ' | Y: ' + e.clientY;

          // Trail zeichnen
          ctx.fillStyle = 'rgba(0, 255, 204, 0.3)';
          ctx.beginPath();
          ctx.arc(e.clientX, e.clientY, 15, 0, Math.PI * 2);
          ctx.fill();
        });
      </script>
    </body>
    </html>
  `);

  // Jetzt bewegt Playwright die Maus — und der Browser zeigt es live!
  console.log('🎬 Live-Demo startet...');

  // Zeichne eine Spirale mit der Maus
  const cx = 640, cy = 360;
  for (let i = 0; i < 360; i += 5) {
    const radius = i * 0.8;
    const x = cx + radius * Math.cos(i * Math.PI / 90);
    const y = cy + radius * Math.sin(i * Math.PI / 90);
    await page.mouse.move(x, y);
    await page.waitForTimeout(20);
  }

  // Klicke ein paar Mal random
  for (let i = 0; i < 10; i++) {
    const x = Math.random() * 1280;
    const y = Math.random() * 720;
    await page.mouse.click(x, y);
    await page.waitForTimeout(300);
  }

  console.log('✅ Demo beendet');
  await browser.close();
})();