#!/usr/bin/env python3
import asyncio
import os
import subprocess
import glob
import shutil
import urllib.request
import json
import traceback
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

async def wait_for_workflow_completion(max_wait_seconds=60):
    print("Warte auf Start und Fertigstellung des Workflows...")
    url = "http://127.0.0.1:3002/api/metrics"
    start_time = asyncio.get_event_loop().time()
    
    # Phase 1: Wait for workflow to become active
    workflow_started = False
    while asyncio.get_event_loop().time() - start_time < 12:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                wf = data.get("_active_workflow")
                if wf:
                    print(f"Workflow gestartet: {wf}")
                    workflow_started = True
                    break
        except Exception as e:
            print(f"Polling metrics error: {e}")
        await asyncio.sleep(1.0)
        
    # Phase 2: Wait for workflow to finish (become None)
    if workflow_started:
        while asyncio.get_event_loop().time() - start_time < max_wait_seconds:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    wf = data.get("_active_workflow")
                    if not wf:
                        print("Workflow erfolgreich abgeschlossen.")
                        return True
            except Exception as e:
                print(f"Polling metrics error: {e}")
            await asyncio.sleep(2.0)
    else:
        # Fallback if workflow didn't register in metrics quickly
        print("Kein aktiver Workflow registriert, warte festen Timeout...")
        await asyncio.sleep(25.0)
    return False

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
            # Launch Chromium in true kiosk fullscreen mode
            browser = await p.chromium.launch(
                headless=False,
                args=["--kiosk", "--no-sandbox", "--disable-setuid-sandbox"]
            )
            # Create context with no_viewport=True to let kiosk mode determine viewport size
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
            
            # Explain Showbox
            await hover_element(
                page,
                "#modular-showbox-container",
                "Das ist meine modulare Showbox in der Mitte unten. Sie ist in drei Layer aufgeteilt: Layer 1 zeigt den System-Status. Layer 2 enthält Entwürfe meiner Worker. Layer 3 dient für User-Entscheidungen, um kritische Datei- oder Git-Aktionen freizugeben.",
                wait_after_speak=1.0
            )
            
            # Explain Interactive Help System
            await hover_element(
                page,
                "#nuke-btn",
                "Sie hat auch eine interaktive Hilfe: Wenn ich mit dem Mauszeiger über Oberflächenelemente fahre, blendet die Showbox sofort eine Erklärung dazu ein.",
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
                "Im Bento-Grid siehst du in Echtzeit meine Leistungskennzahlen wie Anfragen, Fehlerquoten, Antwortzeiten und Token-Verbräuche der Gnome sowie meinen evolutionären Selbstoptimierungs-Log.",
                wait_after_speak=1.0
            )
            
            # Navigate to Help
            await click_element(
                page,
                "button:has-text('Help')",
                "Mein integriertes Help Center liefert dir detaillierte Erklärungen zu allen Workflows und Einstellungen. Ich klicke auf Help.",
                wait_after_speak=1.0
            )
            
            await hover_element(
                page,
                "#help-panel",
                "Hier kannst du jederzeit nachschlagen, wie die verschiedenen Gnome zusammenarbeiten.",
                wait_after_speak=1.0
            )
            
            # Navigate to Workspace
            await click_element(
                page,
                "button:has-text('Workspace')",
                "Und im Workspace verwalte ich alle generierten Dateien und Projektergebnisse. Ich klicke auf Workspace.",
                wait_after_speak=1.0
            )
            
            await hover_element(
                page,
                "#workspace-panel",
                "Hier siehst du die erstellten Dateien und kannst sie direkt im Browser öffnen, ausführen oder eine Vorschau anzeigen.",
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
                "Jetzt schicke ich den Job ab. Mein Schwarm fängt sofort an zu planen, Code zu schreiben und die Seite aufzubauen.",
                wait_after_speak=1.0
            )
            
            await speak("Ich warte nun, bis der Schwarm die Landingpage fertiggestellt hat. Das dauert nur einen Moment.")
            
            # Wait for workflow completion
            await wait_for_workflow_completion(max_wait_seconds=65)
            
            await speak("Perfekt! Der Schwarm hat die Erstellung abgeschlossen. Lass uns das Ergebnis im Workspace ansehen.")
            
            # Click Workspace to view output
            await click_element(
                page,
                "button:has-text('Workspace')",
                "Ich klicke wieder auf Workspace.",
                wait_after_speak=1.0
            )
            
            # Click Preview on index.html
            preview_selector = ".mem-item:has(strong:has-text('index.html')) button:has-text('Preview')"
            await click_element(
                page,
                preview_selector,
                "Hier befindet sich die generierte index.html. Ich klicke auf Vorschau, um die erstellte Seite anzuzeigen.",
                wait_after_speak=1.0
            )
            
            # Hover over the live preview modal area and speak concluding sentences
            await speak("Hier ist das fertige Ergebnis der Landingpage direkt in der Live-Vorschau! Komplett entworfen, geschrieben und strukturiert von meinem lokalen Agenten-Schwarm.")
            await asyncio.sleep(0.5)
            await speak("Das ist die Power von Gnom-Hub. Autonom, lokal und absolut sicher. Vielen Dank fürs Zuschauen!")
            
            # Let the preview be shown for 5 seconds for the video
            await asyncio.sleep(5.0)
            
            await context.close()
            await browser.close()
            
    except Exception as e:
        print(f"Exception during presentation loop: {e}")
        traceback.print_exc()
        
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
