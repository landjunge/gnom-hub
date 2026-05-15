"""Prozess-Management für Gnom-Hub Watchdog."""
import subprocess, signal, os
def find_process(name_or_port):
    """Findet PID nach Name oder Port."""
    try:
        if str(name_or_port).isdigit():
            out = subprocess.check_output(f"lsof -ti:{name_or_port}", shell=True).decode().strip()
            return [int(p) for p in out.split("\n") if p]
        out = subprocess.check_output(["pgrep", "-f", name_or_port]).decode().strip()
        return [int(p) for p in out.split("\n") if p]
    except: return []
def kill_process(target):
    """Killt Prozess nach Name oder Port."""
    pids = find_process(target)
    for pid in pids:
        try: os.kill(pid, signal.SIGTERM)
        except: pass
    return f"Killed {len(pids)} processes: {pids}" if pids else f"No process found for {target}"
def restart_hub():
    """Startet Gnom-Hub neu."""
    kill_process("gnom-hub")
    kill_process("3002")
    kill_process("3100")
    subprocess.Popen(
        ["python3", "-m", "gnom_hub"], cwd=os.path.dirname(os.path.dirname(__file__)),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return "Hub restart initiated — ports 3002+3100"
def process_status():
    """Zeigt laufende Gnom-Hub Prozesse."""
    try:
        out = subprocess.check_output("ps aux | grep -E 'gnom.hub|tiny_agent|watchdog|general|summarizer|soul|cronjob|apikeys|skills' | grep -v grep", shell=True).decode()
        return out.strip() or "No gnom-hub processes found"
    except: return "No gnom-hub processes found"
