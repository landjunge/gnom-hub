# ftp_deploy.py — Deployment via SFTP (with FTP fallback)
import os, json; from .config import DATA_DIR; from .log import get_logger
logger = get_logger("ftp_deploy")
def get_deploy():
    p = DATA_DIR / "state.json"
    try: return json.load(open(p, "r", encoding="utf-8")).get("auto_deploy", False)
    except Exception: return False
def set_deploy(val):
    p = DATA_DIR / "state.json"
    s = json.load(open(p, "r", encoding="utf-8")) if p.exists() else {}
    s["auto_deploy"] = val
    with open(p, "w", encoding="utf-8") as f: json.dump(s, f, indent=2)
def upload(local, remote):
    host = os.environ.get("FTP_HOST"); user = os.environ.get("FTP_USER"); password = os.environ.get("FTP_PASS")
    remote_dir = os.environ.get("FTP_REMOTE_DIR", "netzwerkpunkt.de/httpdocs")
    if not all([host, user, password]):
        logger.warning("Deploy-Credentials fehlen (FTP_HOST, FTP_USER, FTP_PASS)"); return
    try:
        import subprocess
        sftp_cmd = f"cd {remote_dir}\nput {local} {remote}\nbye\n"
        result = subprocess.run(
            ["sftp", "-oBatchMode=yes", f"{user}@{host}"],
            input=sftp_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info(f"SFTP upload: {remote}"); return
    except Exception as e:
        logger.debug(f"SFTP nicht verfügbar, FTP-Fallback: {e}")
    try:
        import ftplib
        with ftplib.FTP(host, timeout=10) as ftp:
            ftp.login(user, password); ftp.cwd(remote_dir)
            with open(local, "rb") as f: ftp.storbinary(f"STOR {remote}", f)
        logger.info(f"FTP upload: {remote}")
    except Exception as e:
        logger.error(f"Upload fehlgeschlagen: {e}")
