import logging
import os, sys, subprocess, platform, psutil
from fastapi import APIRouter, Request
from gnom_hub.core.security.hmac_signer import _get_or_create_secret

router = APIRouter()

@router.get("/api/system/info")
def get_system_info():
    cpu = platform.processor() or platform.machine()
    try:
        cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception as e: logging.getLogger(__name__).error('Fehler in Ermittlung des CPU-Namens: %s', e)
    ram = f"{round(psutil.virtual_memory().total / (1024**3))} GB"
    from gnom_hub.core.config import Config
    template = Config.get_supergnom_template()
    is_supergnom = Config.SUPERGNOM_MODE or (template in ["senior", "headless"])
    return {
        "cpu": cpu,
        "ram": ram,
        "is_intel": "intel" in cpu.lower(),
        "is_supergnom": is_supergnom,
        "template": template,
        "has_elevenlabs": bool(os.environ.get("ELEVENLABS_API_KEY"))
    }

@router.post("/api/restart")
def restart_server(request: Request):
    if request.headers.get("X-Hub-Secret") != _get_or_create_secret().hex():
        return {"error": "Unauthorized"}
    import signal, threading
    subprocess.Popen([sys.executable] + sys.argv)
    # Give the new process time to start, then exit cleanly
    def _delayed_exit():
        import time; time.sleep(1.0)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=_delayed_exit, daemon=True).start()
    return {"status": "restarting"}
