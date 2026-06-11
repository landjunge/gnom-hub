import os; from gnom_hub.core.config import WORKSPACE_DIR
import re as _re

def _safe(wd, f, perms):
    """Prüft ob ein Pfad im erlaubten Bereich liegt — ALLES erlaubt für Worker mit godmode/run."""
    if not perms:
        p = os.path.realpath(os.path.join(wd, f)) if not os.path.isabs(f) else os.path.realpath(f)
        return p if p.startswith(os.path.realpath(str(WORKSPACE_DIR))) else None
    p = os.path.realpath(f) if os.path.isabs(f) else os.path.realpath(os.path.join(wd, f))
    return p

SYSTEM_PATHS = ["src/gnom_hub", "config/", "scripts/", "run.sh", "index.html", ".env"]

def is_system_path(path_str: str) -> bool:
    """Prüft ob ein Pfad auf geschützte Systemdateien zeigt."""
    return any(part in path_str.replace("\\", "/").lower() for part in SYSTEM_PATHS)

def _blockade_level() -> int:
    from gnom_hub.db import get_state_value
    return int(get_state_value("blockade_level", 0))

def is_worker_blocked(agent, f, wd, perms):
    """
    WatchdogAG — Blockade-Level-respektierend.
    Level 0: nie blocken
    Level 1+: System-Pfad-Schutz aktiv
    """
    level = _blockade_level()
    if level == 0:
        return False
    return is_system_path(f)

# Gefährliche Code-Patterns — aufgeteilt in hohes und mittleres Risiko
_HIGH_RISK_RE = _re.compile(
    r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|[a-zA-Z]*-r[a-zA-Z]*-f[a-zA-Z]*)"
    r"|subprocess\.(call|run|Popen|check_output)"
    r"|os\.system\s*\(|os\.popen\s*\(|os\.exec[lvpe]*\s*\(|os\.spawn[lvpe]*\s*\("
    r"|eval\s*\(|exec\s*\(|compile\s*\(.*?(?:eval|exec)"
    r"|shutil\.rmtree\s*\(|shutil\.move\s*\([^,]*,[^,]*/(?:etc|usr|bin|sbin|var|root|tmp)"
    r"|chmod\s+[0-7]*7[0-7]*7\s"
    r"|>\s*/(?:etc|usr|bin|sbin|var|dev)/|>>\s*/(?:etc|usr|bin|sbin|var|dev)/"
    r"|curl.*\|\s*(?:ba)?sh|wget.*\|\s*(?:ba)?sh"
    r"|dd\s+if=|mkfs\.|:\(\)\s*\{\s*:\|:&\s*\};:"
    r"|input\s*\(.*?exec|__builtins__|__globals__|__getattribute__",
    _re.IGNORECASE | _re.DOTALL
)

_MEDIUM_RISK_RE = _re.compile(
    r"__import__\s*\("
    r"|pickle\.(?:load|dumps)\s*\("
    r"|marshal\.(?:load|dumps)\s*\("
    r"|base64\..*decode"
    r"|bytes\.decode\s*\(.*?\)\s*"
    r"|shutil\.move\s*\("
    r"|os\.remove\s*\(|os\.unlink\s*\(",
    _re.IGNORECASE | _re.DOTALL
)


def is_security_block(agent, f, content, wd, perms):
    """
    SecurityAG — Blockade-Level-respektierend.
    Level 0: nie blocken
    Level 1: nie blocken (nur system paths)
    Level 2: high-risk patterns blocken
    Level 3: high + medium risk patterns blocken (medium = warn)
    Level 4: high + medium risk patterns blocken (medium = block)
    """
    level = _blockade_level()
    if level == 0 or level == 1 or not content:
        return None
    if _HIGH_RISK_RE.search(content):
        return "high"
    if level >= 3 and _MEDIUM_RISK_RE.search(content):
        return "medium" if level == 3 else "high"
    return None
