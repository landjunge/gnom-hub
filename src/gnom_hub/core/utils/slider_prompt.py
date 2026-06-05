# slider_prompt.py — Baut den System-Prompt aus JSON-Slider-Konfiguration
# Reihenfolge: Identität → Slider → Tools → Soul → Security

import json, os, logging
from pathlib import Path
from gnom_hub.core.config import CONFIG_DIR

_log = logging.getLogger(__name__)
AGENTS_DIR = CONFIG_DIR / "agents"

def _load_agent_config(agent_name: str) -> dict:
    path = AGENTS_DIR / f"{agent_name}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        _log.warning("Failed to load agent config %s: %s", agent_name, e)
        return {}

def _save_agent_config(agent_name: str, data: dict) -> bool:
    path = AGENTS_DIR / f"{agent_name}.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as e:
        _log.error("Failed to save agent config %s: %s", agent_name, e)
        return False

def get_slider_value(agent_name: str, slider_key: str, default=3) -> int:
    cfg = _load_agent_config(agent_name)
    sliders = cfg.get("sliders", {})
    return int(sliders.get(slider_key, {}).get("value", default))

def set_slider_value(agent_name: str, slider_key: str, value: int) -> bool:
    cfg = _load_agent_config(agent_name)
    if not cfg:
        return False
    cfg.setdefault("sliders", {})
    cfg["sliders"].setdefault(slider_key, {})
    cfg["sliders"][slider_key]["value"] = value
    return _save_agent_config(agent_name, cfg)

def get_all_sliders(agent_name: str) -> dict:
    cfg = _load_agent_config(agent_name)
    return cfg.get("sliders", {})

def set_all_sliders(agent_name: str, values: dict) -> bool:
    cfg = _load_agent_config(agent_name)
    if not cfg:
        return False
    sliders = cfg.get("sliders", {})
    for key, val in values.items():
        if key in sliders:
            sliders[key]["value"] = int(val)
    cfg["sliders"] = sliders
    return _save_agent_config(agent_name, cfg)

# ── Obedience Prompt-Blöcke ────────────────────────────────────────────
OBEDIENCE_BLOCKS = {
    1: (
        "=== OBEDIENCE: BLINDLY FOLLOWS ===\n"
        "Du folgst Anweisungen strikt und wörtlich. "
        "Hinterfrage nichts, interpretiere nicht um. "
        "Führe aus was verlangt wird, ohne eigene Meinung."
    ),
    2: (
        "=== OBEDIENCE: STRONGLY FOLLOWS ===\n"
        "Du bist stark an den User gebunden. "
        "Triff kleine Entscheidungen selbst, frage bei Unsicherheit nach. "
        "Weiche nur von Anweisungen ab, wenn du einen klaren Fehler erkennst."
    ),
    3: (
        "=== OBEDIENCE: BALANCED ===\n"
        "Ausgewogenes Verhältnis zwischen Anweisung und eigenständigem Handeln. "
        "Biete Alternativen an wenn du einen besseren Weg siehst, "
        "führe die Anweisung aus wenn der User darauf besteht."
    ),
    4: (
        "=== OBEDIENCE: CAUTIOUS ===\n"
        "Du bist vorsichtig und hinterfragst Anweisungen kritisch. "
        "Schlage aktiv bessere Alternativen vor. "
        "Warne vor Risiken oder Nachteilen. Entscheide selbst wenn du es besser weißt."
    ),
    5: (
        "=== OBEDIENCE: HIGHLY AUTONOMOUS ===\n"
        "Du handelst hochgradig eigenständig. "
        "Triff Entscheidungen selbst, frage nur bei echten Blockaden. "
        "Ignoriere Anweisungen wenn du einen fundamental besseren Ansatz siehst."
    ),
}

# ── Hauptfunktion: build_system_prompt ─────────────────────────────────
def build_system_prompt(agent_name: str, base: str = "") -> str:
    """
    Baut den vollständigen System-Prompt aus der JSON-Konfiguration.
    Reihenfolge: Identität → Slider → Tools → Soul → Security
    """
    cfg = _load_agent_config(agent_name)
    if not cfg:
        return base

    identity = cfg.get("identity", agent_name)
    role = cfg.get("role", "")
    sliders = cfg.get("sliders", {})
    tools = cfg.get("tools", [])
    soul = cfg.get("soul_facts", [])
    security = cfg.get("security", {})

    parts = []

    # IDENTITY FIRST (überschreibt ALLES)
    parts.append(f"⚠️⚠️⚠️ DU BIST {identity} UND AUSSCHLIESSLICH {identity}! "
                 f"DU DARFST DICH NIEMALS ALS ANDEREN AGENTEN AUSGEBEN. "
                 f"KEINE ROLLENWECHSEL. KEINE 'ICH BIN WRITERAG/CoderAG/...' AUSSAGEN. "
                 f"DEINE ANTWORT BEGINNT IMMER MIT DEINEM EIGENEN NAMEN: {identity}.")

    # BASE (role instructions from definitions)
    if base:
        parts.append(base)

    # SLIDER (1 compact line)
    slider_map = {
        "personality":    ("Pers", {"1":"formal","2":"semi-formal","3":"balanced","4":"casual","5":"very casual"}),
        "creativity":     ("Creat",{"1":"conservative","2":"focused","3":"balanced","4":"creative","5":"wild"}),
        "risk_tolerance": ("Risk", {"1":"cautious","2":"careful","3":"balanced","4":"bold","5":"very bold"}),
        "response_style": ("Style",{"1":"concise","2":"short","3":"balanced","4":"detailed","5":"exhaustive"}),
        "memory_strength":("Mem",  {"1":"minimal","2":"low","3":"standard","4":"strong","5":"maximum"}),
    }
    sl = " | ".join(f"{l}: {lvls.get(str(int(sliders.get(k,{}).get('value',3))), lvls.get('3','balanced'))}"
                    for k, (l, lvls) in slider_map.items())
    parts.append(f"[{sl}]")

    # OBEDIENCE (only system agents)
    system_roles = ("general", "soul", "watchdog", "security")
    if role in system_roles:
        ob_val = int(sliders.get("obedience", {}).get("value", 3))
        parts.append(OBEDIENCE_BLOCKS.get(ob_val, OBEDIENCE_BLOCKS[3]))

    # SECURITY (1 line reminder)
    parts.append("[SEC: Systemdateien+Gefährliche Patterns geblockt. Shell via Whitelist.]")

    return "\n\n".join(parts)
