#!/usr/bin/env python3
import asyncio
import os
import subprocess
import glob
import shutil
from playwright.async_api import async_playwright

def speak(text):
    print(f"TTS: {text}")
    subprocess.run(["say", "-v", "Anna", text])

async def move_mouse(page, x, y, steps=25):
    try:
        current_x = getattr(page, "_virtual_x", 0)
        current_y = getattr(page, "_virtual_y", 0)
        for i in range(steps):
            t = (i + 1) / steps
            t = 1 - (1 - t)**3  # cubic ease out
            ix = current_x + (x - current_x) * t
            iy = current_y + (y - current_y) * t
            await page.mouse.move(ix, iy)
            await page.evaluate(f"if (window.moveVirtualCursor) window.moveVirtualCursor({ix}, {iy});")
            await asyncio.sleep(0.015)
        page._virtual_x = x
        page._virtual_y = y
    except Exception as e:
        print(f"Failed to move mouse: {e}")

async def click_element(page, selector, text_to_speak=None, wait_after_speak=3.0):
    try:
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
                    await asyncio.sleep(wait_after_speak)
                await page.click(selector)
                await asyncio.sleep(1.0)
    except Exception as e:
        print(f"Failed to click element {selector}: {e}")

async def hover_element(page, selector, text_to_speak=None, wait_after_speak=3.0):
    try:
        el = await page.query_selector(selector)
        if el:
            await el.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            box = await el.bounding_box()
            if box:
                x = box["x"] + box["width"] / 2
                y = box["y"] + box["height"] / 2
                await move_mouse(page, x, y)
                if text_to_speak:
                    loop = asyncio.get_event_loop()
                    loop.run_in_executor(None, speak, text_to_speak)
                    await asyncio.sleep(wait_after_speak)
    except Exception as e:
        print(f"Failed to hover element {selector}: {e}")

async def type_text(page, selector, text, delay=0.08):
    try:
        el = await page.query_selector(selector)
        if el:
            await el.scroll_into_view_if_needed()
            box = await el.bounding_box()
            if box:
                x = box["x"] + box["width"] / 2
                y = box["y"] + box["height"] / 2
                await move_mouse(page, x, y)
                await page.evaluate("if (window.clickVirtualCursor) window.clickVirtualCursor();")
                await page.click(selector)
                await asyncio.sleep(0.2)
                
                # Type char by char
                for char in text:
                    await page.keyboard.type(char)
                    await asyncio.sleep(delay)
                await asyncio.sleep(0.5)
    except Exception as e:
        print(f"Failed to type text in {selector}: {e}")

