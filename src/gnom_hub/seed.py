"""Seed-Daten für Neuinstallation — 8 System + 7 Worker Agenten."""
import uuid
from datetime import datetime

SEED_AGENTS = [
    # System (8)
    ("GeneralAG",     "Task distribution, coordination",                  "general"),
    ("SummarizerAG",  "Summaries, information filtering",                 "summarizer"),
    ("WatchdogAG",    "System monitoring, health checks",                 "normal"),
    ("CronjobAG",     "Scheduled tasks",                                  "normal"),
    ("BackupAG",      "Backups, snapshots, recovery",                     "normal"),
    ("SoulAG",        "Swarm consciousness, personality",                 "normal"),
    ("SecurityAG",    "Security, signature verification",                 "normal"),
    ("SkillsAG",      "Skill recognition, capability analysis",           "normal"),
    # Worker (7)
    ("writerAG",      "Texts, scripts, content, and creative writing",    "normal"),
    ("coderAG",       "Programming, writing code, technical execution",   "normal"),
    ("researcherAG",  "Researching, gathering and summarizing info",      "normal"),
    ("editorAG",      "Checking results, editing, quality assurance",     "normal"),
    ("web_crawlerAG", "Web surfer — Fetches web pages, follows links",    "normal"),
    ("data_crawlerAG","Structure extractor — Tables, lists, JSON",        "normal"),
    ("smart_crawlerAG","Anti-blocking crawler — Smart rate-limits",        "normal"),
]

def create_seed():
    return [{"id": str(uuid.uuid4()), "name": n, "port": 0, "description": d,
             "status": "online", "role": r, "created_at": datetime.utcnow().isoformat() + "Z"}
            for n, d, r in SEED_AGENTS]
