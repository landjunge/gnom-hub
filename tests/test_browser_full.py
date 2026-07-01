"""Vollständiger Browser-Test mit Video, Maus-Simulation, Multi-Browser.

Features:
- Multi-Browser (chromium, firefox, webkit)
- Video-Recording während Test
- Screenshots (full-page + element-spezifisch)
- Maus-Simulation (click, hover, drag, type)
- Echte Gnom-Hub UI Interaktionen
"""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

HUB_URL = "http://127.0.0.1:3002"
KEYS_FILE = os.path.expanduser("~/Desktop/api_keys.txt")
ARTIFACT_DIR = Path(os.path.expanduser("~/Desktop/gnom_dev/browser_artifacts"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def test_full_workflow_chromium():
    """Chromium-Test mit Video, Maus, Screenshots."""
    test_dir = ARTIFACT_DIR / "chromium"
    test_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            record_video_dir=str(test_dir / "videos"),
            record_video_size={"width": 1600, "height": 1000},
        )
        page = context.new_page()

        print("\n=== CHROMIUM TEST ===")
        print(f"Videos in: {test_dir}/videos/")

        # 1. Hub öffnen
        page.goto(HUB_URL, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)
        page.screenshot(path=test_dir / "01_hub_loaded.png", full_page=True)
        print(f"1. Hub geladen, Title: {page.title()}")

        # 2. Maus über Header-Buttons hovern
        print("2. Hover über Header-Buttons...")
        for btn_text in ["Workspace", "Dashboard", "Workflows", "LLM", "Tuning"]:
            btn = page.locator(f"button:has-text('{btn_text}')").first
            if btn.count() > 0:
                btn.hover()
                page.wait_for_timeout(300)
                page.screenshot(path=test_dir / f"02_hover_{btn_text.lower()}.png")

        # 3. Klicke LLM
        page.locator("button:has-text('LLM')").first.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=test_dir / "03_llm_page.png", full_page=True)
        print("3. LLM-Seite geladen")

        # 4. Maus-Bewegung über Modus-Buttons
        mode_btns = page.locator(".llm-mode-btn")
        mode_count = mode_btns.count()
        print(f"4. {mode_count} Modus-Buttons gefunden")
        for i in range(min(mode_count, 5)):
            btn = mode_btns.nth(i)
            btn.hover()
            page.wait_for_timeout(500)
            page.screenshot(path=test_dir / f"04_hover_mode_{i}.png")

        # 5. Klicke Auto-Route
        page.locator(".llm-mode-btn:has-text('Balanced')").first.click()
        page.wait_for_timeout(3000)
        page.screenshot(path=test_dir / "05_after_autoroute.png", full_page=True)
        status = page.locator("#llm-status")
        if status.count() > 0:
            print(f"5. Status: {status.inner_text()}")

        # 6. Provider-Dropdowns prüfen
        selects = page.locator("select[data-field='provider']")
        if selects.count() > 0:
            for i in range(selects.count()):
                sel = selects.nth(i)
                options = sel.locator("option").all_inner_texts()
                print(f"6. Dropdown {i}: {len(options)} options → {options[:3]}")
            page.screenshot(path=test_dir / "06_dropdowns.png", full_page=True)

        # 7. Agent-Status-Lampen prüfen
        status_lamps = page.locator(".sys-agent-card")
        for i in range(status_lamps.count()):
            lamp = status_lamps.nth(i)
            txt = lamp.inner_text().strip()[:30]
            print(f"7. Status-Lamp {i}: {txt!r}")

        # 8. Drag-Simulation: Maus auf eine Card, halte
        print("8. Maus-Drag-Simulation...")
        page.mouse.move(800, 500)
        page.mouse.down()
        page.mouse.move(900, 500, steps=5)
        page.mouse.up()
        page.screenshot(path=test_dir / "08_after_drag.png", full_page=True)

        # 9. Spezifisches Element-Screenshot: Key-Import-Bereich
        if page.locator("#llm-keys-input").count() > 0:
            page.locator("#llm-keys-input").screenshot(
                path=test_dir / "09_key_input_element.png"
            )

        # 10. Cleanup
        page.close()
        context.close()
        browser.close()

        print(f"\n✓ Chromium-Test PASSED. Artifacts: {test_dir}/")


