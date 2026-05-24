# path_validator.py — Workspace-basierte Pfadvalidierung
import os; from .config import WORKSPACE_DIR

def _safe(wd, f, perms):
    if "godmode" in perms:
        import logging
        logging.getLogger("gnom_hub.action_write").warning(
            "godmode permission is deprecated — treated as 'run'")
        perms = [p for p in perms if p != "godmode"] + ["run"]
    if os.path.isabs(f) and "run" in perms:
        p = os.path.realpath(f)
        ws_root = os.path.realpath(str(WORKSPACE_DIR))
        return p if p.startswith(ws_root) else None
    p = os.path.realpath(os.path.join(wd, f))
    return p if p.startswith(os.path.realpath(wd)) else None
