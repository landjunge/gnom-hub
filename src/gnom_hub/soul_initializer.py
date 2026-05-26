def get_agent_soul_path(agent_name: str) -> str:
    import os
    from gnom_hub.presentation.api.v1.workspace import get_workspace_dir
    wd = get_workspace_dir()
    agents_dir = os.path.join(wd, ".agents", agent_name.lower())
    os.makedirs(agents_dir, exist_ok=True)
    return os.path.join(agents_dir, "soul.json")

def _commit_soul_git(agent_name: str, path: str):
    import subprocess, os
    from pathlib import Path
    try:
        agent_dir = os.path.dirname(path)
        git_dir = Path(agent_dir) / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "init"], cwd=agent_dir, capture_output=True)
            subprocess.run(["git", "config", "user.name", f"{agent_name} Soul"], cwd=agent_dir, capture_output=True)
            subprocess.run(["git", "config", "user.email", f"{agent_name.lower()}@gnom-hub.local"], cwd=agent_dir, capture_output=True)
        
        subprocess.run(["git", "add", "soul.json"], cwd=agent_dir, capture_output=True)
        diff_res = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "soul.json"] if (git_dir / "refs/heads/master").exists() or (git_dir / "refs/heads/main").exists() or subprocess.run(["git", "rev-parse", "HEAD"], cwd=agent_dir, capture_output=True).returncode == 0 else ["git", "diff", "--cached", "--quiet"], cwd=agent_dir)
        if diff_res.returncode != 0 or not (git_dir / "index").exists():
            subprocess.run([
                "git", "commit", 
                "-m", f"Update Soul config for {agent_name}"
            ], cwd=agent_dir, capture_output=True)
    except Exception as e:
        print(f"Git commit for agent soul failed: {e}")

def get_soul(agent_name: str) -> dict:
    import os, json
    from .db import get_language
    from .agent_definitions import AGENT_DEFINITIONS
    
    lang = get_language()
    name_lower = agent_name.lower()
    
    default_def = AGENT_DEFINITIONS.get(name_lower, {})
    role = default_def.get("role", "default")
    
    lang_data = default_def.get(lang, default_def.get("de", {}))
    character = lang_data.get("character", "Agent")
    directive = lang_data.get("directive", "Hilf dem Schwarm." if lang == "de" else "Help the swarm.")
    permissions = lang_data.get("permissions", ["read"])
    
    path = get_agent_soul_path(agent_name)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                dirty = False
                if "role" not in data: data["role"] = role; dirty = True
                if "character" not in data: data["character"] = character; dirty = True
                if "directive" not in data: data["directive"] = directive; dirty = True
                if "permissions" not in data: data["permissions"] = permissions; dirty = True
                if "breakpoints" not in data: data["breakpoints"] = []; dirty = True
                
                if dirty:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                
                _commit_soul_git(agent_name, path)
                return data
        except Exception as e:
            print(f"Error loading soul.json for {agent_name}: {e}")
    
    default_soul = {
        "role": role,
        "character": character,
        "directive": directive,
        "permissions": permissions,
        "breakpoints": []
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_soul, f, indent=2, ensure_ascii=False)
        _commit_soul_git(agent_name, path)
    except Exception as e:
        print(f"Error writing soul.json for {agent_name}: {e}")
        
    return default_soul

class DynamicSouls(dict):
    def _active_dict(self):
        from .agent_definitions import AGENT_DEFINITIONS
        res = {}
        for k in AGENT_DEFINITIONS.keys():
            res[k] = get_soul(k)
        return res

    def items(self): return self._active_dict().items()
    def keys(self): return self._active_dict().keys()
    def values(self): return self._active_dict().values()
    def get(self, k, d=None): return self._active_dict().get(k, d)
    def __getitem__(self, k): return self._active_dict()[k]
    def __iter__(self): return iter(self._active_dict())
    def __len__(self): return len(self._active_dict())
    def __contains__(self, k): return k in self._active_dict()

SOULS = DynamicSouls()

def check_and_wait_breakpoint(agent_name: str, operation: str, detail: str):
    import time
    from .db import get_active_project, add_chat_message, get_all_agents, set_agent_status
    
    soul = get_soul(agent_name)
    breakpoints = soul.get("breakpoints", [])
    if operation in breakpoints:
        set_agent_status(agent_name, "paused")
        proj = get_active_project()
        message = (f"🛑 [BREAKPOINT] Agent **{agent_name}** pausiert vor der Operation **{operation}** ({detail}).\n"
                   f"Antworte `@@resume {agent_name}` im Chat oder klicke auf **Resume** im Dashboard des Agenten.")
        add_chat_message(proj, "System", "system", "chat", message)
        
        while True:
            agents = get_all_agents()
            current_agent = next((a for a in agents if a["name"].lower() == agent_name.lower()), None)
            if not current_agent:
                break
            if current_agent.get("status") not in ["paused", "offline"]:
                break
            time.sleep(0.5)
            
        set_agent_status(agent_name, "busy")

