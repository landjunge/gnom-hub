import json, threading, uuid, os, tempfile
from datetime import datetime; from .config import DATA_DIR
_lock = threading.Lock()

# ── Default Agents für Neuinstallation ──
SEED_AGENTS = [
    # System (8)
    ("GeneralAG",     "Task-Verteilung, Koordination",              "general"),
    ("SummarizerAG",  "Zusammenfassungen, Informationsfilter",      "summarizer"),
    ("WatchdogAG",    "System-Überwachung, Health-Checks",          "normal"),
    ("CronjobAG",     "Zeitgesteuerte Aufgaben",                    "normal"),
    ("BackupAG",      "Backups, Snapshots, Wiederherstellung",      "normal"),
    ("SoulAG",        "Schwarm-Bewusstsein, Persönlichkeit",        "normal"),
    ("SecurityAG",    "Sicherheit, Signatur-Prüfung",               "normal"),
    ("SkillsAG",      "Skill-Erkennung, Fähigkeiten-Analyse",      "normal"),
    # Worker (7)
    ("writerAG",      "Texte, Skripte, Inhalte und kreatives Schreiben",                  "normal"),
    ("coderAG",       "Programmieren, Code schreiben, technische Umsetzung",              "normal"),
    ("researcherAG",  "Recherchieren, Informationen sammeln und zusammenfassen",           "normal"),
    ("editorAG",      "Ergebnisse prüfen, überarbeiten, Qualität sichern und finalisieren","normal"),
    ("web_crawlerAG", "Web-Surfer — Holt frische Webseiten, folgt Links",                 "normal"),
    ("data_crawlerAG","Struktur-Extraktor — Tabellen, Listen, Preise, JSON",              "normal"),
    ("smart_crawlerAG","Anti-Block-Crawler — Rate-Limits, Filter, schlau",                "normal"),
]

def _seed_agents():
    return [{"id": str(uuid.uuid4()), "name": n, "port": 0, "description": d,
             "status": "online", "role": r, "created_at": datetime.utcnow().isoformat() + "Z"}
            for n, d, r in SEED_AGENTS]

def get_db(n: str):
    p = DATA_DIR / f"{n}.json"
    with _lock:
        if p.exists():
            try:
                with open(p, "r") as f: return json.load(f)
            except Exception as e: print(f"[DB] Lesefehler {n}: {e}"); return []
        if n == "agents":
            s = _seed_agents()
            _atomic_write(p, s)
            return s
    return []

def save_db(n: str, d: list):
    with _lock:
        _atomic_write(DATA_DIR / f"{n}.json", d)

def _atomic_write(path, data):
    """Schreibt erst in temp-Datei, dann rename → kein Datenverlust bei Crash."""
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f: json.dump(data, f, indent=2)
        os.replace(tmp_path, str(path))
    except Exception as e:
        print(f"[DB] Schreibfehler {path.name}: {e}")
        try: os.unlink(tmp_path)
        except: pass

def get_active_project() -> str:
    p = DATA_DIR / "state.json"
    if not p.exists(): return "default"
    try:
        with open(p, "r") as f: return json.load(f).get("active_project", "default")
    except Exception as e: print(f"[DB] state.json Fehler: {e}"); return "default"

def set_active_project(name: str):
    p, s = DATA_DIR / "state.json", {}
    if p.exists():
        try:
            with open(p, "r") as f: s = json.load(f)
        except Exception as e: print(f"[DB] state.json Lesefehler: {e}")
    s["active_project"] = name.strip()
    with _lock:
        _atomic_write(p, s)
