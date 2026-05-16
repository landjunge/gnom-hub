"""Brainstorm Dispatcher — Hub fragt LLM im Namen der Agenten."""
import os, re, requests, threading, uuid
from datetime import datetime
from dotenv import load_dotenv
from .db import get_db, save_db
from .router import ask_router
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
BASE_WORKSPACE = "/Users/landjunge/Documents/AG-Flega/gnom_workspace"

def get_workspace_dir():
    from .db import get_active_project
    d = os.path.join(BASE_WORKSPACE, get_active_project())
    os.makedirs(d, exist_ok=True)
    return d

def _post(sender, content):
    from .db import get_active_project
    entry = {"id": str(uuid.uuid4()), "agent_id": "war-room", "project": get_active_project(), "content": content,
             "metadata": {"type": "brainstorm", "status": "open", "sender": sender},
             "timestamp": datetime.utcnow().isoformat() + "Z"}
    save_db("memory", get_db("memory") + [entry])

def _ask_llm(agent, question, context, bs_mode=False):
    desc = agent.get("description", "")
    role_mem = [m for m in get_db("memory") if m.get("agent_id") == agent.get("id") and m.get("type") == "role"]
    sys_prompt = role_mem[-1]["content"].replace("[SYSTEM-ROLLE] ", "") if role_mem else f"Du bist {agent['name']} ({desc}), ein KI-Agent im Gnom-Hub."
    
    wd = get_workspace_dir()
    files_str = ""
    if os.path.exists(wd): files_str = ", ".join(os.listdir(wd))
    
    sys_prompt += f"\n\n[WORKSPACE: {wd} | Vorhandene Dateien: {files_str}]"
    from .zwc_soul import decode_soul
    from .tool_registry import format_tools_prompt
    role_text = role_mem[-1]["content"] if role_mem else ""
    soul = decode_soul(role_text) or {"role": desc, "permissions": ["read", "write"]}
    sys_prompt += f"\n{format_tools_prompt(soul, agent['name'])}"
    if bs_mode:
        sys_prompt += "\n[MODUS: BRAINSTORM — Nur diskutieren! KEIN [WRITE:] erlaubt. Dateien werden nur auf Einzelauftrag (@AgentName) geschrieben.]"
    
    user_msg = question
    if context: user_msg += f"\n\nBisherige Diskussion:\n{context}"
    try:
        answer = ask_router(user_msg, sys_prompt, agent_name=agent.get("name", ""))
        
        perms = soul.get("permissions", [])
        
        # --- WRITE LOGIC (Permission: "write") ---
        write_matches = re.finditer(r"\[WRITE:\s*(.*?)\](.*?)\[/WRITE\]", answer, re.DOTALL)
        for match in write_matches:
            fname = match.group(1).strip()
            if bs_mode:
                answer = answer.replace(match.group(0), f"[System: WRITE blockiert im Brainstorm-Modus. Nutze @{agent['name']} für Einzelauftrag.]")
                continue
            if "write" not in perms:
                answer = answer.replace(match.group(0), f"[System: {agent['name']} hat keine WRITE-Berechtigung.]")
                continue
            content = match.group(2).strip()
            try:
                fpath = os.path.join(wd, fname)
                if os.path.exists(fpath):
                    import shutil
                    shutil.copy2(fpath, fpath + ".bak")
                with open(fpath, "w") as f: f.write(content)
                answer = answer.replace(match.group(0), f"[System: Datei '{fname}' wurde erfolgreich im Workspace gespeichert.]")
            except Exception as e:
                answer = answer.replace(match.group(0), f"[System-Fehler beim Speichern von {fname}: {e}]")
                
        # --- READ LOGIC (jeder darf lesen) ---
        read_matches = re.finditer(r"\[READ:\s*(.*?)\]", answer)
        for match in read_matches:
            fname = match.group(1).strip()
            p = os.path.join(wd, fname)
            if os.path.exists(p):
                with open(p, "r") as f:
                    file_content = f.read()[:2000]
                answer = answer.replace(match.group(0), f"[Hat {fname} gelesen:\n{file_content}\n...]")
            else:
                answer = answer.replace(match.group(0), f"[Fehler: Datei {fname} nicht gefunden]")
        
        # --- SHELL LOGIC (Permission: "run") ---
        shell_matches = re.finditer(r"\[SHELL:\s*(.*?)\]", answer)
        for match in shell_matches:
            cmd = match.group(1).strip()
            if bs_mode:
                answer = answer.replace(match.group(0), f"[System: SHELL blockiert im Brainstorm-Modus.]")
                continue
            if "run" not in perms and "godmode" not in perms:
                answer = answer.replace(match.group(0), f"[System: {agent['name']} hat keine SHELL-Berechtigung.]")
                continue
            try:
                import subprocess
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=wd)
                out = (result.stdout + result.stderr)[:1500]
                answer = answer.replace(match.group(0), f"[Shell-Ausgabe ({cmd}):\n{out}]")
            except subprocess.TimeoutExpired:
                answer = answer.replace(match.group(0), f"[System: Timeout nach 30s für: {cmd}]")
            except Exception as e:
                answer = answer.replace(match.group(0), f"[Shell-Fehler: {str(e)[:80]}]")
                
        # --- IMAGE LOGIC (Permission: "write", nur writerAG) ---
        img_matches = re.finditer(r"\[IMAGE:\s*(.*?)\]", answer)
        for match in img_matches:
            prompt = match.group(1).strip()
            if bs_mode:
                answer = answer.replace(match.group(0), f"[System: IMAGE blockiert im Brainstorm-Modus.]")
                continue
            if "write" not in perms:
                answer = answer.replace(match.group(0), f"[System: {agent['name']} hat keine IMAGE-Berechtigung.]")
                continue
            try:
                img_key = os.getenv("OPENROUTER_KEY_FREE_1")
                img_res = requests.post("https://openrouter.ai/api/v1/images/generations",
                    headers={"Authorization": f"Bearer {img_key}", "Content-Type": "application/json"},
                    json={"model": "stabilityai/stable-diffusion-xl", "prompt": prompt, "n": 1, "size": "1024x1024"},
                    timeout=60
                )
                if img_res.status_code == 200:
                    img_url = img_res.json().get("data", [{}])[0].get("url", "")
                    answer = answer.replace(match.group(0), f"[Bild generiert: {img_url}]")
                else:
                    answer = answer.replace(match.group(0), f"[System: Bildgenerierung fehlgeschlagen ({img_res.status_code})]")
            except Exception as e:
                answer = answer.replace(match.group(0), f"[System: IMAGE-Fehler: {str(e)[:80]}]")
                
        # --- CRAWL LOGIC (Permission: "crawl", nur crawlerAG) ---
        crawl_matches = re.finditer(r"\[CRAWL:\s*(.*?)\]", answer)
        for match in crawl_matches:
            url = match.group(1).strip()
            if "crawl" not in perms:
                answer = answer.replace(match.group(0), f"[System: {agent['name']} hat keine CRAWL-Berechtigung.]")
                continue
            try:
                r = requests.get(url, timeout=15, headers={"User-Agent": "GnomHub-Crawler/1.0"})
                # HTML-Tags strippen, nur Text
                import re as re2
                text = re2.sub(r'<[^>]+>', ' ', r.text)
                text = re2.sub(r'\s+', ' ', text).strip()[:3000]
                answer = answer.replace(match.group(0), f"[Crawl-Ergebnis ({url[:60]}):\n{text}]")
            except Exception as e:
                answer = answer.replace(match.group(0), f"[Crawl-Fehler: {str(e)[:80]}]")
                
        _post(agent["name"], answer)
    except Exception as e: _post(agent["name"], f"[Fehler: {str(e)[:80]}]")

