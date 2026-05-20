# action_handlers.py — Dispatcher für alle Action-Tags
import re
from .action_write import handle_write, handle_read
from .action_exec import handle_shell, handle_crawl, handle_showbox

def _browser(answer, matches, agent, perms):
    """Verarbeitet [BROWSER: {...}] Tags."""
    if "godmode" not in perms and "desktop" not in perms: return answer
    from .browserAG import browser_action
    import json
    for m in matches:
        try:
            cmd = json.loads(m.group(1).strip())
            r = browser_action(cmd)
            answer = answer.replace(m.group(0), f"[Browser: {r}]")
        except Exception as e:
            answer = answer.replace(m.group(0), f"[Browser-Fehler: {e}]")
    return answer

def process_actions(answer, agent, perms, bs_mode, wd):
    """Verarbeitet alle Action-Tags in einer LLM-Antwort."""
    answer = handle_write(answer, list(re.finditer(r"\[WRITE:\s*(.*?)\](.*?)\[/WRITE\]", answer, re.DOTALL)), agent, perms, bs_mode, wd)
    answer = handle_read(answer, list(re.finditer(r"\[READ:\s*(.*?)\]", answer)), wd, perms)
    answer = handle_shell(answer, list(re.finditer(r"\[SHELL:\s*(.*?)\]", answer)), agent, perms, bs_mode, wd)
    answer = handle_crawl(answer, list(re.finditer(r"\[CRAWL:\s*(.*?)\]", answer)), agent, perms)
    ms = []
    for tag in ("SHOWBOX", "showbox"):
        for m in re.finditer(rf"<{tag}(?::(\d+))?>([\s\S]*?)<\/{tag}>", answer): ms.append((m.group(0), m.group(1) or "", m.group(2)))
        for m in re.finditer(rf"\[{tag}(?::(\d+))?\]([\s\S]*?)\[\/{tag}\]", answer): ms.append((m.group(0), m.group(1) or "", m.group(2)))
        for m in re.finditer(rf"\[{tag}:\s*(.*?)\]", answer, re.DOTALL): ms.append((m.group(0), "", m.group(1)))
    answer = handle_showbox(answer, ms)
    answer = _browser(answer, list(re.finditer(r"\[BROWSER:\s*(.*?)\]", answer, re.DOTALL)), agent, perms)
    return answer
