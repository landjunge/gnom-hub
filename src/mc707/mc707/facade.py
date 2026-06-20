"""Main MC-707 controller class.

Bundles the high-level controllers (transport, scenes, clips, sounds,
patterns, effects, arpeggiator) and the SysEx/status helpers behind a
single façade. This is the entry point most callers will use.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from .control.arpeggiator import ArpeggiatorController
from .control.clips import ClipController
from .control.effects import EffectsController
from .io.midi import MIDIIO
from .control.patterns import PatternController
from .control.scenes import SceneController
from .control.sound_editor import SoundEditor
from .registry.sound_registry import SoundRegistry
from .persistence.sound_store import SoundStore
from .control.sounds import SoundController
from .control.status import StatusController
from .io.sysex import SysExController
from .control.transport import TransportController

logger = logging.getLogger(__name__)

_DEFAULT_SOUND_DIR = Path.home() / ".mc707" / "sounds"


class MC707:
    """Top-level façade for the Roland MC-707 groovebox.

    Parameters
    ----------
    port_name:
        Name of the MIDI output port. If ``None`` (or the port is not
        available) the controller falls back to mock mode.
    device_id:
        Roland device ID (0x00–0x0F) used in SysEx frames.
    mock:
        Force mock mode. Default ``True`` so the library is usable
        out-of-the-box without hardware. Set to ``False`` to attempt a
        real port open.
    sound_dir:
        Filesystem directory for :class:`SoundStore`. Defaults to
        ``~/.mc707/sounds``. Pass an explicit path to redirect sounds
        to a project-local or test directory.

    Attributes
    ----------
    transport:
        :class:`TransportController` — play / stop / record / tempo.
    scenes:
        :class:`SceneController` — scene selection.
    clips:
        :class:`ClipController` — clip triggering, track mute / solo /
        volume / pan.
    sounds:
        :class:`SoundController` — tone / drum-kit / instrument loaders.
    sound_editor:
        :class:`SoundEditor` — live Tone parameter editing via SysEx
        DT1. Owns a cache of the most-recently-written values.
    sound_registry:
        :class:`SoundRegistry` — in-memory named cache of Sound
        instances for the current session.
    sound_store:
        :class:`SoundStore` — JSON persistence for Sounds on disk.
    patterns:
        :class:`PatternController` — step sequencer programming.
    effects:
        :class:`EffectsController` — filter, envelope, master sends,
        MFX slot parameters.
    arpeggiator:
        :class:`ArpeggiatorController` — arp on/off and parameters.
    sysex:
        :class:`SysExController` — low-level SysEx DT1 / RQ1.
    status:
        :class:`StatusController` — cached state read-backs.
    """

    def __init__(
        self,
        port_name: Optional[str] = None,
        device_id: int = 0x00,
        mock: bool = True,
        sound_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self._midi = MIDIIO(port_name=port_name, mock=mock)
        self._device_id = max(0, min(15, device_id))

        # High-level controllers.
        self.transport = TransportController(self._midi)
        self.scenes = SceneController(self._midi)
        self.clips = ClipController(self._midi)
        self.sounds = SoundController(self._midi)
        self.patterns = PatternController(self._midi)
        self.effects = EffectsController(self._midi)
        self.arpeggiator = ArpeggiatorController(self._midi)

        # SysEx and status use the device_id too.
        self.sysex = SysExController(self._midi, device_id=self._device_id)
        self.status = StatusController(self._midi, device_id=self._device_id)

        # Sound definition / editing / persistence.
        self.sound_editor = SoundEditor(self.sysex)
        self.sound_registry = SoundRegistry()
        self.sound_store = SoundStore(
            Path(sound_dir) if sound_dir is not None else _DEFAULT_SOUND_DIR
        )

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    def play(self) -> bool:
        """Start the sequencer (delegates to :attr:`transport`)."""
        return self.transport.play()

    def stop(self) -> bool:
        """Stop the sequencer (delegates to :attr:`transport`)."""
        return self.transport.stop()

    def close(self) -> None:
        """Close the underlying MIDI port. Safe to call multiple times."""
        self._midi.close()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def midi(self) -> MIDIIO:
        """The underlying :class:`MIDIIO` instance (escape hatch)."""
        return self._midi

    @property
    def is_mock(self) -> bool:
        """``True`` if the controller is running in mock mode."""
        return self._midi.is_mock()

    def __repr__(self) -> str:
        mode = "mock" if self.is_mock else "hardware"
        return (
            f"<MC707 device_id=0x{self._device_id:02X} mode={mode} "
            f"port={self._midi._requested_port!r}>"
        )

    def __enter__(self) -> "MC707":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
