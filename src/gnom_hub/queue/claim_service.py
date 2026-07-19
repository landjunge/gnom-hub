"""Hub-side claim/ack/nack — single process writes SQLite for leases."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("gnom_hub.queue.claim")


def claim_next(agent_name: str, timeout: float = 0.5) -> dict[str, Any] | None:
    from gnom_hub.agents.swarm.swarm_comms import fetch_next_message
    from gnom_hub.core.config import DB_PATH

    try:
        t = max(0.05, min(float(timeout), 2.0))
        return fetch_next_message(agent_name, str(DB_PATH), timeout=t)
    except Exception as e:
        logger.warning("claim_next %s: %s", agent_name, e)
        return None


def ack(msg_id: int) -> None:
    from gnom_hub.agents.swarm.swarm_comms import ack_message
    from gnom_hub.core.config import DB_PATH

    ack_message(int(msg_id), str(DB_PATH))


def nack(msg_id: int, reason: str = "") -> None:
    from gnom_hub.agents.swarm.swarm_comms import nack_message
    from gnom_hub.core.config import DB_PATH

    nack_message(int(msg_id), str(DB_PATH), reason or "")
