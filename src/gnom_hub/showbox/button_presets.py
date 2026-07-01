# gnom_hub/showbox/button_presets.py
# Lädt die Button-Presets aus /Users/landjunge/gnom-hub/showbox/buttons/*.json
# und stellt sie als Python-API + HTTP-Endpoint zur Verfügung.
#
# Verwendung im Backend:
#     from gnom_hub.showbox.button_presets import get_preset, all_buttons, categories
#
# HTTP:
#     GET /api/showbox/button-presets           → alle
#     GET /api/showbox/button-presets/<name>    → einzelne Kategorie
#
# Frontend (showbox-buttons.js) ruft diese Presets beim Showbox-Open ab
# und füllt leere Slots im 2x4-Grid mit kontextuellen Standard-Buttons.
import json
from pathlib import Path

# Pfad zum showbox-Ordner — Repo-Root-relative
PRESETS_DIR = Path(__file__).resolve().parents[3] / "showbox" / "buttons"

# Cache
_CACHE: dict = {}
_CACHE_MTIME: dict = {}


def _load_file(path: Path) -> dict:
    """Lädt eine Preset-Datei mit Cache-Invalidierung bei File-Mtime-Änderung."""
    if not path.exists():
        return {"_meta": {"name": path.stem, "error": "not_found"}, "buttons": []}
    mtime = path.stat().st_mtime
    if path.name in _CACHE and _CACHE_MTIME.get(path.name) == mtime:
        return _CACHE[path.name]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        _CACHE[path.name] = data
        _CACHE_MTIME[path.name] = mtime
        return data
    except Exception as e:
        return {"_meta": {"name": path.stem, "error": str(e)}, "buttons": []}


def categories() -> list[str]:
    """Alle verfügbaren Preset-Kategorien (Dateinamen ohne .json)."""
    if not PRESETS_DIR.exists():
        return []
    return sorted(p.stem for p in PRESETS_DIR.glob("*.json"))


def get_preset(name: str) -> dict:
    """Lädt ein einzelnes Preset nach Namen (z.B. 'nav', 'actions', 'agents', 'workflow')."""
    return _load_file(PRESETS_DIR / f"{name}.json")


def all_buttons() -> dict:
    """Alle Presets als Dict: {category: preset_data}."""
    return {cat: get_preset(cat) for cat in categories()}


def get_buttons_for_context(context: str = "default") -> list[dict]:
    """Wählt kontextuell passende Buttons aus den Presets.

    Strategie:
    - 'default':  2x nav (prev/next/close) + 2x actions (approve/reject) + 2x agents + 2x workflow
    - 'tribunal': mehr actions, weniger nav
    - 'show':     mehr workflow, weniger actions
    - 'minimal':  nur nav (prev/next/close)

    Returns flache Liste von Button-Dicts (max 8).
    """
    nav = get_preset("nav").get("buttons", [])
    actions = get_preset("actions").get("buttons", [])
    agents = get_preset("agents").get("buttons", [])
    workflow = get_preset("workflow").get("buttons", [])

    if context == "minimal":
        return nav[:4]
    if context == "tribunal":
        return (nav[:1] + actions[:4] + agents[:2])[:8]
    if context == "show":
        return (nav[:2] + workflow[:4] + agents[:2])[:8]

    # default
    return (nav[:3] + actions[:2] + agents[:2] + workflow[:1])[:8]


def to_frontend_buttons(buttons: list) -> list:
    """Konvertiert JSON-Preset-Format in Frontend-kompatibles Format.

    Mapping:
      action       → onClick (string)
      color (#hex) → Farbname (red/green/blue/cyan/orange/yellow/purple)
      icon         → icon
      label        → label
    """
    color_map = {
        "#ff4d6d": "red", "#6ddb9c": "green", "#4d9fff": "blue",
        "#00e5ff": "cyan", "#ff8c42": "orange", "#ffd84d": "yellow",
        "#c47bff": "purple", "#ff7ab8": "pink", "#7a90b8": "muted",
    }
    out = []
    for i, b in enumerate(buttons):
        color_hex = b.get("color", "").lower()
        color = color_map.get(color_hex, "")
        out.append({
            "id": f"preset-{i}",
            "icon": b.get("icon", ""),
            "label": b.get("label", ""),
            "color": color,
            "onClick": b.get("action", ""),
            "source": "preset",
        })
    return out
