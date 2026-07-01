# preset_service.py — Preset management loader and trigger actions
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from gnom_hub.core.config import CONFIG_DIR

_PRESETS_PATH = os.path.join(os.path.dirname(__file__), "presets.json")
_WORKER_AGENTS = ("coderag", "researcherag", "writerag", "editorag")
_SYSTEM_AGENTS = ("soulag", "watchdogag", "generalag", "securityag")
_ALL_AGENTS = _SYSTEM_AGENTS + _WORKER_AGENTS


def _read_presets_file():
    with open(_PRESETS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _write_presets_file(data):
    with open(_PRESETS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True


def load_presets():
    """Backwards-compatible: returns dict with 'prompts', 'focus', 'targets',
    AND the new 'presets' / 'agent_groups' fields. Per-preset per-agent
    data lives in presets.<slug>.agents.<agent_name>."""
    data = _read_presets_file()
    pdir = CONFIG_DIR / "presets"
    if pdir.exists():
        for fn in [f for f in os.listdir(pdir) if f.endswith(".json")]:
            try:
                with open(pdir / fn, encoding="utf-8") as f: c = json.load(f)
                name = c.get("name")
                if name:
                    data.setdefault("prompts", {})[name] = c.get("prompt_modifier", {})
                    data.setdefault("focus", {})[name] = c.get("description", "Custom.")
                    tm, ta = c.get("model", {}).get("primary"), c.get("allowed_tools", [None])[0]
                    if tm and ta: data.setdefault("targets", {})[name] = [ta.lower() + "ag", tm]
            except Exception as e:
                logging.getLogger(__name__).error('Fehler in Preset-Datei-Laden: %s', e)
    return data


def get_preset_prompt(preset: str, agent_name: str) -> str:
    """Backwards-compatible prompt lookup. Prefers new schema
    presets.<slug>.agents.<agent>.prompt, falls back to old prompts dict."""
    data = load_presets()
    slug = _slugify(preset)
    new = data.get("presets", {}).get(slug, {}).get("agents", {}).get(agent_name.lower(), {})
    if new and "prompt" in new:
        return new["prompt"]
    return data.get("prompts", {}).get(preset, {}).get(agent_name, "")


# ── NEW: per-agent preset CRUD (System + Worker groups) ─────────────

def get_agent_groups() -> dict:
    """Returns {system: [...], worker: [...]} from the active schema."""
    data = _read_presets_file()
    return data.get("agent_groups", {"system": list(_SYSTEM_AGENTS), "worker": list(_WORKER_AGENTS)})


def list_presets() -> list:
    """Returns [{slug, name, description, updated_at, agent_count}, ...]."""
    data = _read_presets_file()
    out = []
    for slug, p in (data.get("presets") or {}).items():
        out.append({
            "slug": slug,
            "name": p.get("name", slug),
            "description": p.get("description", ""),
            "updated_at": p.get("updated_at", ""),
            "agent_count": len(p.get("agents", {})),
        })
    return out


def get_preset(slug: str) -> dict:
    data = _read_presets_file()
    p = data.get("presets", {}).get(slug)
    if not p:
        return None
    return {
        "slug": slug,
        "name": p.get("name", slug),
        "description": p.get("description", ""),
        "created_at": p.get("created_at", ""),
        "updated_at": p.get("updated_at", ""),
        "agents": p.get("agents", {}),
    }


def get_preset_agent(slug: str, agent_name: str) -> dict:
    p = get_preset(slug)
    if not p:
        return None
    return p.get("agents", {}).get(agent_name.lower())


def update_preset_agent(slug: str, agent_name: str, fields: dict) -> bool:
    """Updates the per-agent fields inside an existing preset. Whitelisted
    fields only: prompt, focus, target, creativity, obedience,
    model_override, model_locked, priority, enabled."""
    ALLOWED = {"prompt", "focus", "target", "creativity", "obedience",
               "model_override", "model_locked", "priority", "enabled"}
    clean = {k: v for k, v in (fields or {}).items() if k in ALLOWED}
    agent = agent_name.lower()
    data = _read_presets_file()
    if "presets" not in data or slug not in data["presets"]:
        return False
    if "agents" not in data["presets"][slug]:
        data["presets"][slug]["agents"] = {}
    existing = data["presets"][slug]["agents"].get(agent, {})
    existing.update(clean)
    data["presets"][slug]["agents"][agent] = existing
    data["presets"][slug]["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_presets_file(data)
    return True


def create_preset(name: str, description: str = "") -> str:
    """Creates a new preset by cloning an existing one (or empty if none).
    Returns the new slug."""
    data = _read_presets_file()
    base = "default"
    if not data.get("presets"):
        # Seed from current agent definitions if presets is empty
        new = {"name": name, "description": description,
               "created_at": datetime.now(timezone.utc).isoformat(),
               "updated_at": datetime.now(timezone.utc).isoformat(),
               "schema_generation": 1, "agents": {}}
        for ag in _ALL_AGENTS:
            new["agents"][ag] = {"prompt": "", "focus": "", "target": "auto:stage_2",
                                   "creativity": 3, "obedience": 3, "model_override": None,
                                   "model_locked": False, "priority": "normal", "enabled": True}
        data.setdefault("presets", {})[base] = new
    else:
        # Clone first preset
        first = next(iter(data["presets"]))
        clone = json.loads(json.dumps(data["presets"][first]))
        clone["name"] = name
        clone["description"] = description
        clone["created_at"] = datetime.now(timezone.utc).isoformat()
        clone["updated_at"] = clone["created_at"]
        # unique slug
        slug = _slugify(name)
        i = 1
        while slug in data["presets"]:
            slug = f"{_slugify(name)}_{i}"
            i += 1
        clone["slug"] = slug
        data["presets"][slug] = clone
        base = slug
    _write_presets_file(data)
    return base


def delete_preset(slug: str) -> bool:
    data = _read_presets_file()
    if slug in data.get("presets", {}) and slug != "default":
        del data["presets"][slug]
        _write_presets_file(data)
        return True
    return False


def clone_preset(slug: str, new_name: str) -> str:
    data = _read_presets_file()
    if slug not in data.get("presets", {}):
        return None
    clone = json.loads(json.dumps(data["presets"][slug]))
    clone["name"] = new_name
    new_slug = _slugify(new_name)
    i = 1
    while new_slug in data["presets"]:
        new_slug = f"{_slugify(new_name)}_{i}"
        i += 1
    clone["slug"] = new_slug
    clone["created_at"] = datetime.now(timezone.utc).isoformat()
    clone["updated_at"] = clone["created_at"]
    data["presets"][new_slug] = clone
    _write_presets_file(data)
    return new_slug


def _slugify(s: str) -> str:
    return (s or "").lower().replace(" ", "_").replace("&", "and").replace("/", "_").replace("-", "_")


def _get_preset_agents(conn, preset: str, custom) -> dict:
    adb = {}
    row_adb = conn.execute("SELECT value FROM state WHERE key=?", ("llm_agents",)).fetchone()
    if row_adb:
        try: adb = json.loads(row_adb["value"])
        except Exception as e:
            logging.getLogger(__name__).error('Fehler in Agenten-DB-Parsing: %s', e)
    w = list(_WORKER_AGENTS)
    if isinstance(custom, dict) and custom:
        for a, val in custom.items():
            adb[a] = val
    else:
        kdb = {}
        row_k = conn.execute("SELECT value FROM state WHERE key=?", ("llm_keys",)).fetchone()
        if row_k:
            try: kdb = json.loads(row_k["value"])
            except Exception as e:
                logging.getLogger(__name__).error('Fehler in LLM-Schlüssel-Parsing: %s', e)
        or_v = any(k.get("provider") == "openrouter" and k.get("valid") for k in (kdb.values() if isinstance(kdb, dict) else kdb))
        for a in w: adb[a] = {"provider": "auto", "model": "stage_2" if a != "coderag" else "stage_3"}
        t = load_presets().get("targets", {}).get(preset)
        if t and t[0] in w: adb[t[0]] = {"provider": "openrouter", "model": t[1]} if or_v else {"provider": "auto", "model": "stage_3"}
    return adb


def handle_preset_change(preset: str):
    from gnom_hub.db.connection import get_db_conn
    pdir = CONFIG_DIR / "presets"
    preset_file = pdir / f"{preset.lower().replace(' ', '_')}.json"
    with get_db_conn() as conn:
        conn.execute("BEGIN IMMEDIATE TRANSACTION")
        try:
            # NOTE: `active_preset` wurde früher zusätzlich in `soul_memory` geschrieben.
            # Das war redundant mit dem `state`-Tabellen-Eintrag (Source of Truth für
            # `active_preset` ist seit Router-Refactor `get_state_value("active_preset")`).
            # SoulAG-Validator + Permission-Check in save_soul_fact_smart prüfen den Wert
            # beim Einspeisen über die /api/soul/save-API. Innerhalb dieser Transaktion
            # wird nur noch die state-Tabelle atomar aktualisiert.
            conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)", ("active_preset", json.dumps(preset)))
            all_settings = {}
            row = conn.execute("SELECT value FROM state WHERE key=?", ("agent_settings",)).fetchone()
            if row:
                try: all_settings = json.loads(row["value"])
                except Exception as e:
                    logging.getLogger(__name__).error('Fehler in Agent-Settings-Parsing: %s', e)
            if preset_file.exists():
                with open(preset_file, encoding="utf-8") as f:
                    c = json.load(f)
                    if "agent_settings" in c:
                        for a_name, a_set in c["agent_settings"].items(): all_settings[a_name.lower()] = a_set
                        conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)", ("agent_settings", json.dumps(all_settings)))
            custom = None
            row_c = conn.execute("SELECT value FROM state WHERE key=?", (f"llm_preset_{preset}",)).fetchone()
            if row_c:
                try: custom = json.loads(row_c["value"])
                except Exception as e:
                    logging.getLogger(__name__).error('Fehler in Custom-Preset-Parsing: %s', e)
            adb = _get_preset_agents(conn, preset, custom)
            conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)", ("llm_agents", json.dumps(adb)))
            focus = load_presets().get("focus", {}).get(preset, "Allgemeine Unterstützung.")
            conn.execute("INSERT OR REPLACE INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (str(uuid.uuid4()), "default", "System", "system", "chat",
                          f"Preset gewechselt zu: **{preset}**.\n\nWorker angepasst: *{focus}*", datetime.now(timezone.utc).isoformat(), json.dumps({"type": "chat"})))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

