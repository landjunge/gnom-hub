# scratch/check_buttons.py
from playwright.sync_api import sync_playwright
import time

def main():
    url = "http://127.0.0.1:3002"
    print(f"Connecting to {url} and scanning buttons...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url)
            time.sleep(3) # Wait for bootstrap and War Room rendering
            
            # Find all buttons
            buttons = page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('button').forEach(btn => {
                    list.push({
                        id: btn.id,
                        className: btn.className,
                        text: btn.innerText.trim(),
                        visible: window.getComputedStyle(btn).display !== 'none' && window.getComputedStyle(btn).visibility !== 'hidden',
                        parentId: btn.parentElement ? btn.parentElement.id || btn.parentElement.className : 'none'
                    });
                });
                return list;
            }""")
            
            print("\\n--- ALL BUTTONS ON PAGE ---")
            for i, b in enumerate(buttons):
                vis_str = "VISIBLE" if b['visible'] else "HIDDEN"
                print(f"{i+1}. Text: '{b['text']}' | ID: '{b['id']}' | Class: '{b['className']}' | Parent: '{b['parentId']}' | {vis_str}")
                
            # Find all select dropdowns
            selects = page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('select').forEach(sel => {
                    list.push({
                        id: sel.id,
                        className: sel.className,
                        value: sel.value,
                        visible: window.getComputedStyle(sel).display !== 'none'
                    });
                });
                return list;
            }""")
            print("\\n--- ALL SELECT DROPDOWNS ON PAGE ---")
            for i, s in enumerate(selects):
                vis_str = "VISIBLE" if s['visible'] else "HIDDEN"
                print(f"{i+1}. ID: '{s['id']}' | Class: '{s['className']}' | Value: '{s['value']}' | {vis_str}")

        except Exception as e:
            print(f"Error checking buttons: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
