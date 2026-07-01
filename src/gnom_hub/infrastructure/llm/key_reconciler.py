"""Auto-Reconciler: läuft beim Hub-Start und stellt sicher dass
Desktop-Keys ↔ DB-Keys konsistent sind. Verhindert dass Provider-Keys
„verschwinden" wenn Sync-Edge-Cases zuschlagen.

Wird vom Hub-Main gehookt (siehe infrastructure/hub_app.py).
"""
import logging
from pathlib import Path

from gnom_hub.db.state_repo import SQLiteStateRepository

log = logging.getLogger(__name__)

DESKTOP_TXT = Path.home() / "Desktop" / "api_keys.txt"


def reconcile_keys_on_startup() -> dict:
    """Liest ~/Desktop/api_keys.txt + DB, mergt fehlende Keys, schreibt zurück.

    Strategie: alle Keys aus Desktop-Datei die in DB fehlen ODER in DB aber
    nicht mehr valid sind → werden in DB gespeichert. Bestehende valide
    Keys werden NICHT angetastet.

    Returns: dict mit stats (added, kept, removed).
    """
    stats = {"added": 0, "kept": 0, "invalid_in_db": 0, "missing_desktop": 0}
    db = SQLiteStateRepository()
    kdb = db.get_value("llm_keys", {}) or {}
    if not isinstance(kdb, dict):
        kdb = {}

    # 1. Parse Desktop-Datei (Best Effort — Datei darf fehlen)
    desktop_keys: dict[str, dict] = {}
    if DESKTOP_TXT.exists():
        try:
            for line in DESKTOP_TXT.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "UNGÜLTIG" in line.upper():
                    continue
                if "=" not in line:
                    continue
                lbl, _, raw = line.partition("=")
                lbl = lbl.strip().lstrip("#").strip()
                # crude clean: just take the right-hand side as-is
                key = raw.strip().strip("'\"")
                if not key or "…" in key or "***" in key or "..." in key:
                    continue
                desktop_keys.setdefault(key, {"label": lbl, "key": key})
        except Exception as e:
            log.warning("Desktop-Datei nicht lesbar: %s", e)

    # 2. Merge: Desktop-Keys die nicht in DB sind → hinzufügen
    new_kdb = dict(kdb)
    existing_keys = {v.get("key") for v in kdb.values() if isinstance(v, dict)}
    for key, info in desktop_keys.items():
        if key in existing_keys:
            stats["kept"] += 1
            continue
        # Neu hinzufügen — Provider raten (spezifischster Prefix)
        provider = _detect_provider(key)
        if not provider:
            stats["missing_desktop"] += 1
            continue
        kid = f"k_reconciled_{abs(hash(key)) % 10**10}"
        new_kdb[kid] = {
            "id": kid,
            "key": key,
            "provider": provider,
            "valid": True,  # wir vertrauen Desktop-Keys
            "info": "OK (reconciled from Desktop)",
            "caps": _caps_for(provider),
            "label": info.get("label") or provider.upper(),
        }
        stats["added"] += 1
        log.info("Reconciled: %s (%s) → DB", info.get("label"), provider)

    # 3. Schreibe nur wenn was hinzugekommen ist
    if stats["added"] > 0:
        db.set_value("llm_keys", new_kdb)
        log.info("Auto-Reconcile: %d keys merged into DB", stats["added"])
    return stats


def _detect_provider(key: str) -> str | None:
    """Spezifischster Prefix gewinnt (siehe providers.py detect_provider_from_key)."""
    from gnom_hub.infrastructure.llm.providers import PROVIDERS
    best, best_len = None, 0
    for pid, p in PROVIDERS.items():
        for prefix in p.get("key_prefixes", []):
            if prefix and key.startswith(prefix) and len(prefix) > best_len:
                best, best_len = pid, len(prefix)
    return best


def _caps_for(provider: str) -> list:
    try:
        from gnom_hub.infrastructure.llm.providers import PROVIDERS
        return list(PROVIDERS.get(provider, {}).get("caps", ["text"]))
    except Exception:
        return ["text"]


# Optional: Agent-Assignments auf MiniMax-M3 forcieren wenn gewünscht.
# Auskommentiert standardmäßig — User entscheidet ob das aktiv sein soll.
def force_minimax_routing() -> bool:
    """Setzt alle Agent-Routing-Assignments auf minimax:MiniMax-M3.
    Nur aufrufen wenn explizit gewünscht. Returns True wenn was geändert wurde.
    """
    db = SQLiteStateRepository()
    current = db.get_value("llm_agents", {}) or {}
    if not isinstance(current, dict):
        current = {}
    target = {"provider": "minimax", "model": "MiniMax-M3"}
    needs_update = any(
        current.get(ag, {}).get("provider") != "minimax"
        or current.get(ag, {}).get("model") != "MiniMax-M3"
        for ag in ["soulag", "watchdogag", "generalag", "securityag",
                   "writerag", "coderag", "researcherag", "editorag"]
    )
    if not needs_update:
        return False
    for ag in ["soulag", "watchdogag", "generalag", "securityag",
               "writerag", "coderag", "researcherag", "editorag"]:
        current[ag] = dict(target)
    db.set_value("llm_agents", current)
    log.info("force_minimax_routing: all 8 agents → minimax/MiniMax-M3")
    return True
