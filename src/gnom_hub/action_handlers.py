# action_handlers.py — Dispatcher für alle Action-Tags
import re; from .action_write import handle_write, handle_read
from .action_exec import handle_shell, handle_crawl, handle_showbox
from gnom_hub.security.path_validator import is_worker_blocked
from gnom_hub.security.gatekeeper import verify_write, verify_cmd
from .action_browser import handle_browser

def process_actions(ans, agent, perms, bs_mode, wd):
    perms = list(perms)
    if "godmode" in perms and "run" not in perms: perms.append("run")
    w_ms, r_ms, sh_ms = [], [], []
    for m in re.finditer(r"\[WRITE:\s*(.*?)\](.*?)\[/WRITE\]", ans, re.DOTALL):
        fn, content = m.group(1).strip(), m.group(2).strip()
        if verify_write(agent, fn, content, wd, perms): w_ms.append(m)
        else: ans = ans.replace(m.group(0), f"[Gatekeeper: Schreibzugriff auf '{fn}' verweigert.]")
    for m in re.finditer(r"\[READ:\s*(.*?)\]", ans):
        name = (agent or {}).get("name", "Unknown")
        role = (agent or {}).get("role", "")
        if name.lower() == "generalag" or role == "general" or is_worker_blocked(agent, m.group(1).strip(), wd, perms): ans = ans.replace(m.group(0), f"[WatchdogAG: Lesezugriff blockiert.]")
        else: r_ms.append(m)
    for m in re.finditer(r"\[SHELL:\s*(.*?)\]", ans):
        cmd = m.group(1).strip()
        if verify_cmd(agent, cmd): sh_ms.append(m)
        else: ans = ans.replace(m.group(0), f"[Gatekeeper: Befehlsausführung verweigert.]")
    ans = handle_write(ans, w_ms, agent, perms, bs_mode, wd)
    ans = handle_read(ans, r_ms, wd, perms)
    ans = handle_shell(ans, sh_ms, agent, perms, bs_mode, wd)
    ans = handle_crawl(ans, list(re.finditer(r"\[CRAWL:\s*(.*?)\]", ans)), agent, perms)
    show_ms = [(m.group(0), m.group(1) or "", m.group(2)) for t in ("SHOWBOX", "showbox") for rx in (rf"<{t}(?::([a-zA-Z0-9_\-]+))?>([\s\S]*?)<\/{t}>", rf"\[{t}(?::([a-zA-Z0-9_\-]+))?\]([\s\S]*?)\[\/{t}\]") for m in re.finditer(rx, ans)] + [(m.group(0), "", m.group(1)) for t in ("SHOWBOX", "showbox") for m in re.finditer(rf"\[{t}:\s*(.*?)\]", ans, re.DOTALL)]
    ans = handle_showbox(ans, show_ms)
    return handle_browser(ans, list(re.finditer(r"\[BROWSER:\s*(.*?)\]", ans, re.DOTALL)), agent, perms, wd)
