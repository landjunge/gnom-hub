"""EventBus — lightweight in-process pub/sub for WebSocket broadcasting.

Routes call :meth:`EventBus.publish` after state-changing operations;
each connected WebSocket subscriber receives a copy of every event
through its own asyncio.Queue.

DESIGN
------
* **In-process only.** No cross-process pub/sub — the backend is a
  single uvicorn process. For horizontal scaling, swap this for Redis
  pub/sub or similar.
* **No filtering by default.** Every subscriber gets every event.
  Per-subscriber filtering is the client's job (it ignores events it
  doesn't care about). This keeps the server simple and pushes the
  policy to the edges.
* **Bounded queues.** A slow subscriber doesn't grow memory without
  bound — overflowing events are dropped with a warning.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# Event type catalogue — kept as constants so callers don't fat-finger
# the strings.
EVT_PARAM_CHANGED = "param_changed"
EVT_TRANSPORT_CHANGED = "transport_changed"
EVT_SCENE_CHANGED = "scene_changed"
EVT_CLIP_TRIGGERED = "clip_triggered"
EVT_SOUND_REGISTERED = "sound_registered"
EVT_SOUND_REMOVED = "sound_removed"
EVT_SOUND_SAVED = "sound_saved"
EVT_SOUND_LOADED = "sound_loaded"
EVT_STATE_RESET = "state_reset"


class EventBus:
    """In-process pub/sub for WebSocket clients."""

    QUEUE_MAX_SIZE = 256

    def __init__(self) -> None:
        self._subscribers: List[asyncio.Queue] = []

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(self) -> asyncio.Queue:
        """Register a new subscriber; returns its event queue.

        The caller is responsible for draining the queue (typically
        inside the WebSocket receive loop) and calling
        :meth:`unsubscribe` when the connection drops.
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=self.QUEUE_MAX_SIZE)
        self._subscribers.append(q)
        logger.debug("New subscriber (total=%d)", len(self._subscribers))
        return q

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber and discard its queue."""
        try:
            self._subscribers.remove(queue)
            logger.debug("Subscriber removed (total=%d)", len(self._subscribers))
        except ValueError:
            pass

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish(self, event_type: str, **data: Any) -> None:
        """Broadcast an event to all current subscribers.

        ``data`` becomes the ``data`` field of the :class:`WsEvent`
        payload. If a subscriber's queue is full, the event is dropped
        for that subscriber (with a warning) — slow consumers must not
        block the publishing thread.
        """
        event: Dict[str, Any] = {"type": event_type, "data": data}
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Subscriber queue full — dropping event %s", event_type
                )


__all__ = [
    "EVT_CLIP_TRIGGERED",
    "EVT_PARAM_CHANGED",
    "EVT_SCENE_CHANGED",
    "EVT_SOUND_LOADED",
    "EVT_SOUND_REGISTERED",
    "EVT_SOUND_REMOVED",
    "EVT_SOUND_SAVED",
    "EVT_STATE_RESET",
    "EVT_TRANSPORT_CHANGED",
    "EventBus",
]