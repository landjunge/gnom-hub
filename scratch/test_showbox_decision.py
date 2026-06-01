import sys
import os
import time
import threading

sys.path.insert(0, os.path.abspath("/Users/landjunge/Documents/AG-Flega/src"))

from gnom_hub.db.legacy_db import get_state_value, set_state_value, set_agent_status, get_all_agents
from gnom_hub.core.security.gatekeeper import verify_write

def wait_and_act(action_type):
    print(f"    [Mock User] Thread started, waiting for a pending decision to act ({action_type})...")
    existing_keys = set(get_state_value("pending_decisions", {}).keys())
    
    decision_id = None
    for _ in range(120):  # Wait up to 12 seconds
        time.sleep(0.1)
        pending = get_state_value("pending_decisions", {})
        new_keys = set(pending.keys()) - existing_keys
        if new_keys:
            decision_id = list(new_keys)[0]
            break
            
    if not decision_id:
        print("    [Mock User] ERROR: Timeout waiting for pending decision!")
        return
        
    print(f"    [Mock User] Found decision {decision_id}. Simulating choice: {action_type}")
    if action_type == "approve":
        from gnom_hub.chat.chat_commands import handle_approve_decision
        res = handle_approve_decision(decision_id)
    else:
        from gnom_hub.chat.chat_commands import handle_reject_decision
        res = handle_reject_decision(decision_id)
    print(f"    [Mock User] Action result: {res}")

def main():
    print("=== STARTING SHOWBOX DECISION SYSTEM TEST ===")
    
    from gnom_hub.db.legacy_db import create_agent_record
    agents = get_all_agents()
    if not any(a["name"] == "CoderAG" for a in agents):
        create_agent_record("CoderAG", role="coder", status="online")
        print("    Mock CoderAG agent record created.")
        
    set_state_value("pending_decisions", {})
    set_state_value("approved_security_writes", [])
    set_state_value("enable_confirmations", True)
    
    agent = {"name": "CoderAG", "role": "coder"}
    fn = "/etc/passwd"
    content = "test content"
    wd = "/Users/landjunge/Documents/AG-Flega"
    perms = ["read", "write"]
    
    # 1. Approval Test Case
    print("[1] Launching verify_write check in worker thread (should block and request decision)...")
    t1 = threading.Thread(target=wait_and_act, args=("approve",), daemon=True)
    t1.start()
    
    start_time = time.time()
    approved = verify_write(agent, fn, content, wd, perms)
    elapsed = time.time() - start_time
    
    print(f"\n[2] verify_write finished in {elapsed:.2f} seconds.")
    print(f"    Result (approved): {approved}")
    assert approved is True, "The write action should be approved after user simulation"
    
    whitelist = get_state_value("approved_security_writes", [])
    print(f"    approved_security_writes whitelist: {whitelist}")
    assert fn in whitelist, f"'{fn}' must be in the approved_security_writes list"
    print("    SUCCESS: Decision approved and whitelisted successfully!")
    
    # 2. Rejection Test Case
    print("\n[3] Testing REJECTION flow...")
    set_state_value("pending_decisions", {})
    set_state_value("approved_security_writes", [])
    
    t2 = threading.Thread(target=wait_and_act, args=("reject",), daemon=True)
    t2.start()
    
    start_time = time.time()
    approved = verify_write(agent, fn, content, wd, perms)
    elapsed = time.time() - start_time
    
    print(f"\n[4] verify_write finished in {elapsed:.2f} seconds.")
    print(f"    Result (approved): {approved}")
    assert approved is False, "The write action should be denied after user rejection"
    
    whitelist = get_state_value("approved_security_writes", [])
    print(f"    approved_security_writes whitelist: {whitelist}")
    assert fn not in whitelist, f"'{fn}' must NOT be in the approved_security_writes list"
    print("    SUCCESS: Decision rejected successfully!")
    
    # 3. Persistence Test Case
    print("\n[5] Testing Showbox persistence (preventing overrides during pending decision)...")
    set_state_value("pending_decisions", {"test_id": {"status": "pending"}})
    
    from gnom_hub.db.legacy_db import set_active_showbox, get_active_showbox
    set_active_showbox("Latest Update")
    active = get_active_showbox()
    print(f"    Active Showbox (should NOT be 'Latest Update'): '{active}'")
    assert active != "Latest Update", "Showbox override must be blocked during pending decisions!"
    
    set_state_value("pending_decisions", {"test_id": {"status": "approved"}})
    set_active_showbox("Latest Update")
    active = get_active_showbox()
    print(f"    Active Showbox (should be 'Latest Update'): '{active}'")
    assert active == "Latest Update", "Showbox override must be allowed after decision is resolved!"
    print("    SUCCESS: Showbox persistence works perfectly!")
    
    set_state_value("enable_confirmations", False)
    print("\n=== SHOWBOX DECISION SYSTEM TEST PASSED ===")
    os._exit(0)

if __name__ == "__main__":
    main()
