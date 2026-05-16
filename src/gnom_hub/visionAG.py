import pyautogui
import time
import re
import json
from pathlib import Path
from .provider_switchAG import llm_call
from .gitAG import auto_commit
from .evaluatorAG import evaluate_job
from .sandboxAG import safe_run_command

VISION_DIR = Path(".visions")
VISION_DIR.mkdir(parents=True, exist_ok=True)

VISION_SCHEMA = {
    "description": str,
    "action": ["click", "type", "scroll", "move", "done"],
    "params": (str, int, list, type(None))
}

def take_screenshot() -> str:
    try:
        path = VISION_DIR / f"shot_{time.strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot(str(path))
        return str(path)
    except:
        return "ERROR: Screenshot failed"

def validate_vision_schema(data):
    if not isinstance(data, dict): return False
    for key, expected in VISION_SCHEMA.items():
        if key not in data: return False
        val = data[key]
        if expected == str and not isinstance(val, str): return False
        if isinstance(expected, list) and val not in expected: return False
        if isinstance(expected, tuple) and not any(isinstance(val, t) for t in expected): return False
    return True

def vision_loop(command: str, max_steps: int = 5) -> str:
    for step in range(max_steps):
        screenshot = take_screenshot()
        if "ERROR" in screenshot: return "❌ Vision-Loop abgebrochen"
        
        prompt = f"Screenshot: {screenshot}\nTask: {command}\nSchritt {step+1}/{max_steps}\nNUR valide JSON: {{\"description\": \"...\", \"action\": \"click|type|scroll|move|done\", \"params\": ...}}"
        try:
            resp = llm_call(prompt, system="Vision-Loop-Agent: immer exakt valide JSON.")
            result = json.loads(re.sub(r'```(?:json)?\s*|\s*```', '', resp, flags=re.DOTALL))
            
            if not validate_vision_schema(result) or result.get("action") == "done":
                auto_commit(".", message="Vision Loop Done")
                return f"✅ Vision-Loop fertig: {result.get('description', 'Task erledigt')}"
            
            if result.get("action") == "click": pyautogui.click()
            elif result.get("action") == "type": pyautogui.typewrite(str(result.get("params", "")))
            elif result.get("action") == "scroll": pyautogui.scroll(int(result.get("params", 500)))
            elif result.get("action") == "move": pass
            
            evaluate_job(command, f"Schritt {step}: {result.get('description','')}")
            auto_commit(".", message=f"Vision Step {step}")
            
        except Exception as e:
            safe_run_command(f"echo 'Vision Error Step {step}: {str(e)}' >> .backups/sandbox.log", "visionAG")
            continue
    
    return "⏹️ Vision-Loop pausiert (Max-Schritte)"