def _get_ctx():
    """Holt die letzten 8 Chat-Nachrichten als Kontext."""
    from .db import get_active_project
    from .zwc_soul import strip_zwc
    chat = [m for m in get_db("memory") if m.get("agent_id") == "war-room" and m.get("project", "default") == get_active_project()]
    return "\n".join(f"[{m.get('metadata',{}).get('sender','?')}] {strip_zwc(m['content'])[:1000]}"
                    for m in sorted(chat, key=lambda x: x.get("timestamp",""))[-8:])

def _run_phase(agents, question, ctx, bs_mode=False):
    """Feuert Agenten parallel und wartet bis alle fertig sind."""
    threads = []
    for a in agents:
        t = threading.Thread(target=_ask_llm, args=(a, question, ctx, bs_mode), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=200)

def dispatch(question, target=None):
    """3-Phasen-Pipeline: Worker diskutieren → Summarizer fasst zusammen → General entscheidet."""
    exclude = ["BackupAG"]
    all_online = [a for a in get_db("agents") if a.get("status") == "online" and a.get("name") not in exclude]

    # Einzelauftrag: Direkt feuern, keine Pipeline, WRITE erlaubt (mit Backup)
    if target:
        single = [a for a in get_db("agents") if a.get("status") == "online" and a["name"].lower() == target.lower()]
        ctx = _get_ctx()
        for a in single:
            threading.Thread(target=_ask_llm, args=(a, question, ctx, False), daemon=True).start()
        return [a["name"] for a in single]

    # @bs Pipeline in 3 Phasen (WRITE blockiert!)
    workers = [a for a in all_online if a["name"] not in ("SummarizerAG", "GeneralAG")]
    summarizer = [a for a in all_online if a["name"] == "SummarizerAG"]
    general = [a for a in all_online if a["name"] == "GeneralAG"]

    # Phase 1: Worker diskutieren parallel
    print(f"[BS] Phase 1: Worker ({[a['name'] for a in workers]})")
    _run_phase(workers, question, _get_ctx(), bs_mode=True)

    # Phase 2: Summarizer liest Diskussion, fasst zusammen
    if summarizer:
        print(f"[BS] Phase 2: Summarizer")
        _run_phase(summarizer, question, _get_ctx(), bs_mode=True)

    # Phase 3: General liest alles (inkl. Summary), verteilt Jobs
    if general:
        print(f"[BS] Phase 3: General entscheidet")
        _run_phase(general, question, _get_ctx(), bs_mode=True)

    return [a["name"] for a in workers + summarizer + general]
