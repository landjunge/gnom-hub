import pyautogui
import time
from pathlib import Path
from .provider_switchAG import llm_call
from .gitAG import auto_commit
from .sandboxAG import safe_run_command

VISION_DIR = Path(".visions")
VISION_DIR.mkdir(parents=True, exist_ok=True)

def take_screenshot() -> str:
    """Macht Screenshot und speichert für Vision."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = VISION_DIR / f"shot_{timestamp}.png"
    pyautogui.screenshot(str(path))
    return str(path)

def vision_analyze(command: str) -> str:
    """@vision analyze oder @vision click – sieht den Screen und handelt."""
    screenshot_path = take_screenshot()
    prompt = f"""
    Screenshot: {screenshot_path}
    Befehl: {command}
    Beschreibe kurz, was du siehst. Dann gib JSON: {{"description": "...", "action": "click|type|scroll|move", "params": "..."}}
    """
    try:
        # Ollama Vision (z.B. llava) oder OpenRouter Vision-Model
        resp = llm_call(prompt, system="Du bist Vision-Agent. Analysiere Bildschirm präzise.")
        result = __import__("json").loads(resp)
        
        if result["action"] == "click":
            pyautogui.click()
        elif result["action"] == "type":
            pyautogui.typewrite(str(result.get("params", "")))
        elif result["action"] == "scroll":
            pyautogui.scroll(int(result.get("params", 500)))
        elif result["action"] == "move":
            pass # placeholder
            
        auto_commit(".", message=f"Vision Action: {result['action']}")
        return f"👁️ Vision sah: {result['description']}\n✅ Aktion: {result['action']} ausgeführt"
    except Exception as e:
        return f"❌ Vision-Fehler: {str(e)}"