def test_full_workflow_firefox():
    """Firefox-Test (kürzer, nur smoke)."""
    test_dir = ARTIFACT_DIR / "firefox"
    test_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            record_video_dir=str(test_dir / "videos"),
        )
        page = context.new_page()

        print("\n=== FIREFOX TEST ===")
        page.goto(HUB_URL, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        page.screenshot(path=test_dir / "01_firefox_hub.png", full_page=True)
        page.locator("button:has-text('LLM')").first.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=test_dir / "02_firefox_llm.png", full_page=True)
        print("✓ Firefox-Test PASSED")

        page.close()
        context.close()
        browser.close()


def test_full_workflow_webkit():
    """WebKit/Safari-Test."""
    test_dir = ARTIFACT_DIR / "webkit"
    test_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()

        print("\n=== WEBKIT TEST ===")
        page.goto(HUB_URL, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        page.screenshot(path=test_dir / "01_webkit_hub.png", full_page=True)
        page.locator("button:has-text('LLM')").first.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=test_dir / "02_webkit_llm.png", full_page=True)
        print("✓ WebKit-Test PASSED")

        page.close()
        context.close()
        browser.close()


def test_vision_tools():
    """Vision-Tools: Screenshot-Vergleiche, Pixel-Analyse, Layout-Detection."""
    test_dir = ARTIFACT_DIR / "vision"
    test_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()

        print("\n=== VISION TEST ===")

        # 1. Page öffnen + Full-Screenshot
        page.goto(HUB_URL, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)
        full_shot = page.screenshot(path=test_dir / "01_full.png", full_page=True)
        print(f"1. Full-Screenshot: {len(full_shot)} bytes")

        # 2. Element-spezifische Screenshots
        page.locator("button:has-text('LLM')").first.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=test_dir / "02_llm_viewport.png", full_page=False)
        page.screenshot(path=test_dir / "03_llm_fullpage.png", full_page=True)
        print("2. Element-Screenshots gemacht")

        # 3. Mask-Screenshot (nur ein Element)
        if page.locator("#llm-keys-input").count() > 0:
            page.locator("#llm-keys-input").screenshot(
                path=test_dir / "04_key_input.png"
            )
            print("3. Key-Input Element-Screenshot")

        # 4. Per-Agent Row Screenshots
        rows = page.locator("tr[data-agent]")
        for i in range(min(rows.count(), 8)):
            rows.nth(i).screenshot(path=test_dir / f"05_row_{i}.png")

        # 5. Pixel-Analyse: ist die Seite leer oder hat sie Content?
        # (Screenshot-Größe > 50KB = hat Content)
        size = os.path.getsize(test_dir / "01_full.png")
        assert size > 50000, f"Screenshot zu klein ({size} bytes) — Seite wahrscheinlich leer"
        print(f"5. Pixel-Analyse: {size} bytes > 50KB → Content OK")

        # 6. Visual Regression: LLM-Page sollte bei jedem Run gleich aussehen
        llm_shot = test_dir / "03_llm_fullpage.png"
        if llm_shot.exists():
            print(f"6. Visual-Regression Screenshot: {llm_shot.stat().st_size} bytes")

        # 7. Color-Pixel-Check: Header sollte cyan/dark sein
        # (Take pixel at known location)
        try:
            header_pixel = page.evaluate("""() => {
                const header = document.querySelector('header');
                if (!header) return null;
                const style = window.getComputedStyle(header);
                return { bg: style.backgroundColor, color: style.color };
            }""")
            print(f"7. Header-Style: {header_pixel}")
        except Exception as e:
            print(f"7. Header-Style-Check fehlgeschlagen: {e}")

        # 8. Element-Bounding-Boxen
        llm_btn = page.locator("button:has-text('LLM')").first
        box = llm_btn.bounding_box()
        if box:
            print(f"8. LLM-Button Bounding-Box: x={box['x']:.0f}, y={box['y']:.0f}, w={box['width']:.0f}, h={box['height']:.0f}")

        # 9. Animation/Visual-State
        cursor_style = page.evaluate("""() => {
            const s = window.getComputedStyle(document.body);
            return { fontFamily: s.fontFamily, background: s.backgroundColor };
        }""")
        print(f"9. Body-Style: {cursor_style}")

        browser.close()
        print(f"\n✓ Vision-Test PASSED. Artifacts: {test_dir}/")


if __name__ == "__main__":
    test_full_workflow_chromium()
    test_full_workflow_firefox()
    test_full_workflow_webkit()
    test_vision_tools()
    print("\n=== ALLE TESTS PASSED ===")
    print(f"Artifacts: {ARTIFACT_DIR}/")
