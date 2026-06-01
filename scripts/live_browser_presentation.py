#!/usr/bin/env python3
import asyncio
import os
import subprocess
import glob
import shutil
from playwright.async_api import async_playwright

# Terminate running browsers at the start to ensure clean state
def kill_browsers():
    print("Schließe alle vorhandenen Browser-Instanzen...")
    for proc_pattern in ["Chromium", "Google Chrome", "Chrome"]:
        try:
            subprocess.run(["pkill", "-f", proc_pattern], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Fehler beim Schließen von {proc_pattern}: {e}")

async def speak(text):
    print(f"TTS: {text}")
    try:
        proc = await asyncio.create_subprocess_exec("say", "-v", "Anna", text)
        await proc.wait()
    except Exception as e:
        print(f"TTS Failed: {e}")

import traceback

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
        traceback.print_exc()

async def click_element(page, selector, text_to_speak=None, wait_after_speak=1.0):
    try:
        await page.wait_for_selector(selector, timeout=5000)
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
                    await speak(text_to_speak)
                    await asyncio.sleep(wait_after_speak)
                await page.click(selector)
                await asyncio.sleep(1.0)
    except Exception as e:
        print(f"Failed to click element {selector}: {e}")
        traceback.print_exc()

async def hover_element(page, selector, text_to_speak=None, wait_after_speak=1.0):
    try:
        await page.wait_for_selector(selector, timeout=5000)
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
                    await speak(text_to_speak)
                    await asyncio.sleep(wait_after_speak)
    except Exception as e:
        print(f"Failed to hover element {selector}: {e}")
        traceback.print_exc()

async def type_text(page, selector, text, delay=0.08):
    try:
        await page.wait_for_selector(selector, timeout=5000)
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
        traceback.print_exc()

async def main():
    # First, close any running Chrome/Chromium browsers
    kill_browsers()
    await asyncio.sleep(1.0)

    video_dir = "/Users/landjunge/Documents/AG-Flega/docs/demo_video"
    os.makedirs(video_dir, exist_ok=True)
    
    # Track existing webm files to find the new one later
    pre_existing_webms = set(glob.glob(os.path.join(video_dir, "*.webm")))
    
    await speak("Ich starte meine Präsentation und öffne den Browser im Vollbildmodus.")
    
    try:
        async with async_playwright() as p:
            # Launch Chromium in fullscreen
            browser = await p.chromium.launch(
                headless=False,
                args=["--start-fullscreen", "--no-sandbox", "--disable-setuid-sandbox"]
            )
            # Create context with no_viewport=True to let start-fullscreen command take effect
            context = await browser.new_context(
                no_viewport=True,
                record_video_dir=video_dir
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
            
            # Gnom introduces itself
            await speak("Hallo! Ich bin Gnom-Hub, deine lokale Multi-Agenten-Plattform.")
            await asyncio.sleep(0.5)
            await speak("Ich bin ein autonomer Schwarm von System-Agenten und spezialisierten Workern, die lokal auf deinem Rechner laufen.")
            await asyncio.sleep(1.0)
            
            # Show System Agents
            await hover_element(
                page,
                "#status-lamps",
                "Hier oben im Header siehst du meine vier System-Agenten: Soul-A-G, General-A-G, Security-A-G und Watchdog-A-G. Sie koordinieren und überwachen meine Workflows.",
                wait_after_speak=1.0
            )
            
            # Show Worker Agents
            await hover_element(
                page,
                ".agent-card:has-text('CoderAG')",
                "Links in der Seitenleiste befinden sich meine Worker-Agenten wie der Coder-A-G, der Researcher-A-G, der Writer-A-G und der Editor-A-G.",
                wait_after_speak=1.0
            )
            
            # Explain Pulse
            await hover_element(
                page,
                ".status-lamps",
                "Wenn meine System-Agenten oder Worker aktiv nachdenken, fangen sie an zu pulsieren. So siehst du in Echtzeit an ihrem rhythmischen Puls, wie sie arbeiten.",
                wait_after_speak=1.0
            )
            
            # Navigate to LLM Config
            await click_element(
                page,
                "button:has-text('LLM')",
                "Lass uns nun einen Blick auf meine Steuerelemente werfen. Ich klicke auf LLM-Einstellungen.",
                wait_after_speak=1.0
            )
            
            await hover_element(
                page,
                "#settings-tab-global-content",
                "Hier kannst du API-Schlüssel eintragen, Gang-Presets wählen oder jeden Agenten einem spezifischen Modell zuweisen. Mein integriertes Auto-Routing ermittelt dabei vollautomatisch die besten Verbindungen.",
                wait_after_speak=1.0
            )
            
            # Navigate to Dashboard
            await click_element(
                page,
                "button:has-text('Dashboard')",
                "Als nächstes zeige ich dir mein Bento-Grid Systemdashboard. Ich klicke auf Dashboard.",
                wait_after_speak=1.0
            )
            
            await hover_element(
                page,
                "#dashboard-panel",
                "Im Bento-Grid siehst du in Echtzeit meine Leistungskennzahlen wie Anfragen, Fehlerquoten, Antwortzeiten und Token-Verbräuche der einzelnen Gnome.",
                wait_after_speak=1.0
            )
            
            # Go back to War Room
            await click_element(
                page,
                ".logo",
                "Kehren wir nun in den Haupt-Arbeitsraum zurück.",
                wait_after_speak=1.0
            )
            
            # Type Prompt and run
            await hover_element(
                page,
                "#chat-input",
                "Jetzt demonstriere ich dir, wie einfach du mir Aufgaben erteilen kannst. Ich tippe den Befehl ein, um eine Landingpage für mich erstellen zu lassen.",
                wait_after_speak=1.0
            )
            
            prompt = "@bs Erstelle eine Landingpage für Gnom-Hub"
            await type_text(page, "#chat-input", prompt, delay=0.05)
            
            # Click Send button to run swarm
            await click_element(
                page,
                "button:has-text('Send')",
                "Jetzt schicke ich den Job ab und lasse meinen Schwarm für dich arbeiten. Danke fürs Zuschauen!",
                wait_after_speak=1.0
            )
            
            # Let the visual swarm thinking effect run for 6 seconds for the video
            await asyncio.sleep(6.0)
            
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
            await speak("Das Demovideo wurde erfolgreich unter docs/demo_video/gnom_hub_demo.webm gespeichert.")
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
