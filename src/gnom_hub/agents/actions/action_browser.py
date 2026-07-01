# action_browser.py — Playwright Browser automation execution
# Docker- und Sandbox-Pfade entfernt am 2026-06-15.
# Skripte laufen direkt im Host (cwd=workspace), Gatekeeper (verify_browser) bleibt aktiv.
import logging
import os
import re
import subprocess
import uuid

from gnom_hub.core.security.gatekeeper_browser import verify_browser
from gnom_hub.infrastructure.process.sandbox import run_browser_in_sandbox

_log = logging.getLogger(__name__)

# Default 120s. Browser-Workflows mit Page-Loading, Multi-Step-Forms,
# Screenshots und JS-Evaluation brauchen deutlich mehr als 30s.
DEFAULT_BROWSER_TIMEOUT = 120


def handle_browser(ans, ms, agent, perms, wd) -> str:
    if not ms:
        return ans
    for m in ms:
        code = m.group(1).strip()
        if not verify_browser(agent, code, wd, perms):
            ans = ans.replace(
                m.group(0),
                "[Browser: Sicherheitsüberprüfung fehlgeschlagen. "
                "Verbotene Patterns: os.system / subprocess / eval / exec / __import__ / "
                "ctypes / socket / offene absolute Pfade. Skript wurde NICHT ausgeführt.]",
            )
            continue
        urls = re.findall(r"https?://[^\s'\"]+", code)
        has_ext = any(not any(lh in u for lh in ["localhost", "127.0.0.1"]) for u in urls)
        net = "bridge" if has_ext else "none"  # marker only, no docker
        fn = f"tmp_browser_{uuid.uuid4().hex}.py"
        fp = os.path.join(wd, fn) if wd else fn
        try:
            if wd:
                os.makedirs(wd, exist_ok=True)
            with open(fp, "w") as f:
                f.write(code)
            # Pass absolute path so the sandbox can find the file regardless
            # of what cwd it sets for the subprocess.
            code_path = os.path.abspath(fp)
            try:
                r = run_browser_in_sandbox(code_path, net, timeout=DEFAULT_BROWSER_TIMEOUT)
            except subprocess.TimeoutExpired as te:
                stdout = te.stdout.decode(errors="replace") if isinstance(te.stdout, bytes) else (te.stdout or "")
                stderr = te.stderr.decode(errors="replace") if isinstance(te.stderr, bytes) else (te.stderr or "")
                ans = ans.replace(
                    m.group(0),
                    f"[Browser-Timeout nach {DEFAULT_BROWSER_TIMEOUT}s. "
                    f"stdout: {stdout[:1000]}. "
                    f"stderr: {stderr[:500]}]",
                )
                continue
            out = ((r.stdout or "") + "\n" + (r.stderr or "")).strip() or "[Browser: Keine Ausgabe]"
            if len(out) > 4000:
                out = out[:4000] + "\n... [truncated]"
            ans = ans.replace(m.group(0), f"[Browser-Ausgabe:\n{out}]")
        except Exception as e:
            _log.warning("Browser action failed: %s", e)
            ans = ans.replace(m.group(0), f"[Browser-Fehler: {type(e).__name__}: {e}]")
        finally:
            try:
                if os.path.exists(fp):
                    os.unlink(fp)
            except OSError:
                pass
    return ans
