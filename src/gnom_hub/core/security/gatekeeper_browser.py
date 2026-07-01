# gatekeeper_browser.py — Browser script safety verification
# Static analysis + AST check gates dangerous calls before the script is even written to disk.
# Approved scripts are run in a subprocess with cwd=workspace, no shell, no env-injection.
import ast
import hashlib
import logging
import re

from gnom_hub.agents.capability_manager import request_capability
from gnom_hub.db import add_chat_message

_log = logging.getLogger(__name__)

# Patterns we never want in a worker-authored browser script.
# Each entry: (regex, human-readable reason)
_FORBIDDEN_PATTERNS = [
    (re.compile(r"\bos\s*\.\s*system\s*\(", re.IGNORECASE), "os.system() shell escape"),
    (re.compile(r"\bos\s*\.\s*exec[lvpea]+\s*\(", re.IGNORECASE), "os.exec*() shell escape"),
    (re.compile(r"\bos\s*\.\s*spawn\s*\.", re.IGNORECASE), "os.spawn*() shell escape"),
    (re.compile(r"\bos\s*\.\s*popen\s*\(", re.IGNORECASE), "os.popen() shell escape"),
    (re.compile(r"\bpty\s*\.\s*spawn\s*\(", re.IGNORECASE), "pty.spawn() shell escape"),
    (re.compile(r"\bsubprocess\s*\.", re.IGNORECASE), "subprocess call (shell escape risk)"),
    (re.compile(r"\beval\s*\(", re.IGNORECASE), "eval() arbitrary code execution"),
    (re.compile(r"\bexec\s*\(", re.IGNORECASE), "exec() arbitrary code execution"),
    (re.compile(r"\b__import__\s*\(", re.IGNORECASE), "dynamic import"),
    (re.compile(r"\bcompile\s*\(", re.IGNORECASE), "compile() then exec"),
    (re.compile(r"\bopen\s*\([^)]*['\"]\s*[/~]"), "open() on absolute/system path"),
    (re.compile(r"\bos\s*\.\s*remove\s*\(", re.IGNORECASE), "file deletion via os.remove"),
    (re.compile(r"\bshutil\s*\.\s*rmtree\s*\(", re.IGNORECASE), "recursive file deletion"),
    (re.compile(r"\bsocket\s*\.", re.IGNORECASE), "raw socket access"),
    (re.compile(r"\bctypes\s*\.", re.IGNORECASE), "ctypes (native code execution)"),
    (re.compile(r"\bimportlib\s*\.", re.IGNORECASE), "dynamic import via importlib"),
]

# AST-level: names of dangerous functions. Caught even when imported as
# `from os import system` or aliased. Matches bare function calls.
_AST_FORBIDDEN_CALLS = {
    "system",      # os.system
    "popen",       # os.popen
    "exec",        # builtin exec
    "eval",        # builtin eval
    "compile",     # builtin compile
    "__import__",  # builtin __import__
    "spawn",       # pty.spawn / os.spawn*
    "rmtree",      # shutil.rmtree
    "remove",      # os.remove
    "unlink",      # os.unlink
}

# AST-level: attribute roots that are never safe in a browser script
_AST_FORBIDDEN_ATTR_ROOTS = {
    "subprocess", "ctypes", "socket", "shutil", "importlib",
    # os.X is allowed in principle (os.environ.get etc), but specific os.X
    # dangerous members are caught via _AST_FORBIDDEN_CALLS on the attr name.
}


def _scan_forbidden(code: str) -> str | None:
    """Regex-based pre-filter. Returns first match reason or None."""
    for rx, reason in _FORBIDDEN_PATTERNS:
        if rx.search(code):
            return reason
    return None


def _ast_forbidden(code: str) -> str | None:
    """AST-based check. Catches `from os import system; system(...)` and friends
    that the regex pre-filter misses. Returns reason or None.

    SyntaxError is treated as suspicious and blocks the script (better safe).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"SyntaxError: {e.msg}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Bare call: exec(...), system(...), eval(...)
            if isinstance(func, ast.Name) and func.id in _AST_FORBIDDEN_CALLS:
                return f"call to forbidden builtin/module function {func.id!r}"
            # Attribute call: os.system(...), subprocess.run(...)
            if isinstance(func, ast.Attribute):
                root = _attr_root(func)
                if root in _AST_FORBIDDEN_ATTR_ROOTS:
                    return f"call into forbidden module {root!r}.{func.attr}"
                if root == "os" and func.attr in _AST_FORBIDDEN_CALLS:
                    return f"call to forbidden os.{func.attr}()"
    return None


def _attr_root(node: ast.Attribute) -> str | None:
    """Return the root Name of a chained Attribute access, e.g.
    `os.system` → 'os', `a.b.c` → 'a'. Returns None if no Name at root."""
    cur = node
    while isinstance(cur, ast.Attribute):
        cur = cur.value
    if isinstance(cur, ast.Name):
        return cur.id
    return None


def _is_clean(code: str) -> str | None:
    """Run all checks. Returns the first reason if blocked, else None."""
    return _scan_forbidden(code) or _ast_forbidden(code)


def verify_browser(agent, code, wd, perms) -> bool:
    """Approve or reject a browser script.

    Currently: regex + AST scan for shell-escape / arbitrary-code patterns.
    Future: capability tokens, rate limits, per-agent allowlists.
    """
    name = (agent or {}).get("name", "Unknown")
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]

    forbidden = _is_clean(code)
    if forbidden is not None:
        _log.warning("BROWSER gatekeeper: REJECTED %s (hash %s) — %s", name, code_hash, forbidden)
        try:
            add_chat_message({
                "role": "watchdog",
                "agent": "WatchdogAG",
                "content": f"🛡️ Browser-Script von {name} abgelehnt: {forbidden} (Hash {code_hash})",
            })
        except Exception:
            pass
        return False

    request_capability(name, "BROWSER", code_hash, "AutoApprovedBrowser")
    return True
