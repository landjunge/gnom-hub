"""SoulAG Action-Modul.

SoulAG ist der zentrale Beobachter des Schwarms. Bisher konnte er nur
Fakten speichern und im Chat posten. Mit diesen Actions kann er:

1. **speak()**        — direkte Sprachausgabe an User (via TTS)
2. **dispatch_agent()** — andere Agenten triggern via @mention
3. **list_voices()**   — verfügbare Stimmen anzeigen

Beispiel-Use-Cases:
- "Wenn Blockade sinnlos, schicke ResearcherAG los" (SoulAG → GeneralAG → ResearcherAG)
- "Bei aktueller Bedrohung, sprich User direkt an" (SoulAG.speak)
"""
import logging

from gnom_hub.soul.agent_voices import (
    SYSTEM as _SYSTEM,
)
from gnom_hub.soul.agent_voices import (
    get_voice_for_agent,
)
from gnom_hub.soul.agent_voices import (
    list_voices as _list_voices,
)
from gnom_hub.soul.agent_voices import (
    speak as _speak_raw,
)

_log = logging.getLogger(__name__)


def speak(text: str, agent_name: str = "SoulAG", lang: str = "de") -> bool:
    """SoulAG spricht mit User via TTS in der zugewiesenen Stimme."""
    voice = get_voice_for_agent(agent_name, lang)
    _log.info(f"[SoulAG] speak via '{voice}' on {_SYSTEM}: {text[:50]}...")
    return _speak_raw(text, voice=voice)


def list_voices() -> list:
    """List all available TTS voices on this platform."""
    return _list_voices()


def dispatch_agent(target_agent: str, task: str, sender: str = "SoulAG",
                   context_id: str = None) -> bool:
    """SoulAG triggert einen System-Agent via @mention.

    WICHTIG: SoulAG darf NUR System-Agents dispatchen
    (GeneralAG, SecurityAG, WatchdogAG, SoulAG).
    Worker (WriterAG, CoderAG, ResearcherAG, EditorAG) werden
    AUSSCHLIESSLICH von GeneralAG dispatched.

    Beispiel: dispatch_agent("GeneralAG", "Schicke ResearcherAG los
    um aktuelle Blockaden zu prüfen")
    """
    SYSTEM_AGENTS = {"soulag", "generalag", "securityag", "watchdogag"}
    target_lower = target_agent.lower().replace(" ", "")
    if target_lower not in SYSTEM_AGENTS:
        _log.warning(
            f"[SoulAG] BLOCKED dispatch to '{target_agent}': "
            f"only system agents are allowed. Use GeneralAG instead."
        )
        return False
    try:
        from gnom_hub.chat.brainstorm.brainstorm import dispatch
        from gnom_hub.db import get_active_project
        proj = context_id or get_active_project() or "default"
        # Erweiterte @mention mit SoulAG-Kontext
        message = f"[SOULAG-BEFEHL] {task}"
        dispatched = dispatch(message, target=target_agent, depth=0,
                             sender=sender, context_id=proj)
        _log.info(f"[SoulAG] dispatched to {target_agent}: {task[:50]}...")
        return bool(dispatched)
    except Exception as e:
        _log.error(f"[SoulAG] dispatch failed: {e}")
        return False


def evaluate_blockade(blockade_id: int) -> dict:
    """SoulAG prüft ob eine Blockade noch sinnvoll ist.

    Triggert ResearcherAG zur Recherche im Web/Logs und gibt Empfehlung.
    """
    from gnom_hub.db.connection import get_db_conn
    try:
        with get_db_conn() as conn:
            row = conn.execute(
                "SELECT id, agent_name, reason, status, action_type, "
                "created_at FROM blockade_log WHERE id = ?",
                (blockade_id,)
            ).fetchone()
        if not row:
            return {"valid": False, "reason": "Blockade nicht gefunden"}
        # Trigger ResearcherAG für Bewertung
        task = (
            f"Prüfe ob Blockade #{blockade_id} noch sinnvoll ist: "
            f"Agent={row['agent_name']}, Aktion={row['action_type']}, "
            f"Grund='{row['reason'][:100]}'. "
            f"Antworte kurz: 'JA — sinnvoll weil...' oder 'NEIN — veraltet weil...'."
        )
        ok = dispatch_agent("ResearcherAG", task)
        return {
            "valid": True,
            "blockade": dict(row),
            "researcher_triggered": ok,
            "task": task,
        }
    except Exception as e:
        _log.error(f"[SoulAG] evaluate_blockade failed: {e}")
        return {"valid": False, "error": str(e)}


# ── User-Bedürfnisse (werden in state['user_needs'] gespeichert) ──

