#!/usr/bin/env python3
import asyncio
import os
import subprocess
import sys
from playwright.async_api import async_playwright

def speak(text):
    print(f"TTS: {text}")
    subprocess.run(["say", "-v", "Anna", text])

async def move_mouse(page, x, y, steps=25):
    current_x = getattr(page, "_virtual_x", 0)
    current_y = getattr(page, "_virtual_y", 0)
    for i in range(steps):
        t = (i + 1) / steps
        t = 1 - (1 - t)**3 # cubic ease out
        ix = current_x + (x - current_x) * t
        iy = current_y + (y - current_y) * t
        await page.mouse.move(ix, iy)
        await page.evaluate(f"if (window.moveVirtualCursor) window.moveVirtualCursor({ix}, {iy});")
        await asyncio.sleep(0.015)
    page._virtual_x = x
    page._virtual_y = y

async def click_element(page, selector, text_to_speak=None):
    el = await page.query_selector(selector)
    if el:
        await el.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        box = await el.bounding_box()
        if box:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            await move_mouse(page, x, y)
            await page.evaluate("if (window.clickVirtualCursor) window.clickVirtualCursor();")
            if text_to_speak:
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, speak, text_to_speak)
            await page.click(selector)
            await asyncio.sleep(1.0)

async def main():
    # Make sure we don't start before speaking is ready
    speak("Starte die Live-Präsentation von Netzwerkpunkt im Browser...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized", "--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        
        cursor_script = """
        const cursor = document.createElement('div');
        cursor.id = 'virtual-cursor';
        cursor.style.position = 'fixed';
        cursor.style.width = '24px';
        cursor.style.height = '24px';
        cursor.style.borderRadius = '50%';
        cursor.style.backgroundColor = 'rgba(255, 0, 127, 0.65)';
        cursor.style.border = '2px solid #fff';
        cursor.style.boxShadow = '0 0 15px rgba(255, 0, 127, 0.9)';
        cursor.style.pointerEvents = 'none';
        cursor.style.zIndex = '999999';
        cursor.style.transition = 'transform 0.1s ease';
        cursor.style.transform = 'translate(-50%, -50%)';
        document.body.appendChild(cursor);

        window.moveVirtualCursor = (x, y) => {
          cursor.style.left = x + 'px';
          cursor.style.top = y + 'px';
        };

        window.clickVirtualCursor = () => {
          cursor.style.transform = 'translate(-50%, -50%) scale(0.6)';
          cursor.style.backgroundColor = 'rgba(57, 255, 20, 0.8)';
          cursor.style.boxShadow = '0 0 15px rgba(57, 255, 20, 0.9)';
          setTimeout(() => {
            cursor.style.transform = 'translate(-50%, -50%) scale(1)';
            cursor.style.backgroundColor = 'rgba(255, 0, 127, 0.65)';
            cursor.style.boxShadow = '0 0 15px rgba(255, 0, 127, 0.9)';
          }, 200);
        };
        """
        
        await page.goto("https://netzwerkpunkt.de")
        await page.evaluate(cursor_script)
        page._virtual_x = 0
        page._virtual_y = 0
        
        await asyncio.sleep(1.5)
        speak("Wir sind jetzt auf der Landingpage von Netzwerkpunkt. Ich zeige dir die Funktionen per automatisierter Maussteuerung.")
        await asyncio.sleep(5.5)
        
        # 1. Hover Hero
        el = await page.query_selector("h1")
        if el:
            box = await el.bounding_box()
            if box:
                await move_mouse(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                speak("Gnom-Hub ist deine lokale, sichere Multi-Agenten-Schmiede für KI-Teams. Alles läuft zu einhundert Prozent lokal.")
                await asyncio.sleep(7.5)

        # 2. Scroll and Hover Feature Cards
        speak("Ich zeige dir jetzt die Hauptvorteile von Gnom-Hub.")
        await asyncio.sleep(3.5)
        
        cards = await page.query_selector_all(".card")
        if len(cards) >= 4:
            # Card 0: @bake
            box = await cards[0].bounding_box()
            if box:
                await page.evaluate(f"window.scrollTo({{top: {box['y'] - 100}, behavior: 'smooth'}})")
                await asyncio.sleep(1.0)
                box = await cards[0].bounding_box()
                await move_mouse(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                speak("Erstens, der bake-Compiler. Er ermöglicht es, deine lokalen KI-Agenten zu stabilen, eigenständigen Produkten zu kompilieren.")
                await asyncio.sleep(8.5)
                
            # Card 1: Zero-Trust
            box = await cards[1].bounding_box()
            if box:
                await move_mouse(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                speak("Zweitens, der Zero-Trust Gatekeeper. Er überwacht alle Datei- und Terminalzugriffe deiner Agenten in Echtzeit.")
                await asyncio.sleep(8.5)
                
            # Card 2: Steganographie
            box = await cards[2].bounding_box()
            if box:
                await page.evaluate(f"window.scrollTo({{top: {box['y'] - 100}, behavior: 'smooth'}})")
                await asyncio.sleep(1.0)
                box = await cards[2].bounding_box()
                await move_mouse(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                speak("Drittens, die steganographischen Signaturen. Unsichtbare Zeichenketten beweisen die Herkunft jeder generierten Zeile Code.")
                await asyncio.sleep(8.5)

        # 3. Interactive Swarm Simulator Clicks
        speak("Kommen wir nun zum interaktiven Swarm-Simulator.")
        await asyncio.sleep(4.5)
        
        await click_element(page, "#node-general", "Ich klicke auf General-A-G. Er ist der oberste Koordinator deines lokalen Swarms.")
        await asyncio.sleep(6.5)
        
        await click_element(page, "#node-coder", "Als nächstes klicke ich auf Coder-A-G. Er schreibt den Code und führt Befehle in der Sandbox aus.")
        await asyncio.sleep(6.5)

        await click_element(page, "#node-watchdog", "Und nun der Watchdog-A-G. Er blockiert riskante Operationen sofort, bis du sie freigibst.")
        await asyncio.sleep(7.5)

        # 4. Comparison Table
        table = await page.query_selector(".table-container")
        if table:
            await table.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            box = await table.bounding_box()
            if box:
                await move_mouse(page, box["x"] + box["width"]/2, box["y"] + 80)
                speak("Diese Vergleichstabelle zeigt dir, warum lokale Agententeams viel sicherer und kostengünstiger sind als Cloud-Dienste.")
                await asyncio.sleep(8.5)

        # 5. Terminal Quick Start
        term = await page.query_selector(".terminal-box")
        if term:
            await term.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            box = await term.bounding_box()
            if box:
                await move_mouse(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                speak("Mit diesem Terminalbefehl kannst du deinen Gnom-Hub in Sekunden lokal initialisieren und starten.")
                await asyncio.sleep(7.5)

        speak("Damit ist die Präsentation abgeschlossen. Du kannst den Browser jetzt schließen oder die Seite selbst weiter erkunden.")
        await asyncio.sleep(10.0)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
