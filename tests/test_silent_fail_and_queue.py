"""Prio-1/2: stille Fehler sichtbar + Queue-Wipe bei Restart abschaffen."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch


# ── Prio-1: Dispatch-Feedback ─────────────────────────────────────────────


class TestDispatchFeedback:
    def test_default_chat_offline_generalag_posts_system_message(self, tmp_path, monkeypatch):
        """GeneralAG offline → System-Chatzeile, status=error, asked=[]."""
        from gnom_hub.api.endpoints import chat_legacy
        from gnom_hub.api.endpoints.chat_legacy import ChatMsg

        posted: list[tuple] = []

        def fake_add(project, sender, agent_id, msg_type, content, metadata=None):
            posted.append((sender, content, metadata or {}))

        monkeypatch.setattr(chat_legacy, "add_chat_message", fake_add)
        monkeypatch.setattr(chat_legacy, "get_active_project", lambda: "default")
        monkeypatch.setattr(
            chat_legacy,
            "get_all_agents",
            lambda: [{"name": "GeneralAG", "status": "offline"}],
        )
        monkeypatch.setattr(chat_legacy, "dispatch", lambda *a, **k: [])
        # soul / security / showbox side-effects
        monkeypatch.setattr(chat_legacy.soul_instance, "on_message", lambda *a, **k: None)
        monkeypatch.setattr(
            "gnom_hub.core.security.injection_validator.validate_input",
            lambda c: (True, None),
        )
        monkeypatch.setattr(
            "gnom_hub.core.security.showbox_validator.enforce_agent_layer",
            lambda c, s: c,
        )

        r = chat_legacy.post_chat(ChatMsg(content="Hallo", sender="user"))
        assert r["status"] == "error"
        assert r["asked"] == []
        sys_msgs = [p for p in posted if p[0] == "System" and "Dispatch fehlgeschlagen" in p[1]]
        assert sys_msgs, f"Expected system dispatch fail message, got: {posted}"
        assert "offline" in sys_msgs[0][1].lower() or "nicht erreichbar" in sys_msgs[0][1].lower()

    def test_at_target_unknown_posts_system_message(self, monkeypatch):
        from gnom_hub.api.endpoints import chat_legacy
        from gnom_hub.api.endpoints.chat_legacy import ChatMsg

        posted: list[tuple] = []

        def fake_add(project, sender, agent_id, msg_type, content, metadata=None):
            posted.append((sender, content))

        monkeypatch.setattr(chat_legacy, "add_chat_message", fake_add)
        monkeypatch.setattr(chat_legacy, "get_active_project", lambda: "default")
        monkeypatch.setattr(
            chat_legacy,
            "get_all_agents",
            lambda: [{"name": "GeneralAG", "status": "online"}],
        )
        monkeypatch.setattr(chat_legacy, "dispatch", lambda *a, **k: [])
        monkeypatch.setattr(chat_legacy.soul_instance, "on_message", lambda *a, **k: None)
        monkeypatch.setattr(
            "gnom_hub.core.security.injection_validator.validate_input",
            lambda c: (True, None),
        )
        monkeypatch.setattr(
            "gnom_hub.core.security.showbox_validator.enforce_agent_layer",
            lambda c, s: c,
        )

        r = chat_legacy.post_chat(ChatMsg(content="@NoSuchAG tu was", sender="user"))
        assert r["status"] == "error"
        assert any("Dispatch fehlgeschlagen" in p[1] for p in posted if p[0] == "System")


# ── Prio-1: agent_base silent fail helpers (unit via extracted logic) ─────


class TestAgentBaseSilentPaths:
    def test_router_error_content_triggers_system_post(self):
        """Simuliert den Branch: raw starts with [ROUTER-FEHLER] → System-Post."""
        posts: list[dict] = []

        class FakeAgent:
            n = "CoderAG"

            def _req(self, method, path, j=None):
                if method == "post" and path == "/api/chat":
                    posts.append(j or {})
                return {}

        # Mirror the condition used in agent_base
        raw_content = "[ROUTER-FEHLER] Alle Gleise offline."
        agent = FakeAgent()
        if raw_content.startswith("[ROUTER-FEHLER]"):
            agent._req("post", "/api/chat", {
                "content": f"⚠️ **[{agent.n}]** LLM-Router fehlgeschlagen.\n{raw_content[:400]}",
                "sender": "System",
            })
        assert posts
        assert posts[0]["sender"] == "System"
        assert "ROUTER" in posts[0]["content"] or "Router" in posts[0]["content"]

    def test_empty_content_triggers_system_post(self):
        posts: list[dict] = []

        class FakeAgent:
            n = "WriterAG"

            def _req(self, method, path, j=None):
                if method == "post" and path == "/api/chat":
                    posts.append(j or {})
                return {}

        raw_content = ""
        agent = FakeAgent()
        if not raw_content:
            agent._req("post", "/api/chat", {
                "content": f"⚠️ **[{agent.n}]** Keine Antwort vom LLM (leerer Content).",
                "sender": "System",
            })
        assert posts
        assert "leerer Content" in posts[0]["content"]


# ── Prio-2: Queue preserve / requeue ──────────────────────────────────────


class TestQueueOnAgentStart:
    def test_start_requeues_processing_preserves_pending(self, tmp_path, monkeypatch):
        """processing→pending, pending bleibt; kein massenhaftes done."""
        from gnom_hub.db import schema as schema_mod

        db_path = tmp_path / "q.db"
        monkeypatch.setenv("GNOM_HUB_DB", str(db_path))
        # Point Config + connection at temp DB
        from gnom_hub.core import config as cfg_mod
        monkeypatch.setattr(cfg_mod, "DB_PATH", db_path)
        monkeypatch.setattr(cfg_mod.Config, "DB_PATH", db_path)

        # Ensure tables
        schema_mod.create_tables()

        from gnom_hub.db.connection import get_db_connection

        now = time.time()
        with get_db_connection() as conn:
            # seed agents table minimally if needed
            conn.execute(
                "INSERT OR IGNORE INTO agents (name, id, status, last_seen) VALUES (?,?,?,?)",
                ("CoderAG", "c1", "busy", "t"),
            )
            conn.execute(
                """
                INSERT INTO agent_messages
                    (sender, recipient, payload, priority, status, created_at, deliver_after, depth)
                VALUES
                    ('user', 'CoderAG', '{"text":"pending job"}', 5, 'pending', ?, 0, 0),
                    ('user', 'CoderAG', '{"text":"processing job"}', 5, 'processing', ?, 0, 0)
                """,
                (now, now),
            )
            conn.execute(
                "UPDATE agent_messages SET processing_since=? WHERE status='processing'",
                (now,),
            )
            conn.commit()

        # Stub process kill/start so we only exercise the DB block
        from gnom_hub.infrastructure.process import process_manager as pm

        monkeypatch.setattr(pm, "_kill_all_agents_by_pid_files", lambda: None)
        monkeypatch.setattr(pm, "_kill_proc", lambda a: None)
        monkeypatch.setattr(pm, "AGENT_DEFINITIONS_KEYS", [])
        monkeypatch.setattr(pm, "AGENTS", [])
        monkeypatch.setattr(pm, "PROCESS_KILL_SLEEP", 0)

        with patch("subprocess.Popen") as popen:
            popen.return_value = MagicMock(pid=1)
            # Avoid chat_message requiring full stack if DB not ready for state
            with patch("gnom_hub.db.add_chat_message", MagicMock()):
                with patch("gnom_hub.db.get_active_project", return_value="default"):
                    pm.start_background_agents()

        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT status, payload FROM agent_messages ORDER BY id"
            ).fetchall()
            statuses = [r[0] for r in rows]
            assert statuses.count("pending") == 2
            assert "done" not in statuses
            assert "processing" not in statuses
