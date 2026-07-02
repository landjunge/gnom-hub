"""tests/integration/test_chat_end_to_end.py

End-to-End Chat Test — der WIRKLICHE Test.

Schickt eine echte Chat-Message via HTTP POST /api/chat und wartet
auf eine Antwort von SoulAG. Wäre der wd-Bug (NameError in agent_base.py:119)
oder ein LLM-Key-Desync noch da, würde dieser Test FAILEN mit
"Dead-Letter" in der Response.

Voraussetzung: Hub läuft auf http://127.0.0.1:3002.
Wenn nicht, wird der Test SKIPPED (kein crash, klare Meldung).

Run:
    # 1) Hub starten
    cd /Users/landjunge/gnom-hub && nohup .venv/bin/python -m gnom_hub &>/tmp/hub.log &

    # 2) Tests
    /Users/landjunge/gnom-hub/.venv/bin/python -m pytest tests/integration/test_chat_end_to_end.py -v -s

Was dieser Test PRÜFT (was die 35 Golden-Diff NICHT prüfen):
- Echte HTTP-Round-Trip: Frontend → /api/chat → agent_messages Queue
- Echter Agent-Prozess: BaseAgent.run() → fetch_next_message → ask_router → LLM
- Echte LLM-Integration: MiniMax M3 (oder was auch immer in routing.txt)
- Echte prompt-builder-Pipeline: config/agents/<name>.json → core.prompt.builder
- Echte Action-Pipeline: process_actions mit Workspace-Dir (wd-Variable!)
- Echter Response-Flow: Agent → /api/chat → frontend sichtbar
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import pytest

HUB_URL = "http://127.0.0.1:3002"
HUB_TIMEOUT_S = 15.0
RESPONSE_WAIT_S = 30.0
POLL_INTERVAL_S = 2.0


def _hub_is_alive() -> bool:
    """Prüft ob Hub auf 3002 antwortet."""
    try:
        with urllib.request.urlopen(f"{HUB_URL}/api/agents", timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, ConnectionError, OSError):
        return False


pytestmark = pytest.mark.skipif(
    not _hub_is_alive(),
    reason=f"Hub läuft nicht auf {HUB_URL} — starten mit: nohup .venv/bin/python -m gnom_hub &",
)


def _post_chat(content: str, sender: str = "user") -> dict:
    data = json.dumps({"sender": sender, "content": content}).encode()
    req = urllib.request.Request(
        f"{HUB_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=HUB_TIMEOUT_S) as r:
        return json.loads(r.read())


def _get_recent_chat(limit: int = 20) -> list:
    with urllib.request.urlopen(f"{HUB_URL}/api/chat?limit={limit}", timeout=HUB_TIMEOUT_S) as r:
        return json.loads(r.read())


def _post_agents_list() -> list:
    with urllib.request.urlopen(f"{HUB_URL}/api/agents", timeout=HUB_TIMEOUT_S) as r:
        return json.loads(r.read())


def _wait_for_response(marker: str, sender: str = "SoulAG", timeout: float = RESPONSE_WAIT_S) -> dict | None:
    """Pollt /api/chat bis ein Agent eine Antwort mit `marker` gegeben hat."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for msg in _get_recent_chat(limit=10):
            content = msg.get("content", "")
            if msg.get("sender") == sender and marker in content:
                return msg
            if "Dead-Letter" in content and marker in content:
                return msg  # Auch Dead-Letter zurückgeben damit Test sinnvoll failed
        time.sleep(POLL_INTERVAL_S)
    return None


# ── Tests ──────────────────────────────────────────────────────────────────

def test_hub_alive() -> None:
    """Sanity: Hub antwortet."""
    agents = _post_agents_list()
    assert len(agents) == 8, f"Erwarte 8 Agents, habe {len(agents)}"
    statuses = {a["status"] for a in agents}
    assert "online" in statuses, f"Kein Agent online: {statuses}"


