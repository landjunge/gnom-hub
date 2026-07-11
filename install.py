#!/usr/bin/env python3.10
"""Gnom-Hub — Cross-Platform Installer (macOS, Linux, Windows).

Usage:
    python3 install.py                # normal install
    python3 install.py --help         # show this help
    python3 install.py --check        # pre-flight only, no changes
    python3 install.py --dry-run      # show what would happen
    python3 install.py --uninstall    # remove .venv, config/, workspace
    python3 install.py --no-color     # disable ANSI colors (or env NO_COLOR=1)

Environment:
    NO_COLOR=1                       # disable ANSI colors (per https://no-color.org)
    GNOM_HUB_PORT=3002               # port to check (default: 3002)
    GNOM_HUB_SKIP_PORT_CHECK=1       # skip port availability check
    GNOM_HUB_SKIP_SMOKE_TEST=1       # skip post-install import smoke test
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
VENV_DIR = REPO_DIR / ".venv"
SCRIPTS_DIR = REPO_DIR / "scripts"
DEFAULT_PORT = int(os.environ.get("GNOM_HUB_PORT", "3002"))


# ── Colors (respect NO_COLOR per https://no-color.org) ──────────────────────
def _want_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("GNOM_HUB_NO_COLOR"):
        return False
    return sys.stdout.isatty() and platform.system() != "Windows"


class Colors:
    def __init__(self):
        if _want_color():
            self.GREEN = "\033[0;32m"
            self.YELLOW = "\033[1;33m"
            self.CYAN = "\033[0;36m"
            self.RED = "\033[0;31m"
            self.BOLD = "\033[1m"
            self.RESET = "\033[0m"
        else:
            self.GREEN = self.YELLOW = self.CYAN = self.RED = self.BOLD = self.RESET = ""

    def green(self, s): return f"{self.GREEN}{s}{self.RESET}"
    def yellow(self, s): return f"{self.YELLOW}{s}{self.RESET}"
    def cyan(self, s): return f"{self.CYAN}{s}{self.RESET}"
    def red(self, s): return f"{self.RED}{s}{self.RESET}"
    def bold(self, s): return f"{self.BOLD}{s}{self.RESET}"


C = Colors()


def header():
    print(f"""
{C.cyan("  ██████╗  ███╗   ██╗ ██████╗ ███╗   ███╗")}
{C.cyan(" ██╔════╝  ████╗  ██║██╔═══██╗████╗ ████║")}
{C.cyan(" ██║  ███╗ ██╔██╗ ██║██║   ██║██╔████╔██║")}
{C.cyan(" ██║   ██║ ██║╚██╗██║██║   ██║██║╚██╔╝██║")}
{C.cyan(" ╚██████╔╝ ██║ ╚████║╚██████╔╝██║ ╚═╝ ██║")}
{C.cyan("  ╚═════╝  ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝")}
{C.bold("              INSTALLER")}
{C.bold(" ───────────────────────────────")}
""")


def python_exe_name() -> str:
    """Best available python binary on PATH."""
    for candidate in ("python3.11", "python3.10", "python3.12", "python3.9", "python3"):
        if shutil.which(candidate):
            return candidate
    return "python3"


def venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_pip() -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def shell_launcher_dir() -> Path:
    """Where the .sh launchers live. Always scripts/ on unix; never the repo root."""
    return SCRIPTS_DIR


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="install.py",
        description="Gnom-Hub cross-platform installer.",
    )
    p.add_argument("--check", action="store_true",
                   help="Pre-flight checks only, no filesystem changes.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print planned actions, do not execute them.")
    p.add_argument("--uninstall", action="store_true",
                   help="Remove .venv, config/.env (with confirmation), workspace.")
    p.add_argument("--no-color", action="store_true",
                   help="Disable ANSI colors in output.")
    return p.parse_args()


# ── Pre-flight checks (idempotent, side-effect free) ────────────────────────
def preflight(errors: list[str]) -> dict:
    """Collect environment facts and identify blockers. Return a summary dict."""
    info = {
        "platform": platform.system(),
        "python": python_exe_name(),
        "git": shutil.which("git") is not None,
        "pyproject": (REPO_DIR / "pyproject.toml").is_file(),
        "scripts_dir": SCRIPTS_DIR.is_dir(),
        "venv_present": VENV_DIR.is_dir(),
        "port": DEFAULT_PORT,
        "port_free": port_free(DEFAULT_PORT),
    }
    if info["pyproject"]:
        major_minor = sys.version_info[:2]
        if major_minor < (3, 9):
            errors.append(f"Python {major_minor[0]}.{major_minor[1]} too old (need 3.9+).")
    else:
        errors.append(f"pyproject.toml missing in {REPO_DIR}.")
    if not info["git"]:
        errors.append("git not on PATH (working-tree check will be skipped).")
    return info


def port_free(port: int) -> bool:
    """Return True iff *port* is bindable on localhost."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def print_preflight(info: dict) -> None:
    print(f"{C.bold('▸ Pre-flight check')}")
    print(f"  Platform:    {info['platform']}")
    print(f"  Python:      {info['python']}")
    print(f"  Git:         {'yes' if info['git'] else 'no (working-tree check skipped)'}")
    print(f"  pyproject:   {'yes' if info['pyproject'] else 'MISSING'}")
    print(f"  Scripts/:    {'yes' if info['scripts_dir'] else 'MISSING'}")
    print(f"  .venv:       {'exists' if info['venv_present'] else 'will be created'}")
    p = info["port"]
    status = C.green(f"free (will bind 127.0.0.1:{p})") if info["port_free"] else C.yellow(f"IN USE — something is already on :{p}")
    print(f"  Port {p}:     {status}")
    print()


