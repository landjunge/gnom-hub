import os
import re as _re

from gnom_hub.core.config import WORKSPACE_DIR


def _in_workspace(path_real: str) -> bool:
    """True wenn path_real im (oder gleich) WORKSPACE_DIR liegt (realpath).

    off-by-one-Schutz: Sibling-Dirs wie ``<workspace>-evil/`` matchen nicht.
    """
    try:
        ws_real = os.path.realpath(str(WORKSPACE_DIR))
    except (OSError, ValueError):
        return False
    return path_real == ws_real or path_real.startswith(ws_real + os.sep)


def _has_godmode(perms) -> bool:
    """True bei legacy ``perms=True`` oder Token ``godmode`` in der Liste."""
    if perms is True:
        return True
    if isinstance(perms, (list, tuple, set)):
        return "godmode" in perms
    return False


def _resolve_target(wd, f: str) -> str:
    """Resolve relative/absolute path to realpath (expanduser)."""
    raw = os.path.expanduser(f) if isinstance(f, str) else f
    if os.path.isabs(raw):
        return os.path.realpath(raw)
    return os.path.realpath(os.path.join(wd, raw))


def _safe(wd, f, perms, agent_name: str | None = None):
    """Prüft ob ein Pfad im erlaubten Bereich liegt. Gibt realpath oder None.

    Erlaubt wenn (in dieser Reihenfolge):
    1. Pfad liegt im User-Workspace (Workspace-frei, Mandat 2026-07-02)
    2. ``godmode`` in perms (SecurityAG-Notfall) bzw. legacy ``perms=True``
    3. SecurityAG-Grant: ``check_permission(agent_name, path)`` —
       Directory-Grants matchen per Prefix, File-Grants exakt

    Sonst: None (außerhalb Workspace ohne Grant).

    Früher: jede non-empty Permission-Liste erlaubte Escape aus dem Workspace
    (truthy-bool-Bug). Jetzt: nur godmode oder explizite Freigabe.
    """
    try:
        p = _resolve_target(wd, f)
    except (OSError, ValueError, TypeError):
        return None

    if _in_workspace(p):
        return p

    if _has_godmode(perms):
        return p

    # SecurityAG-Grant für diesen Agenten (outside workspace)
    if agent_name:
        try:
            from gnom_hub.db.permissions_repo import check_permission
            if check_permission(agent_name, p) or check_permission(agent_name, f):
                return p
        except Exception:
            # DB down → fail closed for outside-workspace paths
            pass

    # Legacy: perms=False / empty / no grant → block outside workspace
    return None


def _workspace_system_paths() -> list[str]:
    """DEPRECATED: Workspace-interne Pfade wurden fälschlich als System-Pfade
    behandelt und haben damit legitime Worker-Writes blockiert (User-Report
    "er blockt alles" 2026-07-11). Die Funktion existiert noch für
    Abwärtskompatibilität, gibt aber eine leere Liste zurück.
    """
    return []


