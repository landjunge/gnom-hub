import asyncio
from playwright.async_api import async_playwright

async def main():
    print("🚀 Starting headed Playwright browser...")
    async with async_playwright() as p:
        # Launch headed browser so the user can see it
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to local Gnom-Hub dashboard
        print("🌐 Navigating to http://localhost:3002...")
        await page.goto("http://localhost:3002", timeout=60000)
        
        # Wait for chat input area to load
        print("⏳ Waiting for chat input field...")
        await page.wait_for_selector("#chat-input", state="visible", timeout=30000)
        
        # Type the instruction for @coderag
        instruction = (
            "@coderag: Bitte lies die FTP-Zugangsdaten aus der Datei 'apikeys' (relativer Pfad im Workspace) "
            "und lade alle geänderten HTML- und SVG-Dateien für netzwerkpunkt.de (Unterverzeichnis netzwerkpunkt.de/httpdocs) "
            "und königlichesfeenreich.de (Unterverzeichnis xn--knigliches-feenreich-39b.de/httpdocs) per FTP "
            "auf die echten Webserver hoch. Verwende index.html.bak als index.html für netzwerkpunkt.de, "
            "und feenreich_index.html als index.html für königlichesfeenreich.de. Führe kein git push aus."
        )
        print("✍️ Typing deployment instruction into chat...")
        await page.fill("#chat-input", instruction)
        
        # Submit the form by pressing Enter
        print("📤 Submitting instruction...")
        await page.keyboard.press("Enter")
        
        # Keep browser open for 60 seconds to watch the execution live
        print("👀 Keeping the headed browser open for 60 seconds to watch the Gnom-Hub agents execute...")
        await asyncio.sleep(60)
        
        # Close the browser
        print("🏁 Closing browser.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
