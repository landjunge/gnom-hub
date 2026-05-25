import requests, time, sys, os

API = "http://127.0.0.1:3002/api"

def test_live():
    print("=== LIVE-TEST START: PHASE 13 USER FEEDBACK LOOP ===")
    
    # 1. Send the Job request
    payload = {
        "content": "@GeneralAG @job: Erstelle eine neue Landingpage für ein KI-Tool.",
        "sender": "user"
    }
    print(f"Poste Job an {API}/chat...")
    res = requests.post(f"{API}/chat", json=payload)
    print("API Response:", res.json())
    
    # 2. Poll chat history for GeneralAG's workflow completion and feedback prompt
    print("\nWarte auf Swarm-Aktivität und GeneralAG Abschlussmeldung (bis zu 90 Sek)...")
    feedback_msg = None
    t0 = time.time()
    while time.time() - t0 < 90:
        msgs = requests.get(f"{API}/chat?limit=15").json()
        for m in msgs:
            content = m.get("content", "")
            sender = m.get("sender", "")
            if sender.lower() == "generalag" and "feedback" in content.lower() and "beendet" in content.lower():
                feedback_msg = m
                break
        if feedback_msg:
            break
        time.sleep(3)
        
    if not feedback_msg:
        print("❌ Zeitüberschreitung: GeneralAG hat nicht nach Feedback gefragt!")
        sys.exit(1)
        
    print("\n[LIVE] GeneralAG Antwort empfangen:")
    print(f"Sender: {feedback_msg['sender']} -> {feedback_msg['content']}")
    
    # 3. Send feedback comment via /api/feedback
    feedback_payload = {
        "vote": "down",
        "comment": "Gut, aber der Text könnte persönlicher sein"
    }
    print("\nPoste User-Feedback an /api/feedback...")
    res = requests.post(f"{API}/feedback", json=feedback_payload)
    print("Feedback API Response:", res.json())
    
    # 4. Wait for SoulAG / GeneralAG to process and learn from the feedback
    print("\nWarte auf automatische Lerneffekte in Chat-History (bis zu 30 Sek)...")
    learned_msg = None
    t0 = time.time()
    while time.time() - t0 < 30:
        msgs = requests.get(f"{API}/chat?limit=15").json()
        for m in msgs:
            content = m.get("content", "")
            sender = m.get("sender", "")
            if sender.lower() == "generalag" and "gelernt" in content.lower():
                learned_msg = m
                break
        if learned_msg:
            break
        time.sleep(2)
        
    if not learned_msg:
        print("❌ Zeitüberschreitung: SoulAG / GeneralAG haben das Feedback nicht gelernt!")
        sys.exit(1)
        
    print("\n[LIVE] Feedback-Lernnachricht empfangen:")
    print(f"Sender: {learned_msg['sender']} -> {learned_msg['content']}")
    
    print("\n=== LIVE-TEST ERFOLGREICH BEENDET ===")

if __name__ == "__main__":
    test_live()
