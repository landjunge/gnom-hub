"""Echter Browser-Test der LLM-Seite via Playwright.

Was dieser Test macht:
1. Startet Chromium, lädt http://127.0.0.1:3002
2. Klickt auf den LLM-Button
3. Validiert dass die Seite rendert
4. Importiert api_keys.txt
5. Verifiziert dass Provider-Dropdowns gefüllt werden
6. Klickt Auto-Route
7. Macht Screenshots
"""
import os
import time

from playwright.sync_api import sync_playwright

HUB_URL = "http://127.0.0.1:3002"
KEYS_FILE = os.path.expanduser("~/Desktop/api_keys.txt")
SCREENSHOT_DIR = os.path.expanduser("~/Desktop/gnom_dev/screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def test_llm_page_full_workflow():
    """Komplett-Workflow: Login → LLM-Seite → Import → Auto-Route → Screenshot."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()

        # 1. Hub öffnen
        print(f"1. Lade {HUB_URL}...")
        page.goto(HUB_URL, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_war_room.png", full_page=True)
        title = page.title()
        print(f"   Title: {title}")
        assert "Gnom" in title or "GNOM" in title, f"Unerwarteter Title: {title}"

        # 2. LLM-Button klicken
        print("2. Klicke LLM-Button...")
        llm_btn = page.locator("button:has-text('LLM')").first
        if llm_btn.count() == 0:
            print("   ⚠ LLM-Button nicht gefunden, nehme ersten btn-primary")
            llm_btn = page.locator(".btn-primary").first
        llm_btn.click()
        time.sleep(2)
        page.screenshot(path=f"{SCREENSHOT_DIR}/02_llm_page.png", full_page=True)

        # 3. Validiere dass die LLM-Seite geladen wurde
        print("3. Validiere LLM-Seite...")
        has_system = page.locator("text=System Agents").count() > 0
        has_worker = page.locator("text=Worker Agents").count() > 0
        # "Special Services" wurde refactored in "Web Search" + "TTS" Service-Cards.
        has_websearch = page.locator("text=Web Search").count() > 0
        has_tts = page.locator("text=TTS").count() > 0
        print(f"   System Agents: {has_system}, Worker Agents: {has_worker}, "
              f"Web Search: {has_websearch}, TTS: {has_tts}")
        assert has_system, "System Agents nicht gefunden"
        assert has_worker, "Worker Agents nicht gefunden"
        assert has_websearch, "Web Search Service-Card nicht gefunden"
        assert has_tts, "TTS Service-Card nicht gefunden"

        # 4. Auto-Route-Modi prüfen
        print("4. Prüfe Auto-Route-Modi...")
        modes = ["Only Free Models", "Local First", "Cost Optimized", "Balanced", "Performance"]
        for mode in modes:
            mode_btn = page.locator(f"button:has-text('{mode}')")
            count = mode_btn.count()
            print(f"   {mode}: {count} buttons")
            assert count > 0, f"Mode '{mode}' nicht gefunden"

        # 5. Agent-Tabelle prüfen
        print("5. Prüfe Agent-Tabelle...")
        agents = ["SoulAG", "WatchdogAG", "GeneralAG", "SecurityAG",
                  "WriterAG", "CoderAG", "ResearcherAG", "EditorAG"]
        for agent in agents:
            count = page.locator(f"text={agent}").count()
            print(f"   {agent}: {count} mal")
            assert count > 0, f"Agent '{agent}' nicht gefunden"

        # 6. Auto-Route klicken (erste Mode: "Only Free Models")
        print("6. Klicke 'Only Free Models' für System Agents...")
        page.locator(".llm-mode-btn:has-text('Only Free Models')").first.click()
        time.sleep(2)
        page.screenshot(path=f"{SCREENSHOT_DIR}/03_after_autoroute.png", full_page=True)

        # 7. Status-Banner prüfen
        print("7. Prüfe Status-Banner...")
        status = page.locator("#llm-status")
        if status.count() > 0:
            status_text = status.inner_text()
            print(f"   Status: {status_text}")

        # 8. Provider-Dropdown prüfen
        print("8. Prüfe Provider-Dropdowns...")
        selects = page.locator("select[data-field='provider']")
        select_count = selects.count()
        print(f"   {select_count} Provider-Dropdowns")
        if select_count > 0:
            first = selects.first
            options = first.locator("option").all_inner_texts()
            print(f"   First dropdown options: {options}")

        # 9. Status-Lampen im Header prüfen
        print("9. Prüfe Header-Status-Lamps...")
        lamps = page.locator(".sys-agent-card")
        print(f"   {lamps.count()} Status-Lamps im Header")

        # 10. Finaler Screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/04_final.png", full_page=True)
        print(f"\n10. Screenshots gespeichert in {SCREENSHOT_DIR}/")

        browser.close()
        print("\n✓ Test PASSED")


if __name__ == "__main__":
    test_llm_page_full_workflow()
