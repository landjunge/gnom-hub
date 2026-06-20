"""HTTP routes — one router per MC-707 controller.

Each router is a thin wrapper around the underlying controller methods
on the :class:`MC707` façade. Routes never construct the MC707
themselves; they take it from :func:`mc707.ui.state.get_state`.

Every state-changing route publishes an event on the EventBus after
the controller call so WebSocket subscribers see the change.
"""

from . import (
    arpeggiator,
    clips,
    effects,
    patterns,
    scenes,
    sounds,
    state,
    status,
    sysex,
    transport,
)

ALL_ROUTERS = [
    transport.router,
    scenes.router,
    clips.router,
    sounds.router,
    effects.router,
    arpeggiator.router,
    patterns.router,
    status.router,
    sysex.router,
    state.router,
]

__all__ = ["ALL_ROUTERS"]