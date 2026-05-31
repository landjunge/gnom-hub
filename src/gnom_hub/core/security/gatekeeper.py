# gatekeeper.py — Double approval verification for file writes and shell commands with Showbox decisions
import os
import uuid
import time
import json
from gnom_hub.db.legacy_db import (
    add_chat_message, 
    get_state_value, 
    set_state_value, 
    save_showbox_presentation, 
    set_active_showbox, 
    get_active_project, 
    set_agent_status
)
import gnom_hub.infrastructure.router.router as router
from gnom_hub.core.security.path_validator import is_worker_blocked, is_security_block, _safe
from gnom_hub.agents.capability_manager import check_capability, request_capability

def wait_for_decision(agent_name, action_type, detail, content, rule) -> bool:
    decision_id = str(uuid.uuid4())
    
    # 1. Determine blocker agent and style
    blocker_name = "WatchdogAG"
    blocker_sys = "Du bist WatchdogAG. Erkläre kurz, präzise und bestimmt in deutscher Sprache in genau 1 Satz, gegen welche Workspace- oder Dateiregel die Aktion verstößt."
    blocker_color = "#FFA500"
    blocker_rgb = "255, 165, 0"
    
    if "security" in rule.lower() or "gefahr" in rule.lower() or "sicherheits" in rule.lower():
        blocker_name = "SecurityAG"
        blocker_sys = "Du bist SecurityAG. Erkläre kurz, präzise und bestimmt in deutscher Sprache in genau 1 Satz, welches konkrete Sicherheitsrisiko diese Aktion birgt."
        blocker_color = "#FF69B4"
        blocker_rgb = "255, 105, 180"
        
    # 2. Query blocker explanation
    try:
        blocker_prompt = f"Erkläre in genau 1 Satz, warum die Aktion von {agent_name} ({action_type}: {detail}) blockiert wurde. Regel: {rule}."
        blocker_explanation = router.ask_router(blocker_prompt, sys=blocker_sys, agent_name=blocker_name).content
    except Exception as e:
        blocker_explanation = f"Blockiert wegen: {rule}"
        
    # 3. Query GeneralAG for coordination recommendation
    try:
        general_prompt = (
            f"Die Aktion von {agent_name} ({action_type}: {detail}) wurde blockiert.\n"
            f"Begründung: '{blocker_explanation}'\n"
            f"Gib dem User in genau 1 Satz eine kurze Empfehlung zur Vorgehensweise."
        )
        general_statement = router.ask_router(general_prompt, sys="Du bist GeneralAG. Triff eine kurze Empfehlung in genau 1 Satz.", agent_name="GeneralAG").content
    except Exception as e:
        general_statement = "Bitte passe den Pfad oder Befehl im Workspace an."

    # 4. Register the pending decision
    pending = get_state_value("pending_decisions", {})
    import time
    pending[decision_id] = {
        "agent_name": agent_name,
        "action_type": action_type,
        "detail": detail,
        "content": content,
        "rule": rule,
        "status": "pending",
        "timestamp": time.time()
    }
    set_state_value("pending_decisions", pending)
    
    # 5. Build HTML content for Showbox slide (Compact version - no scroll)
    html_content = (
        f"<div style='padding: 14px; font-family: sans-serif; color: #fff; background: rgba(10, 10, 15, 0.95); height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1);'>"
        f"  <div>"
        f"    <h2 style='color: #ff3333; margin: 0 0 10px 0; display: flex; align-items: center; gap: 8px; font-size: 1.15rem; text-transform: uppercase; letter-spacing: 1px;'>"
        f"      🛑 System-Blockade: {blocker_name}"
        f"    </h2>"
        f"    <div style='font-size: 0.85rem; color: rgba(255,255,255,0.7); margin-bottom: 10px; line-height: 1.3;'>"
        f"      <strong>{agent_name}</strong>: <code style='background: rgba(255,255,255,0.12); padding: 2px 6px; border-radius: 4px; color: #00e5ff; font-family: monospace; font-size: 0.8rem;'>{action_type}: {detail}</code>"
        f"    </div>"
        f"    <div style='background: rgba({blocker_rgb}, 0.05); border-left: 3px solid {blocker_color}; padding: 8px 10px; border-radius: 4px; font-size: 0.82rem; line-height: 1.35; margin-bottom: 8px;'>"
        f"      {blocker_explanation}"
        f"    </div>"
        f"    <div style='background: rgba(255, 255, 255, 0.03); border-left: 3px solid #00FFFF; padding: 6px 10px; border-radius: 4px; font-size: 0.8rem; line-height: 1.3; color: #94a3b8;'>"
        f"      💡 <em>Empfehlung:</em> {general_statement}"
        f"    </div>"
        f"  </div>"
        f"  <div style='display: flex; gap: 10px; margin-top: 10px;'>"
        f"    <button onclick=\"window.api('POST', '/chat', {{content: '@@approve_decision {decision_id}'}}).then(() => {{ this.disabled=true; this.innerText='Erlaubt'; }})\" "
        f"            style='flex: 1; background: #28a745; color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.85rem; transition: background 0.2s;'>"
        f"      Ja, erlauben"
        f"    </button>"
        f"    <button onclick=\"window.api('POST', '/chat', {{content: '@@reject_decision {decision_id}'}}).then(() => {{ this.disabled=true; this.innerText='Abgelehnt'; }})\" "
        f"            style='flex: 1; background: #dc3545; color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.85rem; transition: background 0.2s;'>"
        f"      Nein, blockieren"
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
        f"@user Soll die Aktion von **{agent_name}** ({action_type}: {detail}) erlaubt werden? (Ja/Nein)"
    )
    
    # 8. Pause agent and wait for user input
    set_agent_status(agent_name, "paused")
    
    max_wait_seconds = 300  # 5 minute timeout
    start_time = time.time()
    while True:
        if time.time() - start_time > max_wait_seconds:
            # Auto-reject on timeout
            set_agent_status(agent_name, "busy")
            add_chat_message(
                get_active_project(), "System", "system", "chat",
                f"⏰ [TIMEOUT] Entscheidung für {agent_name} ({action_type}: {detail}) nach 5 Minuten automatisch abgelehnt."
            )
            return False

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
        from gnom_hub.db.legacy_db import get_all_agents
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
    if role in ["soul", "watchdog", "security"]: return True
    
    # 1. CHECK APPROVED LIST FIRST!
    approved_writes = get_state_value("approved_security_writes", []) or []
    if fn in approved_writes: return True
    p = _safe(wd, fn, perms)
    if p:
        real_p = os.path.realpath(p)
        approved_paths = [os.path.realpath(os.path.join(wd, a)) for a in approved_writes]
        if real_p in approved_paths: return True

    if not p:
        return wait_for_decision(name, "WRITE", fn, content, "Pfad liegt außerhalb des zulässigen Workspaces")
        
    if is_worker_blocked(agent, fn, wd, perms):
        return wait_for_decision(name, "WRITE", fn, content, "Zugriff auf geschützte Systemdatei/Pfad")
    if is_security_block(agent, fn, content, wd, perms):
        return wait_for_decision(name, "WRITE", fn, content, "Gefährliche Code-Muster erkannt (z.B. rm -rf, eval, subprocess)")
        
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
            "npm", "npx", "node", "ls", "echo", "cat", "tail",
            "find", "mkdir", "cp", "rm", "wc", "cd", "which", 
            "touch", "chmod", "mv", "grep", "pwd", "clear"
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
    if cmd in (get_state_value("approved_security_commands", []) or []): return True
    
    # Resolves paths in command relative to workspace to avoid false positives on workspace files
    from gnom_hub.chat.brainstorm.brainstorm_helpers import get_workspace_dir
    wd = get_workspace_dir()
    
    import re
    from gnom_hub.core.config import WORKSPACE_DIR
    real_wd = os.path.realpath(str(WORKSPACE_DIR))
    
    # Clean workspace paths out of the command for system path checks
    cmd_lower = cmd.lower()
    tokens = cmd.split()
    cleaned_tokens = []
    for token in tokens:
        clean_token = token.strip("\";'()&|><")
        if "/" in clean_token or "." in clean_token:
            try:
                abs_path = os.path.realpath(os.path.join(wd, clean_token) if not os.path.isabs(clean_token) else clean_token)
                if abs_path == real_wd or abs_path.startswith(real_wd + os.sep):
                    cleaned_tokens.append("[safe_workspace_path]")
                    continue
            except Exception:
                pass
        cleaned_tokens.append(token)
    cleaned_cmd = " ".join(cleaned_tokens).lower()
    
    if any(p in cleaned_cmd for p in ["src/gnom_hub", "config/", "scripts/", "run.sh", "index.html", ".env"]):
        return wait_for_decision(name, "SHELL", cmd, "", "Befehl greift auf geschützte Systemdateien/Pfade zu")
    
    # Smart Rules Engine: Auto-approve whitelisted commands
    is_safe, block_reason = is_command_safe_and_whitelisted(cmd)
    if is_safe:
        request_capability(name, "SHELL", cmd, "AutoApprovedWhitelistedCommand")
        return True
    else:
        return wait_for_decision(name, "SHELL", cmd, "", block_reason)
