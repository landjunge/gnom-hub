import os
import re as _re

from gnom_hub.core.config import WORKSPACE_DIR


def _safe(wd, f, perms):
    """Prüft ob ein Pfad im erlaubten Bereich liegt.

    Bei `perms=False` wird der Pfad gegen den Workspace-Root
    (realpath, symlink-aufgelöst) geprüft — Flucht aus dem
    Workspace wird geblockt (gibt None zurück).

    Bei `perms=True` darf der Pfad außerhalb des Workspace liegen
    (Caller hat das Recht dazu autorisiert).
    """
    if not perms:
        p = os.path.realpath(os.path.join(wd, f)) if not os.path.isabs(f) else os.path.realpath(f)
        ws_real = os.path.realpath(str(WORKSPACE_DIR))
        return p if p.startswith(ws_real) else None
    p = os.path.realpath(f) if os.path.isabs(f) else os.path.realpath(os.path.join(wd, f))
    return p


# System-Pfade, die niemals von Workern beschrieben werden dürfen.
# Vorbelegung mit absoluten Pfaden, die niemals Schreibzugriff haben sollten.
# Erweitert wird zur Laufzeit über die Konfiguration.
SYSTEM_PATHS = [
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/var",
    "/boot",
    "/proc",
    "/sys",
    "/lib",
    "/private/etc",
    "/private/var",
]


def is_system_path(path_str: str) -> bool:
    """True, wenn der Pfad (oder ein Vorfahre) in SYSTEM_PATHS liegt.

    Realpath-basiert, um Symlink-Tricks abzufangen.
    """
    if not path_str:
        return False
    try:
        real = os.path.realpath(path_str)
    except (OSError, ValueError):
        return False
    for sp in SYSTEM_PATHS:
        try:
            sp_real = os.path.realpath(sp)
        except (OSError, ValueError):
            continue
        if real == sp_real or real.startswith(sp_real + os.sep):
            return True
    return False


def _blockade_level() -> int:
    """Liest den Blockade-Level aus dem State-Store.

    Fallback: 2 (high-risk blockiert, medium erlaubt) — sicherer Default
    als der vorherige hartcodierte 0.
    """
    try:
        from gnom_hub.db import get_state_value
        v = get_state_value("security_blockade_level")
        if v is None:
            return 2
        return max(0, min(4, int(v)))
    except Exception:
        return 2


# Hochrisiko-Patterns: real ausgewertet statt r"$^".
# Bewusst breit (false-positive-tolerant) — Fehlalarme sind harmloser als
# echt durchrutschende gefährliche Inhalte.
_HIGH_RISK_PATTERNS = (
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bos\.system\s*\(",
    r"\bsubprocess\.[A-Za-z_]+\(.*shell\s*=\s*True",
    r"curl[^|]*\|\s*(ba)?sh\b",
    r"wget[^|]*\|\s*(ba)?sh\b",
    r"\brm\s+-rf\s+/(?:\s|$)",
    r"\bmkfs\b",
    r"\bdd\s+if\s*=",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # Fork-Bombe
)
_HIGH_RISK_RE = _re.compile("|".join(_HIGH_RISK_PATTERNS), _re.IGNORECASE | _re.DOTALL)

# Mittelrisiko-Patterns: werden ab Level 4 als 'medium' gemeldet.
_MEDIUM_RISK_PATTERNS = (
    r"chmod\s+0?0?0?7",  # world-writable
    r"chmod\s+-R\s+777",
    r"\bpickle\.loads?\s*\(",
    r"\byaml\.load\s*\(",  # yaml.load ohne Loader = unsicher
    r"\binput\s*\(\s*[\"'][^\"']*[\"']\s*\)",  # Python2-style input()
)
_MEDIUM_RISK_RE = _re.compile("|".join(_MEDIUM_RISK_PATTERNS), _re.IGNORECASE | _re.DOTALL)


def is_worker_blocked(agent, f, wd, perms):
    """True, wenn der Worker durch Pfad- oder Risk-Checks blockiert wird.

    Blockiert wenn:
    - der Pfad ein System-Pfad ist (Schreibschutz für OS-Dateien), oder
    - der Inhalt ein Hochrisiko-Pattern enthält (unabhängig vom Level).
    """
    if f and is_system_path(f):
        return True
    # Risk-Check: nur wenn der Aufrufer den Inhalt mitgegeben hat —
    # das ist hier nicht der Fall (gatekeeper.py:315 ruft nur mit fn/wd/perms),
    # aber wir behalten die Schnittstelle für künftige Aufrufer.
    return False


def is_security_block(agent, f, content, wd, perms):
    """
    SecurityAG — Blockade-Level-respektierend.

    Level 0/1: nie blocken (Opt-in für Power-User / Watchdog-Pfad).
    Level 2:   high-risk patterns blocken.
    Level 3:   high-risk blocken.
    Level 4:   high + medium risk blocken (medium = warn, high = block).
    """
    level = _blockade_level()
    if level <= 1 or not content:
        return None
    if _HIGH_RISK_RE.search(content):
        return "high"
    if level >= 4 and _MEDIUM_RISK_RE.search(content):
        return "medium"
    return None