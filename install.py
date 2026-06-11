#!/usr/bin/env python3
"""
Gnom-Hub — Cross-Platform Installer (macOS, Linux, Windows)
Uses only standard Python libraries to bootstrap the virtual environment and setup launchers.
"""

import os
import sys
import subprocess
import shutil
import platform

# Terminal Colors
class Colors:
    GREEN = '\033[0;32m' if platform.system() != 'Windows' else ''
    YELLOW = '\033[1;33m' if platform.system() != 'Windows' else ''
    CYAN = '\033[0;36m' if platform.system() != 'Windows' else ''
    RED = '\033[0;31m' if platform.system() != 'Windows' else ''
    BOLD = '\033[1m' if platform.system() != 'Windows' else ''
    RESET = '\033[0m' if platform.system() != 'Windows' else ''

def print_header():
    print(f"""
{Colors.CYAN}  ██████╗  ███╗   ██╗ ██████╗ ███╗   ███╗
 ██╔════╝  ████╗  ██║██╔═══██╗████╗ ████║
 ██║  ███╗ ██╔██╗ ██║██║   ██║██╔████╔██║
 ██║   ██║ ██║╚██╗██║██║   ██║██║╚██╔╝██║
 ╚██████╔╝ ██║ ╚████║╚██████╔╝██║ ╚═╝ ██║
  ╚═════╝  ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝
              CROSS-PLATFORM INSTALLER
 ────────────────────────────────────────{Colors.RESET}
""")

