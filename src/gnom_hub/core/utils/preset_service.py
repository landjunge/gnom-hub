# preset_service.py — Preset management loader and trigger actions
import logging
import os, json
from gnom_hub.db import get_state_value, set_state_value, save_soul_fact, add_chat_message
from gnom_hub.core.config import CONFIG_DIR
def load_presets():
    path = os.path.join(os.path.dirname(__file__), "presets.json")
    with open(path, "r", encoding="utf-8") as f: data = json.load(f)
    pdir = CONFIG_DIR / "presets"
    if pdir.exists():
        for fn in [f for f in os.listdir(pdir) if f.endswith(".json")]:
            try:
                with open(pdir / fn, "r", encoding="utf-8") as f: c = json.load(f)
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
    return load_presets().get("prompts", {}).get(preset, {}).get(agent_name, "")
def _get_preset_agents(conn, preset: str, custom) -> dict:
    adb = {}
    row_adb = conn.execute("SELECT value FROM state WHERE key=?", ("llm_agents",)).fetchone()
    if row_adb:
        try: adb = json.loads(row_adb["value"])
        except Exception as e:
            logging.getLogger(__name__).error('Fehler in Agenten-DB-Parsing: %s', e)
    w = ["coderag", "researcherag", "writerag", "editorag"]
    if isinstance(custom, dict) and custom:
        for a in w:
            if a in custom: adb[a] = custom[a]
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
    from datetime import datetime, timezone
    import uuid
    pdir = CONFIG_DIR / "presets"
    preset_file = pdir / f"{preset.lower().replace(' ', '_')}.json"
    with get_db_conn() as conn:
        conn.execute("BEGIN IMMEDIATE TRANSACTION")
        try:
            conn.execute("INSERT OR REPLACE INTO soul_memory (key, value, timestamp, priority, agent) VALUES (?, ?, ?, ?, ?)",
                         ("active_preset", preset, datetime.now(timezone.utc).isoformat(), "high", "System"))
            conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)", ("active_preset", json.dumps(preset)))
            all_settings = {}
            row = conn.execute("SELECT value FROM state WHERE key=?", ("agent_settings",)).fetchone()
            if row:
                try: all_settings = json.loads(row["value"])
                except Exception as e:
                    logging.getLogger(__name__).error('Fehler in Agent-Settings-Parsing: %s', e)
            if preset_file.exists():
                with open(preset_file, "r", encoding="utf-8") as f:
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
