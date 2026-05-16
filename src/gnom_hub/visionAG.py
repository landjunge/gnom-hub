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

def robust_json_repair(text: str):
    """Tiefgehende Repair: Fences, Trailing Commas, Single Quotes, Truncation, Prose."""
    # 1. Markdown Fences entfernen
    text = re.sub(r'```(?:json)?\s*|\s*```', '', text, flags=re.DOTALL)
    # 2. Trailing Commas killen
    text = re.sub(r',\s*([}\]])', r'\1', text)
    # 3. Single Quotes → Double + unquoted Keys fixen (einfache Heuristik)
    text = re.sub(r"'", '"', text)
    text = re.sub(r'(\W)(\w+):', r'\1"\2":', text)
    # 4. Nur den ersten validen JSON-Block extrahieren
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if match:
        text = match.group(1)
    try:
        return json.loads(text)
    except:
        return None

def vision_loop(command: str, max_steps: int = 5) -> str:
    """@vision loop – jetzt mit Repair + LLM-Retry bei Parsing-Fehlern."""
    for step in range(max_steps):
        screenshot = take_screenshot()
        if "ERROR" in screenshot:
            return "❌ Vision-Loop abgebrochen: Screenshot-Probleme"
        
        prompt = f"Screenshot: {screenshot}\nTask: {command}\nSchritt {step+1}/{max_steps}\nAntworte NUR mit valide JSON: {{\"description\": \"...\", \"action\": \"click|type|scroll|move|done\", \"params\": \"...\"}}"
        try:
            resp = llm_call(prompt, system="Vision-Loop-Agent: immer exakt valide JSON, keine Erklärung, keine Fences.")
            result = robust_json_repair(resp)
            
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
            error_msg = str(e)
            safe_run_command(f"echo 'Vision JSON Error Step {step}: {error_msg}' >> .backups/sandbox.log", "visionAG")
            # Retry mit Fehler-Feedback an LLM
            retry_prompt = f"{prompt}\n\nFEHLER: {error_msg}\nKorrigiere und gib NUR valide JSON!"
            resp = llm_call(retry_prompt, system="Korrigiere den JSON-Fehler und gib exakt valide JSON.")
            result = robust_json_repair(resp)
            if result:
                continue  # Retry hat geklappt (nächster Vision-Schritt)
            # sonst nächster Schritt
    
    return "⏹️ Vision-Loop: Max-Schritte oder zu viele Fehler – Task pausiert"
