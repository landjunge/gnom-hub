# gatekeeper.py — Double approval verification for file writes and shell commands with Showbox decisions
import os
import uuid
import time
import threading
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
    set_agent_status,
    log_blockade,
)
import gnom_hub.infrastructure.router.router as router
from gnom_hub.core.security.path_validator import is_worker_blocked, is_security_block, _safe
from gnom_hub.agents.capability_manager import check_capability, request_capability

# ── Event-basierte Entscheidungs-Warteschlange ──
# Ersetzt das while-True-Polling (3000 Iterationen in 5min) durch
# threading.Event. Der Thread blockiert im OS-Scheduler mit 0% CPU.
# _signal_decision() wird von @@approve_decision / @@reject_decision
# im Chat aufgerufen und weckt den wartenden Agent-Thread via event.set().
_decisions: dict[str, dict] = {}
_decisions_lock = threading.Lock()

def _signal_decision(decision_id: str, status: str):
    """Weckt den auf eine Entscheidung wartenden Agent-Thread.

    Wird von handle_approve_decision / handle_reject_decision in
    chat_commands.py aufgerufen. Setzt den Entscheidungsstatus und
    triggert threading.Event.set() auf dem Event des wartenden Threads.
    """
    with _decisions_lock:
        entry = _decisions.get(decision_id)
        if entry and entry["status"] == "pending":
            entry["status"] = status
            entry["event"].set()


# ── Blockade Rules System ──

def _get_rules():
    """Lade alle Benutzerregeln aus der State-Tabelle."""
    return get_state_value("blockade_rules", [])


def _save_rules(rules: list):
    """Speichere alle Benutzerregeln."""
    set_state_value("blockade_rules", rules)


def _match_rule(target_value: str, rule_value: str) -> bool:
    """Prüft ob target_value auf rule_value passt (Substring-Match)."""
    return rule_value.lower() in target_value.lower()


def check_blockade_rules(agent_name: str, action_type: str, detail: str) -> str:
    """
    Prüft die Benutzerregeln gegen eine Aktion.
    Gibt zurück: 'allow', 'block' oder '' (keine Regel matcht).
    Konsumiert allow_once-Regeln.
    """
    rules = _get_rules()
    if not rules:
        return ""

    agent_lower = agent_name.lower() if agent_name else ""
    detail_lower = detail.lower() if detail else ""

    # Phase 1: allow_once-Regeln konsumieren (vor allen anderen)
    changed = False
    remaining = []
    consumed = []
    for r in rules:
        agent_match = not r.get("agent") or r["agent"].lower() == agent_lower
        value_match = r["target_value"].lower() in detail_lower
        if r["type"] == "allow_once" and agent_match and value_match:
            consumed.append(r)
            changed = True
        else:
            remaining.append(r)

    if consumed:
        _save_rules(remaining)
        return "allow"

    if changed:
        _save_rules(remaining)

    # Phase 2: Andere Regeln prüfen
    for r in remaining:
        agent_match = not r.get("agent") or r["agent"].lower() == agent_lower
        value_match = r["target_value"].lower() in detail_lower
        if not agent_match or not value_match:
            continue
        if r["type"] == "block_always":
            return "block"
        if r["type"] in ("whitelist", "allow_agent"):
            return "allow"

    return ""


def add_blockade_rule(rule_type: str, target_value: str, agent: str = "", blockade_id: int = None):
    """Fügt eine neue Benutzerregel hinzu."""
    rules = _get_rules()
    rules.append({
        "id": str(uuid.uuid4()),
        "type": rule_type,
        "target_value": target_value,
        "agent": agent or "",
        "blockade_id": blockade_id,
        "created_at": time.time()
    })
    _save_rules(rules)
    return True


def remove_blockade_rule(rule_id: str):
    """Entfernt eine Benutzerregel."""
    rules = _get_rules()
    rules = [r for r in rules if r.get("id") != rule_id]
    _save_rules(rules)
    return True

