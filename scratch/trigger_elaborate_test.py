import time
import requests

API_URL = "http://127.0.0.1:3002/api"

def trigger_elaborate_test():
    print("Clearing chat history to start a clean run...")
    requests.post(f"{API_URL}/chat", json={"content": "@@clear chat", "sender": "user"})
    time.sleep(2)
    
    msg = (
        "@GeneralAG @job: Erstelle ein neues Produkt-Feature-Blatt für ein intelligentes Datei-Management-Tool. "
        "ResearcherAG soll wichtige Trends und Dateigrößen-Features recherchieren. "
        "WriterAG soll basierend darauf einen überzeugenden Produkttext entwerfen. "
        "CoderAG soll eine minimalistische HTML/CSS-Präsentationsseite erstellen."
    )
    print(f"Triggering E2E job:\n{msg}")
    res = requests.post(f"{API_URL}/chat", json={"content": msg, "sender": "user"})
    print("API Response:", res.json())

if __name__ == "__main__":
    trigger_elaborate_test()