def test_soulag_responds_to_simple_greeting() -> None:
    """End-to-End: User schickt 'Hallo' → SoulAG antwortet (nicht Dead-Letter).

    Genau der wd-Bug (NameError) hätte hier gefailt: SoulAG würde nach
    3 Retries in den Dead-Letter-Queue gehen, und die Response wäre
    eine System-Message mit 'Agent SoulAG gescheitert an: ...'.

    User-Mandat 2026-07-02 (Bug 3 Fix): Default-Routing ist GeneralAG,
    SoulAG ist Fallback. Test akzeptiert beide als gültige Annahme.
    """
    marker = f"__e2e_test_{int(time.time())}__"
    user_msg = f"Sag einfach 'ping {marker}' und nichts weiter."
    result = _post_chat(user_msg)
    assert result.get("status") == "dispatched", f"Dispatch failed: {result}"
    # Default-Routing GeneralAG (User-Mandat 2026-07-02), SoulAG als Fallback.
    asked = result.get("asked", [])
    assert any(a in asked for a in ("GeneralAG", "SoulAG")), (
        f"Neither GeneralAG nor SoulAG in asked: {result}"
    )

    # Akzeptiere Antwort von GeneralAG (default) oder SoulAG (fallback).
    response_sender = "GeneralAG" if "GeneralAG" in asked else "SoulAG"
    response = _wait_for_response(marker=marker, sender=response_sender, timeout=RESPONSE_WAIT_S)
    assert response is not None, (
        f"{response_sender} hat in {RESPONSE_WAIT_S}s nicht geantwortet. "
        f"Letzte 10 Chat-Messages checken mit /api/chat?limit=10"
    )
    assert "Dead-Letter" not in response.get("content", ""), (
        f"{response_sender} ging in Dead-Letter (Bug wie wd-NameError):\n{response.get('content', '')}"
    )
    assert marker in response.get("content", ""), (
        f"Marker '{marker}' nicht in {response_sender}-Response:\n{response.get('content', '')[:200]}"
    )


def test_generalag_delegation_chain() -> None:
    """End-to-End: User schickt an @GeneralAG → GeneralAG antwortet.

    Testet die komplette Kette: User → /api/chat → dispatch → GeneralAG.
    Würde fehlschlagen wenn:
    - dispatch_mention kaputt ist
    - GeneralAG nicht antwortet
    - GeneralAG in Dead-Letter geht (z.B. wd-NameError-Bug)
    """
    # Explizite @GeneralAG-Erwähnung (sonst routet /api/chat zu SoulAG)
    user_msg = "@GeneralAG was sind deine 3 Kernrollen? Antworte in einem Satz."

    result = _post_chat(user_msg)
    assert result.get("status") == "dispatched", f"Dispatch failed: {result}"
    assert "GeneralAG" in result.get("asked", []), (
        f"Nicht an GeneralAG dispatched: {result}"
    )

    # GeneralAG sollte antworten (oder ein Worker den es delegiert)
    deadline = time.time() + RESPONSE_WAIT_S
    while time.time() < deadline:
        for msg in _get_recent_chat(limit=10):
            sender = msg.get("sender", "")
            if sender not in ("user", "System") and msg.get("content", "").strip():
                # Wir haben eine non-user/system Antwort
                assert "Dead-Letter" not in msg.get("content", ""), (
                    f"GeneralAG ging in Dead-Letter: {msg.get('content', '')[:200]}"
                )
                return
        time.sleep(POLL_INTERVAL_S)

    pytest.fail(
        f"Keine Antwort von GeneralAG (oder Worker) in {RESPONSE_WAIT_S}s. "
        f"Letzte Messages checken mit /api/chat?limit=10"
    )


def test_all_agents_heartbeat() -> None:
    """Nicht-chat, aber real: alle 8 Agents senden Heartbeats.

    Wenn ein Agent stirbt, wird der Status 'offline' oder
    fehlt komplett in /api/agents. Wir akzeptieren 'online' UND
    'busy' (Agent ist gerade aktiv) als healthy — 'offline' wäre
    ein echter Fehler.
    """
    agents = _post_agents_list()
    healthy = [a for a in agents if a["status"] in ("online", "busy")]
    unhealthy = [a for a in agents if a["status"] not in ("online", "busy")]
    assert len(agents) == 8, f"Erwarte 8 Agents total, habe {len(agents)}"
    assert not unhealthy, (
        f"Agents mit ungesundem Status: {[(a['name'], a['status']) for a in unhealthy]}"
    )
    assert len(healthy) == 8, (
        f"Erwarte 8 healthy agents, habe {len(healthy)}. "
        f"Status-Verteilung: {[(a['name'], a['status']) for a in agents]}"
    )