def wait_for_decision(agent_name, action_type, detail, content, rule) -> bool:
    # Auto-approve if confirmations are disabled
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
    event = threading.Event()

    # Module-level Entscheidungs-Store (kein DB-Polling nötig)
    with _decisions_lock:
        _decisions[decision_id] = {"status": "pending", "event": event}

    # 1. Determine blocker agent
    blocker_name = "WatchdogAG"
    blocker_color = "#FFA500"
    blocker_rgb = "255, 165, 0"

    if "security" in rule.lower() or "gefahr" in rule.lower() or "sicherheits" in rule.lower():
        blocker_name = "SecurityAG"
        blocker_color = "#FF69B4"
        blocker_rgb = "255, 105, 180"

    # 2. Build HTML content for Showbox slide
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

    presentation_name = f"Blockade: {agent_name}"
    save_showbox_presentation(presentation_name, [html_content], sender="GeneralAG")
    set_active_showbox(presentation_name)

    proj = get_active_project()
    add_chat_message(
        proj,
        "GeneralAG",
        "generalag",
        "chat",
        f"@user Soll die Aktion von **{agent_name}** ({action_type}: {detail}) erlaubt werden? (Ja/Nein)"
    )

    set_agent_status(agent_name, "paused")

    # Thread blockiert hier im OS-Scheduler mit 0% CPU-Last.
    # _signal_decision() setzt das Event bei @@approve / @@reject.
    # Bei Timeout nach 300s gibt event.wait() False zurück.
    event.wait(timeout=300)
    with _decisions_lock:
        entry = _decisions.pop(decision_id, None)
        status = entry.get("status", "rejected") if entry else "rejected"

    set_agent_status(agent_name, "busy")

    if status == "approved":
        return True

    if status == "pending":
        log_blockade(agent_name, action_type, detail[:150],
                     f"Timeout 5 Min. — automatisch abgelehnt: {rule}",
                     "timeout", "System", content[:100] if content else "")
        add_chat_message(
            get_active_project(), "System", "system", "chat",
            f"⏰ [TIMEOUT] Entscheidung für {agent_name} ({action_type}: {detail}) nach 5 Minuten automatisch abgelehnt."
        )
    else:
        log_blockade(agent_name, action_type, detail[:150],
                     f"Vom User abgelehnt: {rule}",
                     "rejected", "User", content[:100] if content else "")
    return False

def verify_write(agent, fn, content, wd, perms) -> bool:
    """
    Risikobasierte Prüfung vor Schreibaktionen.
    - Benutzerregeln (whitelist/block) haben Vorfahrt
    - Workspace-Dateien → Auto-Approve
    - System-Dateien (src/gnom_hub, config/, .env, ...) → Hard Block
    - Hochriskante Code-Patterns → Hard Block
    - Mittelriskante Code-Patterns → Warning (log + allow)
    """
    name = (agent or {}).get("name", "Unknown")

    # SoulAG darf NIE Dateien schreiben — nur DB
    if name.lower() == "soulag":
        log_blockade(name, "WRITE", fn,
                     "SoulAG darf keine Dateien schreiben — nur Datenbank (soul_memory).",
                     "blocked", "Gatekeeper", content[:200] if content else "")
        return False

    # Benutzerregeln zuerst prüfen
    rule_result = check_blockade_rules(name, "WRITE", fn)
    if rule_result == "allow":
        request_capability(name, "WRITE", fn, "UserApproved")
        return True
    if rule_result == "block":
        log_blockade(name, "WRITE", fn, f"Dauerhaft blockiert per Benutzerregel: {fn}", "blocked", "User")
        return False

    p = _safe(wd, fn, perms)
    if not p:
        log_blockade(name, "WRITE", fn,
                     f"Pfad ausserhalb des Workspace: {fn}",
                     "blocked", "PathValidator")
        return False

    if is_worker_blocked(agent, fn, wd, perms):
        log_blockade(name, "WRITE", fn, f"System-Pfad blockiert: {fn}", "blocked", "PathValidator")
        return False

    sev = is_security_block(agent, fn, content, wd, perms)
    if sev == "high":
        log_blockade(name, "WRITE", fn, f"Hochriskantes Code-Pattern blockiert", "blocked", "SecurityAG", content[:200] if content else "")
        return False
    if sev == "medium":
        log_blockade(name, "WRITE", fn, f"Mittelriskantes Code-Pattern — gewarnt", "warning", "SecurityAG", content[:200] if content else "")
        # Allow with warning

    request_capability(name, "WRITE", fn, "AutoApprovedSafePath")
    return True

