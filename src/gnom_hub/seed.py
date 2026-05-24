"""Seed-Daten für Neuinstallation — 4 System + 4 Worker Agenten."""
import uuid
from datetime import datetime

SEED_AGENTS = [
    # System (4)
    ("SoulAG",        "Swarm consciousness, personality",                 "normal"),
    ("GeneralAG",     "Task distribution, coordination",                  "general"),
    ("SecurityAG",    "Security, signature verification",                 "normal"),
    ("WatchdogAG",    "System monitoring, health checks",                 "normal"),
    # Worker (4)
    ("ResearcherAG",  "Researching, gathering and summarizing info",      "normal"),
    ("WriterAG",      "Texts, scripts, content, and creative writing",    "normal"),
    ("EditorAG",      "Checking results, editing, quality assurance",     "normal"),
    ("CoderAG",       "Programming, writing code, technical execution",   "normal"),
]

def create_seed():
    return [{"id": str(uuid.uuid4()), "name": n, "port": 0, "description": d,
             "status": "online", "role": r, "created_at": datetime.utcnow().isoformat() + "Z"}
            for n, d, r in SEED_AGENTS]
