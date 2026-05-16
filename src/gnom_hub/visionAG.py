import pyautogui
import time
from pathlib import Path
from .provider_switchAG import llm_call
from .gitAG import auto_commit
from .evaluatorAG import evaluate_job
from .sandboxAG import safe_run_command  # für Notfall-Logs

VISION_DIR = Path(".visions")
VISION_DIR.mkdir(parents=True, exist_ok=True)

def take_screenshot() -> str:
    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = VISION_DIR / f"shot_{timestamp}.png"
        pyautogui.screenshot(str(path))
        return str(path)
    except:
        return "ERROR: Screenshot fehlgeschlagen"

def vision_loop(command: str, max_steps: int = 5) -> str:
    """@vision loop – iterativ, selbstheilend, mit Fehler-Retry."""
    for step in range(max_steps):
        screenshot = take_screenshot()
        if "ERROR" in screenshot:
            return "❌ Vision-Loop abgebrochen: Screenshot-Probleme"
        
        prompt = f"Screenshot: {screenshot}\nTask: {command}\nSchritt {step+1}/{max_steps}\nJSON: {{\"description\": \"...\", \"action\": \"click|type|scroll|move|done\", \"params\": \"...\"}}"
        try:
            resp = llm_call(prompt, system="Vision-Loop-Agent: präzise, bei Fehler 'done' mit Fehlermeldung.")
            result = __import__("json").loads(resp)
            
            if result.get("action") == "done":
                auto_commit(".", message="Vision Loop Done")
                return f"✅ Vision-Loop fertig: {result.get('description', 'Task erledigt')}"
            
            # Aktion ausführen
            if result["action"] == "click": pyautogui.click()
            elif result["action"] == "type": pyautogui.typewrite(str(result.get("params", "")))
            elif result["action"] == "scroll": pyautogui.scroll(int(result.get("params", 500)))
            elif result["action"] == "move": pass
            
            evaluate_job(command, f"Schritt {step}: {result.get('description','')}")
            auto_commit(".", message=f"Vision Step {step}")
            
        except Exception as e:  # JSON, LLM oder Action-Fehler
            safe_run_command(f"echo 'Vision-Error Step {step}: {str(e)}' >> .backups/sandbox.log", "visionAG")
            continue  # Retry nächster Schritt
    
    return "⏹️ Vision-Loop: Max-Schritte oder zu viele Fehler – Task pausiert"
