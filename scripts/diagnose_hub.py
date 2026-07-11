#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Fix python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gnom_hub.core.config import DB_PATH, RUN_DIR
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.db.state_repo import SQLiteStateRepository


def check_pid(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def run_diagnose():
    report = []
    report.append("🔍 **Gnom-Hub System-Diagnose**")
    report.append(f"Zeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Datenbank: `{DB_PATH}`")
    
    # 1. DB-Erreichbarkeit prüfen
    try:
        repo = SQLiteAgentRepository()
        state_repo = SQLiteStateRepository()
        agents = repo.get_all()
        report.append("✅ Datenbankverbindung: **OK**")
    except Exception as e:
        report.append(f"❌ Datenbankverbindung: **FEHLER** ({e})")
        return "\n".join(report)

    # 2. Blockierende Entscheidungen (Gatekeeper) prüfen
    pending_decisions = state_repo.get_value("pending_decisions", {})
    pending_list = [d_id for d_id, d in pending_decisions.items() if d.get("status") == "pending"]
    if pending_list:
        report.append(f"\n⚠️ **Blockierende Freigaben:** {len(pending_list)} ausstehend.")
        for d_id in pending_list:
            d = pending_decisions[d_id]
            report.append(f"  - Agent **{d.get('agent_name')}** wartet auf Freigabe für `{d.get('action_type')}` (`{d.get('detail')[:60]}`).")
            report.append(f"    👉 Freigabe per: `@@approve_decision {d_id}` oder Ablehnung per: `@@reject_decision {d_id}`")
    else:
        report.append("✅ Keine blockierenden Sicherheitsfreigaben ausstehend.")

    # 3. Agenten-Prozess-Check
    report.append("\n🤖 **Agenten-Status & Prozesse:**")
    stuck_found = False
    
    # Standard 8 agent names lowercased
    from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
    all_defs = list(AGENT_DEFINITIONS.values())
    
    for defn in all_defs:
        name = defn["name"]
        agent = next((a for a in agents if a.name.lower() == name.lower()), None)
        
        if not agent:
            report.append(f"❌ **{name}**: Nicht in Datenbank registriert!")
            stuck_found = True
            continue
            
        # PID check
        pid_file = RUN_DIR / f"{name}.pid"
        pid_file_lower = RUN_DIR / f"{name[0].lower() + name[1:]}.pid"
        pid = None
        for p_path in (pid_file, pid_file_lower):
            if p_path.exists():
                try:
                    pid = int(p_path.read_text().strip())
                    break
                except Exception:
                    pass
                    
        is_running = check_pid(pid) if pid else False
        
        # Check heartbeat drift
        now = datetime.now(timezone.utc)
        drift = (now - agent.last_seen.replace(tzinfo=timezone.utc)).total_seconds() if agent.last_seen else 999999
        
        status_str = f"status={agent.status}, drift={int(drift)}s"
        
        if is_running:
            if agent.status == "busy" and drift > 45:
                report.append(f"⚠️ **{name}**: Prozess läuft (PID {pid}), aber HÄNGT/STECKT (busy seit {int(drift)}s).")
                stuck_found = True
            else:
                report.append(f"✅ **{name}**: Läuft aktiv (PID {pid}, {status_str}).")
        else:
            if agent.status in ("online", "busy"):
                report.append(f"❌ **{name}**: Tot! (Laut DB {agent.status}, aber kein laufender Prozess gefunden. {status_str}).")
                stuck_found = True
            else:
                report.append(f"💤 **{name}**: Gestoppt/Offline ({status_str}).")
                
    if stuck_found:
        report.append("\n💡 **Lösungsvorschläge bei Hängern/Abstürzen:**")
        report.append("- Um tote Agenten neu zu starten, führe im Terminal aus: `bash scripts/start_agents.sh`")
        report.append("- Um einen busy-hängenden Agenten manuell zu befreien, nutze: `@@resume [AgentenName]` (z.B. `@@resume CoderAG`)")
    else:
        report.append("\n✅ **Alles in Ordnung:** Der Schwarm läuft reibungslos.")

    return "\n".join(report)

if __name__ == "__main__":
    print(run_diagnose())
