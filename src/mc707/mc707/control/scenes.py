"""Scene controller for the MC-707.

A *scene* on the MC-707 is a snapshot of which clip is active per
track. Selecting a scene switches the entire row of clips at once.

The implementation here dispatches a Program Change on the dedicated
control channel (:attr:`SceneController.CONTROL_CHANNEL`). The exact
addressing on the real device (whether Program Change is the right
message type, or whether scene selection needs a SysEx DT1) is an
**educated guess** — see the ``TEMPLATE`` notes on each method.

TEMPLATE - NEEDS VERIFICATION
-----------------------------
The MC-707 MIDI implementation manual should be consulted before relying
on this path against real hardware. The constants below mark the
assumptions that are still unverified.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — type hint only
    from ..io.midi import MIDIIO

logger = logging.getLogger(__name__)


class SceneController:
    """High-level scene selection for the MC-707.

    Parameters
    ----------
    midi_io:
        A :class:`MIDIIO` instance used to dispatch messages.

    Attributes
    ----------
    CONTROL_CHANNEL:
        MIDI channel (1–16) reserved for control messages such as scene
        selection. 10 mirrors the GM drum channel convention used by
        many Roland grooveboxes.
    """

    # Roland groovebox convention: control / scene-select messages live
    # on MIDI channel 10. May need to be moved to a dedicated SysEx
    # address on the real MC-707.
    # TEMPLATE - NEEDS VERIFICATION
    CONTROL_CHANNEL = 10

    # Program Change value range covers the full 0–127 MIDI space.
    # The MC-707 may only expose a subset (e.g. 0–15) to the user; the
    # method-level validation in :meth:`select` reflects this.
    # TEMPLATE - NEEDS VERIFICATION
    MIN_SCENE = 0
    MAX_SCENE = 127

    def __init__(self, midi_io: "MIDIIO") -> None:
        self._midi = midi_io
        self._current: int = 0

    # ------------------------------------------------------------------
    # Scene selection
    # ------------------------------------------------------------------

    def select(self, scene: int) -> bool:
        """Select a scene by number.

        Parameters
        ----------
        scene:
            Scene index, ``0``–``127``. Values outside this range raise
            :class:`ValueError` so callers cannot silently pick a wrong
            scene.

        Returns
        -------
        bool
            ``True`` if the Program Change was dispatched successfully.

        Notes
        -----
        TEMPLATE - NEEDS VERIFICATION
        Dispatches ``Program Change`` on :attr:`CONTROL_CHANNEL`. The
        MC-707 may instead require a SysEx DT1 at the scene-select
        address. If hardware tests show the scene does not change,
        replace this with the appropriate SysEx frame.
        """
        if not isinstance(scene, int) or isinstance(scene, bool):
            raise ValueError(
                f"scene must be an int in 0..127, got {type(scene).__name__}"
            )
        if scene < self.MIN_SCENE or scene > self.MAX_SCENE:
            raise ValueError(
                f"scene must be between {self.MIN_SCENE} and "
                f"{self.MAX_SCENE} (inclusive), got {scene}"
            )

        self._current = scene
        ok = self._midi.send_program_change(self.CONTROL_CHANNEL, scene)
        if not ok:
            logger.warning("Failed to send Program Change for scene %d.", scene)
        return ok

    def next(self) -> bool:
        """Advance to the next scene (clamped at 127).

        Returns
        -------
        bool
            ``True`` if the Program Change was dispatched successfully.
        """
        self._current = min(self._current + 1, self.MAX_SCENE)
        return self.select(self._current)

    def previous(self) -> bool:
        """Go back to the previous scene (clamped at 0).

        Returns
        -------
        bool
            ``True`` if the Program Change was dispatched successfully.
        """
        self._current = max(self._current - 1, self.MIN_SCENE)
        return self.select(self._current)

    def current(self) -> int:
        """Return the currently selected scene number."""
        return self._current
