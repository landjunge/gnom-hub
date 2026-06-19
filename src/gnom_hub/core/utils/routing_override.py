# routing_override.py — Handles simple text-based agent routing overrides
import os
from pathlib import Path
from gnom_hub.core.config import PROJECT_ROOT

def load_routing_from_txt() -> dict:
    # Precedence paths to check:
    # 1. Project config folder
    # 2. Project root folder
    # 3. User's Desktop
    paths_to_check = [
        Path(PROJECT_ROOT) / "config" / "routing.txt",
        Path(PROJECT_ROOT) / "routing.txt",
        Path.home() / "Desktop" / "routing.txt"
    ]
    
    routing_data = {}
    for p in paths_to_check:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or line.startswith("//"):
                            continue
                        
                        parts = None
                        if "=" in line:
                            parts = line.split("=", 1)
                        elif ":" in line:
                            parts = line.split(":", 1)
                            
                        if parts:
                            agent_key = parts[0].strip().lower()
                            val_str = parts[1].strip()
                            
                            provider = "auto"
                            model = "stage_3"
                            
                            # Parse format: provider | model or provider/model
                            if "|" in val_str:
                                v_parts = val_str.split("|", 1)
                                provider = v_parts[0].strip().lower()
                                model = v_parts[1].strip()
                            elif "/" in val_str:
                                v_parts = val_str.split("/", 1)
                                maybe_p = v_parts[0].strip().lower()
                                if maybe_p in ["lokal", "local", "openrouter", "deepseek", "openai", "anthropic", "gemini", "mistral", "auto"]:
                                    provider = maybe_p
                                    model = v_parts[1].strip()
                                else:
                                    model = val_str
                            else:
                                if val_str.lower() in ["lokal", "local", "openrouter", "deepseek", "openai", "anthropic", "gemini", "mistral", "auto"]:
                                    provider = val_str.lower()
                                else:
                                    model = val_str
                                    
                            if provider == "local":
                                provider = "lokal"
                                
                            routing_data[agent_key] = {"provider": provider, "model": model}
                # Precedence: stop at first found file
                break
            except Exception as e:
                print(f"Error loading routing.txt from {p}: {e}")
                
    return routing_data
