import os, sys, subprocess, platform, psutil
from fastapi import APIRouter, Request
from gnom_hub.core.security.hmac_signer import _get_or_create_secret

router = APIRouter()

@router.get("/api/system/info")
def get_system_info():
    cpu = platform.processor() or platform.machine()
    try:
        cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception: pass
    ram = f"{round(psutil.virtual_memory().total / (1024**3))} GB"
    return {"cpu": cpu, "ram": ram, "is_intel": "intel" in cpu.lower()}

@router.post("/api/restart")
def restart_server(request: Request):
    if request.headers.get("X-Hub-Secret") != _get_or_create_secret().hex():
        return {"error": "Unauthorized"}
    subprocess.Popen([sys.executable] + sys.argv)
    os._exit(0)
