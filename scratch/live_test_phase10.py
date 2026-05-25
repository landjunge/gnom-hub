import time, requests

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
        r = requests.get(f"{API_URL}/chat?limit=50")
        return list(reversed(r.json()))
    except Exception as e:
        return []

def get_metrics():
    try:
        return requests.get(f"{API_URL}/metrics").json()
    except Exception as e:
        return {}

def run_test_message(msg):
    print_banner(f"Sending message: {msg}")
    post_chat(msg)
    
    seen_ids = set(m.get("id") for m in get_chat())
    workflow_active = True
    no_workflow_count = 0
    
    while workflow_active or no_workflow_count < 8:
        time.sleep(3)
        metrics = get_metrics()
        wf = metrics.get("_active_workflow")
        comms = metrics.get("_swarm_comms", [])
        
        if wf:
            print(f"[Workflow State] {wf}")
            if comms:
                print(f"  └─ Swarm Comms: {comms}")
            workflow_active = True
            no_workflow_count = 0
        else:
            workflow_active = False
            no_workflow_count += 1
            
        new_msgs = [m for m in get_chat() if m.get("id") not in seen_ids]
        for m in new_msgs:
            print(f"\n[{m.get('sender')}]: {m.get('content')[:800]}")
            if len(m.get('content')) > 800:
                print("... (truncated)")
            seen_ids.add(m.get("id"))

# Clear Chat
requests.post(f"{API_URL}/chat", json={"content": "@@clear chat", "sender": "user"})
time.sleep(1)

run_test_message("@GeneralAG @job: Erstelle eine neue Landingpage. ResearcherAG soll Inhalte recherchieren, WriterAG soll Texte schreiben, CoderAG soll den Code bauen.")
print("\n--- Waiting 5 seconds before starting test message 2 ---")
time.sleep(5)
run_test_message("@GeneralAG @job: Analysiere die aktuelle Webseite und optimiere sie.")
