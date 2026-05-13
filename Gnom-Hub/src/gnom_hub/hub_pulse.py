import time
import psutil

def main():
    print("GNOM-HUB Pulse gestartet — Watchdog")
    while True:
        hub_running = any("gnom-hub" in " ".join(p.cmdline()) for p in psutil.process_iter() if "python" in p.name().lower())
        if not hub_running:
            print("WARNUNG: GNOM-HUB Prozesse fehlen!")
        time.sleep(10)
