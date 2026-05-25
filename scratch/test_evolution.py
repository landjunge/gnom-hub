import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import sqlite3
from gnom_hub.soul import run_evolution
from gnom_hub.router import ask_router
import gnom_hub.router
from gnom_hub.db import get_db_conn

def test_evolution():
    print("--- TESTING AGENT EVOLUTION & SELF-IMPROVEMENT ---")
    
    # 1. Clear previous evolution facts for CoderAG to avoid interference
    with get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM soul_memory WHERE key LIKE 'evolution_CoderAG%'")
    
    # 2. Run run_evolution with simulated landing page job
    task = "Erstelle eine neue Landingpage für ein KI-Tool."
    history = """
    [CoderAG] Ich habe eine Landingpage in HTML erstellt, aber das Design war zu einfach (nur weißer Hintergrund, keine CSS Stylesheets).
    [WriterAG] Texte wurden eingefügt, aber es fehlt der Slogan für das KI-Tool.
    [EditorAG] Landingpage validiert. Sie funktioniert, aber ist visuell nicht ansprechend.
    """
    print("Starte run_evolution...")
    run_evolution(task, history)
    
    # 3. Check if suggestions were saved
    with get_db_conn() as conn:
        rows = conn.execute("SELECT key, value FROM soul_memory WHERE key LIKE 'evolution_%'").fetchall()
    
    print("\nIn soul_memory gespeicherte Evolution-Fakten:")
    for r in rows:
        print(f"Key: {r['key']} -> Value: {r['value']}")
        
    assert len(rows) > 0, "Es wurden keine Evolution-Regeln gelernt!"
    
    # 4. Check if the rules are injected in router prompt
    original_call = gnom_hub.router._call
    original_try_keys = gnom_hub.router._try_keys
    called_sys = None
    
    def mock_call(pvd, mdl, key, msgs, n):
        nonlocal called_sys
        called_sys = msgs[0]["content"]
        return "Mock Response"
        
    def mock_try_keys(pvd, mdl, keys, msgs, n):
        nonlocal called_sys
        called_sys = msgs[0]["content"]
        return "Mock Response"
        
    gnom_hub.router._call = mock_call
    gnom_hub.router._try_keys = mock_try_keys
    
    try:
        ask_router("Erstelle Landingpage", agent_name="CoderAG")
        print("\nInjected System Prompt for CoderAG:")
        print(called_sys)
        assert called_sys is not None, "System Prompt wurde nicht erfasst!"
        assert "=== SELBSTVERBESSERTE REGELN ===" in called_sys, "Selbstverbesserte Regeln Sektion fehlt!"
        assert any("CSS" in line or "Landingpage" in line for line in called_sys.split("\n")), "CoderAG Regel fehlt im Prompt!"
        print("\nPrompt Injection erfolgreich verifiziert!")
    finally:
        gnom_hub.router._call = original_call
        gnom_hub.router._try_keys = original_try_keys
    
    print("\nEvolution-Test erfolgreich abgeschlossen!")

if __name__ == "__main__":
    test_evolution()