async def main():
    video_dir = "/Users/landjunge/Documents/AG-Flega/docs/demo_video"
    os.makedirs(video_dir, exist_ok=True)
    
    # Track existing webm files to find the new one later
    pre_existing_webms = set(glob.glob(os.path.join(video_dir, "*.webm")))
    
    speak("Starte die automatisierte Präsentation von Gnom-Hub im Browser...")
    
    try:
        async with async_playwright() as p:
            # Launch Chromium with visible window
            browser = await p.chromium.launch(
                headless=True,
                args=["--start-maximized", "--no-sandbox", "--disable-setuid-sandbox"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                record_video_dir=video_dir,
                record_video_size={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            
            # Virtual cursor logic script
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
            
            await page.goto("http://127.0.0.1:3002/")
            await page.evaluate(cursor_script)
            page._virtual_x = 0
            page._virtual_y = 0
            
            await asyncio.sleep(1.5)
            speak("Willkommen bei Gnom-Hub. Ich führe dich heute durch unsere lokale Agenten-Schmiede.")
            await asyncio.sleep(4.5)
            
            # 1. Hover Title Logo
            await hover_element(
                page, 
                ".logo", 
                "Gnom-Hub läuft zu einhundert Prozent lokal und sicher auf deinem Rechner.",
                wait_after_speak=4.5
            )
            
            # 2. Sidebar Agent Cards
            speak("Links siehst du die spezialisierten Gnom-Worker, die mir bei der Arbeit helfen.")
            await asyncio.sleep(3.5)
            
            await hover_element(
                page,
                ".agent-card:has-text('CoderAG')",
                "Coder-A-G schreibt selbstständig Programme und Webseiten in einer isolierten Sandbox.",
                wait_after_speak=5.0
            )
            
            await hover_element(
                page,
                ".agent-card:has-text('ResearcherAG')",
                "Researcher-A-G durchsucht das Internet nach Bibliotheken und Dokumentationen.",
                wait_after_speak=5.0
            )
            
            await hover_element(
                page,
                ".agent-card:has-text('WriterAG')",
                "Writer-A-G erstellt professionelle Texte, Handbücher und Produktbeschreibungen.",
                wait_after_speak=5.0
            )
            
            await hover_element(
                page,
                ".agent-card:has-text('EditorAG')",
                "Und der Editor-A-G übernimmt das Lektorat und sichert die Softwarequalität.",
                wait_after_speak=5.0
            )
            
            # 3. Chat and Thought Area
            await hover_element(
                page,
                "#chat-split-container",
                "Im War-Room in der Mitte siehst du oben die Denkprozesse der Agenten und unten den Chatverlauf.",
                wait_after_speak=6.0
            )
            
            # 4. Type Prompt
            speak("Wir geben dem gesamten Schwarm die Aufgabe, eine Landingpage für Gnom-Hub zu entwerfen.")
            await asyncio.sleep(3.5)
            
            prompt = "@bs Erstelle eine Landingpage für Gnom-Hub"
            await type_text(page, "#chat-input", prompt, delay=0.04)
            
            # 5. Send Prompt
            await click_element(
                page,
                "button:has-text('Send')",
                "Wir senden die Aufgabe ab.",
                wait_after_speak=2.5
            )
            
            # 6. Wait for Swarm & Comment
            speak("General-A-G delegiert die Teilaufgaben an die passenden Worker.")
            await asyncio.sleep(4.0)
            
            speak("Oben können wir jetzt live zuschauen, wie die Gnome miteinander diskutieren und Ansätze austauschen.")
            await asyncio.sleep(5.0)
            
            speak("Alles wird sicher von unserem Gatekeeper überwacht, ohne Gefahr von ungewollten Dateizugriffen.")
            await asyncio.sleep(6.0)
            
            speak("Coder-A-G und Writer-A-G entwerfen nun das HTML-Grundgerüst und die Texte.")
            await asyncio.sleep(7.0)
            
            # 7. Navigation bar demonstration
            await hover_element(
                page,
                "button:has-text('Workspace')",
                "Oben in der Menüleiste können wir in den Workspace wechseln, um generierte Dateien zu prüfen.",
                wait_after_speak=5.0
            )
            
            await hover_element(
                page,
                "button:has-text('Dashboard')",
                "Das Bento-Grid-Dashboard zeigt uns Systemstatistiken und Token-Verbräuche.",
                wait_after_speak=4.5
            )
            
            speak("Der Entwurf wurde erfolgreich in der Showbox bereitgestellt.")
            await asyncio.sleep(4.0)
            
            speak("Die Präsentation ist abgeschlossen und das Video wurde erfolgreich aufgezeichnet.")
            await asyncio.sleep(3.0)
            
            await context.close()
            await browser.close()
    except Exception as e:
        print(f"Exception during presentation loop: {e}")
        
    # Find and rename the recorded video
    try:
        await asyncio.sleep(1.0)
        current_webms = set(glob.glob(os.path.join(video_dir, "*.webm")))
        new_webms = current_webms - pre_existing_webms
        
        if new_webms:
            # Sort to get the absolute newest one
            latest_video = max(new_webms, key=os.path.getctime)
            dest_video = os.path.join(video_dir, "gnom_hub_demo.webm")
            shutil.move(latest_video, dest_video)
            print(f"Recorded video successfully saved and renamed to: {dest_video}")
            speak("Das Demovideo wurde unter docs/demo_video/gnom_hub_demo.webm gespeichert.")
        else:
            # Fallback to search all webm files if set difference was empty
            video_files = glob.glob(os.path.join(video_dir, "*.webm"))
            if video_files:
                latest_video = max(video_files, key=os.path.getctime)
                dest_video = os.path.join(video_dir, "gnom_hub_demo.webm")
                if latest_video != dest_video:
                    shutil.move(latest_video, dest_video)
                    print(f"Fallback: Renamed {latest_video} to {dest_video}")
    except Exception as e:
        print(f"Error handling video renaming: {e}")

if __name__ == "__main__":
    asyncio.run(main())
