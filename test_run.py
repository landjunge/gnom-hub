import sys
sys.path.append('src/gnom_hub')
from routes_chat import handle_chat_message

prompt = "@bs Wir wollen den Gnom-Hub (https://github.com/landjunge/gnom-hub) viral machen und in Suchmaschinen auf Platz 1 für 'Zero Bloat Autonomous AI' bringen. Werft mir eure aggressivsten und effizientesten Ideen zu. Wie nutzen wir den visionAG und desktopAG, um das Projekt vollautomatisch im Web zu streuen?"

print("Starte Brainstorming...")
res = handle_chat_message(prompt)
print("\n--- ERGEBNIS ---")
print(res)
