import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import uuid
from gnom_hub.soul import handle_user_feedback
import gnom_hub.infrastructure.router.router as router
from gnom_hub.db import get_db_conn

def test_feedback():
    print("--- TESTING USER FEEDBACK LOOP & CONTINUOUS IMPROVEMENT ---")
    
    # 1. Clear previous feedback facts to avoid clutter
    with get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM soul_memory WHERE key LIKE 'feedback_%'")
            conn.execute("DELETE FROM soul_memory WHERE key LIKE 'evolution_%'")
            
    # 2. Mock router to capture LLM invocation details
    original_call = router._call
    original_try_keys = router._try_keys
    called_sys = None
    called_p = None
    
    def mock_call(pvd, mdl, key, msgs, n):
        nonlocal called_sys, called_p
        called_sys = msgs[0]["content"]
        called_p = msgs[1]["content"]
        return '[{"agent": "WriterAG", "rule": "Verwende emotionaleres Copywriting."}]'
        
    def mock_try_keys(pvd, mdl, keys, msgs, n):
        nonlocal called_sys, called_p
        called_sys = msgs[0]["content"]
        called_p = msgs[1]["content"]
        return '[{"agent": "WriterAG", "rule": "Verwende emotionaleres Copywriting."}]'
        
    router._call = mock_call
    router._try_keys = mock_try_keys
    
    try:
        # 3. Simulate user submitting feedback
        vote = "down"
        comment = "Der Text der Landingpage könnte persönlicher und emotionaler sein."
        print(f"Sende Feedback: Vote={vote}, Kommentar='{comment}'")
        handle_user_feedback(vote, comment)
        
        # 4. Verify feedback was saved
        with get_db_conn() as conn:
            fb_rows = conn.execute("SELECT key, value FROM soul_memory WHERE key LIKE 'feedback_%'").fetchall()
            ev_rows = conn.execute("SELECT key, value FROM soul_memory WHERE key LIKE 'evolution_%'").fetchall()
            
        print("\nGespeicherte Feedback-Fakten:")
        for r in fb_rows:
            print(f"Key: {r['key']} -> Value: {r['value']}")
            
        print("\nAus Feedback gelernte Evolution-Fakten:")
        for r in ev_rows:
            print(f"Key: {r['key']} -> Value: {r['value']}")
            
        assert len(fb_rows) > 0, "Feedback wurde nicht in soul_memory gespeichert!"
        assert len(ev_rows) > 0, "Es wurden keine Evolution-Regeln aus dem Feedback gelernt!"
        assert "User-Feedback:" in ev_rows[0]['value'], "Evolution-Wert enthält nicht das Präfix 'User-Feedback:'!"
        assert "Optimierer" in called_sys, "GeneralAG wurde nicht als Feedback-Optimierer gerufen!"
        
        print("\nFeedback-Lernschleife erfolgreich verifiziert!")
        
    finally:
        router._call = original_call
        router._try_keys = original_try_keys
        
    print("\nFeedback-Test erfolgreich abgeschlossen!")

if __name__ == "__main__":
    test_feedback()