def save_user_need(need: str, priority: str = "medium") -> bool:
    """SoulAG speichert ein User-Bedürfnis (z.B. "kompakte Antworten", "Code immer in TypeScript")."""
    from gnom_hub.db.state_repo import SQLiteStateRepository
    try:
        repo = SQLiteStateRepository()
        needs = repo.get_value("user_needs", []) or []
        needs.append({"need": need, "priority": priority, "ts": _now()})
        repo.set_value("user_needs", needs)
        _log.info(f"[SoulAG] saved user need: {need[:60]} ({priority})")
        return True
    except Exception as e:
        _log.error(f"[SoulAG] save_user_need failed: {e}")
        return False


def get_user_needs() -> list:
    """Alle gespeicherten User-Bedürfnisse."""
    from gnom_hub.db.state_repo import SQLiteStateRepository
    try:
        return SQLiteStateRepository().get_value("user_needs", []) or []
    except Exception:
        return []


# ── Capabilities der Agenten (text/vision/image/audio/tools) ──

AGENT_CAPS = {
    "SoulAG":       ["text", "memory", "dispatch"],
    "WatchdogAG":   ["text", "monitoring", "blockade_solve"],
    "GeneralAG":    ["text", "coordination", "dispatch"],
    "SecurityAG":   ["text", "security", "blockade_evaluate"],
    "WriterAG":     ["text", "creative_writing"],
    "CoderAG":      ["text", "code", "tools"],
    "ResearcherAG": ["text", "web_search", "research", "tools"],
    "EditorAG":     ["text", "editing", "proofreading"],
}

# Was kann welche Task (semantisch)
TASK_CAP_KEYWORDS = {
    "image":        ["image", "bild", "grafik", "picture", "photo", "illustration", "render"],
    "audio":        ["audio", "ton", "sound", "music", "tts", "stimme", "voice", "speak", "sprich"],
    "video":        ["video", "film", "clip", "record", "aufzeichnung"],
    "code":         ["code", "programm", "script", "function", "klasse", "bug", "fix", "implement"],
    "web_search":   ["search", "suche", "find", "finde", "google", "brave", "recherche", "research"],
    "creative":     ["write", "schreib", "story", "geschichte", "poem", "text", "artikel", "blog"],
    "analysis":     ["analysiere", "analyze", "vergleich", "compare", "evaluier", "evaluate", "review"],
    "blockade":     ["blockade", "sperre", "block", "blockiert", "locked", "freigeben", "unlock"],
}


def what_can(agent_name: str) -> list:
    """Was kann dieser Agent? Liste von Capabilities."""
    return AGENT_CAPS.get(agent_name, [])


def find_agent_for_task(task: str) -> dict:
    """SoulAG findet den passenden Agenten für eine Task.

    Beispiel: find_agent_for_task("Recherchiere X im Web")
              → {"agent": "ResearcherAG", "reason": "web_search capability", ...}
    """
    task_lower = task.lower()
    matches = []
    for cap, keywords in TASK_CAP_KEYWORDS.items():
        for kw in keywords:
            if kw in task_lower:
                matches.append(cap)
                break
    if not matches:
        return {"agent": None, "reason": "no specific capability match", "task": task}
    # Finde Agent der die erste match-Cap hat
    for cap in matches:
        for agent, caps in AGENT_CAPS.items():
            if cap in caps:
                # Vermeide Worker wenn System-Agent die Cap auch hat
                if cap in ["blockade", "analysis", "web_search"]:
                    if cap in AGENT_CAPS.get("GeneralAG", []):
                        return {"agent": "GeneralAG", "capability": cap,
                                "reason": f"GeneralAG can coordinate {cap}"}
                return {"agent": agent, "capability": cap,
                        "reason": f"{agent} has '{cap}' capability"}
    return {"agent": None, "reason": "no agent found", "task": task}


# ── WatchdogAG Blockade lösen ──

def solve_blockade(blockade_id: int, reason: str = "") -> dict:
    """SoulAG beauftragt WatchdogAG eine Blockade zu lösen."""
    from gnom_hub.db.connection import get_db_conn
    try:
        with get_db_conn() as conn:
            row = conn.execute(
                "SELECT id, agent_name, action_type, reason FROM blockade_log "
                "WHERE id = ? AND status = 'blocked'",
                (blockade_id,)
            ).fetchone()
        if not row:
            return {"ok": False, "reason": "Blockade nicht aktiv"}
        task = (
            f"[BLOCKADE-LÖSUNG] Blockade #{blockade_id} aufheben. "
            f"User-Begründung: {reason or 'keine Angabe'}. "
            f"Betroffener Agent: {row['agent_name']}, Aktion: {row['action_type']}. "
            f"Prüfe ob die Blockade noch nötig ist und hebe sie ggf. auf."
        )
        ok = dispatch_agent("WatchdogAG", task)
        return {
            "ok": ok,
            "blockade": dict(row),
            "task": task,
            "watchdog_triggered": ok,
        }
    except Exception as e:
        _log.error(f"[SoulAG] solve_blockade failed: {e}")
        return {"ok": False, "error": str(e)}


def _now() -> str:
    """ISO timestamp."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
