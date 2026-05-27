# gatekeeper.py — Double approval verification for file writes and shell commands with Showbox decisions
import os
import uuid
import time
import json
from .db import (
    add_chat_message, 
    get_state_value, 
    set_state_value, 
    save_showbox_presentation, 
    set_active_showbox, 
    get_active_project, 
    set_agent_status
)
import gnom_hub.router as router
from .path_validator import is_worker_blocked, is_security_block, _safe
from .capability_manager import check_capability, request_capability

def wait_for_decision(agent_name, action_type, detail, content, rule) -> bool:
    decision_id = str(uuid.uuid4())
    
    # 1. Determine blocker agent and style
    blocker_name = "WatchdogAG"
    blocker_sys = "Du bist WatchdogAG. Erkläre kurz, präzise und bestimmt in deutscher Sprache (max 2 Sätze), gegen welche Workspace- oder Dateiregel die Aktion verstößt (z.B. Zugriff auf geschützte Systemdatei, Überschreiten des Zeilenlimits)."
    blocker_color = "#FFA500"
    blocker_rgb = "255, 165, 0"
    
    if "security" in rule.lower() or "gefahr" in rule.lower() or "sicherheits" in rule.lower():
        blocker_name = "SecurityAG"
        blocker_sys = "Du bist SecurityAG. Erkläre kurz, präzise und bestimmt in deutscher Sprache (max 2 Sätze), welches konkrete Sicherheitsrisiko diese Aktion birgt (z.B. nicht autorisierter Systembefehl, potenzielle Schadsoftware, unsichere Paketquelle)."
        blocker_color = "#FF69B4"
        blocker_rgb = "255, 105, 180"
        
    # 2. Query blocker explanation
    try:
        blocker_prompt = f"Erkläre kurz (max 2 Sätze) warum die Aktion von {agent_name} ({action_type}: {detail}) blockiert wurde. Grund/Regel: {rule}."
        blocker_explanation = router.ask_router(blocker_prompt, sys=blocker_sys, agent_name=blocker_name).content
    except Exception as e:
        blocker_explanation = f"Aktion blockiert aufgrund von Regelverletzung: {rule} ({e})"
        
    # 3. Query SoulAG for context/assessment
    try:
        soul_prompt = (
            f"Der Worker {agent_name} versucht die Aktion '{action_type}: {detail}' auszuführen, "
            f"die von {blocker_name} blockiert wurde.\n"
            f"Gibt es im Gedächtnis des Schwarms relevante Vorlieben, Einstellungen oder Kontext des Users zu dieser Datei/diesem Befehl?\n"
            f"Antworte in deutscher Sprache und fasse die Fakten und deine Einschätzung in max 2 Sätzen zusammen."
        )
        soul_assessment = router.ask_router(soul_prompt, sys="Du bist SoulAG. Analysiere das Problem und gib eine kurze Einschätzung.", agent_name="SoulAG").content
    except Exception as e:
        soul_assessment = f"Keine Einschätzung von SoulAG verfügbar: {e}"
        
    # 4. Query GeneralAG for coordination recommendation
    try:
        general_prompt = (
            f"Die Aktion von {agent_name} ({action_type}: {detail}) wurde blockiert.\n"
            f"Einschätzung von {blocker_name}: '{blocker_explanation}'\n"
            f"Einschätzung von SoulAG: '{soul_assessment}'\n"
            f"Nimm als Orchestrator Stellung dazu und empfehle dem User in deutscher Sprache kurz (max 2 Sätze) eine Vorgehensweise."
        )
        general_statement = router.ask_router(general_prompt, sys="Du bist GeneralAG. Triff eine kurze Empfehlung.", agent_name="GeneralAG").content
    except Exception as e:
        general_statement = "Empfehlung: Bitte prüfe die Berechtigungen oder passe den Code an."

    # 5. Register the pending decision
    pending = get_state_value("pending_decisions", {})
    pending[decision_id] = {
        "agent_name": agent_name,
        "action_type": action_type,
        "detail": detail,
        "content": content,
        "rule": rule,
        "status": "pending"
    }
    set_state_value("pending_decisions", pending)
    
    # 6. Build HTML content for Showbox slide with agent colors and pulsing frame trigger
    html_content = (
        f"<div style='padding: 20px; font-family: sans-serif; color: #fff; background: rgba(10, 10, 15, 0.95); height: 100%; box-sizing: border-box; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1);'>"
        f"  <h2 style='color: #ff3333; margin: 0; display: flex; align-items: center; gap: 10px; font-size: 1.3rem; text-transform: uppercase; letter-spacing: 1px;'>"
        f"    <span style='font-size: 1.6rem;'>🛑</span> CRITICAL: System-Blockade"
        f"  </h2>"
        f"  <div style='font-size: 0.95rem; color: rgba(255,255,255,0.7); margin-bottom: 5px;'>"
        f"    <strong>Aktion:</strong> <code style='background: rgba(255,255,255,0.15); padding: 3px 8px; border-radius: 4px; color: #fff; font-family: monospace;'>{action_type}: {detail}</code> durch <strong style='color: #fff;'>{agent_name}</strong>"
        f"  </div>"
        f"  <div style='border-left: 4px solid {blocker_color}; background: rgba({blocker_rgb}, 0.08); padding: 12px; border-radius: 4px;'>"
        f"    <div style='color: {blocker_color}; font-weight: bold; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 4px; display: flex; align-items: center; gap: 5px;'>"
        f"      🛡️ {blocker_name}"
        f"    </div>"
        f"    <div style='font-size: 0.9rem; line-height: 1.45;'>{blocker_explanation}</div>"
        f"  </div>"
        f"  <div style='border-left: 4px solid #FF0000; background: rgba(255, 0, 0, 0.08); padding: 12px; border-radius: 4px;'>"
        f"    <div style='color: #FF0000; font-weight: bold; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 4px; display: flex; align-items: center; gap: 5px;'>"
        f"      🧠 SoulAG (Gedächtnis)"
        f"    </div>"
        f"    <div style='font-size: 0.9rem; line-height: 1.45;'>{soul_assessment}</div>"
        f"  </div>"
        f"  <div style='border-left: 4px solid #00FFFF; background: rgba(0, 255, 255, 0.08); padding: 12px; border-radius: 4px;'>"
        f"    <div style='color: #00FFFF; font-weight: bold; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 4px; display: flex; align-items: center; gap: 5px;'>"
        f"      👑 GeneralAG (Koordinator)"
        f"    </div>"
        f"    <div style='font-size: 0.9rem; line-height: 1.45;'>{general_statement}</div>"
        f"  </div>"
        f"  <div style='display: flex; gap: 15px; margin-top: 10px;'>"
        f"    <button onclick=\"window.api('POST', '/chat', {{content: '@@approve_decision {decision_id}'}}).then(() => {{ this.disabled=true; this.innerText='Erlaubt'; }})\" "
        f"            style='flex: 1; background: #28a745; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 0.95rem; transition: background 0.2s;'> "
        f"      Ja, Aktion erlauben"
        f"    </button>"
        f"    <button onclick=\"window.api('POST', '/chat', {{content: '@@reject_decision {decision_id}'}}).then(() => {{ this.disabled=true; this.innerText='Abgelehnt'; }})\" "
        f"            style='flex: 1; background: #dc3545; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 0.95rem; transition: background 0.2s;'> "
        f"      Nein, blockiert lassen"
        f"    </button>"
        f"  </div>"
        f"</div>"
    )
    
    # 7. Save and set active showbox presentation with GeneralAG as sender
    presentation_name = f"Blockade: {agent_name}"
    save_showbox_presentation(presentation_name, [html_content], sender="GeneralAG")
    set_active_showbox(presentation_name)
    
    # Send message to chat
    proj = get_active_project()
    add_chat_message(
        proj, 
        "GeneralAG", 
        "generalag", 
        "chat", 
        f"@user @SoulAG: [BLOCKADE] Die geplante Aktion von **{agent_name}** ({action_type}: {detail}) verletzt Watchdog-Regeln. Bitte entscheide in der Showbox!"
    )
    
    # 8. Pause agent and wait for user input
    set_agent_status(agent_name, "paused")
    
    while True:
        pending = get_state_value("pending_decisions", {})
        d = pending.get(decision_id)
        if d:
            if d["status"] == "approved":
                set_agent_status(agent_name, "busy")
                return True
            elif d["status"] == "rejected":
                set_agent_status(agent_name, "busy")
                return False
                
        # Fallback check if agent was resumed externally
        from .db import get_all_agents
        agents = get_all_agents()
        current_agent = next((a for a in agents if a["name"].lower() == agent_name.lower()), None)
        if current_agent and current_agent.get("status") not in ["paused", "offline"]:
            break
            
        time.sleep(0.5)
        
    set_agent_status(agent_name, "busy")
    return False

