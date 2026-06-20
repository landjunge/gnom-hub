"""In-memory registry for named MC-707 Sounds.

A lightweight cache mapping sound names to :class:`Sound` instances
during a session. Persistence is delegated to :class:`SoundStore`.

Use this for:
  * "What sounds are loaded right now?" — :meth:`list`
  * "Pull up the current lead tone by name" — :meth:`get` / ``in``
  * Quick UI state — e.g. a dropdown of currently-loaded sounds

Use :class:`SoundStore` when the lifetime needs to outlive a process.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from ..models.sound import Sound

logger = logging.getLogger(__name__)


class SoundRegistry:
    """In-memory named-sound cache.

    Keys are unique by ``Sound.name``. Re-registering an existing name
    overwrites the previous entry.
    """

    def __init__(self) -> None:
        self._sounds: Dict[str, Sound] = {}

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def register(self, sound: Sound) -> None:
        """Add or replace a Sound by name."""
        self._sounds[sound.name] = sound
        logger.debug("Registered sound %r", sound.name)

    def remove(self, name: str) -> bool:
        """Remove a sound by name. Returns ``True`` if it existed."""
        existed = self._sounds.pop(name, None) is not None
        if existed:
            logger.debug("Removed sound %r", name)
        return existed

    def clear(self) -> None:
        """Drop all entries."""
        self._sounds.clear()

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[Sound]:
        """Return the sound with this name, or ``None`` if absent."""
        return self._sounds.get(name)

    def require(self, name: str) -> Sound:
        """Return the sound with this name, or raise ``KeyError``."""
        if name not in self._sounds:
            raise KeyError(f"Sound {name!r} not in registry")
        return self._sounds[name]

    def list(self) -> list[str]:
        """Return all registered names, sorted alphabetically."""
        return sorted(self._sounds.keys())

    def all(self) -> list[Sound]:
        """Return all registered sounds (sorted by name)."""
        return [self._sounds[name] for name in self.list()]

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._sounds)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._sounds

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.list())

    def __repr__(self) -> str:
        return f"<SoundRegistry size={len(self._sounds)}>"


__all__ = ["SoundRegistry"]