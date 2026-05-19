"""Seed-Daten für Neuinstallation — 8 System + 7 Worker Agenten."""
import uuid
from datetime import datetime

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
    ("writerAG",      "Texte, Skripte, Inhalte und kreatives Schreiben",                   "normal"),
    ("coderAG",       "Programmieren, Code schreiben, technische Umsetzung",               "normal"),
    ("researcherAG",  "Recherchieren, Informationen sammeln und zusammenfassen",            "normal"),
    ("editorAG",      "Ergebnisse prüfen, überarbeiten, Qualität sichern und finalisieren", "normal"),
    ("web_crawlerAG", "Web-Surfer — Holt frische Webseiten, folgt Links",                  "normal"),
    ("data_crawlerAG","Struktur-Extraktor — Tabellen, Listen, Preise, JSON",               "normal"),
    ("smart_crawlerAG","Anti-Block-Crawler — Rate-Limits, Filter, schlau",                 "normal"),
]

def create_seed():
    return [{"id": str(uuid.uuid4()), "name": n, "port": 0, "description": d,
             "status": "online", "role": r, "created_at": datetime.utcnow().isoformat() + "Z"}
            for n, d, r in SEED_AGENTS]
