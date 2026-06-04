import os
import time

paths = [
    "/Users/landjunge/Desktop/apikeys",
    "/Users/landjunge/Desktop/apikeys.txt",
    "/Users/landjunge/Desktop/api_keys.txt"
]

print("Warte auf Erstellung der apikeys-Datei auf dem Desktop...")
found = False
while not found:
    for p in paths:
        if os.path.exists(p):
            # Check if it has been modified recently or contains the required text
            with open(p, "r") as f:
                content = f.read()
            if "netzwerkpunkt" in content or "feenreich" in content:
                print(f"\n🎉 Datei gefunden unter {p}!")
                print("Inhalt:")
                print("="*40)
                print(content)
                print("="*40)
                found = True
                break
    if not found:
        time.sleep(2)
