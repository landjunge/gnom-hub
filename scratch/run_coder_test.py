import time
import requests
import os
from pathlib import Path

API_URL = "http://127.0.0.1:3002/api"
WORKSPACE_DIR = Path("/Users/landjunge/Documents/AG-Flega/gnom_workspace/default")

def post_chat(msg):
    try:
        r = requests.post(f"{API_URL}/chat", json={"content": msg, "sender": "user"})
        return r.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_chat():
    try:
        r = requests.get(f"{API_URL}/chat?limit=20")
        return list(reversed(r.json()))
    except Exception as e:
        print(f"Error: {e}")
        return []

def run_coder_test():
    # Clear chat
    requests.post(f"{API_URL}/chat", json={"content": "@@clear chat", "sender": "user"})
    time.sleep(1)
    
    # Clean workspace test files if exists
    test_file = WORKSPACE_DIR / "test_coder.txt"
    if test_file.exists():
        test_file.unlink()
        
    msg = (
        "@CoderAG: Erstelle eine Testdatei [WRITE: test_coder.txt]Hallo von CoderAG[/WRITE] im Workspace. "
        "Führe danach ein Browser-Skript aus, um http://127.0.0.1:3002/api/health zu öffnen: "
        "[BROWSER:\n"
        "import asyncio\n"
        "from playwright.async_api import async_playwright\n"
        "async def main():\n"
        "    async with async_playwright() as p:\n"
        "        browser = await p.chromium.launch()\n"
        "        page = await browser.new_page()\n"
        "        await page.goto('http://127.0.0.1:3002/api/health')\n"
        "        content = await page.content()\n"
        "        print('Browser-Inhalt:', content)\n"
        "        await browser.close()\n"
        "asyncio.run(main())\n"
        "]"
    )
    
    print("Posting message to CoderAG...")
    res = post_chat(msg)
    print(f"Response: {res}\n")
    
    seen_ids = set()
    completed = False
    for _ in range(30):
        time.sleep(3)
        msgs = get_chat()
        for m in msgs:
            mid = m.get("id")
            if mid not in seen_ids:
                seen_ids.add(mid)
                sender = m.get("sender")
                content = m.get("content")
                if sender != "System" and "cleared" not in content:
                    print(f"[{sender}]: {content}")
                if sender == "CoderAG":
                    completed = True
        if completed:
            break
            
    # Check if file was created
    if test_file.exists():
        print(f"\nSUCCESS: test_coder.txt was created! Content: '{test_file.read_text()}'")
    else:
        print("\nFAILURE: test_coder.txt was NOT created.")

if __name__ == "__main__":
    run_coder_test()
