import subprocess
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path
from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.chat.chat_commands_handlers import handle_clear, handle_status, handle_job, _post_chat

router = APIRouter()

def handle_allclear(q):
    """Führt kompletten System-Cleanup durch und startet Hub neu."""
    import requests, os
    port = os.environ.get('GNOM_HUB_PORT', '3002')
    try:
        r = requests.post(f"http://127.0.0.1:{port}/api/admin/clean-all", timeout=10)
        if r.status_code == 200:
            _post_chat("System", "🧹 Alles gelöscht. Hub startet neu...")
        else:
            _post_chat("System", f"Cleanup-Fehler: HTTP {r.status_code}")
    except Exception as e:
        _post_chat("System", f"Cleanup-Fehler: {str(e)[:100]}")
    return {"status": "ok"}

@router.get("/help")
def get_help():
    return FileResponse(str(Path(__file__).parent.parent / "frontend" / "help.html"))

@router.get("/api/ideas")
def get_ideas(): return SQLiteStateRepository().get_value("ideas", [])

@router.get("/api/jobs")
def get_jobs():
    return sorted(SQLiteStateRepository().get_value("jobs", []), key=lambda j: j.get("ts",""), reverse=True)[:20]

def handle_free(q):
    t = q.replace("@","").strip().lower()
    SQLiteAgentRepository().clear_jobs(t or None)
    _post_chat("System", f"Jobs cleared: {t or 'ALL'}")
    return {"status": "ok"}

