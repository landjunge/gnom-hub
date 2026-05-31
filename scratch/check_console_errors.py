# scratch/check_console_errors.py
from playwright.sync_api import sync_playwright
import time

def main():
    url = "http://127.0.0.1:3003"
    print("Checking page console errors and thoughts panel DOM status...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(err.message))
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}") if msg.type == "error" else None)
        
        try:
            page.goto(url)
            time.sleep(2)
            
            # Print status of #thought-display and senior-mode class
            body_class = page.evaluate("document.body.className")
            thought_display_style = page.evaluate("const el = document.getElementById('thought-display'); el ? window.getComputedStyle(el).display : 'not_found'")
            header_style = page.evaluate("const el = document.querySelector('#chat-split-container > div:first-child'); el ? window.getComputedStyle(el).display : 'not_found'")
            
            print(f"Body classes: '{body_class}'")
            print(f"thought-display computed display: '{thought_display_style}'")
            print(f"thought-display header computed display: '{header_style}'")
            
            if errors:
                print("❌ JavaScript Errors encountered:")
                for e in errors:
                    print(f"  - {e}")
            else:
                print("✅ No JavaScript runtime errors found on page load.")
                
        except Exception as e:
            print(f"Error checking page: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
