import sys, time, requests

sys.path.insert(0, "src")
from gnom_hub.soul import soul_instance

def print_banner(text):
    print("=" * 60)
    print(f" {text}")
    print("=" * 60)

print_banner("1. Testing Semantic Context Injection (Zero Keyword Overlap)")
injected = soul_instance.inject_context(
    "Du bist CoderAG. Erstelle die Webseiten-Templates.", 
    "Erstelle eine moderne HTML-Vorlage für unser Corporate-Design."
)
print(injected)
print("\n")

API_URL = "http://127.0.0.1:3002/api"

# Post Session 2 Job
msg = '@GeneralAG @job: Erstelle eine einfache HTML-Vorlage für unsere Homepage.'
print_banner(f"2. Posting Job to GeneralAG: {msg}")
requests.post(f"{API_URL}/chat", json={"content": msg, "sender": "user"})

seen_ids = set()
for m in requests.get(f"{API_URL}/chat?limit=50").json():
    seen_ids.add(m.get("id"))

workflow_active = True
no_workflow_count = 0

print("Monitoring swarm execution turns...")
while workflow_active or no_workflow_count < 12:
    time.sleep(3)
    metrics = requests.get(f"{API_URL}/metrics").json()
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
        
    try:
        new_msgs = [m for m in reversed(requests.get(f"{API_URL}/chat?limit=50").json()) if m.get("id") not in seen_ids]
        for m in new_msgs:
            print(f"\n[{m.get('sender')}]: {m.get('content')[:600]}")
            if len(m.get('content')) > 600:
                print("... (truncated)")
            seen_ids.add(m.get("id"))
    except Exception as e:
        print(f"Error reading chat: {e}")
