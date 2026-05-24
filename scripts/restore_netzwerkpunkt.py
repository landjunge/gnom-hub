#!/usr/bin/env python3
"""Restore netzwerkpunkt.de files via FTP.

Credentials are loaded from environment variables or config/.env.
Required env vars: FTP_HOST, FTP_USER, FTP_PASS
"""
import ftplib, os, sys

def _load_env():
    """Load credentials from config/.env if env vars are not set."""
    if os.environ.get("FTP_HOST"):
        return
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(__file__), "..", "config", ".env")
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)
    except ImportError:
        print("⚠️  python-dotenv nicht installiert. Bitte FTP_HOST, FTP_USER, FTP_PASS als Umgebungsvariablen setzen.")

FTP_DIR = "netzwerkpunkt.de/httpdocs"
SCRATCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../gnom_workspace/default"))
FILES = ["index.html", "gnom_landing.html", "gnom_hub.html", "gnom_hub_v2.html", "gnom_hub_landing.html", "charaktere.md", "README.md", "style.css"]

def main():
    _load_env()
    ftp_host = os.environ.get("FTP_HOST")
    ftp_user = os.environ.get("FTP_USER")
    ftp_pass = os.environ.get("FTP_PASS")

    if not all([ftp_host, ftp_user, ftp_pass]):
        print("❌ FTP-Credentials fehlen. Bitte FTP_HOST, FTP_USER, FTP_PASS setzen oder config/.env konfigurieren.")
        sys.exit(1)

    print("=== 🛠️ Restoring netzwerkpunkt.de files ===")
    try:
        print(f"🔌 Connecting to {ftp_host}...")
        with ftplib.FTP(ftp_host, timeout=30) as ftp:
            ftp.login(ftp_user, ftp_pass)
            ftp.cwd(FTP_DIR)
            for fn in FILES:
                local_path = os.path.join(SCRATCH_DIR, fn)
                if not os.path.isfile(local_path):
                    print(f"❌ Missing file: {local_path}")
                    continue
                with open(local_path, "rb") as f:
                    ftp.storbinary(f"STOR {fn}", f)
                print(f"  ✅ {fn} restored")
        print("\n🎉 **RESTORATION COMPLETE!**")
    except Exception as e:
        print(f"\n❌ Error during restoration: {e}")

if __name__ == "__main__":
    main()
