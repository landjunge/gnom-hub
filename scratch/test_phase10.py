import time
import requests
from pathlib import Path

API_URL = "http://127.0.0.1:3002/api"

def print_banner(text):
    print("=" * 60)
    print(f" {text}")
    print("=" * 60)

def post_chat(msg):
    try:
        r = requests.post(f"{API_URL}/chat", json={"content": msg, "sender": "user"})
        return r.json()
    except Exception as e:
        print(f"Error posting chat: {e}")
        return None

def get_chat():
    try:
        r = requests.get(f"{API_URL}/chat?limit=40")
        return list(reversed(r.json()))
    except Exception as e:
        print(f"Error getting chat: {e}")
        return []

def get_metrics():
    try:
        r = requests.get(f"{API_URL}/metrics")
        return r.json()
    except Exception as e:
        return {}

def run_test():
    print_banner("PHASE 10: Dynamic Swarm Intelligence Test")
    
    # 1. Clear chat history
    print("Clearing chat history...")
    requests.post(f"{API_URL}/chat", json={"content": "@@clear chat", "sender": "user"})
    time.sleep(2)
    
    # 2. Post the sequential dependency job
    msg = (
        "@GeneralAG @job: Erstelle eine Projektbeschreibung für ein neues KI-Modul. "
        "ResearcherAG soll zuerst recherchieren, welche Features dafür wichtig sind. "
        "Erst wenn die Features bekannt sind, soll WriterAG die Texte schreiben. "
        "Zum Schluss soll CoderAG den Code bauen."
    )
    print(f"Posting job:\n{msg}\n")
    res = post_chat(msg)
    print(f"API Response: {res}\n")
    
    # 3. Monitor the dynamic swarm coordinator turns
    seen_ids = set()
    for m in get_chat():
        seen_ids.add(m.get("id"))
        
    workflow_active = True
    no_workflow_count = 0
    
    print("Monitoring swarm execution turns...")
    while workflow_active or no_workflow_count < 3:
        time.sleep(3)
        metrics = get_metrics()
        wf = metrics.get("_active_workflow")
        comms = metrics.get("_swarm_comms", [])
        
        if wf:
            print(f"\n[Workflow State] {wf}")
            if comms:
                print(f"  └─ Swarm Comms: {comms}")
            workflow_active = True
            no_workflow_count = 0
        else:
            workflow_active = False
            no_workflow_count += 1
            
        new_msgs = [m for m in get_chat() if m.get("id") not in seen_ids]
        for m in new_msgs:
            sender = m.get("sender")
            content = m.get("content")
            print(f"\n[{sender}]: {content[:400]}")
            if len(content) > 400:
                print("... (truncated)")
            seen_ids.add(m.get("id"))
            
    print("\nPhase 10 Test execution complete.")

if __name__ == "__main__":
    run_test()