# ── Side-effecting actions (gated on dry-run) ──────────────────────────────
def ensure_venv(dry: bool) -> None:
    pip_exe = venv_pip()
    if VENV_DIR.is_dir():
        if not pip_exe.exists():
            print(f"  {C.yellow('.venv exists but is incomplete (no pip). Re-creating...')}")
            if not dry:
                shutil.rmtree(VENV_DIR, ignore_errors=True)
                subprocess.check_call([python_exe_name(), "-m", "venv", str(VENV_DIR)])
                print(f"  {C.green('.venv re-created ✓')}")
        else:
            print(f"  {C.green('.venv already present ✓')}")
        return
    print("  Creating .venv …")
    if not dry:
        subprocess.check_call([python_exe_name(), "-m", "venv", str(VENV_DIR)])
        print(f"  {C.green('.venv created ✓')}")


def upgrade_dependencies(dry: bool) -> None:
    """Always upgrade so changes to pyproject.toml propagate."""
    pip = venv_pip()
    print(f"{C.bold('▸ Installing + upgrading dependencies')}")
    print("  pip install --upgrade pip …")
    if not dry:
        subprocess.check_call([str(pip), "install", "--upgrade", "pip"])
    print("  pip install -e .[dev] …")
    if not dry:
        subprocess.check_call([str(pip), "install", "-e", f"{REPO_DIR}[dev]"])
    print(f"  {C.green('Dependencies installed ✓')}")


def ensure_dirs(dry: bool) -> None:
    print(f"{C.bold('▸ Ensuring directories')}")
    targets = [
        REPO_DIR / "logs",
        REPO_DIR / "gnom_workspace" / "default",
        REPO_DIR / "config",
    ]
    for d in targets:
        if d.exists():
            print(f"  {C.green(f'{d.relative_to(REPO_DIR)}/  ✓')}")
        else:
            print(f"  creating {d.relative_to(REPO_DIR)}/")
            if not dry:
                d.mkdir(parents=True, exist_ok=True)


def write_env_template(dry: bool) -> None:
    env_file = REPO_DIR / "config" / ".env"
    print(f"{C.bold('▸ .env config')}")
    if env_file.exists():
        print(f"  {C.green('config/.env already exists, leaving untouched ✓')}")
        return
    template = """# ── Gnom-Hub Configuration ──
# Set at least one provider key (any combination works):

# DeepSeek
# DEEPSEEK_API_KEY=sk-...

# OpenRouter
# OPENROUTER_KEY_FREE_1=sk-or-...

# OpenAI
# OPENAI_API_KEY=sk-proj-...

# Anthropic
# ANTHROPIC_API_KEY=sk-ant-...

# Gemini
# GEMINI_API_KEY=aizas...

# Brave Search (web search)
# BRAVE_SEARCH_API_KEY=BSA...

# ElevenLabs (TTS)
# ELEVENLABS_API_KEY=sk_...
"""
    print("  writing config/.env template …")
    if not dry:
        env_file.write_text(template, encoding="utf-8")
    print(f"  {C.green('config/.env template written ✓')}")


