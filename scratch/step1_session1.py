import time, requests, sqlite3
from gnom_hub.core.config import Config

API_URL = "http://127.0.0.1:3002/api"

def print_banner(text):
    print("=" * 60)
    print(f" {text}")
    print("=" * 60)

# Clear chat
print("Clearing chat history...")
requests.post(f"{API_URL}/chat", json={"content": "@@clear chat", "sender": "user"})
time.sleep(2)

# Post Corporate Identity Preference
msg = '@user: Für alle zukünftigen Web-Projekte: Nutze immer das Corporate Identity Farbthema "Midnight Neon" mit Hintergrund #0a0f1d und Akzent #39ff14.'
print(f"Posting user preference:\n{msg}\n")
requests.post(f"{API_URL}/chat", json={"content": msg, "sender": "user"})

print("Waiting 8 seconds for SoulAG to extract and persist the facts...")
time.sleep(8)

print_banner("Current Stored Soul Facts in SQLite Database")
try:
    conn = sqlite3.connect(str(Config.DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT key, value, timestamp FROM soul_memory").fetchall()
    for r in rows:
        print(f"Fact -> Key: {r['key']} | Value: {r['value']} | Saved: {r['timestamp']}")
    conn.close()
except Exception as e:
    print(f"Error reading DB: {e}")
