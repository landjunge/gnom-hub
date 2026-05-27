import time
import requests

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

def run_system_level_permission_tests():
    print_banner("System-Level Permission Tests for GeneralAG")
    import sys, os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, project_root)
    sys.path.insert(0, os.path.join(project_root, "src"))
    try:
        from gnom_hub.gatekeeper import verify_write, verify_cmd
        from gnom_hub.path_validator import is_worker_blocked, is_security_block
        from gnom_hub.tool_registry import get_tools_for_agent
        
        mock_general = {"name": "GeneralAG", "role": "general"}
        
        # Test 1: Tool Registry (no tools for general)
        tools = get_tools_for_agent(mock_general)
        assert tools == {}, f"GeneralAG should have no tools, got: {tools}"
        print("✅ System Test 1 Passed: GeneralAG gets 0 tools in its prompt.")
        
        # Test 2: verify_write must return False for generalag
        write_ok = verify_write(mock_general, "test.py", "print('hello')", "/tmp", [])
        assert write_ok is False, "GeneralAG write operations must be blocked by gatekeeper."
        print("✅ System Test 2 Passed: GeneralAG WRITE operation blocked.")
        
        # Test 3: verify_cmd must return False for generalag
        cmd_ok = verify_cmd(mock_general, "ls -la")
        assert cmd_ok is False, "GeneralAG shell operations must be blocked by gatekeeper."
        print("✅ System Test 3 Passed: GeneralAG SHELL operation blocked.")
        
        # Test 4: Path validator must block generalag
        blocked = is_worker_blocked(mock_general, "test.py", "/tmp", [])
        assert blocked is True, "GeneralAG must be blocked in path validator."
        print("✅ System Test 4 Passed: GeneralAG blocked in path validation.")
        
        # Test 5: process_actions must allow Showbox but block Write/Read/Shell
        from gnom_hub.action_handlers import process_actions
        ans = "Hello [WRITE: test.py]print('bad')[/WRITE] [READ: test.py] [SHELL: ls] <SHOWBOX:1>['Slide 1']</SHOWBOX>"
        processed = process_actions(ans, mock_general, [], False, "/tmp")
        assert "[Gatekeeper: Schreibzugriff" in processed or "verweigert" in processed, f"Write should be blocked: {processed}"
        assert "[WatchdogAG: Lesezugriff" in processed, f"Read should be blocked: {processed}"
        assert "[Gatekeeper: Befehlsausführung" in processed or "verweigert" in processed, f"Shell should be blocked: {processed}"
        assert "<SHOWBOX:1>" in processed, f"Showbox should be allowed: {processed}"
        assert '"sig"' in processed, f"Showbox signature should be present: {processed}"
        print("✅ System Test 5 Passed: GeneralAG Showbox is allowed, but file reads/writes/commands are blocked.")
        
        return True
    except Exception as e:
        print(f"❌ System-level permission tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_chat_delegation_test():
    print_banner("E2E Chat Delegation Test")
    
    # 1. Clear chat history
    print("Clearing chat history...")
    requests.post(f"{API_URL}/chat", json={"content": "@@clear chat", "sender": "user"})
    time.sleep(2)
    
    # 2. Post a task directly without @GeneralAG or @job to see if it defaults to GeneralAG and delegates.
    msg = "Erstelle ein Python-Skript, das die Dateigröße berechnet."
    print(f"Posting user message:\n{msg}\n")
    res = post_chat(msg)
    print(f"API Response: {res}\n")
    
    # 3. Monitor chat
    seen_ids = set()
    generalag_delegated = False
    coderag_replied = False
    
    print("Monitoring chat responses for 120 seconds...")
    for _ in range(60):
        time.sleep(2)
        chat = get_chat()
        new_msgs = [m for m in chat if m.get("id") not in seen_ids]
        for m in new_msgs:
            sender = m.get("sender")
            content = m.get("content")
            print(f"[{sender}]: {content[:400]}...")
            seen_ids.add(m.get("id"))
            
            if sender == "GeneralAG":
                # Check for case-insensitive CoderAG mention
                if "@coderag" in content.lower():
                    generalag_delegated = True
                    print("✅ GeneralAG successfully delegated to CoderAG!")
                
                # Check for direct answer indicators in GeneralAG response
                if "import os" in content or "def " in content or "```python" in content:
                    print("❌ Failure: GeneralAG directly outputted code!")
            
            if sender == "CoderAG":
                if "import os" in content or "def " in content or "```python" in content or "os.path.getsize" in content:
                    coderag_replied = True
                    print("✅ CoderAG successfully answered the delegated task with code!")
                    
    return generalag_delegated, coderag_replied

if __name__ == "__main__":
    sys_ok = run_system_level_permission_tests()
    delegated, replied = run_chat_delegation_test()
    
    print_banner("TEST SUMMARY")
    if sys_ok and delegated and replied:
        print("🎉 ALL TESTS PASSED: GeneralAG is restricted at the system level and successfully orchestrates.")
    else:
        print(f"❌ TEST FAILED. Sys Tests: {sys_ok}, Delegated: {delegated}, Replied: {replied}")