def install_launchers(dry: bool) -> None:
    """Symlink-or-copy the canonical shell launchers from scripts/ into the
    repo root so the user can just type ./start_gnom_hub.sh without remembering
    the scripts/ path. On Windows we generate .bat wrappers that call the
    PowerShell scripts.
    """
    print(f"{C.bold('▸ Generating launcher shortcuts')}")
    sysname = platform.system()
    if sysname != "Windows":
        for name in ("start_gnom_hub.sh", "stop_gnom_hub.sh"):
            target = REPO_DIR / name
            source = SCRIPTS_DIR / name
            if not source.exists():
                print(f"  {C.yellow(f'{name}: scripts/{name} missing, skipping')}")
                continue
            if target.exists() or target.is_symlink():
                print(f"  {C.green(f'{name} already in repo root ✓')}")
                continue
            print(f"  linking {name} → scripts/{name}")
            if not dry:
                os.symlink(source, target)
        if platform.system() == "Darwin":
            setup_mac = SCRIPTS_DIR / "setup_macos_shortcut.sh"
            if setup_mac.exists():
                print(f"  {C.bold('Building macOS Gnom-Hub.app shortcut …')}")
                if not dry:
                    try:
                        subprocess.check_call(["bash", str(setup_mac)])
                        print(f"  {C.green('Gnom-Hub.app installed to /Applications ✓')}")
                    except subprocess.CalledProcessError as e:
                        print(f"  {C.yellow(f'App bundle build skipped: {e}')}")
    else:
        # Windows: ensure .bat wrappers exist in repo root pointing at scripts/
        for bat_name, ps_name in (("start_gnom_hub.bat", "start.ps1"),
                                  ("stop_gnom_hub.bat", "stop.ps1")):
            bat = REPO_DIR / bat_name
            if bat.exists():
                print(f"  {C.green(f'{bat_name} already in repo root ✓')}")
                continue
            print(f"  writing {bat_name} …")
            if not dry:
                bat.write_text(
                    f'@echo off\n'
                    f'powershell -ExecutionPolicy Bypass -File "%~dp0scripts\\{ps_name}"\n',
                    encoding="utf-8",
                )


def smoke_test() -> bool:
    """Quick import sanity: gnom_hub + workspace_dir() must work."""
    if os.environ.get("GNOM_HUB_SKIP_SMOKE_TEST"):
        print(f"  {C.yellow('skipped (GNOM_HUB_SKIP_SMOKE_TEST)')}")
        return True
    print(f"{C.bold('▸ Smoke test')}")
    py = venv_python()
    if not py.exists():
        print(f"  {C.red('venv missing python, skipping smoke test')}")
        return False
    code = (
        "import gnom_hub, sys; "
        "from gnom_hub.core.config import Config; "
        "from gnom_hub.core.agent_names import ALL_AGENTS, FROZEN; "
        "assert FROZEN, 'agent_names FROZEN flag missing'; "
        "assert len(ALL_AGENTS) == 8, f'expected 8 agents, got {len(ALL_AGENTS)}'; "
        "p = Config.workspace_dir(); "
        "assert p.is_absolute(), f'workspace_dir not absolute: {p}'; "
        "print('OK', p, ALL_AGENTS[0]); "
        "sys.exit(0)"
    )
    try:
        result = subprocess.run(
            [str(py), "-c", code],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "GNOM_HUB_ENV": "test", "TESTING": "true"},
        )
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  {C.red(f'smoke test crashed: {e}')}")
        return False
    if result.returncode != 0:
        print(f"  {C.red('smoke test FAILED')}")
        print(C.red(result.stderr or result.stdout))
        return False
    print(f"  {C.green(result.stdout.strip() or 'OK')}")
    return True


def port_check() -> bool:
    if os.environ.get("GNOM_HUB_SKIP_PORT_CHECK"):
        return True
    if port_free(DEFAULT_PORT):
        print(f"  Port {DEFAULT_PORT}: {C.green('free')}")
        return True
    print(f"  Port {DEFAULT_PORT}: {C.yellow('IN USE — kill the process or set GNOM_HUB_PORT=<other>')}")
    return False


def working_tree_repair(dry: bool) -> None:
    """If git is present, repair a partial-checkout working tree."""
    if not shutil.which("git") or not (REPO_DIR / ".git").is_dir():
        return
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO_DIR), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10,
        )
        missing = [ln[3:] for ln in r.stdout.splitlines() if ln.startswith(" D ")]
        if not missing:
            return
        print(f"  {C.yellow(f'Working-Tree unvollständig ({len(missing)} fehlende Dateien). Repariere …')}")
        if not dry:
            subprocess.check_call(["git", "-C", str(REPO_DIR), "checkout", "HEAD", "--", "."])
            print(f"  {C.green('Working-Tree repariert ✓')}")
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  {C.yellow(f'Working-Tree-Check übersprungen: {e}')}")