def verify_write(agent, fn, content, wd, perms) -> bool:
    name = (agent or {}).get("name", "Unknown")
    role = (agent or {}).get("role", "")
    if name.lower() == "generalag" or role == "general":
        add_chat_message("default", "WatchdogAG", "watchdogag", "chat", f"🛑 [BLOCKADE] GeneralAG hat keine Berechtigung, Dateien zu schreiben oder zu editieren.")
        return False
    if check_capability(name, "WRITE", fn): return True
    
    p = _safe(wd, fn, perms)
    if not p:
        return wait_for_decision(name, "WRITE", fn, content, "Pfad liegt außerhalb des zulässigen Workspaces")
        
    if is_worker_blocked(agent, fn, wd, perms):
        return wait_for_decision(name, "WRITE", fn, content, "Zugriff auf geschützte Systemdatei/Pfad")
    if is_security_block(agent, fn, content, wd, perms):
        return wait_for_decision(name, "WRITE", fn, content, "Gefährliche Code-Muster erkannt (z.B. rm -rf, eval, subprocess)")
        
    if role in ["soul", "watchdog", "security"]: return True
    p = _safe(wd, fn, perms)
    approved = [os.path.realpath(os.path.join(wd, a)) for a in (get_state_value("approved_security_writes", []) or [])]
    if p and os.path.realpath(p) in approved: return True
    
    # Safe Workspace Writes Auto-Approval:
    # If the path is safe (in workspace), not worker-blocked, and has no dangerous security patterns,
    # we automatically grant capability and approve without slow LLM queries.
    request_capability(name, "WRITE", fn, "AutoApprovedSafePath")
    return True

