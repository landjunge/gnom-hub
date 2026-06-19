# compiler.py — Compiles a Gnom-Hub instance into a standalone SuperGNOM
import os
import shutil
import sqlite3
import json, logging
from pathlib import Path
from gnom_hub.core.config import PROJECT_ROOT, DB_PATH
from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS

def to_yaml(data, indent=0) -> str:
    lines = []
    spacer = " " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{spacer}{k}:")
                lines.append(to_yaml(v, indent + 2))
            else:
                if isinstance(v, str) and ("\n" in v or ":" in v or "#" in v or " " in v):
                    lines.append(f"{spacer}{k}: '{v}'")
                else:
                    lines.append(f"{spacer}{k}: {v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{spacer}-")
                lines.append(to_yaml(item, indent + 2))
            else:
                if isinstance(item, str) and ("\n" in item or ":" in item or "#" in item or " " in item):
                    lines.append(f"{spacer}- '{item}'")
                else:
                    lines.append(f"{spacer}- {item}")
    return "\n".join(lines)

def get_dependencies() -> list:
    deps = []
    try:
        with open(PROJECT_ROOT / "pyproject.toml", "r", encoding="utf-8") as f:
            lines = f.readlines()
        in_deps = False
        for line in lines:
            line = line.strip()
            if "dependencies = [" in line:
                in_deps = True
                continue
            if in_deps:
                if "]" in line:
                    break
                # Extract package name (remove quotes, commas, trailing comments)
                clean = line.replace('"', '').replace("'", "").replace(",", "").split("#")[0].strip()
                if clean:
                    deps.append(clean)
    except Exception:
        # Fallback default dependencies
        deps = [
            "fastapi>=0.100.0", "uvicorn>=0.20.0", "pydantic>=2.0.0", 
            "requests>=2.28.0", "psutil>=5.9.0", "python-dotenv>=1.0.0", 
            "httpx>=0.24.0", "sentence-transformers>=3.0.0",
            "faiss-cpu>=1.7.0", "numpy<2"
        ]
    return deps

def ollama_get_models_with_sizes() -> list:
    """Holt alle lokalen Ollama-Modelle + ihre Größen in GB.
    Returns: [{"name": "llama3.2:3b", "size_gb": 1.88}, ...]
    """
    try:
        import httpx
        r = httpx.get("http://127.0.0.1:11434/api/tags", timeout=3.0)
        if r.status_code == 200:
            result = []
            for m in r.json().get("models", []):
                size_gb = round(m.get("size", 0) / 1024 / 1024 / 1024, 2)
                result.append({"name": m["name"], "size_gb": size_gb})
            return result
    except Exception as e:
        logging.getLogger(__name__).error('Ollama-Abfrage fehlgeschlagen: %s', e)
    return []


def routing_get_models_used() -> list:
    """Liest config/routing.txt und gibt alle model-Werte zurück (deduped)."""
    from gnom_hub.core.config import CONFIG_DIR
    routing_file = CONFIG_DIR / "routing.txt"
    models = set()
    if routing_file.exists():
        for line in routing_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            val = line.split("=", 1)[1].strip()
            for part in val.split("|"):
                m = part.strip()
                if m and m != "minimax" and m != "ollama" and m != "deepseek":
                    models.add(m)
    return sorted(models)


def intersect_ollama_routing() -> dict:
    """Schnittmenge Ollama-Modelle ∩ routing-Modelle.
    Returns: {"matches": [{"name","size_gb","source":"both"}],
              "ollama_only": [...], "routing_only": [...],
              "total_size_gb": float}
    """
    ollama = {m["name"]: m["size_gb"] for m in ollama_get_models_with_sizes()}
    routing = set(routing_get_models_used())

    matches = []
    for name in sorted(ollama.keys() & routing):
        matches.append({"name": name, "size_gb": ollama[name], "source": "both"})

    ollama_only = [
        {"name": n, "size_gb": s, "source": "ollama"}
        for n, s in sorted(ollama.items()) if n not in routing
    ]
    routing_only = [{"name": n, "source": "routing"} for n in sorted(routing) if n not in ollama]

    return {
        "matches": matches,
        "ollama_only": ollama_only,
        "routing_only": routing_only,
        "total_ollama_size_gb": round(sum(ollama.values()), 2),
    }


