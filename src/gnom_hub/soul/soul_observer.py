# soul_observer.py — SoulAG Behavior-Analyst
# Analysiert Denkprozesse aller Agenten auf Auffälligkeiten:
# 1. Prompt-Injection-Versuche (Agent verhält sich plötzlich "fremdgesteuert")
# 2. Tool-Mismatch (Agent versucht X mehrfach, hat aber nicht die Permission)
# 3. Failure-Loop (Agent dreht sich im Kreis, immer gleiche Fehler)
# 4. Stuck-Pattern (Agent erkennt selbst dass er nicht weiterkommt)
#
# Erkenntnisse werden an GeneralAG kommuniziert, der dann reagieren kann.
import logging
import re
import threading
import time
from collections import defaultdict, deque

_log = logging.getLogger(__name__)

# In-Memory Ring-Buffer pro Agent: letzte 20 Denkprozess-Extraktionen
_agent_history: dict = defaultdict(lambda: deque(maxlen=20))
_agent_history_lock = threading.Lock()

# Erkannte Probleme werden hier gecached, damit wir GeneralAG nicht mit Wiederholungen zumüllen
_recent_alerts: dict = defaultdict(float)  # key -> last_alert_ts
_ALERT_COOLDOWN_S = 300  # 5 Min zwischen gleichen Alerts


# ── Pattern-Definitionen ──────────────────────────────────────────
INJECTION_PATTERNS = [
    (r"ignoriere\s+(?:alle|alle\s+vorherigen|alle\s+obigen).*?(?:regeln|anweisungen|richtlinien)",
     "ignoriere-anweisungen"),
    (r"vergiss\s+(?:alle|alle\s+vorherigen).*?(?:regeln|anweisungen)",
     "vergiss-anweisungen"),
    (r"du\s+bist\s+(?:jetzt|nun)\s+(?:ein|eine)\s+\w+",
     "neue-identitaet"),
    (r"system\s*:\s*.*?neue.*?(?:rolle|identit[aä]t|aufgabe)",
     "system-rollen-override"),
    (r"schicke?\s+(?:alle|token|daten).*?(?:an|nach|zu)\s+https?://",
     "exfiltration"),
    (r"(?:api[_\-]?key|password|passwort|secret)\s*[:=]\s*\S+",
     "credential-leak"),
    (r"send\s+to\s+\S+@\S+",  # EN exfil
     "email-exfil"),
    (r"exfiltrat|datenleck|leak\s+the",
     "exfil-keyword"),
]

TOOL_MISMATCH_PATTERNS = [
    (r"(?:ich\s+)?(?:kann|darf)\s+nicht\s+(?:schreiben|lesen|zugreifen|ausführen)",
     "permission-denied"),
    (r"tool\s+fehlt|fehlende[s]?\s+tool|missing\s+tool",
     "missing-tool"),
    (r"(?:versuche|probiere)\s+(?:screencapture|ffmpeg|git)\s+.*?(?:scheitert|fehlschlägt|blocked)",
     "blocked-attempt"),
    (r"gatekeeper\s+(?:blockiert|verweigert|lehnt\s+ab)",
     "gatekeeper-block"),
    (r"(?:hat|haben|habe|ich\s+habe)?\s*keine\s+(?:berechtigung|permission|access|rechte|tools)",
     "no-permission"),
    (r"(?:screencapture|video_record|ffmpeg).*?(?:nicht\s+(?:verfügbar|installiert|erlaubt))",
     "video-tool-missing"),
]

FAILURE_LOOP_PATTERNS = [
    (r"(?:wieder|schon\s+wieder|erneut|gleiche|immer\s+wieder)\s+(?:fehler|problem|error|gescheitert)",
     "repeated-failure"),
    (r"(?:im\s+kreis|kreislauf|endlosschleife|schleife)",
     "loop-detection"),
    (r"(?:3\.?\s*mal|4\.?\s*mal|5\.?\s*mal|mehrfach|oftmals)\s+(?:versucht|probiert|gescheitert)",
     "multiple-attempts"),
]

STUCK_PATTERNS = [
    (r"(?:ich\s+)?weiß\s+nicht\s+(?:mehr|weiter|was|wie)",
     "stuck-uncertainty"),
    (r"(?:ich\s+)?komme\s+nicht\s+weiter|kein\s+fortschritt|kommen\s+wir\s+nicht\s+weiter",
     "stuck-progress"),
    (r"(?:brauche|benötige|needs?)\s+(?:hilfe|help|unterstützung|rückmeldung|feedback)",
     "needs-help"),
    (r"(?:frage|unclear|unklar|missverständnis|verwirrt)",
     "confusion"),
]


