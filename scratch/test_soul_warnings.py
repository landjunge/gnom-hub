import sys, os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import gnom_hub.db
from gnom_hub.soul import soul_instance
from gnom_hub.db import save_soul_fact, get_chat_history

def test_soul_warnings():
    print("============================================================")
    print(" 🚀 STARTING SOULAG INJECTION WARNING TEST")
    print("============================================================")
    
    gnom_hub.db.init_db()
    
    # Save a test fact
    save_soul_fact("test_warn_key", "Always use tab for indentation.", agent="SoulAG")
    
    # Reset/clear injections tracking
    soul_instance._injections.clear()
    
    # First injection (no warning)
    sys_prompt = "You are CoderAG."
    res1 = soul_instance.inject_context(sys_prompt, "Always use tab for indentation. What style should I use?", agent_name="CoderAG")
    print("First injection output:\n", res1)
    
    # Verify that the fact was injected
    assert "Always use tab" in res1
    
    # Second injection (should trigger warning)
    res2 = soul_instance.inject_context(sys_prompt, "Always use tab for indentation. What style should I use?", agent_name="CoderAG")
    print("\nSecond injection output:\n", res2)
    assert "Always use tab" in res2
    
    # Verify that a warning message was posted to the chat database
    hist_after = get_chat_history("default", limit=5)
    warning_msgs = [m for m in hist_after if m.get("sender") == "SoulAG" and "[HINWEIS]" in m.get("content")]
    
    print("\nWarning messages found in chat:")
    for m in warning_msgs:
        print(f"- {m['content']}")
        
    assert len(warning_msgs) > 0, "No warning message was posted by SoulAG!"
    assert "@CoderAG" in warning_msgs[0]["content"], "Warning didn't target CoderAG!"
    assert "Always use tab" in warning_msgs[0]["content"], "Warning didn't mention the injected fact!"
    
    print("============================================================")
    print(" 🎉 SOULAG WARNING TEST PASSED SUCCESSFULLY!")
    print("============================================================")

if __name__ == "__main__":
    test_soul_warnings()