def bake_ollama_models(dist_dir: Path, selected: list) -> dict:
    """Bereitet Ollama-Modelle für den USB-Stick vor.
    Echte Installation = ollama pull auf Zielsystem. Wir liefern nur:
      - models-info.json mit den Namen
      - run.sh ruft beim Start automatisch 'ollama pull' für fehlende Modelle
    KEINE Symlinks/Blo bs auf den Stick — die wären auf einem anderen Mac tot.
    Returns: {"mode": "auto_pull", "size_gb": float, "models": [...]}
    """
    selected = [s for s in (selected or []) if s]
    if not selected:
        return {"mode": "none", "size_gb": 0.0, "models": []}

    ollama_index = {m["name"]: m for m in ollama_get_models_with_sizes()}
    valid = [s for s in selected if s in ollama_index]
    total_gb = round(sum(ollama_index[s]["size_gb"] for s in valid), 2)

    info = {
        "selected": valid,
        "total_gb": total_gb,
        "mode": "auto_pull",
        "note": "Ollama pull wird beim ersten Start automatisch ausgefuehrt. Internet erforderlich.",
        "models": [
            {"name": m, "size_gb": ollama_index[m]["size_gb"]}
            for m in valid
        ],
    }

    (dist_dir / "models-info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def bake_supergnom(name: str, template: str = "chat", selected_models: list = None) -> str:
    # 1. Normalise name
    safe_name = "".join([c if c.isalnum() or c == "_" else "" for c in name.lower()]).strip("_")
    if not safe_name:
        raise ValueError("Ungültiger Name für den SuperGNOM.")

    dist_dir = PROJECT_ROOT / "dist" / f"supergnom_{safe_name}"
    dist_dir.mkdir(parents=True, exist_ok=True)
    src_dest = dist_dir / "src"
    if src_dest.exists():
        shutil.rmtree(src_dest)
    shutil.copytree(PROJECT_ROOT / "src", src_dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))

    # Copy agents folder structure
    agents_dest = dist_dir / "agents"
    if agents_dest.exists():
        shutil.rmtree(agents_dest)
    shutil.copytree(PROJECT_ROOT / "agents", agents_dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))

    # Copy config folder structure (excluding keys and environment files)
    cfg_dest = dist_dir / "config"
    if cfg_dest.exists():
        shutil.rmtree(cfg_dest)
    shutil.copytree(PROJECT_ROOT / "config", cfg_dest, ignore=shutil.ignore_patterns("*.json", ".env*"))

    # Recreate isolated user directory structure for portable operation
    gnom_home = dist_dir / ".gnom-hub"
    data_dir = gnom_home / "data"
    run_dir = gnom_home / "run"
    data_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Copy database file to distribution package
    db_dest = data_dir / "gnomhub.db"
    shutil.copy2(DB_PATH, db_dest)

    # Create local workspace directory
    workspace_dest = dist_dir / "gnom_workspace"
    workspace_dest.mkdir(parents=True, exist_ok=True)

    # Clean temporary and session-bound tables in target DB copy
    try:
        conn = sqlite3.connect(str(db_dest))
        for tbl in ["audit_log", "explainable_outputs", "graceful_degradation_failures", 
                    "token_budget_logs", "token_budget_alerts", "showbox_presentations"]:
            try:
                conn.execute(f"DELETE FROM {tbl}")
            except sqlite3.OperationalError as e:
                logging.getLogger(__name__).error('Fehler in bake_supergnom (Tabelle löschen): %s', e)
        try:
            conn.execute("DELETE FROM chat WHERE id NOT IN (SELECT id FROM chat ORDER BY timestamp DESC LIMIT 1000)")
        except sqlite3.OperationalError as e:
            logging.getLogger(__name__).error('Fehler in bake_supergnom (Chat löschen): %s', e)
        try:
            conn.execute("DELETE FROM soul_memory WHERE key NOT IN ('active_preset', 'approved_system_paths', 'approved_security_writes', 'approved_security_commands')")
        except sqlite3.OperationalError as e:
            logging.getLogger(__name__).error('Fehler in bake_supergnom (soul_memory löschen): %s', e)
        conn.execute("DELETE FROM state WHERE key NOT IN ('active_preset', 'agent_settings')")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error cleaning DB: {e}")

    comp_defs_dummy = {}
    try:
        import hashlib
        from gnom_hub.core.utils.evolution_v2 import get_active_version
        
        compiled_defs = {}
        prompt_hashes = {}
        
        for k, v in AGENT_DEFINITIONS.items():
            compiled_defs[k] = v.copy()
            active_v = get_active_version(v["name"])
            if active_v:
                evolved_prompt = active_v.base_prompt + "\n" + "\n".join(active_v.modifications)
                compiled_defs[k]["sys_prompt"] = evolved_prompt
                print(f"Baking evolved prompt for {v['name']} (version {active_v.id})")
            
            p_bytes = compiled_defs[k]["sys_prompt"].encode("utf-8")
            prompt_hashes[v["name"]] = hashlib.sha256(p_bytes).hexdigest()
            
        target_def_file = src_dest / "gnom_hub" / "agents" / "agent_definitions.py"
        with open(target_def_file, "w", encoding="utf-8") as f:
            f.write(f"AGENT_DEFINITIONS = {repr(compiled_defs)}\n")
            
        with open(cfg_dest / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(prompt_hashes, f, indent=2)
    except Exception as e:
        print(f"Error baking prompts: {e}")

    # Copy package configurations
    shutil.copy2(PROJECT_ROOT / "pyproject.toml", dist_dir / "pyproject.toml")

    # Bake Ollama models (auto-detect: <2GB embedded, else linker)
    try:
        models_info = bake_ollama_models(dist_dir, selected_models)
        config_data["ollama_models"] = models_info
        with open(dist_dir / "supergnom_config.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.getLogger(__name__).error('Bake Ollama-Modelle fehlgeschlagen: %s', e)

    # Generate custom static configuration file (for backward compatibility)
    config_data = {
        "name": safe_name,
        "template": template,
        "baked_at": os.popen("date").read().strip(),
    }
    with open(dist_dir / "supergnom_config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

    # Generate cross-platform yaml configuration file containing locked models & dependencies
    try:
        try:
            from gnom_hub.db import get_state_value
            custom_models = get_state_value("llm_agents") or {}
        except Exception:
            custom_models = {}
        
        models_lock = {}
        for k, v in AGENT_DEFINITIONS.items():
            agent_name = v["name"]
            model_info = custom_models.get(agent_name.lower(), {})
            models_lock[agent_name] = model_info.get("model") or v.get("model", "ollama/deepseek-r1")
    except Exception:
        models_lock = {}

    supergnom_yaml_data = {
        "name": safe_name,
        "template": template,
        "baked_at": config_data["baked_at"],
        "models": models_lock,
        "dependencies": get_dependencies(),
        "prompt_hashes": prompt_hashes if 'prompt_hashes' in locals() else {}
    }
    with open(dist_dir / "supergnom.yaml", "w", encoding="utf-8") as f:
        f.write(to_yaml(supergnom_yaml_data))

    # Write custom portable .env configuration file
    env_content = (
        f"SUPERGNOM_MODE=True\n"
        f"GNOM_HUB_HOME=./.gnom-hub\n"
        f"PORT=3003\n"
        f"HOST=127.0.0.1\n"
        f"DEFAULT_LLM_PROVIDER={os.getenv('DEFAULT_LLM_PROVIDER', 'ollama')}\n"
    )
    if os.getenv("DEEPSEEK_API_KEY"):
        env_content += f"DEEPSEEK_API_KEY={os.getenv('DEEPSEEK_API_KEY')}\n"
    if os.getenv("OPENROUTER_API_KEY"):
        env_content += f"OPENROUTER_API_KEY={os.getenv('OPENROUTER_API_KEY')}\n"
    if os.getenv("OLLAMA_BASE_URL"):
        env_content += f"OLLAMA_BASE_URL={os.getenv('OLLAMA_BASE_URL')}\n"
    
    with open(cfg_dest / ".env", "w", encoding="utf-8") as f:
        f.write(env_content)

    # Write keys.txt for easy API key access
    keys_lines = []
    if os.getenv("DEEPSEEK_API_KEY"):
        keys_lines.append(f"DEEPSEEK_API_KEY={os.getenv('DEEPSEEK_API_KEY')}")
    if os.getenv("OPENROUTER_API_KEY"):
        keys_lines.append(f"OPENROUTER_API_KEY={os.getenv('OPENROUTER_API_KEY')}")
    if keys_lines:
        with open(dist_dir / "keys.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(keys_lines) + "\n")

    # Write Unix execution startup script (run.sh)
    run_sh_content = (
        "#!/bin/bash\n"
        "DIR=\"$( cd \"$( dirname \"${BASH_SOURCE[0]}\" )\" >/dev/null 2>&1 && pwd )\"\n"
        "cd \"$DIR\"\n"
        "export GNOM_HUB_HOME=\"$DIR/.gnom-hub\"\n"
        "export SUPERGNOM_MODE=True\n"
        "export GNOM_HUB_PORT=3003\n"
        "export PORT=3003\n"
        "export PYTHONPATH=\"src:.:\\$PYTHONPATH\"\n"
        "\n"
        "# ── ONLINE/OFFLINE DETECTION ──\n"
        "MODE=\"ONLINE\"\n"
        "if curl -s --connect-timeout 3 https://api.deepseek.com > /dev/null 2>&1; then\n"
        "  echo \"🌐 Internet: ONLINE → DeepSeek\"\n"
        "  export DEFAULT_LLM_PROVIDER=deepseek\n"
        "else\n"
        "  echo \"📡 Internet: OFFLINE → lokales Ollama\"\n"
        "  export DEFAULT_LLM_PROVIDER=ollama\n"
        "  MODE=\"OFFLINE\"\n"
        "fi\n"
        "\n"
        "# ── USB-STICK DETECTION ──\n"
        "if [[ \"$DIR\" == /Volumes/* ]] || [[ \"$DIR\" == /media/* ]]; then\n"
        "  echo \"💾 USB-Stick erkannt → bevorzugt lokale Ressourcen\"\n"
        "  export PREFER_LOCAL=true\n"
        "  MODE=\"${MODE} (USB)\"\n"
        "fi\n"
        "\n"
        "if [ ! -d \".venv\" ]; then\n"
        "  echo '📦 Erstelle venv...'\n"
        "  python3 -m venv .venv\n"
        "  source .venv/bin/activate\n"
        "  pip install -q fastapi uvicorn pydantic requests python-dotenv psutil httpx python-multipart\n"
        "else\n"
        "  source .venv/bin/activate\n"
        "fi\n"
        "\n"
        "# ── OLLAMA MODEL LADEN (falls models-info.json existiert) ──\n"
        "if [ -f \"models-info.json\" ]; then\n"
        "  if command -v ollama &>/dev/null; then\n"
        "    echo '🤖 Prüfe Ollama-Modelle...'\n"
        "    EXISTING=$(ollama list 2>/dev/null | awk 'NR>1 {print $1}')\n"
        "    NEEDED=$(python3 -c \"import json; d=json.load(open('models-info.json')); print('\\n'.join(m['name'] for m in d.get('models',[])))\" 2>/dev/null)\n"
        "    for m in $NEEDED; do\n"
        "      if ! echo \"$EXISTING\" | grep -q \"^${m%%:*}$\"; then\n"
        "        echo \"⬇️  Lade $m ...\"\n"
        "        ollama pull \"$m\"\n"
        "      else\n"
        "        echo \"✅ $m bereits vorhanden\"\n"
        "      fi\n"
        "    done\n"
        "  else\n"
        "    echo '⚠️  Ollama nicht installiert. Installiere von https://ollama.com'\n"
        "  fi\n"
        "fi\n"
        "\n"
        "# ── START ──\n"
        "echo \"🚀 Starte SuperGNOM ($MODE)...\"\n"
        "python3 -m uvicorn gnom_hub.api.app:app --host 127.0.0.1 --port 3003 &\n"
        "sleep 4\n"
        "\n"
        "# ── MODE IM CHAT ANZEIGEN ──\n"
        "if [ \"$MODE\" != \"ONLINE\" ]; then\n"
        "  curl -s -X POST http://127.0.0.1:3003/api/chat \\\n"
        "    -H \"Content-Type: application/json\" \\\n"
        "    -d \"{\\\"content\\\":\\\"📡 **$MODE** — $([ \"$DEFAULT_LLM_PROVIDER\" = \"ollama\" ] && echo 'Lokales Ollama aktiv' || echo 'DeepSeek online')\\\",\\\"sender\\\":\\\"System\\\"}\" \\\n"
        "    > /dev/null 2>&1\n"
        "fi\n"
        "\n"
        "echo \"✅ SuperGNOM bereit: http://127.0.0.1:3003\"\n"
        "if command -v open &>/dev/null; then open \"http://127.0.0.1:3003\"; fi\n"
        "wait\n"
    )
    run_sh_path = dist_dir / "run.sh"
    with open(run_sh_path, "w", encoding="utf-8") as f:
        f.write(run_sh_content)
    os.chmod(run_sh_path, 0o755)

    # Write README.txt
    readme_content = (
        f"SUPERGNOM: {safe_name}\n"
        f"Gebacken am: {os.popen('date').read().strip()}\n"
        f"\n"
        f"START (Mac/Linux):\n"
        f"  bash run.sh\n"
        f"\n"
        f"START (Windows):\n"
        f"  run.bat\n"
        f"\n"
        f"Der SuperGNOM startet auf http://127.0.0.1:3003\n"
        f"\n"
        f"MODI:\n"
        f"  ONLINE  — Internet verfügbar → DeepSeek Cloud-LLM\n"
        f"  OFFLINE — Kein Internet → lokales Ollama (muss installiert sein)\n"
        f"  USB     — Von USB-Stick gestartet → bevorzugt lokale Ressourcen\n"
        f"\n"
        f"LLM-MODELLE:\n"
        f"  models-info.json  — gewählte Ollama-Modelle\n"
        f"  Beim ersten Start auf neuem Mac: 'ollama pull' wird automatisch ausgeführt\n"
        f"  Internet erforderlich beim ersten Start (~XX GB Download)\n"
        f"\n"
        f"STRUKTUR:\n"
        f"  run.sh / run.bat  — Start-Skripte\n"
        f"  keys.txt          — API-Keys (nicht teilen!)\n"
        f"  config/           — Agenten-Konfiguration\n"
        f"  agents/           — 8 Gnom-Agenten\n"
        f"  models-info.json  — Liste der zu ladenden Ollama-Modelle\n"
        f"  gnom_workspace/   — Arbeitsverzeichnis\n"
        f"  .gnom-hub/        — Datenbank\n"
        f"\n"
        f"STOPPEN:\n"
        f"  pkill -f gnom_hub\n"
        f"\n"
        f"PRESETS: config/presets/ — hier eigene Konfigurationen ablegen\n"
        f"KEYS:    keys.txt — API-Key für Cloud-LLMs eintragen\n"
    )
    with open(dist_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)

    # Write Windows execution startup script (run.bat)
    run_bat_content = (
        "@echo off\n"
        "cd /d \"%~dp0\"\n"
        "set GNOM_HUB_HOME=%~dp0.gnom-hub\n"
        "set SUPERGNOM_MODE=True\n"
        "set GNOM_HUB_PORT=3003\n"
        "set PORT=3003\n"
        "set PYTHONPATH=src;%PYTHONPATH%\n"
        "if not exist .venv (\n"
        "  echo Erstelle venv...\n"
        "  python -m venv .venv\n"
        "  call .venv\\Scripts\\activate.bat\n"
        "  pip install fastapi uvicorn pydantic requests python-dotenv psutil httpx python-multipart\n"
        ") else (\n"
        "  call .venv\\Scripts\\activate.bat\n"
        ")\n"
        "echo Starte SuperGNOM...\n"
        "python -m uvicorn gnom_hub.api.app:app --host 127.0.0.1 --port 3003\n"
    )
    run_bat_path = dist_dir / "run.bat"
    with open(run_bat_path, "w", encoding="utf-8") as f:
        f.write(run_bat_content)

    return str(dist_dir)