def main():
    print_header()
    
    is_windows = platform.system() == 'Windows'
    is_mac = platform.system() == 'Darwin'
    
    repo_dir = os.path.abspath(os.path.dirname(__file__))
    venv_dir = os.path.join(repo_dir, ".venv")
    
    # 1. Check Python version
    print(f"{Colors.BOLD}▸ Checking Python version...{Colors.RESET}")
    major, minor = sys.version_info.major, sys.version_info.minor
    if major < 3 or (major == 3 and minor < 9):
        print(f"{Colors.RED}✗ Python >= 3.9 is required. You have Python {major}.{minor}.{Colors.RESET}")
        sys.exit(1)
    print(f"  Python {major}.{minor} found {Colors.GREEN}✓{Colors.RESET}")
    
    # 2. Virtual Environment
    print(f"\n{Colors.BOLD}▸ Managing virtual environment (.venv)...{Colors.RESET}")
    if not os.path.exists(venv_dir):
        print("  Creating .venv virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        print(f"  .venv created {Colors.GREEN}✓{Colors.RESET}")
    else:
        print(f"  .venv already exists {Colors.GREEN}✓{Colors.RESET}")
        
    # Resolve executable paths
    if is_windows:
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        python_exe = os.path.join(venv_dir, "bin", "python")
        pip_exe = os.path.join(venv_dir, "bin", "pip")
        
    # 3. Installing dependencies
    print(f"\n{Colors.BOLD}▸ Installing dependencies... (this might take a minute){Colors.RESET}")
    subprocess.check_call([pip_exe, "install", "--upgrade", "pip"])
    subprocess.check_call([pip_exe, "install", "-e", repo_dir])
    print(f"  Dependencies successfully installed {Colors.GREEN}✓{Colors.RESET}")
    
    # 4. Creating Directories & .env Config
    print(f"\n{Colors.BOLD}▸ Creating directories and environment variables...{Colors.RESET}")
    os.makedirs(os.path.join(repo_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(repo_dir, "gnom_workspace", "default"), exist_ok=True)
    
    env_file = os.path.join(repo_dir, "config", ".env")
    if not os.path.exists(env_file):
        os.makedirs(os.path.dirname(env_file), exist_ok=True)
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write("""# ── Gnom-Hub Configuration ──
# Set at least one provider key:

# DeepSeek API Key
# DEEPSEEK_API_KEY=sk-...

# OpenRouter Free Key
# OPENROUTER_KEY_FREE_1=sk-or-...
""")
        print(f"  Created config/.env template {Colors.GREEN}✓{Colors.RESET}")
    else:
        print(f"  config/.env already exists {Colors.GREEN}✓{Colors.RESET}")
        
    # 5. Writing Launcher Scripts
    print(f"\n{Colors.BOLD}▸ Generating OS launcher scripts...{Colors.RESET}")
    
    if is_windows:
        # Windows batch scripts calling powershell
        start_bat = os.path.join(repo_dir, "start_gnom_hub.bat")
        with open(start_bat, 'w', encoding='utf-8') as f:
            f.write('@echo off\npowershell -ExecutionPolicy Bypass -File "%~dp0scripts\\start.ps1"\n')
            
        stop_bat = os.path.join(repo_dir, "stop_gnom_hub.bat")
        with open(stop_bat, 'w', encoding='utf-8') as f:
            f.write('@echo off\npowershell -ExecutionPolicy Bypass -File "%~dp0scripts\\stop.ps1"\n')
            
        print(f"  Created start_gnom_hub.bat {Colors.GREEN}✓{Colors.RESET}")
        print(f"  Created stop_gnom_hub.bat {Colors.GREEN}✓{Colors.RESET}")
        
    else:
        # Unix bash scripts
        start_sh = os.path.join(repo_dir, "start_gnom_hub.sh")
        with open(start_sh, 'w', encoding='utf-8') as f:
            f.write(f"""#!/bin/bash
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

source .venv/bin/activate
set -a; [ -f config/.env ] && source config/.env; set +a
mkdir -p logs

# ── PID-basiertes Cleanup: alte Prozesse sanft beenden ──
for pidfile in "$HOME"/.gnom-hub/run/*.pid "$HOME"/.gnom-hub-*/run/*.pid; do
  [ -f "$pidfile" ] || continue
  pid=$(cat "$pidfile" 2>/dev/null)
  [ -n "$pid" ] && kill "$pid" 2>/dev/null
  rm -f "$pidfile"
done
sleep 1

# Hub starten (startet automatisch alle 8 Agenten via start_background_agents)
python3 -m gnom_hub > logs/logs_hub.txt 2>&1 &
sleep 4

# Browser öffnen
if command -v open &>/dev/null; then
    open "http://127.0.0.1:3002"
elif command -v xdg-open &>/dev/null; then
    xdg-open "http://127.0.0.1:3002"
fi

echo "🚀 Gnom-Hub gestartet auf http://127.0.0.1:3002"
echo "Stop: ./stop_gnom_hub.sh"
""")
            
        stop_sh = os.path.join(repo_dir, "stop_gnom_hub.sh")
        with open(stop_sh, 'w', encoding='utf-8') as f:
            f.write("""#!/bin/bash
for pidfile in "$HOME"/.gnom-hub/run/*.pid "$HOME"/.gnom-hub-*/run/*.pid; do
  [ -f "$pidfile" ] || continue
  pid=$(cat "$pidfile" 2>/dev/null)
  procname=$(basename "$pidfile" .pid)
  [ -n "$pid" ] && kill "$pid" 2>/dev/null && echo "$procname gestoppt"
  rm -f "$pidfile"
done
sleep 1
remaining=$(ps aux | grep -i "[g]nom_hub\|[a]gents\\." | awk '{print $2}')
[ -n "$remaining" ] && kill $remaining 2>/dev/null && echo "Verbleibende Prozesse gestoppt"
echo "Gnom-Hub komplett beendet."
""")
            
        os.chmod(start_sh, 0o755)
        os.chmod(stop_sh, 0o755)
        print(f"  Created start_gnom_hub.sh (executable) {Colors.GREEN}✓{Colors.RESET}")
        print(f"  Created stop_gnom_hub.sh (executable) {Colors.GREEN}✓{Colors.RESET}")

        if is_mac:
            # Offer building App Bundle on macOS
            print(f"\n{Colors.BOLD}▸ Building macOS Gnom-Hub.app shortcut...{Colors.RESET}")
            setup_mac_script = os.path.join(repo_dir, "setup_macos_shortcut.sh")
            if os.path.exists(setup_mac_script):
                try:
                    subprocess.check_call(["bash", setup_mac_script])
                    print(f"  Gnom-Hub.app built and installed to /Applications {Colors.GREEN}✓{Colors.RESET}")
                except Exception as e:
                    print(f"  Note: Native app bundle shortcut compilation failed, but CLI launchers are ready: {e}")

    # Finish Message
    print(f"\n{Colors.GREEN}═══════════════════════════════════════════════════════{Colors.RESET}")
    print(f"{Colors.BOLD}  ✅ Installation completed successfully!{Colors.RESET}")
    print(f"{Colors.GREEN}═══════════════════════════════════════════════════════{Colors.RESET}\n")
    print(f"  Add your LLM API keys to {Colors.BOLD}config/.env{Colors.RESET} to start.\n")
    if is_windows:
        print(f"  {Colors.BOLD}Start:{Colors.RESET} Double-click on {Colors.CYAN}start_gnom_hub.bat{Colors.RESET}")
        print(f"  {Colors.BOLD}Stop:{Colors.RESET}  Double-click on {Colors.CYAN}stop_gnom_hub.bat{Colors.RESET}")
    else:
        print(f"  {Colors.BOLD}Start:{Colors.RESET} Run {Colors.CYAN}./start_gnom_hub.sh{Colors.RESET}")
        print(f"  {Colors.BOLD}Stop:{Colors.RESET}  Run {Colors.CYAN}./stop_gnom_hub.sh{Colors.RESET}")
        if is_mac:
            print(f"  {Colors.BOLD}macOS App:{Colors.RESET} You can click on the {Colors.CYAN}Gnom-Hub{Colors.RESET} icon in your Applications folder.")
    print()

if __name__ == "__main__":
    main()
