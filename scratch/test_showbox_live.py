import urllib.request
import json
import time

def send_presentation(name, slides, sender):
    url = "http://127.0.0.1:3002/api/showbox/presentations"
    data = {
        "name": name,
        "slides": slides,
        "sender": sender
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as res:
            print(f"Successfully sent presentation '{name}' from '{sender}': {res.read().decode('utf-8')}")
    except Exception as e:
        print(f"Error sending presentation '{name}': {e}")

def main():
    print("=== STARTING LIVE SHOWBOX ROUTING TEST ===")
    
    # 1. System Agent Layer (Layer 1)
    print("\n[1] Sending System Agent presentation (SoulAG)...")
    send_presentation(
        name="SoulAG Status",
        slides=[
            "<div style='color:#00e5ff; font-weight:bold;'>SoulAG Aktivität</div>",
            "Gedächtnis erfolgreich aktualisiert.",
            "Semantischer Index ist synchronisiert."
        ],
        sender="SoulAG"
    )
    time.sleep(3)
    
    # 2. Worker Agent Layer (Layer 2)
    print("\n[2] Sending Worker Agent presentation (CoderAG)...")
    send_presentation(
        name="CoderAG Code-Upgrade",
        slides=[
            "<div style='color:#ffa500; font-weight:bold;'>CoderAG Task</div>",
            "Refactoring des Moduls showbox.js abgeschlossen.",
            "Einbindung in index.html war erfolgreich."
        ],
        sender="CoderAG"
    )
    time.sleep(3)
    
    # 3. User / Decision Layer (Layer 3)
    print("\n[3] Sending Decision/User Blockade (WatchdogAG Blockade)...")
    send_presentation(
        name="Blockade: Schreibzugriff",
        slides=[
            "<div style='color:#39ff14; font-weight:bold;'>Sicherheit-Freigabe</div>",
            "Watchdog blockiert Schreiben in <code>/etc/passwd</code>.",
            "Soll die Freigabe erteilt werden?<br><br>"
            "<button style='background:rgba(57,255,20,0.15); border:1px solid #39ff14; color:#fff; padding:4px 10px; border-radius:4px; font-weight:bold; cursor:pointer;'>Ja, erlauben</button> "
            "<button style='background:rgba(255,0,0,0.15); border:1px solid #ff0000; color:#fff; padding:4px 10px; border-radius:4px; font-weight:bold; cursor:pointer;'>Nein, blockieren</button>"
        ],
        sender="WatchdogAG"
    )
    
    print("\n=== LIVE TEST PRESENTATIONS DISPATCHED ===")

if __name__ == "__main__":
    main()
