# integrity.py — ZWC-based system file integrity protection
"""
Schützt Gnom-Systemdateien mit unsichtbaren ZWC-Signaturen (Zero-Width Characters).

Workflow:
  sign_system_files(root)    → Berechnet SHA-256 Hashes, speichert sie als ZWC in config/integrity.zwc
  verify_system_files(root)  → Liest ZWC-Manifest, vergleicht Hashes, gibt modifizierte Dateien zurück
  is_integrity_enabled()     → Prüft ob der Schutz aktiv ist
"""
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

# ── Geschützte Systemdateien (relativ zum Projekt-Root) ──────────────────────
PROTECTED_SYSTEM_FILES = [
    "src/gnom_hub/core/security/gatekeeper.py",
    "src/gnom_hub/core/security/path_validator.py",
    "src/gnom_hub/core/security/integrity.py",
    "src/gnom_hub/api/app.py",
    "src/gnom_hub/api/endpoints/router.py",
    "run.sh",
    "src/gnom_hub/frontend/core.js",
]

_MANIFEST_COMMENT = (
    "# GNOM-HUB System Integrity Manifest\n"
    "# Dieses File enthält unsichtbare ZWC-Signaturen der Systemdateien.\n"
    "# Nicht manuell editieren — Schutz wird durch @system save / @system unsave gesteuert.\n"
    "# Generated: {ts}\n"
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sign_system_files(root: Path) -> dict:
    """
    Berechnet SHA-256 für alle geschützten Dateien und schreibt das
    ZWC-kodierte Manifest nach config/integrity.zwc.
    Gibt das Hash-Dict zurück.
    """
    from gnom_hub.soul.zwc_soul import soul_to_bits, bits_to_zwc

    hashes: dict[str, str] = {}
    missing: list[str] = []

    for rel in PROTECTED_SYSTEM_FILES:
        p = root / rel
        if p.exists():
            hashes[rel] = _sha256(p)
        else:
            missing.append(rel)
            log.warning("integrity: Datei nicht gefunden beim Signieren: %s", rel)

    # ZWC-kodieren: {"v":1, "hashes": {...}}
    payload = {"v": 1, "hashes": hashes}
    zwc_data = bits_to_zwc(soul_to_bits(payload))

    ts = datetime.now(timezone.utc).isoformat()
    header = _MANIFEST_COMMENT.format(ts=ts)
    # readable line + invisible ZWC appended
    manifest_content = header + "# Files: " + ", ".join(hashes.keys()) + "\n" + zwc_data + "\n"

    manifest_path = _get_manifest_path(root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest_content, encoding="utf-8")

    log.info("integrity: %d Dateien signiert → %s", len(hashes), manifest_path)
    if missing:
        log.warning("integrity: %d Dateien fehlten beim Signieren: %s", len(missing), missing)

    # Schutz aktivieren
    _set_enabled(True)
    return hashes


def verify_system_files(root: Path) -> list[str]:
    """
    Liest das ZWC-Manifest und vergleicht Hashes.
    Gibt eine Liste modifizierter (oder fehlender) Dateien zurück.
    Leere Liste = alles in Ordnung.
    """
    from gnom_hub.soul.zwc_soul import decode_soul

    manifest_path = _get_manifest_path(root)
    if not manifest_path.exists():
        log.info("integrity: Kein Manifest gefunden — Integritätsprüfung übersprungen.")
        return []

    raw = manifest_path.read_text(encoding="utf-8")
    payload = decode_soul(raw)

    if not payload or not isinstance(payload.get("hashes"), dict):
        log.error("integrity: Manifest ist korrupt oder nicht lesbar!")
        return ["[MANIFEST KORRUPT]"]

    stored: dict[str, str] = payload["hashes"]
    tampered: list[str] = []

    for rel, expected_hash in stored.items():
        p = root / rel
        if not p.exists():
            tampered.append(f"{rel} (fehlt)")
            continue
        current = _sha256(p)
        if current != expected_hash:
            tampered.append(rel)
            log.warning("integrity: Datei verändert: %s", rel)

    if not tampered:
        log.info("integrity: ✅ Alle %d Systemdateien unverändert.", len(stored))
    else:
        log.error("integrity: ⚠️ %d Systemdatei(en) manipuliert: %s", len(tampered), tampered)

    return tampered


def is_integrity_enabled() -> bool:
    try:
        from gnom_hub.db.legacy_db import get_state_value
        return bool(get_state_value("integrity_check_enabled", False))
    except Exception:
        return False


def _set_enabled(val: bool) -> None:
    try:
        from gnom_hub.db.legacy_db import set_state_value
        set_state_value("integrity_check_enabled", val)
    except Exception as e:
        log.error("integrity: Konnte Schutz-Flag nicht setzen: %s", e)


def disable_integrity() -> None:
    """@system unsave — Schutz deaktivieren."""
    _set_enabled(False)
    log.info("integrity: ⚠️ Integritätsschutz DEAKTIVIERT. Systemdateien können verändert werden.")


def _get_manifest_path(root: Path) -> Path:
    from gnom_hub.core.config import CONFIG_DIR
    return CONFIG_DIR / "integrity.zwc"
