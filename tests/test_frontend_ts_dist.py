"""S5: committed TypeScript frontend bundle must stay present and coherent."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "src" / "gnom_hub" / "frontend" / "gnom-ts.js"
INDEX = ROOT / "src" / "gnom_hub" / "frontend" / "index.html"
CORE = ROOT / "src" / "gnom_hub" / "frontend" / "core.js"


def test_gnom_ts_bundle_exists_and_exports():
    assert BUNDLE.is_file(), "gnom-ts.js missing — run scripts/build_frontend_ts.sh"
    text = BUNDLE.read_text(encoding="utf-8")
    assert len(text) > 500
    # IIFE / global surface
    assert "GnomTS" in text
    assert "agentColor" in text
    assert "extractMentions" in text
    assert "createApiClient" in text
    assert "FROZEN_AGENTS" in text
    # Slice-2 surface
    assert "apiRequest" in text
    assert "discoverApiBase" in text
    assert "formatStatsPanel" in text
    assert "escapeHtml" in text
    assert "safeJsonParse" in text
    # Slice-3 chat
    assert "pushChatHistory" in text
    assert "navigateChatHistory" in text
    assert "classifyLocalCommand" in text
    assert "formatChatResponseToast" in text
    assert "prepareOutgoingChat" in text
    assert "extractThoughtsAndClean" in text
    # Known palette parity with core.js
    assert "#FF0000" in text  # CoderAG
    assert "#FF5E00" in text  # SoulAG


def test_index_loads_gnom_ts_before_core():
    html = INDEX.read_text(encoding="utf-8")
    i_ts = html.find("gnom-ts.js")
    i_core = html.find("core.js")
    assert i_ts >= 0, "index.html must load gnom-ts.js"
    assert i_core >= 0
    assert i_ts < i_core, "gnom-ts.js must load before core.js"


def test_core_prefers_gnom_ts_agent_color():
    core = CORE.read_text(encoding="utf-8")
    assert "GnomTS" in core
    assert re.search(r"GnomTS\.agentColor", core)
    assert re.search(r"GnomTS\.apiRequest", core)
    assert re.search(r"GnomTS\.discoverApiBase", core)
    assert re.search(r"GnomTS\.formatStatsPanel", core)
    assert re.search(r"GnomTS\.escapeHtml", core)


def test_chat_js_wires_gnom_ts_chat_helpers():
    chat = (ROOT / "src" / "gnom_hub" / "frontend" / "chat.js").read_text(encoding="utf-8")
    assert "classifyLocalCommand" in chat
    assert "prepareOutgoingChat" in chat
    assert "formatChatResponseToast" in chat
    assert "pushChatHistory" in chat
    assert "navigateChatHistory" in chat
    assert "extractThoughtsAndClean" in chat


def test_ts_source_tree_present():
    ts_root = ROOT / "src" / "gnom_hub" / "frontend" / "ts"
    assert (ts_root / "package.json").is_file()
    assert (ts_root / "src" / "index.ts").is_file()
    assert (ts_root / "src" / "agents.ts").is_file()
    assert (ts_root / "src" / "api.ts").is_file()
    assert (ts_root / "src" / "chat_mentions.ts").is_file()
    assert (ts_root / "src" / "stats.ts").is_file()
    assert (ts_root / "src" / "security.ts").is_file()
    assert (ts_root / "src" / "chat_history.ts").is_file()
    assert (ts_root / "src" / "chat_commands.ts").is_file()
    assert (ts_root / "src" / "chat_response.ts").is_file()
    assert (ts_root / "src" / "chat_content.ts").is_file()