def handle_git(q, rb=False):
    import re as _re
    ALLOWED_GIT = {'status', 'log', 'diff', 'show', 'branch', 'stash', 'add', 'commit', 'push', 'pull', 'fetch', 'checkout', 'reset', 'clone'}
    from gnom_hub.api.endpoints.workspace import get_workspace_dir
    wd = get_workspace_dir()
    p = q.split(" ", 1)
    if rb:
        if len(p) < 2 or not _re.match(r'^[a-f0-9]{7,40}$', p[1].strip()):
            _post_chat("System", "Git: Ungültiger Rollback-Ref. Nur gültige Commit-Hashes erlaubt.")
            return {"status": "error", "message": "Invalid rollback ref"}
        cmd = f"reset --hard {p[1].strip()}"
    else:
        cmd = p[1] if len(p) > 1 else "status"
        subcmd = cmd.split()[0]
        if subcmd not in ALLOWED_GIT:
            _post_chat("System", f"Git: Subcommand '{subcmd}' nicht erlaubt. Erlaubt: {', '.join(sorted(ALLOWED_GIT))}")
            return {"status": "error", "message": f"Git subcommand not allowed: {subcmd}"}
    from pathlib import Path
    if not (Path(wd) / ".git").exists(): 
        subprocess.run(["git", "init"], cwd=wd, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Gnom-Hub Agents"], cwd=wd, capture_output=True)
        subprocess.run(["git", "config", "user.email", "agents@gnom-hub.local"], cwd=wd, capture_output=True)
    try: 
        import shlex
        r = subprocess.run(["git"] + shlex.split(cmd), cwd=wd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception as e: 
        r = f"Error: {e}"
    _post_chat("System", f"Git: {r[:300]}"); return {"status": "ok"}

def handle_resume(q):
    agent_name = q.strip().replace("@", "")
    if not agent_name:
        _post_chat("System", "Fehler: Bitte gib einen Agenten-Namen an (z.B. @@resume CoderAG)")
        return {"status": "error", "message": "Missing agent name"}
    
    from gnom_hub.db import set_agent_status, get_all_agents
    agents = get_all_agents()
    agent = next((a for a in agents if a["name"].lower() == agent_name.lower()), None)
    if not agent:
        _post_chat("System", f"Fehler: Agent '{agent_name}' nicht gefunden.")
        return {"status": "error", "message": "Agent not found"}
        
    set_agent_status(agent["name"], "busy")
    _post_chat("System", f"Agent **{agent['name']}** wurde fortgesetzt.")
    return {"status": "ok"}

def _signal_decision_handler(decision_id: str, status: str):
    """Weckt den wartenden wait_for_decision-Thread via Event."""
    try:
        from gnom_hub.core.security.gatekeeper import _signal_decision
        _signal_decision(decision_id, status)
    except ImportError:
        pass

def handle_approve_decision(q):
    decision_id = q.strip()
    from gnom_hub.db import get_state_value, set_state_value, set_agent_status
    pending = get_state_value("pending_decisions", {})
    if decision_id in pending:
        d = pending[decision_id]
        d["status"] = "approved"
        set_state_value("pending_decisions", pending)
        if d["action_type"] == "WRITE":
            writes = get_state_value("approved_security_writes", [])
            writes.append(d["detail"])
            set_state_value("approved_security_writes", writes)
        elif d["action_type"] == "SHELL":
            cmds = get_state_value("approved_security_commands", [])
            cmds.append(d["detail"])
            set_state_value("approved_security_commands", cmds)
        _signal_decision_handler(decision_id, "approved")
        set_agent_status(d["agent_name"], "busy")
        try:
            from gnom_hub.db import set_active_showbox, delete_showbox_presentation
            set_active_showbox("")
            delete_showbox_presentation(f"Blockade: {d['agent_name']}")
        except Exception as e:
            print(f"Error clearing blockade presentation: {e}")
        _post_chat("System", f"Entscheidung '{decision_id}': Aktion von **{d['agent_name']}** wurde **erlaubt**.")
        return {"status": "ok"}
    else:
        _post_chat("System", f"Fehler: Entscheidung '{decision_id}' nicht gefunden.")
        return {"status": "error", "message": "Decision not found"}

def handle_reject_decision(q):
    decision_id = q.strip()
    from gnom_hub.db import get_state_value, set_state_value, set_agent_status
    pending = get_state_value("pending_decisions", {})
    if decision_id in pending:
        d = pending[decision_id]
        d["status"] = "rejected"
        set_state_value("pending_decisions", pending)
        _signal_decision_handler(decision_id, "rejected")
        set_agent_status(d["agent_name"], "busy")
        try:
            from gnom_hub.db import set_active_showbox, delete_showbox_presentation
            set_active_showbox("")
            delete_showbox_presentation(f"Blockade: {d['agent_name']}")
        except Exception as e:
            print(f"Error clearing blockade presentation: {e}")
        _post_chat("System", f"Entscheidung '{decision_id}': Aktion von **{d['agent_name']}** wurde **abgelehnt**.")
        return {"status": "ok"}
    else:
        _post_chat("System", f"Fehler: Entscheidung '{decision_id}' nicht gefunden.")
        return {"status": "error", "message": "Decision not found"}

def handle_bake(q):
    parts = q.strip().split()
    if not parts or not parts[0].strip():
        _post_chat("System", "Fehler: Bitte gib einen Namen für deinen SuperGNOM an (z.B. `@bake senior_assistant`)")
        return {"status": "error", "message": "Missing name"}
    name = parts[0]
    template = parts[1] if len(parts) > 1 else "chat"
    _post_chat("System", f"🚀 Starte Kompilierung von SuperGNOM **{name}** (Template: *{template}*)...")
    try:
        from gnom_hub.core.utils.compiler import bake_supergnom
        dist_path = bake_supergnom(name, template)
        _post_chat("System", f"✅ SuperGNOM **{name}** erfolgreich kompiliert!\n\nVerzeichnis: `{dist_path}`\n\nStarte ihn im neuen Ordner per: `bash run.sh`")
        return {"status": "ok", "path": dist_path}
    except Exception as e:
        _post_chat("System", f"❌ Fehler bei der Kompilierung: {str(e)}")
        return {"status": "error", "message": str(e)}

def handle_emergency(q):
    query = q.strip()
    if not query:
        _post_chat("System", "Fehler: Bitte gib einen Suchbegriff für die Notfall-Abfrage an (z.B. `@emergency Python`).")
        return {"status": "error", "message": "Missing query"}
    _post_chat("System", f"🚨 Starte Notfall-Abfrage in der passiven Archiv-Datenbank für: **{query}**...")
    try:
        from gnom_hub.db.passive_db import emergency_search
        results = emergency_search(query, limit=5)
        if not results:
            _post_chat("System", "⚠️ Keine passenden Einträge im passiven Archiv gefunden.")
            return {"status": "ok", "results": []}
        md = f"📋 **Gefundene Archiv-Einträge ({len(results)}):**\n\n"
        for r in results:
            ts = r.get("timestamp", "").split("T")[0]
            md += f"- **[{ts}] {r.get('sender')} ({r.get('category')}):** {r.get('content')}\n"
        _post_chat("System", md)
        return {"status": "ok", "results": results}
    except Exception as e:
        _post_chat("System", f"❌ Fehler bei der Notfall-Abfrage: {str(e)}")
        return {"status": "error", "message": str(e)}

def handle_diagnose(q):
    q = q.strip().lower()
    if q in ("", "process", "system", "hangs"):
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from scripts.diagnose_hub import run_diagnose
        report = run_diagnose()
        _post_chat("System", report)
        return {"status": "ok"}
    
    from gnom_hub.chat.brainstorm.brainstorm import dispatch
    _post_chat("System", "🔍 Starte Selbstdiagnose der Gnom-Agenten...")
    task = "Führe eine Selbstdiagnose deiner Systemumgebung und Berechtigungen durch. Versuche testweise eine Datei zu schreiben und einen harmlosen Shell-Befehl auszuführen, um zu prüfen, ob dir Schreibrechte (WRITE) oder Terminalrechte (SHELL) fehlen. Prüfe auch die Verfügbarkeit von Programmen wie 'git' und 'docker'. Melde alle fehlenden Berechtigungen oder Tools SOFORT als Warnung über die Showbox!"
    dispatch(task, target="all")
    return {"status": "ok"}

def handle_help(q):
    help_html_slides = [
        # Slide 1: Welcome & UI
        (
            "<div style='padding: 30px; color: #f1f3f9; font-family: sans-serif; height: 100%; display: flex; flex-direction: column; justify-content: center;'>"
            "<h1 style='color: #00e5ff; font-size: 2.5rem; font-family: Orbitron, sans-serif; margin-bottom: 24px; text-shadow: 0 0 15px rgba(0, 229, 255, 0.5);'>🧠 GNOM-HUB CLI & UI ANLEITUNG</h1>"
            "<p style='font-size: 1.25rem; line-height: 1.7; margin-bottom: 24px; color: #8b9bb4;'>"
            "Willkommen in der Showbox. Hier findest du alle Steuerungsoptionen für dein offline Agenten-Team."
            "</p>"
            "<ul style='font-size: 1.15rem; line-height: 2.0; margin-left: 24px; color: #f1f3f9;'>"
            "<li><strong>War Room (Mitte):</strong> Chat-Eingabe und Anzeige der Denkprozesse.</li>"
            "<li><strong>Showbox (Rechts):</strong> Render-Fläche für Entwürfe, Genehmigungen und Web-Previews.</li>"
            "<li><strong>Workspace (Tab 2):</strong> Lokale Dateiübersicht und Sandboxes.</li>"
            "<li><strong>Metrics (Tab 3):</strong> Bento-Grid mit Token- und RAM-Statistiken.</li>"
            "<li><strong>LLM Config (Tab 4):</strong> Schieberegler für Agentenverhaltensweisen.</li>"
            "</ul>"
            "</div>"
        ),
        # Slide 2: The 8 Agents
        (
            "<div style='padding: 30px; color: #f1f3f9; font-family: sans-serif; height: 100%; display: flex; flex-direction: column; justify-content: center;'>"
            "<h1 style='color: #39ff14; font-size: 2.5rem; font-family: Orbitron, sans-serif; margin-bottom: 24px; text-shadow: 0 0 15px rgba(57, 255, 20, 0.5);'>🤖 ROLLENPROFILE DER 8 GNOME</h1>"
            "<div style='display: grid; grid-template-columns: 1fr 1fr; gap: 30px; font-size: 1.1rem; line-height: 1.6;'>"
            "<div>"
            "<h3 style='color: #ff007f; font-size: 1.3rem; margin-bottom: 12px; font-family: Orbitron, sans-serif;'>System-Layer (Administrativ)</h3>"
            "<ul style='margin-left: 20px;'>"
            "<li><strong>GeneralAG:</strong> Delegiert Aufgaben exklusiv an die 4 Worker.</li>"
            "<li><strong>SoulAG:</strong> Verwaltet Langzeitgedächtnis und injiziert Kontext.</li>"
            "<li><strong>WatchdogAG:</strong> Blockiert unbefugte Dateizugriffe und Systemänderungen.</li>"
            "<li><strong>SecurityAG:</strong> Scannt Codes und pip-Pakete vor Ausführung.</li>"
            "</ul>"
            "</div>"
            "<div>"
            "<h3 style='color: #00e5ff; font-size: 1.3rem; margin-bottom: 12px; font-family: Orbitron, sans-serif;'>Worker-Layer (Ausführend)</h3>"
            "<ul style='margin-left: 20px;'>"
            "<li><strong>CoderAG:</strong> Schreibt Scripte, Codes und Web-UIs.</li>"
            "<li><strong>WriterAG:</strong> Erstellt Texte, Newsletter und Dokumentationen.</li>"
            "<li><strong>ResearcherAG:</strong> Recherchiert im Netz und crawlt Webseiten.</li>"
            "<li><strong>EditorAG:</strong> Lektoriert Entwürfe und refaktoriert Programmierungen.</li>"
            "</ul>"
            "</div>"
            "</div>"
            "</div>"
        ),
        # Slide 3: Commands & @-Tags
        (
            "<div style='padding: 30px; color: #f1f3f9; font-family: sans-serif; height: 100%; display: flex; flex-direction: column; justify-content: center;'>"
            "<h1 style='color: #ff007f; font-size: 2.5rem; font-family: Orbitron, sans-serif; margin-bottom: 24px; text-shadow: 0 0 15px rgba(255, 0, 127, 0.5);'>⚙️ CHAT-KOMMANDOS (COMMANDS)</h1>"
            "<table style='width: 100%; border-collapse: collapse; font-size: 1.1rem; line-height: 1.8; text-align: left;'>"
            "<tr><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); color: #00e5ff;'><strong>@AgentName -&gt; Aufgabe</strong></td><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08);'>Zuweisung über GeneralAG (z.B. <code>@coderag -&gt; baue WebUI</code>)</td></tr>"
            "<tr><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); color: #00e5ff;'><strong>@worker -&gt; Aufgabe</strong></td><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08);'>Delegiert eine Aufgabe an alle online Worker-Agenten gleichzeitig.</td></tr>"
            "<tr><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); color: #00e5ff;'><strong>@@diagnose</strong></td><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08);'>Triggert die Selbstdiagnose aller Gnome live im Panel.</td></tr>"
            "<tr><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); color: #00e5ff;'><strong>@@status</strong></td><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08);'>Listet die aktiven Jobs und Stati aller Gnome auf.</td></tr>"
            "<tr><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); color: #00e5ff;'><strong>@tts on / off / toggle</strong></td><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08);'>Schaltet Sprachausgabe (TTS) global an oder aus.</td></tr>"
            "<tr><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); color: #00e5ff;'><strong>@@clear</strong></td><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08);'>Löscht den Verlauf des aktuellen Chats.</td></tr>"
            "<tr><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); color: #00e5ff;'><strong>@@help / @@hilfe</strong></td><td style='padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08);'>Öffnet diese interaktive Anleitung direkt in deiner Showbox!</td></tr>"
            "</table>"
            "</div>"
        ),
        # Slide 4: Baking & SuperGNOM
        (
            "<div style='padding: 30px; color: #f1f3f9; font-family: sans-serif; height: 100%; display: flex; flex-direction: column; justify-content: center;'>"
            "<h1 style='color: #00e5ff; font-size: 2.5rem; font-family: Orbitron, sans-serif; margin-bottom: 24px; text-shadow: 0 0 15px rgba(0, 229, 255, 0.5);'>🏭 @bake & PORTABLE PRODUKTE</h1>"
            "<p style='font-size: 1.25rem; line-height: 1.7; margin-bottom: 20px; color: #8b9bb4;'>"
            "Nachdem du deinen Agentenschwarm evolviert hast, kannst du ihn einfrieren und kompilieren:"
            "</p>"
            "<ul style='font-size: 1.15rem; line-height: 2.0; margin-left: 24px; color: #f1f3f9;'>"
            "<li><strong>Befehl:</strong> <code>@@bake [Name] [Template]</code> (z.B. <code>@@bake meine_app chat</code>)</li>"
            "<li><strong>Kompilierung:</strong> Erzeugt einen standfesten, standalone-lauffähigen Ordner in <code>dist/</code>.</li>"
            "<li><strong>Integritätsschutz:</strong> Prompts werden festgeschrieben, geschützt vor Drifts und Manipulationen.</li>"
            "</ul>"
            "</div>"
        )
    ]
    
    import json
    slides_json = json.dumps(help_html_slides)
    _post_chat("System", f"📖 **Gnom-Hub Handbuch geladen:** Die vollständige Anleitung wurde direkt in deine Showbox übertragen! <SHOWBOX:1>{slides_json}</SHOWBOX>")
    return {"status": "ok"}

def handle_confirmations(q):
    from gnom_hub.db import get_state_value, set_state_value
    val = q.strip().lower()
    if val in ("on", "true", "1", "enable"):
        set_state_value("enable_confirmations", True)
        _post_chat("System", "🛡️ **Gatekeeper-Bestätigungen aktiviert:** Gefährliche Aktionen müssen ab jetzt wieder manuell freigegeben werden.")
    elif val in ("off", "false", "0", "disable"):
        set_state_value("enable_confirmations", False)
        _post_chat("System", "⚡ **Gatekeeper-Bestätigungen deaktiviert:** Alle Datei- und Befehlszugriffe werden automatisch freigegeben (Auto-Approve).")
    else:
        current = get_state_value("enable_confirmations", False)
        status = "Aktiviert" if current else "Deaktiviert"
        _post_chat("System", f"ℹ️ **Gatekeeper-Bestätigungen:** {status}. Nutze `@@confirmations off` zum Ausschalten oder `@@confirmations on` zum Einschalten.")
    return {"status": "ok"}


def handle_spass(q):
    from gnom_hub.db import get_state_value, set_state_value, get_all_agents
    agents = get_all_agents()
    settings = get_state_value("agent_settings", {})
    
    humor_prompt = "Strikte Regel: Sei humorvoll, locker und witzig. Humor steht vor Logik! Nimm dich selbst und die Aufgabe nicht zu ernst, baue Witze oder lustige Vergleiche ein."
    
    t = q.strip().lower()
    if t in ("off", "disable", "ende", "end", "stop", "0", "false"):
        for a in agents:
            a_name = a.get("name", "").lower()
            if not a_name:
                continue
            a_settings = settings.get(a_name, {})
            a_settings["personality"] = 3
            a_settings["creativity"] = 3
            a_settings["risk_tolerance"] = 3
            a_settings["response_style"] = 3
            
            orig_prompt = a_settings.get("custom_prompt", "")
            if humor_prompt in orig_prompt:
                orig_prompt = orig_prompt.replace(humor_prompt, "")
            a_settings["custom_prompt"] = orig_prompt.strip()
            settings[a_name] = a_settings
            
        set_state_value("agent_settings", settings)
        _post_chat("System", "😐 **Humor-Modus deaktiviert (@spass off/ende):** Alle Agenten wurden auf Normalbetrieb (Standard-Reglerwerte) zurückgesetzt.")
        return {"status": "ok"}
    
    for a in agents:
        a_name = a.get("name", "").lower()
        if not a_name:
            continue
        a_settings = settings.get(a_name, {})
        a_settings["personality"] = 5
        a_settings["creativity"] = 5
        a_settings["risk_tolerance"] = 5
        a_settings["response_style"] = 4
        
        orig_prompt = a_settings.get("custom_prompt", "")
        if "Humor steht vor Logik!" not in orig_prompt:
            a_settings["custom_prompt"] = (orig_prompt + "\n\n" + humor_prompt).strip()
        settings[a_name] = a_settings
        
    set_state_value("agent_settings", settings)
    
    _post_chat("System", "🤪 **Humor-Modus aktiviert (@spass):** Alle Agenten wurden auf maximale Kreativität (Wild), sehr lockeren Umgangston (Sehr locker) und hohe Risikobereitschaft eingestellt. Humor steht ab jetzt vor Logik!")
    return {"status": "ok"}


def handle_blockade(q):
    from gnom_hub.db import get_state_value, set_state_value, set_agent_status
    val = q.strip().lower()
    if val in ("off", "false", "0", "disable", "aus"):
        set_state_value("enable_confirmations", False)
        
        # Auto-approve all pending decisions immediately
        pending = get_state_value("pending_decisions", {})
        approved_count = 0
        for d_id, d in list(pending.items()):
            if d.get("status") == "pending":
                d["status"] = "approved"
                
                # Update approved lists
                if d.get("action_type") == "WRITE":
                    writes = get_state_value("approved_security_writes", []) or []
                    writes.append(d["detail"])
                    set_state_value("approved_security_writes", writes)
                elif d.get("action_type") == "SHELL":
                    cmds = get_state_value("approved_security_commands", []) or []
                    cmds.append(d["detail"])
                    set_state_value("approved_security_commands", cmds)
                
                _signal_decision_handler(d_id, "approved")
                set_agent_status(d["agent_name"], "busy")
                
                # Delete Showbox card
                try:
                    from gnom_hub.db import delete_showbox_presentation
                    delete_showbox_presentation(f"Blockade: {d['agent_name']}")
                except Exception as e:
                    print(f"Error clearing blockade presentation: {e}")
                
                approved_count += 1
                
        set_state_value("pending_decisions", pending)
        
        # Also clear active showbox if needed
        try:
            from gnom_hub.db import set_active_showbox
            set_active_showbox("")
        except Exception:
            pass
            
        msg = "⚡ **System-Blockaden deaktiviert:** Alle Datei- und Befehlszugriffe werden automatisch freigegeben (Auto-Approve)."
        if approved_count > 0:
            msg += f" {approved_count} ausstehende Freigabe(n) wurden automatisch genehmigt."
        _post_chat("System", msg)
        
    elif val in ("on", "true", "1", "enable", "an", "ein"):
        _post_chat("System", "ℹ️ **System-Blockaden sind dauerhaft deaktiviert.** Alle Agenten arbeiten im Auto-Approve-Modus.")
    else:
        current = get_state_value("enable_confirmations", False)
        status = "Deaktiviert (Auto-Approve)" if not current else "Aktiviert (Bestätigungspflichtig)"
        _post_chat("System", f"ℹ️ **System-Blockaden:** {status}. Nutze `@blockade aus` zum Ausschalten oder `@blockade an` zum Einschalten.")
        
    return {"status": "ok"}

