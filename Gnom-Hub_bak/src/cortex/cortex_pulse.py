#!/usr/bin/env python3
"""
GNOM-HUB PULSE — Watchdog des Gnom-Hubs
=====================================
Überwacht ausschließlich die internen Gnom-Hub Komponenten:
- Gnom-Hub (FastAPI)
- Gnom-Hub MCP (MCP Server)
- Gnom-Hub Pulse (Sich selbst)

Prüft regelmäßig, ob die Prozesse noch leben und schlägt Alarm bei Abstürzen.
Keine automatischen Neustarts, nur Monitoring und Logging.
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_run_dir

POLL_INTERVAL = 10  # Alle 10 Sekunden prüfen

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "💓", "WARN": "⚠️", "ERROR": "❌", "OK": "✅"}
    icon = icons.get(level, "📌")
    print(f"[{ts}] {icon} {msg}")

def is_process_alive(pid: int) -> bool:
    """Prüft ob ein Prozess mit der gegebenen PID läuft."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def main():
    log("=" * 50)
    log("GNOM-HUB Pulse gestartet — Watchdog")
    log(f"Prüf-Intervall: {POLL_INTERVAL}s")
    
    pulse_port = int(os.environ.get("CORTEX_PULSE_PORT", 0))
    if pulse_port:
        log(f"Pulse Port: {pulse_port}")
    
    run_dir = get_run_dir()
    pid_file = run_dir / "pids.json"
    
    # Warte kurz, damit der Hub Zeit hat, die pids.json zu schreiben
    time.sleep(2)
    
    if not pid_file.exists():
        log(f"Konnte {pid_file} nicht finden. Ist der Gnom-Hub korrekt gestartet?", "ERROR")
        return

    known_pids = {}
    try:
        with open(pid_file, "r") as f:
            known_pids = json.load(f)
    except Exception as e:
        log(f"Fehler beim Lesen der PIDs: {e}", "ERROR")
        return

    if not known_pids:
        log("Keine Prozesse in pids.json gefunden.", "WARN")

    # Status-Tracking, um Meldungen nicht zu spammen
    status_map = {name: True for name in known_pids}
    
    log("Überwache Prozesse:")
    for name, pid in known_pids.items():
        log(f"  - {name} (PID: {pid})")

    log("=" * 50)

    # Dummy-Socket binden, um den Port (falls zugewiesen) zu blockieren
    pulse_socket = None
    if pulse_port:
        import socket
        pulse_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            pulse_socket.bind(("127.0.0.1", pulse_port))
            pulse_socket.listen(1)
        except Exception as e:
            log(f"Konnte Port {pulse_port} nicht binden: {e}", "WARN")

    while True:
        try:
            time.sleep(POLL_INTERVAL)
            
            # PIDs neu einlesen (falls sie sich ändern sollten)
            if pid_file.exists():
                try:
                    with open(pid_file, "r") as f:
                        current_pids = json.load(f)
                        # Aktualisiere PIDs und Status falls neue hinzukamen
                        for name, pid in current_pids.items():
                            if name not in known_pids or known_pids[name] != pid:
                                known_pids[name] = pid
                                status_map[name] = True
                except Exception:
                    pass # Fehler beim Lesen stillschweigend ignorieren beim Polling

            all_alive = True
            for name, pid in known_pids.items():
                alive = is_process_alive(pid)
                
                # Wenn Status sich von True auf False ändert -> Crash
                if not alive and status_map.get(name, True):
                    log(f"Kritischer Fehler: [{name}] (PID {pid}) ist unerwartet abgestürzt!", "ERROR")
                    status_map[name] = False
                
                # Wenn Status sich von False auf True ändert -> Wieder da
                elif alive and not status_map.get(name, True):
                    log(f"Prozess [{name}] (PID {pid}) ist wieder erreichbar.", "OK")
                    status_map[name] = True

                if not alive:
                    all_alive = False

            if not all_alive:
                log("Achtung: Nicht alle Gnom-Hub Komponenten laufen ordnungsgemäß.", "WARN")

        except KeyboardInterrupt:
            log("Pulse Watchdog manuell beendet.")
            break
        except Exception as e:
            log(f"Unerwarteter Fehler im Watchdog: {e}", "ERROR")
            time.sleep(10)

if __name__ == "__main__":
    main()
