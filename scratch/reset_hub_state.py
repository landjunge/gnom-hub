#!/usr/bin/env python3
import sqlite3
import os
import json

db_path = os.path.expanduser('~/.gnom-hub/data/gnomhub.db')
if not os.path.exists(db_path):
    print("Database not found.")
    exit(1)

print("Connecting to Gnom-Hub database...")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Clear state values
state_keys_to_clear = ['jobs', 'active_workflow', 'active_swarm_comms', 'active_showbox']
with conn:
    for key in state_keys_to_clear:
        conn.execute("DELETE FROM state WHERE key = ?", (key,))
        print(f"Cleared state key: {key}")

# Reset agents
with conn:
    conn.execute("UPDATE agents SET active_job = NULL, status = 'online'")
    print("Reset all agents to status 'online' and active_job = NULL")

# Optional: Clean duplicate user brainstorming messages from the presentation attempts
with conn:
    # Delete recent duplicate user presentation prompts to keep history clean
    conn.execute("DELETE FROM chat WHERE sender = 'user' AND content LIKE '%@bs Erstelle eine Landingpage%'")
    print("Removed duplicate user presentation prompts from chat history")

conn.close()
print("Hub state reset completed successfully.")
