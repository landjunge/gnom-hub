# scratch/dump_chat.py
import sqlite3

def main():
    db_path = "/Users/landjunge/.gnom-hub/data/gnomhub.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        print("Tables:", tables)
        
        # Print schemas
        for table in ['chat', 'explainable_outputs', 'chat_messages']:
            if table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                print(f"\nSchema of {table}:", cursor.fetchall())
                
        if 'explainable_outputs' in tables:
            cursor.execute("SELECT * FROM explainable_outputs ORDER BY id DESC LIMIT 5;")
            print("\n--- RECENT EXPLAINABLE_OUTPUTS ---")
            for r in cursor.fetchall():
                print(r)
                
        if 'chat' in tables:
            cursor.execute("SELECT sender, content, timestamp FROM chat WHERE sender != 'user' ORDER BY timestamp DESC LIMIT 20;")
            print("\n--- RECENT AGENT CHAT MESSAGES ---")
            for r in cursor.fetchall():
                sender, content, ts = r
                print(f"[{ts}] {sender}: {content[:100]}... (len: {len(content)})")
                if "<think>" in content:
                    print("  -> Contains <think> tag!")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