# ── Uninstall ───────────────────────────────────────────────────────────────
def uninstall() -> int:
    print(f"{C.bold('Uninstall Gnom-Hub?')}")
    targets = []
    if VENV_DIR.exists():
        targets.append(str(VENV_DIR.relative_to(REPO_DIR)))
    env = REPO_DIR / "config" / ".env"
    if env.exists():
        targets.append(str(env.relative_to(REPO_DIR)))
    workspace = REPO_DIR / "gnom_workspace"
    if workspace.exists():
        targets.append(str(workspace.relative_to(REPO_DIR)))
    data = Path.home() / ".gnom-hub"
    if data.exists():
        targets.append(f"{data} (user data)")

    if not targets:
        print("  Nothing to remove.")
        return 0
    print("  Will remove:")
    for t in targets:
        print(f"    • {t}")
    ans = input("  Continue? [y/N]: ").strip().lower()
    if ans not in ("y", "yes", "ja", "j"):
        print("  Aborted.")
        return 0
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR, ignore_errors=True)
        print(f"  {C.green('.venv removed')}")
    if env.exists():
        env.unlink()
        print(f"  {C.green('config/.env removed')}")
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
        print(f"  {C.green('gnom_workspace/ removed')}")
    if data.exists():
        print(f"  {C.yellow(f'User data at {data} NOT removed automatically.')}")
        print(f"  Remove manually if desired: rm -rf {data}")
    print()
    print(f"{C.green('Uninstall complete.')}")
    return 0


# ── Main ────────────────────────────────────────────────────────────────────
def main() -> int:
    args = parse_args()
    if args.no_color or os.environ.get("NO_COLOR"):
        os.environ["NO_COLOR"] = "1"

    if args.uninstall:
        return uninstall()

    header()

    print(C.bold("▸ Detecting environment"))
    errors: list[str] = []
    info = preflight(errors)
    print_preflight(info)

    if errors:
        for e in errors:
            print(C.red(f"  ✗ {e}"))
        print()
        print(C.red("Pre-flight failed. Fix the above and re-run."))
        return 1

    if args.check:
        print(C.green("Pre-flight OK — nothing changed (--check)."))
        return 0

    print(C.bold("▸ Installing"))
    dry = args.dry_run
    working_tree_repair(dry)
    ensure_venv(dry)
    upgrade_dependencies(dry)
    ensure_dirs(dry)
    write_env_template(dry)
    install_launchers(dry)

    print()
    print(C.bold("▸ Verifying"))
    smoke_ok = smoke_test()
    port_ok = port_check()
    print()

    print(f"{C.green('═══════════════════════════════════════════════════════')}")
    if smoke_ok and port_ok:
        print(C.bold("  ✅ Installation completed successfully!"))
    elif smoke_ok and not port_ok:
        print(C.bold("  ⚠️  Installed, but the default port is busy."))
        print(f"      Set {C.cyan('GNOM_HUB_PORT=<other>')} before starting, or free port {DEFAULT_PORT}.")
    else:
        print(C.bold("  ⚠️  Installed, but smoke test failed. Run scripts/diagnose_hub.py for details."))
    print(f"{C.green('═══════════════════════════════════════════════════════')}")
    print()
    print(f"  Add your LLM API keys to {C.bold('config/.env')} to start.")
    print()

    is_win = platform.system() == "Windows"
    if is_win:
        print(f"  {C.bold('Start:')} Double-click {C.cyan('start_gnom_hub.bat')}")
        print(f"  {C.bold('Stop: ')} Double-click {C.cyan('stop_gnom_hub.bat')}")
    else:
        print(f"  {C.bold('Start:')} {C.cyan('./start_gnom_hub.sh')}")
        print(f"  {C.bold('Stop: ')} {C.cyan('./stop_gnom_hub.sh')}")
        if platform.system() == "Darwin":
            print(f"  {C.bold('macOS: ')} {C.cyan('Gnom-Hub.app')} in /Applications")
    print()
    if not is_win:
        print(f"  Uninstall: {C.cyan('python3 install.py --uninstall')}")
    return 0


if __name__ == "__main__":
    if sys.version_info < (3, 9):
        _newer = shutil.which("python3.12") or shutil.which("python3.11") or shutil.which("python3.10")
        if _newer:
            print(f"[installer] Detected Python {sys.version_info.major}.{sys.version_info.minor} (too old). Re-execing with {_newer}...")
            os.execv(_newer, [_newer, __file__, *sys.argv[1:]])
        print(
            f"[installer] Python {sys.version_info.major}.{sys.version_info.minor} is too old "
            "(need 3.9+). Install python3.10 or newer and retry.",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(main())
