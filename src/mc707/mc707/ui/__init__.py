"""mc707 Web-UI — FastAPI-Backend für die Roland MC-707.

Standalone lauffähiges Web-Backend, das die :mod:`mc707` Controller über
HTTP + WebSocket exponiert. Funktioniert ohne KI / Agent — der gesamte
State lebt im Backend (in-memory + optional Disk-Persistenz via
:class:`mc707.persistence.sound_store.SoundStore`).

Starten::

    # Standalone (Mock-Modus)
    python -m mc707.ui

    # Mit echter Hardware
    python -m mc707.ui --port-name "MC-707 MIDI OUT"

    # Via uvicorn direkt
    uvicorn mc707.ui.app:app --host 0.0.0.0 --port 8765

Die WebSocket-Schnittstelle (``/ws``) ist für den späteren
Agent-Overlay-Layer (Track 4) gedacht — der Server publisht
State-Change-Events, Clients (UI, Agent) können subscriben.

ARCHITEKTUR
-----------

* :class:`mc707.ui.state.BackendState` hält die MC707-Instanz + Caches.
* Routes in :mod:`mc707.ui.routes` sind dünne Wrapper um die Controller.
* :class:`mc707.ui.events.EventBus` broadcasted State-Changes an alle
  WebSocket-Subscriber.
* State lebt im Backend, NICHT im Agent — Agent ist nur ein Subscriber.
"""

__version__ = "0.1.0"

from .app import create_app  # noqa: E402  (must come after __version__)

__all__ = ["create_app"]