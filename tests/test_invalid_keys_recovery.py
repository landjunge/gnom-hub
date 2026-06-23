"""Tests for desktop_syncer.reverify_invalid_keys().

Defense-in-Depth: `sync_desktop_keys()` liest nur aktive (nicht-auskommentierte)
Zeilen aus api_keys.txt. Sobald ein Key dort als `# UNGÜLTIG:` landet, wird er
nie wieder angefasst — auch wenn der Provider ihn inzwischen wieder akzeptiert.

`reverify_invalid_keys()` durchbricht diesen Stillstand:
1. Findet alle `# UNGÜLTIG:`-Zeilen
2. Verifiziert jeden gegen seinen Provider
3. Schreibt reaktivierte Keys zurück in den Active-Bereich
4. Triggert sync_desktop_keys damit die DB aktualisiert wird

Diese Tests prüfen genau das mit gemockten Provider-Endpoints.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest


# ─── Helpers ────────────────────────────────────────────────────────────────

def _write_keys_file(path: Path, lines: list[str]) -> None:
    """Write a fake api_keys.txt (no real keys involved)."""
    path.write_text("\n".join(lines) + "\n")


def _read_keys_file(path: Path) -> list[str]:
    return [l for l in path.read_text().splitlines() if l.strip()]


# ─── Core behavior ──────────────────────────────────────────────────────────

class TestReverifyInvalidKeys:
    """End-to-end test der Re-Verify-Logik mit gemockten Provider-Endpoints."""

    @pytest.mark.asyncio
    async def test_recovers_key_when_provider_now_accepts(self, tmp_path):
        """Wenn Provider jetzt 200 returnt → Key wird aus UNGÜLTIG rausgenommen."""
        from gnom_hub.infrastructure.llm import desktop_syncer

        keys_file = tmp_path / "api_keys.txt"
        _write_keys_file(keys_file, [
            "BraveSearch=BSA-fakekey123",
            "# UNGÜLTIG: MiniMax=sk-cp-fakekey-1234567890",
        ])

        # Mock: auto_detect_and_verify returns valid=True für unseren fake-Key
        mock_result = {
            "valid": True,
            "info": "OK",
            "caps": ["text", "vision", "image"],
            "provider": "minimax",
        }
        with patch.object(
            desktop_syncer, "auto_detect_and_verify",
            new=AsyncMock(return_value=mock_result),
        ), patch.object(
            desktop_syncer, "sync_desktop_keys",
            new=AsyncMock(return_value={}),
        ):
            r = await desktop_syncer.reverify_invalid_keys(
                desktop_path=keys_file, force=True,
            )

        assert r["checked"] == 1
        assert r["recovered"] == ["MiniMax"]
        assert r["still_invalid"] == []

        lines = _read_keys_file(keys_file)
        assert any(l.startswith("MiniMax=sk-cp-fakekey") for l in lines), (
            f"Recovered key not in active section: {lines}"
        )
        assert not any("MiniMax" in l and "UNGÜLTIG" in l for l in lines), (
            f"Key still marked UNGÜLTIG: {lines}"
        )

    @pytest.mark.asyncio
    async def test_leaves_key_invalid_when_provider_still_rejects(self, tmp_path):
        """Wenn Provider weiterhin failt → Zeile bleibt unverändert in UNGÜLTIG."""
        from gnom_hub.infrastructure.llm import desktop_syncer

        keys_file = tmp_path / "api_keys.txt"
        original_line = "# UNGÜLTIG: OpenRouter=sk-or-v1-deadbeef"
        _write_keys_file(keys_file, [original_line])

        mock_result = {"valid": False, "info": "401", "caps": [], "provider": "openrouter"}
        with patch.object(
            desktop_syncer, "auto_detect_and_verify",
            new=AsyncMock(return_value=mock_result),
        ):
            r = await desktop_syncer.reverify_invalid_keys(
                desktop_path=keys_file, force=True,
            )

        assert r["checked"] == 1
        assert r["recovered"] == []
        assert r["still_invalid"] == ["OpenRouter"]
        assert _read_keys_file(keys_file) == [original_line], (
            "File should be unchanged when no key recovered"
        )

    @pytest.mark.asyncio
    async def test_mixed_batch_partial_recovery(self, tmp_path):
        """Drei Keys: einer wird reaktiviert, einer bleibt, einer wird gerade geprüft."""
        from gnom_hub.infrastructure.llm import desktop_syncer

        keys_file = tmp_path / "api_keys.txt"
        _write_keys_file(keys_file, [
            "Brave=BSA-keep",
            "# UNGÜLTIG: GoodKey=sk-cp-recover-me",
            "# UNGÜLTIG: BadKey=sk-cp-still-broken",
            "# UNGÜLTIG: AnotherBad=sk-or-v1-no-way",
        ])

        # unterschiedliche Ergebnisse pro Key
        async def fake_verify(k, lbl):
            if "recover-me" in k:
                return {"valid": True, "info": "OK", "caps": ["text"], "provider": "minimax"}
            return {"valid": False, "info": "401", "caps": [], "provider": "openai"}

        with patch.object(
            desktop_syncer, "auto_detect_and_verify", side_effect=fake_verify,
        ), patch.object(
            desktop_syncer, "sync_desktop_keys", new=AsyncMock(return_value={}),
        ):
            r = await desktop_syncer.reverify_invalid_keys(
                desktop_path=keys_file, force=True,
            )

        assert r["checked"] == 3
        assert r["recovered"] == ["GoodKey"]
        assert set(r["still_invalid"]) == {"BadKey", "AnotherBad"}

        lines = _read_keys_file(keys_file)
        assert any(l.startswith("GoodKey=sk-cp-recover-me") for l in lines)
        assert any(l.startswith("# UNGÜLTIG: BadKey=") for l in lines)
        assert any(l.startswith("# UNGÜLTIG: AnotherBad=") for l in lines)

    @pytest.mark.asyncio
    async def test_no_invalid_keys_is_noop(self, tmp_path):
        """Datei ohne UNGÜLTIG-Zeilen → checked=0, kein File-Write."""
        from gnom_hub.infrastructure.llm import desktop_syncer

        keys_file = tmp_path / "api_keys.txt"
        active = ["Brave=BSA-keep", "MiniMax=sk-cp-already-active"]
        _write_keys_file(keys_file, active)

        with patch.object(
            desktop_syncer, "auto_detect_and_verify", new=AsyncMock(),
        ) as mock_verify:
            r = await desktop_syncer.reverify_invalid_keys(
                desktop_path=keys_file, force=True,
            )
            mock_verify.assert_not_called()

        assert r["checked"] == 0
        assert r["recovered"] == []
        assert _read_keys_file(keys_file) == active


# ─── Endpoint-Integration ───────────────────────────────────────────────────

class TestReverifyEndpoint:
    """`POST /api/llm/keys/reverify` muss force=True durchreichen."""

    @pytest.mark.asyncio
    async def test_endpoint_calls_force_true(self):
        """Der manuelle Endpoint darf den Throttle nicht respektieren.

        Wir mocken das Original-Modul `desktop_syncer`, weil der Endpoint die
        Funktion via `from ... import reverify_invalid_keys` lokal bindet —
        ein `patch.object(llm_keys, ...)` würde diese lokale Bindung nicht
        abfangen.
        """
        from gnom_hub.infrastructure.llm import desktop_syncer
        from gnom_hub.api.endpoints import llm_keys

        called_with_force = []

        async def fake_reverify(desktop_path=None, force=False):
            called_with_force.append(force)
            return {"checked": 0, "recovered": [], "still_invalid": [], "skipped": False}

        with patch.object(
            desktop_syncer, "reverify_invalid_keys", side_effect=fake_reverify,
        ):
            result = await llm_keys.reverify_keys()

        assert called_with_force == [True], (
            f"Endpoint should call with force=True, got {called_with_force}"
        )
        assert result["checked"] == 0


# ─── Background-Task-Integration ────────────────────────────────────────────

class TestReverifyBackgroundLoop:
    """Der Background-Loop in app.py darf nicht beim ersten Tick crashen."""

    @pytest.mark.asyncio
    async def test_loop_logs_recovery_and_survives_exceptions(self, tmp_path):
        """Loop-Worker: recovered wird geloggt, Exceptions werden geschluckt.

        Sequenz die wir simulieren:
          sleep(60)  → initial delay durchlassen
          verify()   → returns recovered (call #1) → log "Recovered 1 key(s)"
          sleep(1800) → durchlassen
          verify()   → raises RuntimeError (call #2) → geschluckt durch except
          sleep(1800) → cancel (Test-Ende, BEVOR call #3 startet)

        Was der Test garantiert:
          a) call #1 läuft und produziert ein "Recovered" Log
          b) call #2 wirft Exception, Loop überlebt (CancelledError kommt von sleep, nicht von Exception)
          c) CancelledError wird an Caller weitergereicht (sonst hängt der Test)
        """
        from gnom_hub.infrastructure.llm import desktop_syncer
        from gnom_hub.api.app import start_invalid_keys_reverifier

        call_count = 0

        async def fake_reverify(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"checked": 1, "recovered": ["MiniMax"], "still_invalid": []}
            if call_count == 2:
                raise RuntimeError("simulated transient network error")
            return {"checked": 0, "recovered": [], "still_invalid": []}

        sleep_count = 0

        async def fake_sleep(seconds):
            nonlocal sleep_count
            sleep_count += 1
            # Beim 3. main-loop sleep canceln (also nachdem Exception geschluckt wurde).
            # Initial-delay (sleep 1) + sleep nach call #1 (sleep 2) durchlassen.
            # sleep nach call #2 (sleep 3, nach Exception) → cancel.
            if sleep_count >= 3 and seconds >= 30 * 60:
                raise asyncio.CancelledError()
            return None

        with patch.object(
            desktop_syncer, "reverify_invalid_keys", side_effect=fake_reverify,
        ), patch.object(
            desktop_syncer.asyncio, "sleep", side_effect=fake_sleep,
        ):
            with pytest.raises(asyncio.CancelledError):
                await start_invalid_keys_reverifier()

        # Genau 2 calls: einer erfolgreich, einer mit Exception (geschluckt).
        # Wäre die Exception nicht geschluckt worden, wäre pytest.raises() mit
        # RuntimeError gefailt, nicht mit CancelledError.
        assert call_count == 2, (
            f"Expected 2 verify calls (1 success + 1 swallowed exception), got {call_count}"
        )
