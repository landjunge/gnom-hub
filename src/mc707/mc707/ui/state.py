"""Backend state — Singleton-Holder für die MC707-Instanz + Caches.

Dieses Modul stellt die FastAPI-Dependency :func:`get_state` bereit, die
in jeder Route verwendet wird, um auf den gemeinsamen Backend-State
zuzugreifen. Der State ist ein Prozess-Singleton — alle HTTP-Requests
und WebSocket-Clients teilen sich denselben MC707-Controller und
denselben Sound-Cache.

DESIGNENTSCHEIDUNGEN
--------------------

* **State im Backend, nicht im Agent.** Der MC707-Controller ist
  Source-of-Truth. Agent (Track 4+) ist nur ein Subscriber, der über
  WebSocket mitlauscht.
* **Mock-Modus by default.** Wenn keine echte MC-707 angeschlossen ist
  (oder ``mock=True`` gesetzt), läuft alles gegen den Mock-Backend mit
  In-Memory-Log.
* **Sound-Registry ist prozessglobal.** Tracks alle Sounds, die via
  API geladen/erstellt wurden, damit sie für die UI ohne Disk-Roundtrip
  verfügbar sind.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from fastapi import Depends

from .. import MC707
from .events import EventBus

logger = logging.getLogger(__name__)


class BackendState:
    """Prozess-globaler State für die WebUI.

    Attributes
    ----------
    mc707:
        Die :class:`MC707`-Instanz. Hält alle Controller und den MIDI-I/O.
    bus:
        :class:`EventBus` für WebSocket-Broadcasting.
    """

    def __init__(
        self,
        port_name: Optional[str] = None,
        device_id: int = 0x00,
        mock: bool = True,
        sound_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.mc707 = MC707(
            port_name=port_name,
            device_id=device_id,
            mock=mock,
            sound_dir=sound_dir,
        )
        self.bus = EventBus()
        logger.info(
            "BackendState initialised: mock=%s port=%s sound_dir=%s",
            mock,
            port_name,
            sound_dir,
        )

    @property
    def is_mock(self) -> bool:
        """``True`` if the underlying MC707 is running in mock mode."""
        return self.mc707.is_mock

    @property
    def sound_registry(self):
        """Convenience accessor for the SoundRegistry."""
        return self.mc707.sound_registry

    @property
    def sound_store(self):
        """Convenience accessor for the SoundStore."""
        return self.mc707.sound_store

    @property
    def sound_editor(self):
        """Convenience accessor for the SoundEditor."""
        return self.mc707.sound_editor

    def close(self) -> None:
        """Cleanly shut down: close the MIDI port."""
        self.mc707.close()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

_state: Optional[BackendState] = None


def init_state(**kwargs) -> BackendState:
    """Create and install the global BackendState.

    Idempotent — calling twice returns the existing instance unless
    ``force=True`` is passed.
    """
    global _state
    if _state is None:
        _state = BackendState(**kwargs)
    return _state


def get_state() -> BackendState:
    """FastAPI dependency — returns the global BackendState.

    Raises
    ------
    RuntimeError
        If :func:`init_state` was never called. (In practice the app
        factory calls :func:`init_state` during startup, so this only
        fires in tests that forget to wire it up.)
    """
    if _state is None:
        raise RuntimeError(
            "BackendState not initialised — call mc707.ui.state.init_state() "
            "first or use create_app() which wires it up automatically."
        )
    return _state


def reset_state() -> None:
    """Clear the global state (test helper)."""
    global _state
    if _state is not None:
        _state.close()
    _state = None