# gatekeeper.py — Double approval verification for file writes and shell commands with Showbox decisions
import os
import uuid
import time
import logging
import json
from html import escape as html_escape
from gnom_hub.db import (
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

# Injectable clock functions for testability (C1 fix)
_clock_time = time.time
_clock_sleep = time.sleep

def wait_for_decision(agent_name, action_type, detail, content, rule) -> bool:
    # Auto-approve if confirmations are disabled (default is False/disabled as requested by user)
    from gnom_hub.db import get_state_value
    if not get_state_value("enable_confirmations", False):
        proj = get_active_project()
        add_chat_message(
            proj, 
            "WatchdogAG", 
            "watchdogag", 
            "chat", 
            f"⚡ [AUTO-APPROVED] Aktion von **{agent_name}** ({action_type}: {detail}) automatisch freigegeben."
        )
        return True

    decision_id = str(uuid.uuid4())
    
    # 1. Determine blocker agent
    blocker_name = "WatchdogAG"
    blocker_color = "#FFA500"
    blocker_rgb = "255, 165, 0"
    
    if "security" in rule.lower() or "gefahr" in rule.lower() or "sicherheits" in rule.lower():
        blocker_name = "SecurityAG"
        blocker_color = "#FF69B4"
        blocker_rgb = "255, 105, 180"

    # 2. Register the pending decision
    pending = get_state_value("pending_decisions", {})
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
    
    # 3. Build HTML content for Showbox slide (Super compact - no LLM queries, extremely direct)
    # Escape all user-supplied values to prevent XSS in the Showbox HTML
    safe_agent = html_escape(str(agent_name))
    safe_action = html_escape(str(action_type))
    safe_detail = html_escape(str(detail))
    safe_rule = html_escape(str(rule))
    safe_blocker = html_escape(str(blocker_name))
    html_content = (
        f"<div style='padding: 12px; font-family: sans-serif; color: #fff; background: rgba(10, 10, 15, 0.96); height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1);'>"
        f"  <div>"
        f"    <h2 style='color: #ff3333; margin: 0 0 6px 0; display: flex; align-items: center; gap: 8px; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.5px;'>"
        f"      🛑 Blockade: {safe_blocker}"
        f"    </h2>"
        f"    <div style='font-size: 0.8rem; color: rgba(255,255,255,0.7); margin-bottom: 6px; line-height: 1.35;'>"
        f"      <strong>Wer:</strong> {safe_agent}<br>"
        f"      <strong>Aktion:</strong> <code style='background: rgba(255,255,255,0.1); padding: 1px 4px; border-radius: 3px; color: #00e5ff; font-family: monospace; font-size: 0.75rem;'>{safe_action}: {safe_detail}</code>"
        f"    </div>"
        f"    <div style='background: rgba({blocker_rgb}, 0.05); border-left: 3px solid {blocker_color}; padding: 6px 8px; border-radius: 4px; font-size: 0.78rem; line-height: 1.3; color: #f8fafc;'>"
        f"      <strong>Grund:</strong> {safe_rule}"
        f"    </div>"
        f"  </div>"
        f"  <div style='display: flex; gap: 10px; margin-top: 8px;'>"
        f"    <button onclick=\"window.api('POST', '/chat', {{content: '@@approve_decision {decision_id}'}}).then(() => {{ this.disabled=true; this.innerText='Erlaubt'; }})\" "
        f"            style='flex: 1; background: #28a745; color: white; border: none; padding: 8px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.8rem; transition: background 0.2s;'>"
        f"      Ja, erlauben"
        f"    </button>"
        f"    <button onclick=\"window.api('POST', '/chat', {{content: '@@reject_decision {decision_id}'}}).then(() => {{ this.disabled=true; this.innerText='Abgelehnt'; }})\" "
        f"            style='flex: 1; background: #dc3545; color: white; border: none; padding: 8px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.8rem; transition: background 0.2s;'>"
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
    start_time = _clock_time()
    while True:
        if _clock_time() - start_time > max_wait_seconds:
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
        from gnom_hub.db import get_all_agents
        agents = get_all_agents()
        current_agent = next((a for a in agents if a["name"].lower() == agent_name.lower()), None)
        if current_agent and current_agent.get("status") not in ["paused", "offline"]:
            break
            
        _clock_sleep(0.3)  # NOTE: Blocking poll — runs in worker thread via asyncio.to_thread
        
    set_agent_status(agent_name, "busy")
    return False

def verify_write(agent, fn, content, wd, perms) -> bool:
    """
    Nicht-blockierende Prüfung vor Schreibaktionen.
    - Workspace-Dateien → Auto-Approve
    - System-Dateien (src/gnom_hub, config/, .env, ...) → Instant Block
    - Gefährliche Code-Patterns → Instant Block
    Keine Warte-Dialoge mehr.
    """
    name = (agent or {}).get("name", "Unknown")

    p = _safe(wd, fn, perms)
    if not p:
        return False

    if is_worker_blocked(agent, fn, wd, perms):
        return False

    if is_security_block(agent, fn, content, wd, perms):
        return False

    request_capability(name, "WRITE", fn, "AutoApprovedSafePath")
    return True

def is_command_safe_and_whitelisted(cmd: str, agent: dict = None):
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
        
        # 2. Erweiterte Whitelist erlaubter Executables
        allowed_execs = {
            # Python
            "python3", "python", "pytest", "pip", "pip3", "uv",
            # Node
            "npm", "npx", "node", "yarn", "pnpm", "bun",
            # Git
            "git", "gh",
            # Dateisystem
            "ls", "echo", "cat", "tail", "head", "find", "mkdir", "cp",
            "rm", "wc", "which", "touch", "chmod", "mv", "grep", "pwd",
            "stat", "date", "sort", "uniq", "du", "df", "diff", "tree",
            "cut", "awk", "sed", "xargs", "tee", "tr",
            # Archive
            "zip", "unzip", "tar", "gzip", "gunzip",
            # Netzwerk / Tools
            "curl", "wget", "brew", "make", "cmake", "cargo", "go",
            "java", "mvn", "gradle", "docker", "docker-compose",
            "open", "pbcopy", "pbpaste", "xclip", "xdg-open",
            # Shell builtins (oft in commands)
            "bash", "sh", "zsh", "env", "export", "source",
        }

        if exec_name not in allowed_execs:
            # C2 fix: godmode darf KEINE unbekannten Binaries ausführen.
            # godmode erweitert nur Argument-Freiheiten, nicht die Executable-Whitelist.
            return False, f"Befehl '{exec_name}' ist nicht auf der Whitelist erlaubter Programme."

        # 3. Argument-Validierung für spezifische Befehle
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
                        # Netzwerk nicht erreichbar → Auto-approve mit Warning statt Hard-Block
                        logging.getLogger(__name__).warning(
                            "gatekeeper: PyPI-Check für '%s' nicht möglich (Netzwerk?), auto-approve: %s",
                            pkg_clean, e
                        )
                        continue  # Weiter, nicht blocken

        elif exec_name in ("npm", "npx", "yarn", "pnpm", "bun"):
            # Node-Pakete generell erlauben — Worker benötigen das
            # Nur offensichtliche Gefahren abfangen
            full_cmd = " ".join(args_tokens).lower()
            if "rm -rf" in full_cmd or "&&rm" in full_cmd or "curl|sh" in full_cmd:
                return False, f"Gefährliche Verkettung in npm-Befehl erkannt."
                        
        elif exec_name == "rm":
            # C3 fix: Resolve ALL paths to catch ~/, ../../../, symlinks etc.
            dangerous_roots = {"/", os.path.expanduser("~")}
            system_prefixes = (
                "/etc", "/usr", "/bin", "/sbin", "/var", "/boot", "/proc", "/sys", "/lib",
                "/private/etc", "/private/var"
            )
            for arg in args_tokens:
                if arg.startswith("-"): continue
                resolved = os.path.realpath(os.path.expanduser(arg))
                if resolved in dangerous_roots:
                    return False, f"rm auf '{resolved}' ist nicht erlaubt."
                if resolved.startswith(system_prefixes):
                    return False, f"rm auf Systempfad '{resolved}' ist nicht erlaubt."
            # rm -rf auf Gnom-Systemdateien blockieren
            if "-rf" in args_tokens or "-fr" in args_tokens:
                for arg in args_tokens:
                    if arg.startswith("-"): continue
                    abs_arg = os.path.realpath(os.path.expanduser(arg))
                    if any(sys_path in abs_arg for sys_path in ["src/gnom_hub", "run.sh", ".env"]):
                        return False, f"rm -rf auf Systemdatei '{arg}' ist nicht erlaubt."

        elif exec_name == "git":
            allowed_git_subcmds = {
                "status", "log", "diff", "commit", "add", "checkout",
                "reset", "init", "config", "pull", "fetch",
                "clone", "stash", "branch", "merge", "rebase", "tag",
                "remote", "show", "blame", "shortlog", "describe"
            }
            # git push ist NUR dem User via @@git push erlaubt
            if args_tokens and args_tokens[0] == "push":
                return False, (
                    "git push ist Agenten nicht erlaubt. "
                    "Nur der User darf pushen — nutze @@git push im Chat."
                )
            if not args_tokens or args_tokens[0] not in allowed_git_subcmds:
                return False, f"Git Subbefehl '{args_tokens[0] if args_tokens else ''}' ist nicht autorisiert."
                
    return True, ""

def verify_cmd(agent, cmd):
    """
    Nicht-blockierende Prüfung vor Shell-Befehlen.
    - GeneralAG (role=general): KEINE Shell-Befehle erlaubt
    - Whitelist-Prüfung (erlaubte Befehle)
    - System-Pfad-Schutz (kein Zugriff auf src/gnom_hub, config/, .env, ...)
    - Keine Warte-Dialoge.
    """
    name = (agent or {}).get("name", "Unknown")
    role = (agent or {}).get("role", "")

    if role == "general" or name.lower() == "generalag":
        return False

    from gnom_hub.core.config import WORKSPACE_DIR
    from gnom_hub.chat.brainstorm.brainstorm_helpers import get_workspace_dir
    from gnom_hub.core.security.path_validator import is_system_path
    import re as _re

    real_wd = os.path.realpath(str(WORKSPACE_DIR))
    wd = get_workspace_dir()

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

    if is_system_path(cleaned_cmd):
        return False

    is_safe, _block_reason = is_command_safe_and_whitelisted(cmd, agent)
    if not is_safe:
        return False

    request_capability(name, "SHELL", cmd, "AutoApprovedWhitelistedCommand")
    return True