def _is_high_risk_exec(exec_name: str, args_tokens: list) -> bool:
    """Bestimmt ob ein Befehl wirklich hochriskant ist (hard block) oder nur mittel (warning)."""
    high_risk_execs = {"dd", "mkfs", "fdisk", "parted", "reboot", "shutdown", "init", "poweroff", "halt"}
    if exec_name in high_risk_execs:
        return True
    # Check if any arg contains an rm -rf targeting system paths (even via sudo/other wrappers)
    full_args = " ".join(args_tokens).lower()
    if "rm" in full_args and ("-rf" in full_args or "-fr" in full_args):
        for arg in args_tokens:
            if arg.startswith("-"): continue
            resolved = os.path.realpath(os.path.expanduser(arg))
            if resolved == "/" or resolved.startswith(("/etc", "/usr", "/bin", "/sbin", "/var", "/private")):
                return True
            if any(sys_path in resolved for sys_path in ["src/gnom_hub", "run.sh", ".env"]):
                return True
    # Check for pipe-to-sh patterns in args
    if "|" in full_args:
        if "sh" in full_args or "bash" in full_args:
            return True
    return False


def is_command_safe_and_whitelisted(cmd: str, agent: dict = None):
    """
    Parses a shell command and determines if it is safe and whitelisted.
    Returns (is_safe, severity, reason).
    severity: None (safe), "high" (hard block), "medium" (warning+allow)
    """
    import re
    import requests

    # Pre-check for pipe-to-sh dangerous patterns (curl|sh, wget|bash etc.)
    # These can span across split boundaries, so check the raw cmd first.
    cmd_lower = cmd.lower()
    if re.search(r'(curl|wget|fetch)\b.*\|\s*(ba)?sh\b', cmd_lower):
        return False, "high", "Piping von curl/wget in Shell ist nicht erlaubt."
    
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
            # Dateisystem / Navigation
            "ls", "echo", "cat", "tail", "head", "find", "mkdir", "cp",
            "rm", "wc", "which", "touch", "chmod", "mv", "grep", "pwd",
            "stat", "date", "sort", "uniq", "du", "df", "diff", "tree",
            "cut", "awk", "sed", "xargs", "tee", "tr",
            "cd", "file", "command",
            # Archive
            "zip", "unzip", "tar", "gzip", "gunzip",
            # Netzwerk / Tools
            "curl", "wget", "brew", "make", "cmake", "cargo", "go",
            "java", "mvn", "gradle", "docker", "docker-compose",
            "open", "pbcopy", "pbpaste", "xclip", "xdg-open",
            # Shell builtins (oft in commands)
            "bash", "sh", "zsh", "env", "export", "source", "type",
        }

        if exec_name not in allowed_execs:
            if _is_high_risk_exec(exec_name, args_tokens):
                return False, "high", f"Hochrisiko-Befehl '{exec_name}' blockiert."
            # Unbekannt aber nicht hochriskant → warning + allow
            return False, "medium", f"Befehl '{exec_name}' ist nicht auf der Whitelist — gewarnt."

        # 3. Argument-Validierung für spezifische Befehle
        if exec_name in ("pip", "pip3"):
            if len(args_tokens) >= 2 and args_tokens[0] == "install":
                packages = [a for a in args_tokens[1:] if not a.startswith("-")]
                if not packages:
                    return False, "medium", "Ungültiger pip install Befehl ohne Paketnamen."

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
                                return False, "high", f"Paket '{pkg_clean}' hat bekannte Sicherheitslücken auf PyPI."
                            releases = data.get("releases", {})
                            if len(releases) < 1:
                                return False, "medium", f"Paket '{pkg_clean}' hat keine gültigen Releases auf PyPI."
                        else:
                            return False, "medium", f"Paket '{pkg_clean}' konnte nicht auf PyPI verifiziert werden (Status {r.status_code})."
                    except Exception as e:
                        logging.getLogger(__name__).warning(
                            "gatekeeper: PyPI-Check für '%s' nicht möglich (Netzwerk?), auto-approve: %s",
                            pkg_clean, e
                        )
                        continue

        elif exec_name in ("npm", "npx", "yarn", "pnpm", "bun"):
            full_cmd = " ".join(args_tokens).lower()
            if "rm -rf" in full_cmd or "&&rm" in full_cmd or "curl|sh" in full_cmd:
                return False, "high", f"Gefährliche Verkettung in npm-Befehl erkannt."
                        
        elif exec_name == "rm":
            dangerous_roots = {"/", os.path.expanduser("~")}
            system_prefixes = (
                "/etc", "/usr", "/bin", "/sbin", "/var", "/boot", "/proc", "/sys", "/lib",
                "/private/etc", "/private/var"
            )
            for arg in args_tokens:
                if arg.startswith("-"): continue
                resolved = os.path.realpath(os.path.expanduser(arg))
                if resolved in dangerous_roots:
                    return False, "high", f"rm auf '{resolved}' ist nicht erlaubt."
                if resolved.startswith(system_prefixes):
                    return False, "high", f"rm auf Systempfad '{resolved}' ist nicht erlaubt."
            if "-rf" in args_tokens or "-fr" in args_tokens:
                for arg in args_tokens:
                    if arg.startswith("-"): continue
                    abs_arg = os.path.realpath(os.path.expanduser(arg))
                    if any(sys_path in abs_arg for sys_path in ["src/gnom_hub", "run.sh", ".env"]):
                        return False, "high", f"rm -rf auf Systemdatei '{arg}' ist nicht erlaubt."

        elif exec_name == "git":
            allowed_git_subcmds = {
                "status", "log", "diff", "commit", "add", "checkout",
                "reset", "init", "config", "pull", "fetch",
                "clone", "stash", "branch", "merge", "rebase", "tag",
                "remote", "show", "blame", "shortlog", "describe"
            }
            # Git NUR ueber @@git push (User-Chat-Command), NIEMALS ueber [SHELL:]
            return False, "high", (
                "git ist Agenten nicht erlaubt. "
                "Nutze @@git push, @@git status etc. im Chat (nur User)."
            )
                
    return True, None, ""