def is_command_safe_and_whitelisted(cmd: str):
    """
    Parses a shell command and determines if it is safe and whitelisted.
    Returns (is_safe, reason).
    """
    import re
    import requests
    
    # 1. Clean the command and split it by common shell chain operators.
    parts = re.split(r'(&&|\|\||;|\|)', cmd)
    for part in parts:
        part = part.strip()
        if not part or part in ("&&", "||", ";", "|"):
            continue
            
        # Parse individual command: skip environment variables (e.g. A=B) at the start
        tokens = part.split()
        exec_token = None
        args_tokens = []
        for t in tokens:
            if "=" in t and exec_token is None:
                continue
            if exec_token is None:
                exec_token = t
            else:
                args_tokens.append(t)
                
        if not exec_token:
            continue
            
        # Normalize executable name (e.g. './run.sh' -> 'run.sh', '/usr/bin/python3' -> 'python3')
        exec_name = os.path.basename(exec_token).strip()
        
        # 2. Strict Whitelist of Allowed Base Executables
        allowed_execs = {
            "python3", "python", "pytest", "git", "pip", "pip3",
            "npm", "npx", "node", "ls", "echo", "cat", "tail"
        }
        
        if exec_name not in allowed_execs:
            return False, f"Befehl '{exec_name}' ist nicht auf der Whitelist erlaubter Programme."
            
        # 3. Arguments validation for specific commands
        if exec_name in ("pip", "pip3"):
            if len(args_tokens) >= 2 and args_tokens[0] == "install":
                packages = [a for a in args_tokens[1:] if not a.startswith("-")]
                if not packages:
                    return False, "Ungültiger pip install Befehl ohne Paketnamen."
                
                safe_packages = {
                    "pytest", "requests", "fpdf2", "numpy", "pandas",
                    "fastapi", "uvicorn", "jinja2", "pycompile", "autopep8"
                }
                
                for pkg in packages:
                    pkg_clean = re.split(r'(==|>=|<=|>|<)', pkg)[0].strip()
                    if pkg_clean.lower() in safe_packages:
                        continue
                    
                    try:
                        url = f"https://pypi.org/pypi/{pkg_clean}/json"
                        r = requests.get(url, timeout=3.0)
                        if r.status_code == 200:
                            data = r.json()
                            vulns = data.get("vulnerabilities", [])
                            if vulns:
                                return False, f"Paket '{pkg_clean}' hat bekannte Sicherheitslücken auf PyPI."
                            releases = data.get("releases", {})
                            if len(releases) < 1:
                                return False, f"Paket '{pkg_clean}' hat keine gültigen Releases auf PyPI."
                        else:
                            return False, f"Paket '{pkg_clean}' konnte nicht auf PyPI verifiziert werden (Status {r.status_code})."
                    except Exception as e:
                        return False, f"Netzwerkfehler bei der Verifizierung von '{pkg_clean}': {e}"
                        
        elif exec_name in ("npm", "npx"):
            if len(args_tokens) >= 2 and args_tokens[0] == "install":
                packages = [a for a in args_tokens[1:] if not a.startswith("-")]
                safe_npm = {"vite", "react", "vue", "next"}
                for pkg in packages:
                    if pkg.lower() not in safe_npm:
                        return False, f"NPM Paket '{pkg}' ist nicht als sicher vordefiniert."
                        
        elif exec_name == "git":
            allowed_git_subcmds = {"status", "log", "diff", "commit", "add", "checkout", "reset", "init", "config"}
            if not args_tokens or args_tokens[0] not in allowed_git_subcmds:
                return False, f"Git Subbefehl '{args_tokens[0] if args_tokens else ''}' ist nicht autorisiert."
                
    return True, ""

def verify_cmd(agent, cmd):
    name = (agent or {}).get("name", "Unknown")
    role = (agent or {}).get("role", "")
    if name.lower() == "generalag" or role == "general":
        add_chat_message("default", "WatchdogAG", "watchdogag", "chat", f"🛑 [BLOCKADE] GeneralAG hat keine Berechtigung, Terminal-Befehle auszuführen.")
        return False
    if check_capability(name, "SHELL", cmd): return True
    if role in ["soul", "watchdog", "security"]: return True
    if any(p in cmd.lower() for p in ["src/gnom_hub", "config/", "scripts/", "run.sh", "index.html", ".env"]):
        return wait_for_decision(name, "SHELL", cmd, "", "Befehl greift auf geschützte Systemdateien/Pfade zu")
    if cmd in (get_state_value("approved_security_commands", []) or []): return True
    
    # Smart Rules Engine: Auto-approve whitelisted commands
    is_safe, block_reason = is_command_safe_and_whitelisted(cmd)
    if is_safe:
        request_capability(name, "SHELL", cmd, "AutoApprovedWhitelistedCommand")
        return True
    else:
        return wait_for_decision(name, "SHELL", cmd, "", block_reason)
