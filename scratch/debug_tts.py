import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Starte Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Listen for console messages
        page.on("console", lambda msg: print(f"🚀 [CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"❌ [PAGE ERROR] {err}"))
        
        print("Navigiere zu Gnom-Hub auf Port 3003...")
        await page.goto("http://127.0.0.1:3003")
        await page.wait_for_timeout(2000)
        
        # Check current ttsEnabled in localStorage
        tts_enabled = await page.evaluate("localStorage.getItem('ttsEnabled')")
        print(f"localStorage 'ttsEnabled': {tts_enabled}")
        
        # If not true, toggle it
        if tts_enabled != "true":
            print("Aktiviere TTS über Click...")
            await page.click("#tts-toggle-btn")
            await page.wait_for_timeout(500)
            tts_enabled = await page.evaluate("localStorage.getItem('ttsEnabled')")
            print(f"localStorage 'ttsEnabled' nach Click: {tts_enabled}")
            
        # Send a message to GeneralAG to trigger agent response
        print("Sende Chat-Nachricht...")
        await page.fill("#chat-input", "@generalag hello speak something")
        await page.click("button:has-text('Send')")
        
        print("Warte 20 Sekunden auf Antworten und TTS...")
        await page.wait_for_timeout(20000)
        
        await browser.close()
        print("Playwright beendet.")

if __name__ == "__main__":
    asyncio.run(main())
