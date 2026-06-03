#!/usr/bin/env python3
"""
Gnom-Hub — Cross-Platform Uninstaller (macOS, Linux, Windows)
Removes virtual environment, logs, caches, generated launchers, and optional user data.
"""

import os
import sys
import shutil
import platform
import subprocess

class Colors:
    GREEN = '\033[0;32m' if platform.system() != 'Windows' else ''
    YELLOW = '\033[1;33m' if platform.system() != 'Windows' else ''
    CYAN = '\033[0;36m' if platform.system() != 'Windows' else ''
    RED = '\033[0;31m' if platform.system() != 'Windows' else ''
    BOLD = '\033[1m' if platform.system() != 'Windows' else ''
    RESET = '\033[0m' if platform.system() != 'Windows' else ''

def main():
    print(f"""
{Colors.RED}  ╔═══════════════════════════════════════════╗
  ║       GNOM-HUB UNINSTALLER (ALL OS)       ║
  ╚═══════════════════════════════════════════╝{Colors.RESET}
""")

    repo_dir = os.path.abspath(os.path.dirname(__file__))
    data_dir = os.path.join(os.path.expanduser("~"), ".gnom-hub")
    is_windows = platform.system() == 'Windows'
    is_mac = platform.system() == 'Darwin'

    print("  This script will remove:")
    print("    • All running Gnom-Hub processes")
    print("    • Virtual environment (.venv/)")
    print("    • Log directories and files")
    print("    • Python cache (__pycache__/)")
    print("    • Generated launcher scripts")
    if is_mac:
        print("    • macOS App Bundle (/Applications/Gnom-Hub.app)")
    print()

    # User Input
    keep_data = input(f"  {Colors.BOLD}Keep user database and memory files at '{data_dir}'? [Y/n]: {Colors.RESET}").strip().lower()
    keep_config = input(f"  {Colors.BOLD}Keep local configuration and token files in 'config/'? [Y/n]: {Colors.RESET}").strip().lower()
    confirm = input(f"  {Colors.RED}{Colors.BOLD}Are you sure you want to uninstall Gnom-Hub? [y/N]: {Colors.RESET}").strip().lower()

    if confirm not in ['y', 'yes', 'j', 'ja']:
        print("  Uninstallation aborted.")
        sys.exit(0)

    # 1. Terminate running processes
    print(f"\n{Colors.BOLD}▸ Stopping Gnom-Hub processes...{Colors.RESET}")
    if is_windows:
        stop_ps_script = os.path.join(repo_dir, "scripts", "stop.ps1")
        if os.path.exists(stop_ps_script):
            try:
                subprocess.check_call(["powershell", "-ExecutionPolicy", "Bypass", "-File", stop_ps_script])
            except Exception:
                # Fallback taskkill
                subprocess.run('taskkill /f /fi "imagename eq python.exe" /fi "windowtitle eq Gnom-Hub*"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run('taskkill /f /fi "imagename eq python.exe" /fi "windowtitle eq Gnom-Hub*"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # macOS / Linux
        subprocess.run('pkill -f "[pP]ython.*gnom_hub"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run('pkill -f "[pP]ython.*agents\..*AG"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run('pkill -f "[pP]ython.*agents\.run_agent"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"  Processes terminated {Colors.GREEN}✓{Colors.RESET}")

    # 2. Delete Virtual Environment
    print(f"\n{Colors.BOLD}▸ Removing virtual environment...{Colors.RESET}")
    venv_dir = os.path.join(repo_dir, ".venv")
    if os.path.exists(venv_dir):
        shutil.rmtree(venv_dir, ignore_errors=True)
        print(f"  Deleted .venv/ {Colors.GREEN}✓{Colors.RESET}")
    else:
        print("  No .venv/ found")

    # 3. Cleaning Logs & Caches
    print(f"\n{Colors.BOLD}▸ Cleaning logs & Python cache...{Colors.RESET}")
    logs_dir = os.path.join(repo_dir, "logs")
    if os.path.exists(logs_dir):
        shutil.rmtree(logs_dir, ignore_errors=True)
    
    # Clean file logs in root
    for f in os.listdir(repo_dir):
        if f.startswith("logs_") and f.endswith(".txt"):
            try:
                os.remove(os.path.join(repo_dir, f))
            except Exception:
                pass
                
    # Clean Python caches
    for root, dirs, files in os.walk(repo_dir):
        for d in dirs:
            if d == '__pycache__':
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
        for file in files:
            if file.endswith('.pyc') or file.endswith('.pyo'):
                try:
                    os.remove(os.path.join(root, file))
                except Exception:
                    pass
                    
    # Clean egg-info directories
    egg_dirs = [os.path.join(repo_dir, "src", "gnom_hub.egg-info"), os.path.join(repo_dir, "gnom_hub.egg-info")]
    for ed in egg_dirs:
        if os.path.exists(ed):
            shutil.rmtree(ed, ignore_errors=True)
            
    print(f"  Logs and cache cleared {Colors.GREEN}✓{Colors.RESET}")

    # 4. Remove generated Launchers
    print(f"\n{Colors.BOLD}▸ Cleaning generated launcher scripts...{Colors.RESET}")
    launchers = [
        os.path.join(repo_dir, "start_gnom_hub.bat"),
        os.path.join(repo_dir, "stop_gnom_hub.bat"),
        os.path.join(repo_dir, "start_gnom_hub.sh"),
        os.path.join(repo_dir, "stop_gnom_hub.sh"),
        os.path.join(repo_dir, "sandbox.py")
    ]
    for l in launchers:
        if os.path.exists(l):
            try:
                os.remove(l)
            except Exception:
                pass
    print(f"  Launchers removed {Colors.GREEN}✓{Colors.RESET}")

    # 5. Remove macOS App bundle
    if is_mac:
        app_path = "/Applications/Gnom-Hub.app"
        if os.path.exists(app_path):
            print(f"\n{Colors.BOLD}▸ Removing macOS App Bundle...{Colors.RESET}")
            # Requires subprocess call due to potential directory permissions
            subprocess.run(["rm", "-rf", app_path])
            print(f"  Deleted {app_path} {Colors.GREEN}✓{Colors.RESET}")

    # 6. Optional Data Deletion
    if keep_data in ['n', 'no', 'nein']:
        print(f"\n{Colors.BOLD}▸ Removing database and user memory files...{Colors.RESET}")
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir, ignore_errors=True)
            print(f"  Deleted {data_dir} {Colors.GREEN}✓{Colors.RESET}")
    else:
        print(f"\n  Database and user memory files preserved in: {data_dir}")

    # 7. Optional Config & Secrets Deletion
    if keep_config in ['n', 'no', 'nein']:
        print(f"\n{Colors.BOLD}▸ Removing configuration and token files...{Colors.RESET}")
        config_dir = os.path.join(repo_dir, "config")
        if os.path.exists(config_dir):
            for f in os.listdir(config_dir):
                if f in (".env", ".hub_secret") or ".gnom-hub-tokens" in f:
                    try:
                        os.remove(os.path.join(config_dir, f))
                        print(f"  Deleted config/{f} {Colors.GREEN}✓{Colors.RESET}")
                    except Exception:
                        pass
    else:
        print(f"\n  Configuration and token files preserved in: config/")

    print(f"\n{Colors.GREEN}═══════════════════════════════════════════════════════{Colors.RESET}")
    print(f"{Colors.BOLD}  ✅ Uninstallation completed successfully!{Colors.RESET}")
    print(f"{Colors.GREEN}═══════════════════════════════════════════════════════{Colors.RESET}\n")

if __name__ == "__main__":
    main()
