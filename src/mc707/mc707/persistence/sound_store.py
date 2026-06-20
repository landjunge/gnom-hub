"""Persistence for MC-707 Sounds.

Saves and loads :class:`Sound` instances to/from JSON files. The on-disk
format is the Pydantic ``model_dump_json()`` output — round-trip safe,
human-readable, and stable across Python versions.

DESIGN CHOICES
--------------
* Filesystem-only — no database. Each Sound becomes one ``.json`` file
  under the configured base directory. This makes the store trivially
  inspectable (``cat ~/.mc707/sounds/bass_01.json``) and easy to version
  (git, sync, etc.).
* Names are slugified — ``"My Bass #1!"`` becomes ``my_bass_1.json``.
  Collisions are avoided with a numeric suffix (``foo.json``,
  ``foo_1.json``, …).
* The store does **not** lock files — concurrent processes writing to
  the same directory may clobber each other. Out of scope for now.

EDUCATED GUESS MARKERS
----------------------
None — this module has no MC-707-specific knowledge beyond the Sound
schema. The Pydantic model owns the validation rules.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional, Union

from ..models.sound import Sound

logger = logging.getLogger(__name__)


_SLUG_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _slugify(name: str) -> str:
    """Convert a Sound name to a filesystem-safe slug.

    Strategy: replace any run of unsafe characters with a single
    underscore, strip leading/trailing punctuation, lowercase.
    Falls back to ``"sound"`` on empty results.
    """
    slug = _SLUG_RE.sub("_", name).strip("._-")
    return slug.lower() or "sound"


class SoundStore:
    """JSON file store for Sounds.

    Parameters
    ----------
    base_dir:
        Directory under which sounds are saved. Created on the first
        save if it does not yet exist.
    """

    def __init__(self, base_dir: Union[str, Path]) -> None:
        self._base = Path(base_dir)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def base_dir(self) -> Path:
        """The directory this store reads from and writes to."""
        return self._base

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list(self) -> list[str]:
        """Return all sound names (file stems) in the store, sorted."""
        if not self._base.exists():
            return []
        return sorted(p.stem for p in self._base.glob("*.json"))

    def exists(self, name: str) -> bool:
        """Return ``True`` if a sound with this name is on disk."""
        return (self._base / f"{_slugify(name)}.json").exists()

    # ------------------------------------------------------------------
    # Save / load
    # ------------------------------------------------------------------

    def save(self, sound: Sound, name: Optional[str] = None) -> Path:
        """Persist *sound* to ``base_dir/{slug}.json``.

        Parameters
        ----------
        sound:
            The Sound to persist.
        name:
            Optional override for the on-disk name. Defaults to
            ``sound.name``.

        Returns
        -------
        pathlib.Path
            The path that was written.

        Notes
        -----
        If the target file already exists, a numeric suffix is appended
        (``foo.json`` → ``foo_1.json``). The store never silently
        overwrites an existing sound.
        """
        self._base.mkdir(parents=True, exist_ok=True)
        stem = _slugify(name or sound.name)
        path = self._unique_path(stem)
        path.write_text(sound.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Saved sound %r → %s", sound.name, path)
        return path

    def load(self, name: str) -> Sound:
        """Load a Sound by name.

        Raises
        ------
        FileNotFoundError
            If no file with this slug exists under :attr:`base_dir`.
        ValueError
            If the file contents are not valid JSON or do not match
            the Sound schema.
        """
        path = self._base / f"{_slugify(name)}.json"
        if not path.exists():
            raise FileNotFoundError(f"No sound named {name!r} in {self._base}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return Sound.model_validate(data)

    def delete(self, name: str) -> bool:
        """Remove the file for *name*.

        Returns ``True`` if a file was deleted, ``False`` if no such
        sound existed.
        """
        path = self._base / f"{_slugify(name)}.json"
        if path.exists():
            path.unlink()
            logger.info("Deleted sound %r (%s)", name, path)
            return True
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _unique_path(self, stem: str) -> Path:
        """Return a path under :attr:`base_dir` that does not yet exist.

        Walks ``{stem}.json``, ``{stem}_1.json``, … until a free name
        is found.
        """
        candidate = self._base / f"{stem}.json"
        n = 1
        while candidate.exists():
            candidate = self._base / f"{stem}_{n}.json"
            n += 1
        return candidate


__all__ = ["SoundStore"]