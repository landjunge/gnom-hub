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

def take_screenshot() -> str:
    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = VISION_DIR / f"shot_{timestamp}.png"
        pyautogui.screenshot(str(path))
        return str(path)
    except:
        return "ERROR: Screenshot failed"

def safe_json_parse(text: str):
    """Robuste JSON-Extraktion – handhabt Müll, Markdown, extra Text."""
    try:
        return json.loads(text)
    except:
        # Fallback 1: JSON-Block aus Markdown/Code-Block extrahieren
        match = re.search(r'```(?:json)?\s*(.+?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        # Fallback 2: Erstes { ... } im Text finden
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        return None

def vision_loop(command: str, max_steps: int = 5) -> str:
    """@vision loop – iterativ, selbstheilend, mit starker JSON-Validierung."""
    for step in range(max_steps):
        screenshot = take_screenshot()
        if "ERROR" in screenshot:
            return "❌ Vision-Loop abgebrochen: Screenshot-Probleme"
        
        prompt = f"Screenshot: {screenshot}\nTask: {command}\nSchritt {step+1}/{max_steps}\nAntworte NUR mit valide JSON: {{\"description\": \"...\", \"action\": \"click|type|scroll|move|done\", \"params\": \"...\"}}"
        try:
            resp = llm_call(prompt, system="Vision-Loop-Agent: immer valide JSON ausgeben, keine Erklärung.")
            result = safe_json_parse(resp)
            
            if not result or result.get("action") == "done":
                auto_commit(".", message="Vision Loop Done")
                return f"✅ Vision-Loop fertig: {result.get('description', 'Task erledigt') if result else 'Task abgeschlossen'}"
            
            # Aktion ausführen
            if result.get("action") == "click": pyautogui.click()
            elif result.get("action") == "type": pyautogui.typewrite(str(result.get("params", "")))
            elif result.get("action") == "scroll": pyautogui.scroll(int(result.get("params", 500)))
            elif result.get("action") == "move": pass
            
            evaluate_job(command, f"Schritt {step}: {result.get('description','')}")
            auto_commit(".", message=f"Vision Step {step}")
            
        except Exception as e:
            safe_run_command(f"echo 'Vision JSON Error Step {step}: {str(e)}' >> .backups/sandbox.log", "visionAG")
            continue  # Retry
    
    return "⏹️ Vision-Loop: Max-Schritte oder zu viele Fehler – Task pausiert"