def _scan_patterns(text: str, patterns: list) -> list:
    """Returns list of (category, match) for all pattern hits."""
    hits = []
    text_lower = text.lower()
    for pattern, category in patterns:
        m = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
        if m:
            hits.append((category, m.group(0)[:80]))
    return hits


def analyze_agent_thought(agent_name: str, thought_text: str) -> dict:
    """
    Hauptanalyse: ein Agent hat gerade einen Denkprozess abgeschlossen.
    Gibt ein dict mit erkannten Auffälligkeiten zurück:
    {
      "agent": str,
      "timestamp": float,
      "injection": [matches],   # evtl. Prompt-Injection
      "tool_mismatch": [matches],
      "failure_loop": [matches],
      "stuck": [matches],
      "alerts": [str],          # kurze Beschreibungen für GeneralAG
    }
    """
    now = time.time()
    with _agent_history_lock:
        history = _agent_history[agent_name]
        history.append({"ts": now, "text": thought_text[:1500]})

    result = {
        "agent": agent_name,
        "timestamp": now,
        "injection": _scan_patterns(thought_text, INJECTION_PATTERNS),
        "tool_mismatch": _scan_patterns(thought_text, TOOL_MISMATCH_PATTERNS),
        "failure_loop": _scan_patterns(thought_text, FAILURE_LOOP_PATTERNS),
        "stuck": _scan_patterns(thought_text, STUCK_PATTERNS),
        "alerts": [],
    }

    # ── Wiederholungs-Check: gleiche Probleme in letzten 5 Einträgen? ──
    recent = list(history)[-5:]
    tool_mismatch_count = sum(
        1 for h in recent
        if _scan_patterns(h["text"], TOOL_MISMATCH_PATTERNS)
    )
    failure_count = sum(
        1 for h in recent
        if _scan_patterns(h["text"], FAILURE_LOOP_PATTERNS)
    )

    # ── Alerts generieren (mit Cooldown) ──
    if result["injection"]:
        alert = f"⚠️ Mögliche Prompt-Injection in {agent_name}-Denkprozess erkannt"
        if _should_alert(f"inject:{agent_name}"):
            result["alerts"].append(alert)
            _log.warning(alert + ": " + str(result["injection"][:2]))

    if tool_mismatch_count >= 2:
        alert = f"🔧 {agent_name} hat wiederholt Tool-Probleme (Permission/Block) — GeneralAG bitte Tool-Situation prüfen"
        if _should_alert(f"tool_mismatch:{agent_name}"):
            result["alerts"].append(alert)
            _log.info(alert + f" (Vorkommen: {tool_mismatch_count}/letzte-5)")

    if failure_count >= 2:
        alert = f"🔁 {agent_name} dreht sich im Kreis (mehrere Fehler in Folge) — GeneralAG bitte Alternativ-Strategie vorgeben"
        if _should_alert(f"failure_loop:{agent_name}"):
            result["alerts"].append(alert)
            _log.info(alert + f" (Vorkommen: {failure_count}/letzte-5)")

    if result["stuck"] and len(history) >= 3:
        alert = f"🆘 {agent_name} signalisiert Hilfebedarf — GeneralAG bitte unterstützen"
        if _should_alert(f"stuck:{agent_name}"):
            result["alerts"].append(alert)
            _log.info(alert + ": " + str(result["stuck"][:2]))

    return result


def _should_alert(key: str) -> bool:
    """Rate-Limit: gleicher Alert max alle 5 Min."""
    now = time.time()
    last = _recent_alerts.get(key, 0)
    if now - last < _ALERT_COOLDOWN_S:
        return False
    _recent_alerts[key] = now
    return True


def notify_generalag(analysis: dict) -> bool:
    """
    Schickt einen Hinweis an GeneralAG im Chat, falls Alerts vorhanden.
    Returns True wenn etwas gesendet wurde.
    """
    if not analysis.get("alerts"):
        return False
    try:
        from gnom_hub.db import add_chat_message, get_active_project
        msg = (
            "🧠 **[SoulAG-Beobachtung]** zu @" + analysis["agent"] + ":\n\n" +
            "\n".join(f"• {a}" for a in analysis["alerts"]) +
            "\n\n_Details: " + str({
                "injection": len(analysis["injection"]),
                "tool_mismatch": len(analysis["tool_mismatch"]),
                "failure_loop": len(analysis["failure_loop"]),
                "stuck": len(analysis["stuck"]),
            }) + "_"
        )
        add_chat_message(
            get_active_project(),
            "SoulAG", "soulag", "chat", msg,
        )
        return True
    except Exception as e:
        _log.error("notify_generalag fehlgeschlagen: %s", e)
        return False
