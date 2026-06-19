"""TTS Engine — Provider-dispatchable.

Liest den aktiven TTS-Provider aus ``llm_service_tts`` und routet entsprechend:
- minimax      → OpenAI-kompatibles /v1/audio/speech an api.minimax.io
- openai-tts   → OpenAI /v1/audio/speech
- elevenlabs   → bestehender ElevenLabs-Pfad (Default)
- (alles andere) → ElevenLabs-Fallback

Cache: 1 Minute pro (Provider + Voice + Text), verhindert Spammy-Re-Calls.
Falls der Provider scheitert: ``None`` zurück, der Caller (api/audio/tts) fällt
auf Browser Web Speech zurück.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from gnom_hub.core.config import DATA_DIR

_log = logging.getLogger(__name__)

AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

# Cache: {cache_key: (timestamp, audio_path)}
_TTS_CACHE: dict[str, tuple[float, Path]] = {}
_CACHE_TTL_SECONDS = 60  # 1 Minute


# ─── Active-Provider-Lookup ──────────────────────────────────────────────────

def _active_tts_config() -> dict[str, Any]:
    """Liest die persistierte TTS-Service-Konfiguration (provider, model, key_id)."""
    try:
        from gnom_hub.db.state_repo import SQLiteStateRepository
        cfg = SQLiteStateRepository().get_value("llm_service_tts", {}) or {}
        return cfg if isinstance(cfg, dict) else {}
    except Exception as e:  # pragma: no cover — defensive
        _log.debug("Konnte llm_service_tts nicht lesen: %s", e)
        return {}


def _resolve_key_for_provider(provider: str) -> str:
    """Sucht den ersten gültigen API-Key für *provider* in llm_keys."""
    if not provider:
        return ""
    try:
        from gnom_hub.db.state_repo import SQLiteStateRepository
        keys = SQLiteStateRepository().get_value("llm_keys", {}) or {}
        for entry in keys.values():
            if not isinstance(entry, dict):
                continue
            if entry.get("provider") == provider and entry.get("valid") and entry.get("key"):
                return entry["key"]
    except Exception as e:  # pragma: no cover
        _log.debug("Key-Lookup für %s fehlgeschlagen: %s", provider, e)
    return ""


# ─── Cache ───────────────────────────────────────────────────────────────────

def _cache_key(provider: str, text: str, voice_id: str) -> str:
    return f"{provider}:{voice_id}:{text}"


def _cache_get(key: str) -> Optional[Path]:
    entry = _TTS_CACHE.get(key)
    if not entry:
        return None
    ts, path = entry
    if time.time() - ts >= _CACHE_TTL_SECONDS or not path.exists():
        try:
            path.unlink()
        except OSError:
            pass
        _TTS_CACHE.pop(key, None)
        return None
    return path


def _cache_put(key: str, path: Path) -> None:
    _TTS_CACHE[key] = (time.time(), path)


def _cache_purge_expired() -> int:
    now = time.time()
    expired = [k for k, (ts, _) in _TTS_CACHE.items() if now - ts >= _CACHE_TTL_SECONDS]
    for k in expired:
        _, path = _TTS_CACHE.pop(k, (None, None))
        try:
            if path and path.exists():
                path.unlink()
        except OSError:
            pass
    return len(expired)


# ─── Provider-Backends ───────────────────────────────────────────────────────

def _tts_elevenlabs(text: str, voice_id: str) -> Optional[Path]:
    """Bestehender ElevenLabs-Pfad (unverändertes Verhalten)."""
    if not ELEVEN_KEY:
        return None
    import requests
    vid = voice_id or ELEVEN_VOICE
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
        headers={"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"},
        json={"text": text, "model_id": "eleven_multilingual_v2"},
        timeout=15,
    )
    if r.status_code != 200:
        return None
    out = AUDIO_DIR / f"tts_el_{hash(text + vid) & 0xFFFFFFFF}.mp3"
    out.write_bytes(r.content)
    return out


def _tts_openai_compat(base_url: str, api_key: str, model: str, text: str, voice: str) -> Optional[Path]:
    """OpenAI-kompatibles /v1/audio/speech (OpenAI, MiniMax, kompatible)."""
    import requests
    r = requests.post(
        f"{base_url.rstrip('/')}/audio/speech",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "input": text, "voice": voice or "alloy", "response_format": "mp3"},
        timeout=20,
    )
    if r.status_code != 200:
        _log.info("TTS %s → HTTP %s: %s", base_url, r.status_code, r.text[:200])
        return None
    out = AUDIO_DIR / f"tts_oa_{hash(text + model + voice) & 0xFFFFFFFF}.mp3"
    out.write_bytes(r.content)
    return out


# ─── Public API ──────────────────────────────────────────────────────────────

def _strip_zero_width(text: str) -> str:
    for c in ('\u200b', '\u200c', '\u200d', '\u200e', '\u200f', '\ufeff'):
        text = text.replace(c, '')
    return text


def tts(text: str, voice_id: str = "") -> Optional[Path]:
    """Provider-dispatchable TTS → MP3-Pfad. None = Caller fällt auf Web Speech.

    Reihenfolge:
        1. Cache (provider-aware Key)
        2. Aktive TTS-Provider-Konfig aus llm_service_tts
        3. Provider-spezifischer Backend-Call
        4. Bei jedem Fehlschlag: ElevenLabs-Fallback, dann None
    """
    text = _strip_zero_width(text or "")
    if not text.strip():
        return None

    cfg = _active_tts_config()
    provider = (cfg.get("provider") or "").strip().lower()
    model = (cfg.get("model") or "tts-1").strip()
    voice = voice_id or cfg.get("voice") or ""

    # Cache-Key ist provider-scoped, damit verschiedene Provider sich nicht
    # in die Quere kommen.
    cache_k = _cache_key(provider or "elevenlabs", text, voice or voice_id)
    cached = _cache_get(cache_k)
    if cached:
        return cached

    out: Optional[Path] = None

    # ── 1. Provider-spezifischer Pfad ────────────────────────────────────────
    if provider == "minimax":
        key = _resolve_key_for_provider("minimax")
        if key:
            try:
                out = _tts_openai_compat(
                    "https://api.minimax.io/v1",
                    key,
                    model="tts-1",
                    text=text,
                    voice=voice or "alloy",
                )
                if out:
                    _log.info("TTS via MiniMax OK (%d bytes)", out.stat().st_size)
                else:
                    _log.info("TTS via MiniMax fehlgeschlagen — Fallback ElevenLabs")
            except Exception as e:
                _log.warning("TTS via MiniMax exception: %s", e)

    elif provider == "openai-tts":
        key = _resolve_key_for_provider("openai")
        if key:
            try:
                out = _tts_openai_compat(
                    "https://api.openai.com/v1",
                    key,
                    model=model,
                    text=text,
                    voice=voice or "alloy",
                )
            except Exception as e:
                _log.warning("TTS via OpenAI exception: %s", e)

    # ── 2. ElevenLabs-Fallback (immer verfügbar wenn Env-Key gesetzt) ───────
    if out is None:
        try:
            out = _tts_elevenlabs(text, voice_id)
            if out:
                _log.info("TTS via ElevenLabs OK (%d bytes)", out.stat().st_size)
        except Exception as e:
            _log.warning("TTS ElevenLabs exception: %s", e)

    if out is None:
        return None

    _cache_put(cache_k, out)
    if len(_TTS_CACHE) > 50:
        _cache_purge_expired()
    return out


def cache_stats() -> dict:
    """Cache-Statistiken für Health-Endpoint."""
    now = time.time()
    entries = [
        {"key": k[:60], "age_sec": round(now - ts, 1), "path": str(p)}
        for k, (ts, p) in _TTS_CACHE.items()
    ]
    return {
        "size": len(_TTS_CACHE),
        "ttl_seconds": _CACHE_TTL_SECONDS,
        "entries": entries,
    }


def cache_clear() -> int:
    """Leert den gesamten Cache. Returns Anzahl gelöschter Einträge."""
    count = len(_TTS_CACHE)
    for k, (_, path) in list(_TTS_CACHE.items()):
        try:
            if path and path.exists():
                path.unlink()
        except OSError:
            pass
    _TTS_CACHE.clear()
    return count