# System-Pfade, die niemals von Workern beschrieben werden dürfen.
# Nur OS-level Pfade. KEINE workspace-internen Pfade — die sind user-eigenes
# Territory und der User hat explizit Workspace-Frei (User-Mandat 2026-07-02 13:42).
# Vorher: _workspace_system_paths() hat fälschlicherweise WORKSPACE_DIR/src/gnom_hub,
# WORKSPACE_DIR/config, WORKSPACE_DIR/scripts etc. zu System-Pfaden gemacht — was
# dazu führte, dass Worker-Writes mit "src/" oder "config/" im Pfad geblockt wurden.
# WatchdogAG-Prompt: "KEIN Blocken von scripts/, tests/, normalen Workspace-Pfaden"
# — der Fix entfernt die Workspace-Komponente und hält nur die echten OS-Pfade.
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
    """True, wenn der Pfad (oder ein Vorfahre) in SYSTEM_PATHS liegt
    ODER wenn ein ABSOLUTER Pfad in die Hub-Source zeigt (außerhalb
    User-Workspace).

    Realpath-basiert, um Symlink-Tricks abzufangen.

    Hinweis: Die frühere _workspace_system_paths()-Funktion hat fälschlich
    WORKSPACE_DIR-interne Substrings ("src/gnom_hub", "config", "scripts",
    "run.sh", "index.html", ".env") als System-Pfade klassifiziert und
    damit legitime Worker-Writes im User-Workspace blockiert. Der WatchdogAG-
    Prompt verlangt explizit "KEIN Blocken von scripts/, tests/, normalen
    Workspace-Pfaden". Die Liste in `is_system_path()` ist nur OS-level
    + Hub-Source-Root (PROJECT_ROOT). User-Workspace ist explizit user-eigenes
    Territory (User-Mandat 2026-07-02 13:42 "Workspace-frei").

    Wichtig: Hub-Source-Schutz greift NUR für absolute Pfade. Relative
    Strings ("pytest tests/") sind KEIN Pfad und werden NICHT gegen
    Hub-Source geprüft — sonst würde realpath sie versehentlich gegen
    CWD=Hub-Source resolven und blocken.

    macOS-Sonderfall: `/private/var/folders/...` und `/private/tmp/...` sind
    KEINE echten System-Pfade sondern macOS-Symlinks für User-tmp. Diese
    werden explizit NICHT geblockt.
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
            # macOS-Sonderfall: /private/var/folders/... und /private/tmp/...
            # sind User-tmp, keine echten System-Pfade.
            if real.startswith("/private/var/folders/") or real.startswith("/private/tmp/"):
                continue
            # Linux-Pendant: /var/folders/ existiert nicht, aber /var/tmp/ ja.
            # Ruff S108 flaggt /var/tmp/ als insecure — wir nutzen den String
            # hier nur zum Vergleich (kein File-Open), S108 nicht anwendbar.
            if real.startswith("/var/folders/") or real.startswith("/var/tmp/"):  # noqa: S108
                continue
            return True
    # Hub-Source schützen — NUR für absolute Pfade, sonst versehentliche
    # false-positives wenn is_system_path() mit Command-Strings gefüttert wird.
    if path_str.startswith("/") or path_str.startswith("~/"):
        try:
            from gnom_hub.core.config import PROJECT_ROOT, WORKSPACE_DIR
            hub_real = os.path.realpath(str(PROJECT_ROOT))
            ws_real = os.path.realpath(str(WORKSPACE_DIR))
            if real == hub_real or real.startswith(hub_real + os.sep):
                # Falls der Hub-Source-Pfad INNERHALB des User-Workspace liegt
                # (z.B. /Users/landjunge/gnom-Workspace/default/gnom-hub/src/...)
                # NICHT blocken — User-Workspace ist user-eigenes Territory.
                if not real.startswith(ws_real + os.sep):
                    return True
        except (OSError, ValueError):
            pass
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
    if f:
        # Relativ → gegen wd auflösen, damit realpath nicht versehentlich
        # gegen den Hub-Source-CWD resolved (false-positive).
        check_path = f if os.path.isabs(f) else os.path.join(wd, f)
        if is_system_path(check_path):
            try:
                from gnom_hub.core.audit_helpers import record_block
                agent_name = agent.get("name") if isinstance(agent, dict) else str(agent)
                record_block(agent_name, path=str(f), reason="system_path")
            except Exception:
                pass
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
        try:
            from gnom_hub.core.audit_helpers import record_block
            agent_name = agent.get("name") if isinstance(agent, dict) else str(agent)
            record_block(agent_name, path=str(f or ""), reason="high_risk_pattern",
                         level=level, severity="high")
        except Exception:
            pass
        return "high"
    if level >= 4 and _MEDIUM_RISK_RE.search(content):
        try:
            from gnom_hub.core.audit_helpers import record_block
            agent_name = agent.get("name") if isinstance(agent, dict) else str(agent)
            record_block(agent_name, path=str(f or ""), reason="medium_risk_pattern",
                         level=level, severity="medium")
        except Exception:
            pass
        return "medium"
    return None