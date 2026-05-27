# action_browser.py — Playwright Browser automation execution in Docker
import os, uuid, re
from gnom_hub.security.gatekeeper_browser import verify_browser
from gnom_hub.process.sandbox import is_docker_running, run_browser_in_sandbox

def handle_browser(ans, ms, agent, perms, wd) -> str:
    if not ms: return ans
    if not is_docker_running():
        for m in ms: ans = ans.replace(m.group(0), "[Browser: Docker offline. Ausführung blockiert.]")
        return ans
    for m in ms:
        code = m.group(1).strip()
        if not verify_browser(agent, code, wd, perms):
            ans = ans.replace(m.group(0), "[Browser: Sicherheitsüberprüfung fehlgeschlagen.]")
            continue
        urls = re.findall(r'https?://[^\s\'"]+', code)
        has_ext = any(not any(lh in u for lh in ["localhost", "127.0.0.1"]) for u in urls)
        net = "bridge" if has_ext else "none"
        fn = f"tmp_browser_{uuid.uuid4().hex}.py"
        fp = os.path.join(wd, fn)
        try:
            with open(fp, "w") as f: f.write(code)
            r = run_browser_in_sandbox(fn, net, timeout=45)
            out = (r.stdout + "\n" + r.stderr).strip() or "[Browser: Keine Ausgabe]"
            ans = ans.replace(m.group(0), f"[Browser-Ausgabe:\n{out}]")
        except Exception as e:
            ans = ans.replace(m.group(0), f"[Browser-Fehler: {str(e)}]")
        finally:
            if os.path.exists(fp): os.unlink(fp)
    return ans
