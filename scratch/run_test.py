import time
import requests
import json
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
        r = requests.get(f"{API_URL}/chat?limit=30")
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

def monitor_until_workflow_completes():
    seen_ids = set()
    # Populate existing messages to avoid printing historical ones
    for m in get_chat():
        seen_ids.add(m.get("id"))
    
    workflow_active = True
    no_workflow_count = 0
    
    while workflow_active or no_workflow_count < 3:
        time.sleep(3)
        # Check active workflow in metrics
        metrics = get_metrics()
        wf = metrics.get("_active_workflow")
        comms = metrics.get("_swarm_comms", [])
        
        if wf:
            print(f"\n[Dashboard Banner] {wf}")
            if comms:
                print(f"  └─ Swarm Comms: {comms}")
            workflow_active = True
            no_workflow_count = 0
        else:
            workflow_active = False
            no_workflow_count += 1
            
        # Get new messages
        new_msgs = [m for m in get_chat() if m.get("id") not in seen_ids]
        for m in new_msgs:
            sender = m.get("sender")
            content = m.get("content")
            print(f"\n[{sender}]: {content}")
            seen_ids.add(m.get("id"))
            
    print("\nWorkflow completed.")

def run_tests():
    print_banner("TEST 1: Start Landing Page swarm workflow")
    msg1 = "@GeneralAG @job: Erstelle eine neue Landingpage. ResearcherAG soll Inhalte recherchieren, WriterAG soll Texte schreiben, CoderAG soll den Code bauen."
    print(f"Posting: {msg1}")
    res1 = post_chat(msg1)
    print(f"API Response: {res1}")
    
    monitor_until_workflow_completes()
    
    time.sleep(5)
    
    print_banner("TEST 2: Start Website analysis & optimization workflow")
    msg2 = "@GeneralAG @job: Analysiere die aktuelle Webseite und optimiere sie."
    print(f"Posting: {msg2}")
    res2 = post_chat(msg2)
    print(f"API Response: {res2}")
    
    monitor_until_workflow_completes()
    
    # Print tails of logs
    print_banner("Agent Logs summary")
    for name in ["generalAG", "researcherAG", "writerAG", "coderAG"]:
        log_file = Path("logs") / f"logs_{name}.txt"
        if log_file.exists():
            lines = log_file.read_text().splitlines()
            print(f"\n--- {name} logs (last 10 lines) ---")
            for line in lines[-10:]:
                print(line)

if __name__ == "__main__":
    run_tests()
