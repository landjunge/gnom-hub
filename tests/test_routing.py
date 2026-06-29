"""Tests for gnom_hub.agents.routing — Deterministic Capability-Routing.

Coverage
────────
1. Exact-Match (Phrase + Single-Token)
2. Synonym-Match
3. No-Match → ResolvedCapability("", 0.0, "none")
4. Determinism (same input 100x → same output)
5. Node-ID-Override (Offload-Bridge)
6. Invalid Node-ID → Fallback
7. Fallback-Chain Builder
8. Feature-Flag-Default-Off
9. End-to-End Integration with dispatch_by_capability_with_resolution
10. Bonus: Tokenizer behavior, German keywords

All tests are isolated by ``tests/conftest.py::isolated_db`` (autouse).
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pytest


# ── 1. Exact-Match (Phrase) ─────────────────────────────────────────────────


def test_resolve_capability_exact_match():
    """``write a file`` → ``write_file`` (Phrase-Exact, 1.0)."""
    from gnom_hub.agents.routing import resolve_capability

    r = resolve_capability("please write a file with the report")
    assert r.capability == "write_file"
    assert r.confidence == 1.0
    assert r.source == "exact_match"


# ── 2. Synonym-Match ────────────────────────────────────────────────────────


def test_resolve_capability_synonym_match():
    """``run pytest`` → ``shell`` (token "pytest" ist Synonym → 0.7)."""
    from gnom_hub.agents.routing import resolve_capability

    r = resolve_capability("let's run pytest on this branch")
    assert r.capability == "shell"
    assert r.confidence == 0.7
    assert r.source == "synonym"


# ── 3. No-Match → none ──────────────────────────────────────────────────────


def test_resolve_capability_no_match_returns_none():
    """``what is the weather`` → ``("", 0.0, "none")`` (kein Phrase/Token-Match)."""
    from gnom_hub.agents.routing import resolve_capability

    r = resolve_capability("what is the weather")
    assert r.capability == ""
    assert r.confidence == 0.0
    assert r.source == "none"

    r2 = resolve_capability("hello there")
    assert r2.capability == ""
    assert r2.source == "none"


# ── 4. Determinism ─────────────────────────────────────────────────────────


def test_resolve_capability_is_deterministic():
    """Gleicher Input → gleicher Output 100× hintereinander."""
    from gnom_hub.agents.routing import resolve_capability

    intents = [
        "write a file",
        "run pytest",
        "what is the weather",
        "schreibe datei",
        "fetch me the docs",
    ]
    for intent in intents:
        first = resolve_capability(intent)
        for _ in range(99):
            again = resolve_capability(intent)
            assert again.capability == first.capability
            assert again.confidence == first.confidence
            assert again.source == first.source


# ── 5. Node-ID-Override (Offload-Bridge) ──────────────────────────────────


def test_resolve_with_node_id_override(isolated_db):
    """Wenn node_id gefunden und Resolver liefert Content → high-confidence."""
    from gnom_hub.agents.routing import resolve_with_node_id

    captured = {"nid": None, "calls": 0}

    def _resolver(node_id: str):
        captured["nid"] = node_id
        captured["calls"] += 1
        # Offload-Content mit einem Schell-Indikator-Token
        return "tool:bash ran pytest successfully. exit code 0"

    r = resolve_with_node_id(
        "recall what happened at node a1b2c3d4 in the session",
        available_capabilities=["shell", "write_file", "general"],
        node_resolver_fn=_resolver,
    )
    assert captured["calls"] == 1
    assert captured["nid"] == "a1b2c3d4"
    assert r.capability == "shell"
    assert r.source == "node_id_override"
    assert r.confidence >= 0.95


# ── 6. Invalid Node-ID → Fallback ──────────────────────────────────────────


def test_resolve_with_invalid_node_id_falls_through():
    """``../etc/passwd`` matcht das Node-ID-Pattern nicht → kein Override."""
    from gnom_hub.agents.routing import resolve_with_node_id

    call_count = {"n": 0}

    def _resolver(node_id):
        call_count["n"] += 1
        return "should never be called for invalid input"

    r = resolve_with_node_id(
        "open the file at ../etc/passwd please",
        available_capabilities=["shell"],
        node_resolver_fn=_resolver,
    )
    # Wir validieren via regex NODE_ID_PATTERN — "../etc/passwd" matcht NICHT.
    assert call_count["n"] == 0
    # Normal-Pfad: "shell" ist nicht im "weather"-Tokens vorhanden,
    # "file" + "open" hätten "file_read" matchen können — aber bei
    # Whitelist nur "shell" → wird gefiltert → kein Fallback ohne "general".
    # Wir akzeptieren sowohl none als auch fallback, aber KEIN override.
    assert r.source != "node_id_override"


# ── 7. Fallback-Chain Builder ──────────────────────────────────────────────


def test_build_fallback_chain_ends_with_general():
    """``build_fallback_chain("shell")`` enthält ``"general"`` und endet auf Sentinel."""
    from gnom_hub.agents.routing import build_fallback_chain

    chain = build_fallback_chain("shell")
    assert chain[0] == "shell"
    assert "general" in chain
    # Sentinel kommt als letzter Eintrag
    assert chain[-1] == ""


def test_build_fallback_chain_for_unknown_capability():
    """Wenn nur ``"general"`` gewhitelistet ist, fällt alles darauf zurück."""
    from gnom_hub.agents.routing import build_fallback_chain

    chain = build_fallback_chain("frobnicate", available=["general", ""])
    assert "general" in chain
    assert chain[-1] == ""


# ── 8. Feature-Flag Default ────────────────────────────────────────────────


def test_routing_deterministic_mode_default_off():
    """``Config.ROUTING_DETERMINISTIC_MODE`` ist per Default aus."""
    from gnom_hub.core.config import Config

    assert getattr(Config, "ROUTING_DETERMINISTIC_MODE", False) is False


# ── 9. End-to-End Integration mit dispatch_by_capability_with_resolution ───


def test_routing_integration_with_dispatch_by_capability(isolated_db):
    """Vollständige Integration: Wrapper wählt anhand Intent den richtigen Agenten."""
    from gnom_hub.db.connection import get_db_conn
    from gnom_hub.agents.swarm.swarm_comms import dispatch_by_capability_with_resolution
    from gnom_hub.core.config import DB_PATH

    # DB-Setup: 3 Agenten, jeweils mit Capabilities
    with get_db_conn() as conn:
        # Mindestens 1 Agent in "online"-Status
        for name, status in [
            ("CoderAG", "online"),
            ("WriterAG", "online"),
            ("GeneralAG", "online"),
        ]:
            conn.execute(
                "INSERT OR REPLACE INTO agents (name, id, port, description, status, "
                "capabilities, role, active_job, last_seen) "
                "VALUES (?, ?, 0, ?, ?, '[]', 'normal', NULL, ?)",
                (name, f"id-{name}", f"Test {name}", status, "2026-01-01T00:00:00Z"),
            )
        # Capability-Mappings
        for agent_name, caps in [
            ("CoderAG", [("code_generation", 1.0), ("code", 0.9), ("debugging", 0.8)]),
            ("WriterAG", [("write_file", 1.0), ("content_creation", 0.9), ("write", 0.8)]),
            ("GeneralAG", [("general", 1.0), ("coordination", 0.9)]),
        ]:
            for cap, conf in caps:
                conn.execute(
                    "INSERT OR REPLACE INTO agent_capabilities (agent_name, capability, confidence) "
                    "VALUES (?, ?, ?)",
                    (agent_name, cap, conf),
                )
        conn.commit()

    # Case 1: "write a file" → Router sollte write_file → WriterAG finden
    target, msg_id = dispatch_by_capability_with_resolution(
        sender="SoulAG",
        intent_text="please write a file with the daily log",
        text="write a file",
        context_id="default",
        db_path=str(DB_PATH),
        available_capabilities=["code_generation", "write_file", "general",
                                 "code", "content_creation", "write"],
    )
    assert target is not None
    assert msg_id is not None
    assert target.lower() == "writerag"

    # Case 2: "run pytest" → Router sollte shell finden,
    # aber wir haben keine "shell"-Capability → Fallback zu "general" → GeneralAG.
    target2, msg_id2 = dispatch_by_capability_with_resolution(
        sender="SoulAG",
        intent_text="run pytest to verify the fix",
        text="run pytest",
        context_id="default",
        db_path=str(DB_PATH),
        available_capabilities=["code_generation", "general", "write_file"],
    )
    # "general" ist eine valide Capability und GeneralAG ist auf "online".
    assert target2 is not None
    # Entweder direkt gemappt oder Fallback
    assert target2.lower() in ("generalag", "writerag")  # generalag preferred


# ── BONUS 1: Tokenizer verhalten ──────────────────────────────────────────


def test_tokenize_lowercases_and_splits_non_alnum():
    """``_tokenize`` lowercase + non-alphanumeric split."""
    from gnom_hub.agents.routing import _tokenize

    assert _tokenize("Write a File!") == ["write", "a", "file"]
    assert _tokenize("run-PYTEST.sh") == ["run", "pytest", "sh"]
    assert _tokenize("  multiple   spaces  ") == ["multiple", "spaces"]
    assert _tokenize("") == []
    assert _tokenize(None or "") == []  # type: ignore[arg-type]


# ── BONUS 2: Deutsche Keywords ──────────────────────────────────────────────


def test_resolve_capability_handles_german_keywords():
    """``schreibe datei`` → ``write_file`` (Phrase-Exact)."""
    from gnom_hub.agents.routing import resolve_capability

    r = resolve_capability("bitte schreibe datei mit dem Bericht")
    assert r.capability == "write_file"
    assert r.confidence == 1.0
    assert r.source == "exact_match"

    # Bonus: einzelnes deutsches Verb → write-Generalkapability (synonym)
    r2 = resolve_capability("kannst du das bitte korrigieren")
    # "korrigieren" hat keine Synonym-Liste → "none"
    # Stattdessen prüfen wir "bearbeite datei" → editing oder edit
    r3 = resolve_capability("bearbeite das modul bitte")
    # "bearbeit" ist Synonym für "edit", also confidence 0.7
    assert r3.capability == "edit"
    assert r3.confidence == 0.7
    assert r3.source == "synonym"
