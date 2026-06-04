import asyncio
from playwright.async_api import async_playwright

async def main():
    print("🚀 Starting headed Playwright browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("🌐 Navigating to http://localhost:3002...")
        await page.goto("http://localhost:3002", timeout=60000)
        
        print("⏳ Waiting for chat input field...")
        await page.wait_for_selector("#chat-input", state="visible", timeout=30000)
        
        instruction = (
            "@code: Bitte lies die FTP-Zugangsdaten aus 'apikeys' (relativer Pfad im Workspace) "
            "und lade alle geänderten HTML- und SVG-Dateien für netzwerkpunkt.de (Unterverzeichnis netzwerkpunkt.de/httpdocs) "
            "und königlichesfeenreich.de (Unterverzeichnis xn--knigliches-feenreich-39b.de/httpdocs) per FTP "
            "auf die echten Webserver hoch. Verwende index.html.bak als index.html für netzwerkpunkt.de, "
            "und feenreich_index.html als index.html für königlichesfeenreich.de. Führe kein git push aus."
        )
        
        print("✍️ Typing deployment instruction into chat...")
        await page.fill("#chat-input", instruction)
        
        print("📤 Submitting instruction...")
        await page.keyboard.press("Enter")
        
        # Keep open for 120 seconds to watch the model process, execute the FTP curl commands, and finish the live upload
        print("👀 Watching the execution live for 120 seconds...")
        await asyncio.sleep(120)
        
        print("🏁 Closing browser.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
