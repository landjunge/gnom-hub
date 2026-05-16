import pyautogui, time, json
from .provider_switchAG import llm_call
from .sandboxAG import safe_run_command
from .gitAG import auto_commit

pyautogui.FAILSAFE = True

def desktop_action(command: str) -> str:
    prompt = f"Befehl: {command}\nÜbersetze in JSON: {{\"action\": \"click|type|scroll|open_app|keypress|move|run_cmd\", \"params\": ...}}"
    try:
        a = json.loads(llm_call(prompt, "Du bist präziser Desktop-Parser. Nur valide JSON.", 150))
        if a["action"] == "click": pyautogui.click()
        elif a["action"] == "type": pyautogui.typewrite(str(a["params"]))
        elif a["action"] == "scroll": pyautogui.scroll(int(a.get("params", 500)))
        elif a["action"] == "open_app":
            pyautogui.hotkey("command", "space"); time.sleep(0.5); pyautogui.typewrite(str(a["params"]) + "\n")
        elif a["action"] == "keypress": pyautogui.press(str(a["params"]))
        elif a["action"] == "move":
            x, y = map(int, str(a["params"]).split(","))
            pyautogui.moveTo(x, y)
        elif a["action"] == "run_cmd": return safe_run_command(str(a["params"]), "desktopAG")
        auto_commit(".")
        return f"✅ Desktop: {a['action']} ausgeführt"
    except Exception as e: return f"❌ Desktop-Fehler: {str(e)}"
