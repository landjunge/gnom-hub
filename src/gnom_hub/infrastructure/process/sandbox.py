# sandbox.py — Direct host execution (no Docker, no macOS sandbox-exec).
# User decides 2026-06-15: keep it simple, run directly in workspace cwd.
# Gatekeeper still applies for FILE writes (verify_write) and FILE reads
# via path_validator. Shell commands are restricted via argv-style execution
# (no shell interpolation) plus the gatekeeper whitelist.
import logging
import re as _re
import shlex
import subprocess
import sys
import os

from gnom_hub.core.config import WORKSPACE_DIR

_log = logging.getLogger(__name__)


# Operatoren, an denen wir den Befehl in Segmente zerlegen.
# NICHT enthalten: "|" — Pipes zwischen zwei vertrauenswürdigen Kommandos
# würden einen Shell-Interpreter erfordern; das lehnen wir bewusst ab.
# Das Whitelist-Modul blockt ohnehin `curl|sh` / `wget|sh` / `fetch|sh` als
# eigenständige High-Risk-Patterns, sodass die häufigste Pipe-Mißbrauchsform
# schon vor argv-Parsing gefangen wird.
_SEGMENT_SPLIT_RE = _re.compile(r"\s*(?:&&|\|\||;)\s*")


def _resolve_workspace_dir():
    """Ermittelt das Workspace-cwd des aktiven Agenten-Projekts.

    Fällt robust auf WORKSPACE_DIR zurück, falls die State-DB nicht
    verfügbar ist — die Sicherheitsschicht (Whitelist + argv-Mode) ist
    davon unabhängig, der Pfad nur ein Komfort.
    """
    try:
        from gnom_hub.db.state_repo import SQLiteStateRepository
        proj = SQLiteStateRepository().get_active_project() or "default"
        return os.path.abspath(os.path.join(str(WORKSPACE_DIR), proj))
    except Exception as e:
        _log.debug("sandbox: state-DB nicht verfügbar (%s) — Fallback auf WORKSPACE_DIR", e)
        return os.path.abspath(str(WORKSPACE_DIR))


def _blocked(reason: str):
    """CompletedProcess-kompatibles Ergebnis für abgewiesene Kommandos."""
    return subprocess.CompletedProcess(args="", returncode=126, stdout="", stderr=f"[sandbox] {reason}")


def _tokenize_segments(command: str):
    """Zerlegt den Befehl in (segment_text, operator) Paare und parsed jedes
    Segment via shlex.

    operator ist '&&', '||', ';' oder None (vor dem ersten Segment).
    Gibt (segments, error) zurück — segments = [(op, argv_list), ...].
    """
    # Split mit behaltenem Separator via re.split
    parts = _re.split(r"(\s*(?:&&|\|\||;)\s*)", command)
    segments = []  # list of (operator, argv_list)
    pending_op = None
    for part in parts:
        if part == "":
            continue
        # ist es ein Operator?
        stripped = part.strip()
        if stripped in ("&&", "||", ";"):
            pending_op = stripped
            continue
        # ein Segment-Text
        seg = part.strip()
        if not seg:
            continue
        try:
            tokens = shlex.split(seg, posix=True)
        except ValueError as e:
            return None, _blocked(f"could not parse segment {seg!r}: {e}")
        if not tokens:
            continue
        # Pipes / Redirects explizit ablehnen — argv-Mode kennt sie nicht.
        if "|" in tokens:
            return None, _blocked(
                "pipe '|' is not allowed in argv-mode (use ; or && to chain)"
            )
        if any(tok in ("<", ">", ">>", "<<") for tok in tokens):
            return None, _blocked(
                "shell redirects are not allowed in argv-mode"
            )
        segments.append((pending_op, tokens))
        pending_op = None
    if not segments:
        return None, _blocked("no executable segments after parsing")
    return segments, None


def run_in_sandbox(command: str, agent=None, timeout: int = 30):
    """Führt ein Shell-Kommando im Workspace-cwd des Agenten aus.

    Sicherheitsstapel (defence in depth):
      1. Whitelist-Vorprüfung via `is_command_safe_and_whitelisted`
         (gatekeeper.py) — blockt `rm -rf /`, `mkfs`, `curl|sh` etc.
      2. Per-Segment-Parse via `shlex` — Argv-Listen statt Shell-String.
      3. `subprocess.run(args, shell=False, ...)` — keine Shell-Interpolation.
      4. Implizite Segment-Verkettung an `&&` / `||` / `;` — bei
         Non-zero-Returncode wird die Kette abgebrochen.

    Bewusst NICHT unterstützt:
      - Pipes (`|`) zwischen nicht-Shell-Kommandos — würde Shell erfordern.
      - Redirects (`<`, `>`, `>>`) — gleicher Grund.
      - Backticks / `$()`-Substitution — durch argv-Mode strukturell unmöglich.
    """
    from gnom_hub.core.security.gatekeeper import is_command_safe_and_whitelisted

    # 1. Whitelist-Check am Gesamtbefehl
    is_safe, severity, reason = is_command_safe_and_whitelisted(command, agent=agent)
    if not is_safe:
        return _blocked(f"blocked by gatekeeper ({severity}): {reason}")

    # 2. Segment-Parsing + Argv-Aufbau
    segments, err = _tokenize_segments(command)
    if err is not None:
        return err

    # 3. Sequentielle Ausführung mit shell=False und Operator-Semantik
    wd = _resolve_workspace_dir()
    last_result = None
    for op, parts in segments:
        # Operator-Semantik aus dem Vorsegment:
        #   && : Vorsegment muss rc==0 gehabt haben, sonst Short-Circuit.
        #   || : Vorsegment muss rc!=0 gehabt haben, sonst Short-Circuit.
        #   ;  : immer ausführen.
        if op == "&&" and last_result is not None and last_result.returncode != 0:
            break
        if op == "||" and last_result is not None and last_result.returncode == 0:
            break
        try:
            last_result = subprocess.run(
                parts,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=wd,
            )
        except FileNotFoundError as e:
            return subprocess.CompletedProcess(
                args=parts, returncode=127, stdout="",
                stderr=f"[sandbox] command not found: {e}",
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                args=parts, returncode=124, stdout="",
                stderr=f"[sandbox] timeout after {timeout}s",
            )
        except OSError as e:
            return subprocess.CompletedProcess(
                args=parts, returncode=126, stdout="",
                stderr=f"[sandbox] OS error: {e}",
            )
    return last_result


def run_browser_in_sandbox(code_path: str, net: str = "none", timeout: int = 30):
    """Run a Python script in the agent's workspace cwd.

    Verwendet bereits argv-Style (kein shell=True) — bleibt unverändert.
    """
    wd = _resolve_workspace_dir()
    # Resolve code_path to absolute: caller may pass a relative filename
    # (action_browser.py writes tmp_browser_*.py into wd), so we need to look
    # it up in wd. If the caller already passed an absolute path, keep it.
    if not os.path.isabs(code_path):
        candidate = os.path.join(wd, code_path)
        if os.path.exists(candidate):
            code_path = candidate
        elif not os.path.exists(code_path):
            # Last resort: leave it as-is so the error message is informative
            code_path = os.path.abspath(code_path)
    py_exec = sys.executable or "python3"
    return subprocess.run(
        [py_exec, code_path], capture_output=True, text=True, timeout=timeout, cwd=wd,
    )