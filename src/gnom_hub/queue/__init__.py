"""Queue helpers (stability plan S2).

Default: agents claim jobs via Hub HTTP so only the hub process holds
SQLite write locks for claim/ack. No Docker, no external broker.

``GNOM_QUEUE_MODE``:
  - ``hub`` (default) — agents use /api/queue/claim|ack|nack
  - ``sqlite`` — legacy direct BEGIN IMMEDIATE in agent process
"""

from __future__ import annotations

import os

_MODE = os.environ.get("GNOM_QUEUE_MODE", "hub").strip().lower()


def queue_mode() -> str:
    return _MODE if _MODE in ("hub", "sqlite") else "hub"


def use_hub_claim() -> bool:
    return queue_mode() == "hub"
