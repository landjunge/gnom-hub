"""WebSocket endpoint for live state-change broadcasts.

Clients connect to ``/ws`` and receive every event published on the
:class:`EventBus`. The current protocol is firehose-style — every
subscriber gets every event. Per-client filtering is the client's job
(it just ignores events it doesn't care about).

Wire format (JSON, one message per line):

    Server → Client:  {"type": "param_changed", "data": {...}}
    Client → Server:  {"action": "subscribe", "events": ["param_changed"]}
                      {"action": "unsubscribe", "events": [...]}
                      {"action": "ping"}

The ``subscribe``/``unsubscribe`` actions are accepted today but the
server still fires every event — they're a forward-compat hook so
clients can declare intent now without breaking when per-subscriber
filtering is added.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .state import get_state

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Bidirectional WebSocket channel."""
    await websocket.accept()
    state = get_state()
    queue = state.bus.subscribe()
    subscriptions: Set[str] = set()

    async def sender() -> None:
        """Forward events from the bus to the WebSocket."""
        try:
            while True:
                event = await queue.get()
                await websocket.send_text(json.dumps(event))
        except WebSocketDisconnect:
            logger.debug("WebSocket sender: client disconnected")
        except Exception as exc:  # noqa: BLE001
            logger.warning("WebSocket sender error: %s", exc)

    async def receiver() -> None:
        """Receive client messages (subscribe / ping / etc.)."""
        nonlocal subscriptions
        try:
            while True:
                msg = await websocket.receive_text()
                try:
                    payload = json.loads(msg)
                except json.JSONDecodeError:
                    logger.warning("WebSocket: ignoring non-JSON message")
                    continue

                action = payload.get("action")
                if action == "ping":
                    await websocket.send_text(
                        json.dumps({"type": "pong", "data": {}})
                    )
                elif action == "subscribe":
                    events = payload.get("events") or []
                    if isinstance(events, list):
                        subscriptions.update(str(e) for e in events)
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "subscribed",
                                "data": {"events": sorted(subscriptions)},
                            }
                        )
                    )
                elif action == "unsubscribe":
                    events = payload.get("events") or []
                    if isinstance(events, list):
                        subscriptions.difference_update(str(e) for e in events)
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "unsubscribed",
                                "data": {"events": sorted(subscriptions)},
                            }
                        )
                    )
                else:
                    logger.debug("WebSocket: unknown action %r", action)
        except WebSocketDisconnect:
            logger.debug("WebSocket receiver: client disconnected")
        except Exception as exc:  # noqa: BLE001
            logger.warning("WebSocket receiver error: %s", exc)

    sender_task = asyncio.create_task(sender())
    receiver_task = asyncio.create_task(receiver())

    try:
        done, pending = await asyncio.wait(
            {sender_task, receiver_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        state.bus.unsubscribe(queue)
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass