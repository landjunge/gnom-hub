# zwc_codec.py — Pure-stdlib ZWC codec primitives.
#
# Extracted from gnom_hub.soul.zwc_soul (2026-06-29) to break the dependency
# on ``gnom_hub.soul`` which transitively imports SoulAG → sentence_transformers
# → torch. The action_write.py handler used to lazily
# ``from gnom_hub.soul.zwc_soul import add_agent_metadata`` on every
# successful [WRITE:], which triggered a ~5-30s cold-start on first call
# and caused LLM-side race conditions ("file not written" user reports).
#
# This module is functionally identical to zwc_soul.py for the symbols
# it exposes but has ZERO soul/lifecycle imports — pure stdlib only
# (json, base64, logging, time). It can be safely imported from any
# request-handling code path.
import base64
import json
import logging
import time

# Zero-width character map: bit '0' → U+200B, bit '1' → U+200C.
Z = {"0": "​", "1": "‌"}
R = {"​": "0", "‌": "1"}

_log = logging.getLogger(__name__)


def soul_to_bits(d: dict) -> str:
    """Encode a dict as a base64-encoded JSON, then to a binary string."""
    return "".join(
        format(ord(c), "08b")
        for c in base64.b64encode(
            json.dumps(d, separators=(",", ":")).encode()
        ).decode()
    )


def bits_to_zwc(b: str) -> str:
    """Encode each bit three times (Hamming-like repetition) and map to ZWC chars."""
    return "".join(Z[bit] for bit in "".join(bit * 3 for bit in b))


def extract_zwc(t: str) -> str:
    """Extract the bit-string from a text containing ZWC chars."""
    return "".join(R.get(c, "") for c in t if c in R)


def strip_zwc(t: str) -> str:
    """Remove ZWC chars from a text."""
    return "".join(c for c in t if c not in R)


def correct_ecc(zb: str) -> str:
    """Repetition-code ECC: majority vote per 3-bit chunk."""
    c = ""
    for i in range(0, len(zb), 3):
        g = zb[i:i + 3]
        if len(g) < 3:
            break
        c += "0" if g.count("0") >= 2 else "1"
    return c


def decode_soul(t: str):
    """Decode a ZWC-encoded dict out of a text. Returns None on failure."""
    zb = extract_zwc(t)
    if not zb or len(zb) % 3 != 0:
        return None
    cb = correct_ecc(zb)
    try:
        raw = "".join(chr(int(cb[i:i + 8], 2)) for i in range(0, len(cb), 8))
        return json.loads(base64.b64decode(raw).decode())
    except Exception:
        _log.debug("ZWC decode failed for input length %d", len(t))
        return None


def add_agent_metadata(agent_name: str, message: str, extra: dict = None) -> str:
    """Append invisible ZWC metadata to a message identifying the source agent.

    Args:
        agent_name: Source agent identifier (e.g. "CoderAG").
        message:    Visible message body.
        extra:      Optional dict merged into the encoded payload
                    (e.g. SoulAG directives).
    Returns:
        The original message plus an invisible ZWC signature.
    """
    data = {"agent": agent_name, "ts": time.time()}
    if extra:
        data["extra"] = extra
    return message + bits_to_zwc(soul_to_bits(data))
