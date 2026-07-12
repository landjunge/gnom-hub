# action_desktop.py — Desktop GUI automation (Mouse & Keyboard control)
import json
import os
import uuid


def verify_desktop(agent, action, details) -> bool:
    from gnom_hub.db import add_chat_message, get_active_project, get_state_value
    name = (agent or {}).get("name", "Unknown")
    
    if not get_state_value("enable_confirmations", False):
        proj = get_active_project()
        add_chat_message(
            proj,
            "WatchdogAG",
            "watchdogag",
            "chat",
            f"⚡ [AUTO-APPROVED] Desktop-Aktion von **{name}** ({action}: {details}) automatisch freigegeben."
        )
        return True
        
    from gnom_hub.core.security.gatekeeper import wait_for_decision
    return wait_for_decision(name, "DESKTOP", f"{action}: {details}", "", "Desktop GUI Interaktion angefordert")

def handle_desktop(ans, matches, agent, perms, wd) -> str:
    if not matches:
        return ans
    # Permission-Check (2026-07-11 — User-Mandat 21:24 "checke rechte überall"):
    # Desktop-Control ist sehr riskant (Maus/Keyboard auf User-Maschine) — nur godmode.
    if perms and "godmode" not in perms:
        name = (agent or {}).get("name", "?")
        for m in matches:
            ans = ans.replace(
                m.group(0),
                f"[System: {name} hat keine DESKTOP-Berechtigung. Nur SecurityAG (godmode).]",
            )
        return ans

    try:
        import pyautogui
        # Disable pyautogui fail-safe or set safety margins
        pyautogui.FAILSAFE = True
    except ImportError:
        for m in matches:
            ans = ans.replace(m.group(0), "[Desktop: pyautogui ist nicht installiert.]")
        return ans

    for m in matches:
        raw_json = m.group(1).strip()
        try:
            d = json.loads(raw_json)
            action = d.get("action", "").lower()
            
            # Extract arguments
            x = d.get("x")
            y = d.get("y")
            text = d.get("text", "")
            key = d.get("key", "")
            amount = d.get("amount", 0)
            
            if not action:
                ans = ans.replace(m.group(0), "[Desktop: Keine Aktion angegeben.]")
                continue
                
            details = ""
            if action in ("click", "double_click", "right_click", "move"):
                details = f"x={x}, y={y}"
            elif action == "type":
                details = f"text={text[:30]}"
            elif action == "press":
                details = f"key={key}"
            elif action == "scroll":
                details = f"amount={amount}"
            elif action == "screenshot":
                details = "Bildschirmfoto aufnehmen"
                
            if not verify_desktop(agent, action, details):
                ans = ans.replace(m.group(0), "[Desktop: Sicherheitsüberprüfung verweigert.]")
                continue
                
            result_msg = ""
            
            # Execute action using pyautogui
            if action == "click":
                if x is not None and y is not None:
                    pyautogui.click(x=int(x), y=int(y))
                    result_msg = f"Klick bei ({x}, {y}) ausgeführt."
                else:
                    pyautogui.click()
                    result_msg = "Klick bei aktueller Mausposition ausgeführt."
                    
            elif action == "double_click":
                if x is not None and y is not None:
                    pyautogui.doubleClick(x=int(x), y=int(y))
                    result_msg = f"Doppelklick bei ({x}, {y}) ausgeführt."
                else:
                    pyautogui.doubleClick()
                    result_msg = "Doppelklick bei aktueller Mausposition ausgeführt."
                    
            elif action == "right_click":
                if x is not None and y is not None:
                    pyautogui.rightClick(x=int(x), y=int(y))
                    result_msg = f"Rechtsklick bei ({x}, {y}) ausgeführt."
                else:
                    pyautogui.rightClick()
                    result_msg = "Rechtsklick bei aktueller Mausposition ausgeführt."
                    
            elif action == "move":
                if x is not None and y is not None:
                    pyautogui.moveTo(x=int(x), y=int(y), duration=0.5)
                    result_msg = f"Maus zu ({x}, {y}) bewegt."
                else:
                    result_msg = "Fehler: Koordinaten x und y fehlen für Mausbewegung."
                    
            elif action == "type":
                if text:
                    pyautogui.write(text, interval=0.05)
                    result_msg = f"Text '{text[:20]}...' getippt."
                else:
                    result_msg = "Fehler: Text fehlt für Tippen."
                    
            elif action == "press":
                if key:
                    pyautogui.press(key)
                    result_msg = f"Taste '{key}' gedrückt."
                else:
                    result_msg = "Fehler: Taste fehlt für Tastendruck."
                    
            elif action == "scroll":
                pyautogui.scroll(int(amount))
                result_msg = f"Scroll-Aktion ({amount}) ausgeführt."
                
            elif action == "screenshot":
                filename = f"desktop_screenshot_{uuid.uuid4().hex[:8]}.png"
                filepath = os.path.join(wd, filename)
                pyautogui.screenshot(filepath)
                
                # Save to presentation so it can be viewed in the browser showbox!
                from gnom_hub.db import save_showbox_presentation, set_active_showbox
                # Use raw endpoint to serve the image safely to showbox
                html_slide = f"<div style='padding:10px;text-align:center;color:#fff;'><h3 style='margin:0 0 10px 0;'>🖥️ Desktop Screenshot</h3><img src='/api/workspace/{filename}/raw' style='max-width:100%;max-height:85vh;border-radius:8px;border:1px solid #444;' /></div>"
                save_showbox_presentation("Desktop Screenshot", [html_slide], sender="System")
                set_active_showbox("Desktop Screenshot")
                result_msg = f"Screenshot unter '{filename}' gespeichert und in Showbox geladen."
                
            else:
                result_msg = f"Fehler: Unbekannte Desktop-Aktion '{action}'."
                
            ans = ans.replace(m.group(0), f"[Desktop: {result_msg}]")
            
        except Exception as e:
            error_str = str(e)
            if "accessibility" in error_str.lower() or "permission" in error_str.lower():
                error_str = "PyAutoGUI benötigt macOS Bedienungshilfen-Berechtigung (Systemeinstellungen -> Datenschutz & Sicherheit -> Bedienungshilfen)."
            ans = ans.replace(m.group(0), f"[Desktop-Fehler: {error_str}]")
            
    return ans