def verify_cmd(agent, cmd):
    """
    Nicht-blockierende Prüfung vor Shell-Befehlen.
    - Benutzerregeln (whitelist/block) haben Vorfahrt
    - GeneralAG (role=general): KEINE Shell-Befehle erlaubt
    - Whitelist-Prüfung (erlaubte Befehle)
    - System-Pfad-Schutz (kein Zugriff auf src/gnom_hub, config/, .env, ...)
    - Keine Warte-Dialoge.
    """
    name = (agent or {}).get("name", "Unknown")
    role = (agent or {}).get("role", "")

    # SoulAG darf NIE Shell-Befehle ausführen — nur DB
    if name.lower() == "soulag":
        log_blockade(name, "SHELL", cmd[:150],
                     "SoulAG darf keine Shell-Befehle ausführen — nur Datenbank (soul_memory).",
                     "blocked", "Gatekeeper", cmd[:200])
        return False

    # Benutzerregeln zuerst prüfen
    rule_result = check_blockade_rules(name, "SHELL", cmd)
    if rule_result == "allow":
        request_capability(name, "SHELL", cmd, "UserApproved")
        return True
    if rule_result == "block":
        log_blockade(name, "SHELL", cmd[:150], f"Dauerhaft blockiert per Benutzerregel: {cmd[:80]}", "blocked", "User", cmd[:200])
        return False

    if role == "general" or name.lower() == "generalag":
        log_blockade(name, "SHELL", cmd[:150], "GeneralAG darf keine Shell-Befehle ausführen", "blocked", "Gatekeeper", cmd[:200])
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
        log_blockade(name, "SHELL", cmd[:150], f"Befehl enthält System-Pfad", "blocked", "PathValidator", cmd[:100])
        return False

    is_safe, sev, _block_reason = is_command_safe_and_whitelisted(cmd, agent)
    if not is_safe:
        if sev == "high":
            log_blockade(name, "SHELL", cmd[:150], f"Blockiert: {_block_reason}", "blocked", "Gatekeeper", cmd[:200])
            return False
        else:
            log_blockade(name, "SHELL", cmd[:150], f"Gewarnt: {_block_reason}", "warning", "Gatekeeper", cmd[:200])
            # Medium risk → warn but allow

    request_capability(name, "SHELL", cmd, "AutoApprovedWhitelistedCommand")
    return True
