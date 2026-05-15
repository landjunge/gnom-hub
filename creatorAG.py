"""Creator Agent - Setup Assistant für Gnom-Hub Agenten"""
import os, sys

def setup():
    print("🤖 Willkommen beim Gnom-Hub Installer!")
    try: num = int(input("Wie viele Agenten möchtest du erstellen? "))
    except: return print("Bitte eine Zahl eingeben!")
    
    if not os.path.exists("org.py"): return print("❌ Fehler: org.py (Template) nicht gefunden!")
    with open("org.py", "r") as f: template = f.read()
    
    for i in range(num):
        print(f"\n--- Agent {i+1} ---")
        name = input("Name des Agenten (z.B. InfoAG): ").strip()
        print("System-Prompt / Rolle (max 7 Zeilen, beenden mit 2x Enter):")
        lines = []
        while True:
            l = input()
            if not l: break
            lines.append(l)
        desc = "\\n".join(lines).strip()
        if not name: continue
        
        code = template.replace('NAME, POLL = "http://127.0.0.1:3100/sse", "OrgAG", 10', f'NAME, POLL = "http://127.0.0.1:3100/sse", "{name}", 10')
        code = code.replace('SYS = "Du bist OrgAG."', f'SYS = """{desc}"""')
        
        with open(f"{name}.py", "w") as f: f.write(code)
        
        with open("start_agents.sh", "r") as f: lines = f.readlines()
        cmd = f"python3 {name}.py > logs_{name.lower()}.txt 2>&1 &\n"
        if cmd not in lines:
            lines.insert(-2, cmd)
            with open("start_agents.sh", "w") as f: f.writelines(lines)
        
        print(f"✅ {name}.py erstellt und in start_agents.sh registriert!")
    
    print("\n🎉 Setup abgeschlossen! Starte './start_agents.sh' um alle Agenten hochzufahren.")

if __name__ == "__main__": setup()
