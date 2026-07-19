"""OpenRouter free-model rotation + short cooldown after failures.

When a free model returns 429/404/empty, the main router should try the next
free slug automatically. Cooldown avoids hammering a known-bad model for a
short window while still allowing eventual retry.
"""
from __future__ import annotations

import logging
import time

from gnom_hub.core.config import Config

log = logging.getLogger(__name__)

# Seconds a failed free model is deprioritized (still tried last if nothing else works).
FREE_FAIL_COOLDOWN_S = 120.0
_STATE_FAILED = "openrouter_failed_models"
_STATE_WORKING = "openrouter_working_models"


def _repo():
    from gnom_hub.db.state_repo import SQLiteStateRepository
    return SQLiteStateRepository()


def _read_failed(repo=None) -> dict[str, float]:
    repo = repo or _repo()
    raw = repo.get_value(_STATE_FAILED) or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    now = time.time()
    for k, v in raw.items():
        try:
            ts = float(v)
        except (TypeError, ValueError):
            continue
        if now - ts < FREE_FAIL_COOLDOWN_S * 4:  # keep a bit of history
            out[str(k)] = ts
    return out


def is_model_cooled_down(model: str, now: float | None = None, repo=None) -> bool:
    """True if model failed recently and should not be preferred."""
    now = now if now is not None else time.time()
    failed = _read_failed(repo)
    ts = failed.get(model)
    if ts is None:
        return False
    return (now - ts) < FREE_FAIL_COOLDOWN_S


def mark_model_failed(model: str, repo=None) -> None:
    if not model:
        return
    repo = repo or _repo()
    failed = _read_failed(repo)
    failed[model] = time.time()
    # prune very old
    cutoff = time.time() - FREE_FAIL_COOLDOWN_S * 4
    failed = {k: v for k, v in failed.items() if v >= cutoff}
    try:
        repo.set_value(_STATE_FAILED, failed)
    except Exception as e:
        log.debug("mark_model_failed persist failed: %s", e)
    # drop from working list so we don't stick to a broken free model
    try:
        working = list(repo.get_value(_STATE_WORKING) or [])
        if model in working:
            working = [m for m in working if m != model]
            repo.set_value(_STATE_WORKING, working)
    except Exception as e:
        log.debug("mark_model_failed working prune failed: %s", e)
    log.info("OpenRouter free model cooled down for %.0fs: %s", FREE_FAIL_COOLDOWN_S, model)


def mark_model_success(model: str, repo=None) -> None:
    if not model:
        return
    repo = repo or _repo()
    try:
        working = list(repo.get_value(_STATE_WORKING) or [])
        if model in working:
            working.remove(model)
        working.append(model)  # round-robin: last success goes to end
        # keep list bounded
        if len(working) > 24:
            working = working[-24:]
        repo.set_value(_STATE_WORKING, working)
    except Exception as e:
        log.debug("mark_model_success working update failed: %s", e)
    # clear cooldown on success
    try:
        failed = _read_failed(repo)
        if model in failed:
            del failed[model]
            repo.set_value(_STATE_FAILED, failed)
    except Exception as e:
        log.debug("mark_model_success cooldown clear failed: %s", e)


def build_free_model_chain(preferred: str | None = None, repo=None) -> list[str]:
    """Ordered unique free-model slugs for fallback.

    Order:
      1. preferred (if any) when not cooled down
      2. remembered working free models (not cooled)
      3. Config.OPENROUTER_FREE_MODELS (not cooled)
      4. preferred even if cooled (last resort among free)
      5. remaining cooled free models
    """
    repo = repo or _repo()
    now = time.time()
    free = list(getattr(Config, "OPENROUTER_FREE_MODELS", []) or [])
    try:
        working = list(repo.get_value(_STATE_WORKING) or [])
    except Exception:
        working = []

    # Only keep free-ish / openrouter free pool ids in working for this chain
    def _is_free_slug(m: str) -> bool:
        if not m:
            return False
        ml = m.lower()
        return (
            ml.endswith(":free")
            or ml == "openrouter/free"
            or m in free
        )

    working_free = [m for m in working if _is_free_slug(m)]

    hot: list[str] = []
    cold: list[str] = []

    def _add(m: str, force_cold: bool = False) -> None:
        if not m or m in hot or m in cold:
            return
        if force_cold or is_model_cooled_down(m, now=now, repo=repo):
            cold.append(m)
        else:
            hot.append(m)

    # Preferred always first (even if recently failed) — one more shot, then rotate
    if preferred:
        hot.append(preferred)

    for m in working_free:
        _add(m)
    for m in free:
        _add(m)
    # last resort: remaining cooled free models
    for m in free + working_free:
        _add(m, force_cold=True)

    return hot + cold


def openrouter_provider_candidates(preferred: str | None = None, repo=None) -> list[tuple[str, str]]:
    """``[(\"openrouter\", model), ...]`` for the free rotation chain."""
    return [("openrouter", m) for m in build_free_model_chain(preferred, repo=repo)]
