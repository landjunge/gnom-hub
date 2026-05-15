"""Role Prompt Implanter — schreibt System-Prompt in Agent-Dateien."""
import os
from pathlib import Path
HOME = Path.home()
TARGETS = ["soul.md", "SOUL.md", "system.md", "core.md"]
SEP = "\n\n---\n\n"
def _find_agent_dir(name):
    """Sucht ~/.{name_lower}/ als Agent-Verzeichnis."""
    d = HOME / f".{name.lower()}"
    return d if d.is_dir() else None
def _find_target(agent_dir):
    """Sucht soul.md → system.md → core.md in agent_dir."""
    for t in TARGETS:
        p = agent_dir / t
        if p.exists(): return p
    return None
def implant(agent_name, prompt):
    """Implantiert System-Prompt in Agent-Datei. Returns Pfad oder None."""
    d = _find_agent_dir(agent_name)
    if not d: return None
    target = _find_target(d)
    if not target: target = d / "soul.md"
    marker_start, marker_end = "<!-- GNOM-HUB ROLE START -->", "<!-- GNOM-HUB ROLE END -->"
    block = f"{marker_start}\n{prompt}\n{marker_end}"
    if target.exists():
        content = target.read_text(encoding="utf-8")
        if marker_start in content:
            import re
            content = re.sub(f"{marker_start}.*?{marker_end}", block, content, flags=re.DOTALL)
        else:
            content = block + SEP + content
    else:
        content = block + "\n"
    target.write_text(content, encoding="utf-8")
    return str(target)
