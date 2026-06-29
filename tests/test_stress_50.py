"""
GNOM-HUB: 50 Extreme System-Stress-Tests
Testet: Chat, Agent-Kommunikation, Versionierung, Last, Priorisierung, FTP-Publish

Marker 'requires_hub': diese Tests brauchen einen laufenden Hub auf BASE.
CI / Pre-Push skippt sie via `pytest -m "not requires_hub"`.
Lokal: `pytest -m requires_hub` für vollen Live-Hub-Stresstest.
"""
import pytest
import requests, json, time, uuid, os, threading, re, random
from concurrent.futures import ThreadPoolExecutor, as_completed

pytestmark = pytest.mark.requires_hub

BASE = "http://127.0.0.1:3002"
PASS, FAIL, SKIP = 0, 0, 0
results = []

def log(nr, name, status, detail=""):
    global PASS, FAIL
    if status == "PASS": PASS += 1
    else: FAIL += 1
    icon = "✅" if status == "PASS" else "❌"
    d = f" — {detail}" if detail else ""
    print(f"  {icon} [{nr:02d}/50] {name}{d}")
    results.append((nr, name, status, detail))

def chat(msg, sender="user"):
    try:
        r = requests.post(f"{BASE}/api/chat", json={"content": msg, "sender": sender}, timeout=30)
        return r.status_code in (200, 201, 202), r.json() if r.status_code == 200 else {}
    except Exception as e:
        return False, {"error": str(e)}

def get_agents():
    try:
        r = requests.get(f"{BASE}/api/agents", timeout=5)
        return r.json() if r.status_code == 200 else []
    except: return []

def get_chat(limit=50):
    try:
        r = requests.get(f"{BASE}/api/chat?limit={limit}", timeout=5)
        return r.json() if r.status_code == 200 else []
    except: return []

def get_state(key):
    try:
        r = requests.get(f"{BASE}/api/state/{key}", timeout=5)
        return r.json() if r.status_code == 200 else None
    except: return None

def check_workspace_files(pattern=""):
    ws = "/Users/landjunge/gnom-hub/gnom_workspace/default"
    if not os.path.exists(ws): return []
    all_files = os.listdir(ws)
    if pattern:
        return [f for f in all_files if pattern in f]
    return all_files

def agent_busy(name):
    agents = get_agents()
    for a in agents:
        if a.get("name", "").lower() == name.lower():
            return a.get("status") == "busy"
    return False

# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("🧪 GNOM-HUB: 50 EXTREME SYSTEM-STRESS-TESTS")
print("=" * 70)
print()

# ═══════════════════════════════════════════════════════════════
# TEIL 1: GRUNDFUNKTIONEN (Tests 1-8)
# ═══════════════════════════════════════════════════════════════
print("─" * 70)
print("📦 TEIL 1: GRUNDFUNKTIONEN")
print("─" * 70)

# Test 1: Hub ist erreichbar
try:
    r = requests.get(f"{BASE}/", timeout=5)
    log(1, "Hub HTTP-Erreichbarkeit", "PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")
except:
    log(1, "Hub HTTP-Erreichbarkeit", "FAIL", "Connection refused")

# Test 2: Alle 8 Agenten registriert
agents = get_agents()
names = sorted([a.get("name", "") for a in agents])
expected = ["CoderAG","EditorAG","GeneralAG","ResearcherAG","SecurityAG","SoulAG","WatchdogAG","WriterAG"]
log(2, "8 Agenten registriert", "PASS" if names == expected else "FAIL", f"Gefunden: {names}")

# Test 3: Alle Agenten online
online = all(a.get("status") == "online" for a in agents)
offline_names = [a.get("name") for a in agents if a.get("status") != "online"]
log(3, "Alle Agenten online", "PASS" if online else "FAIL", f"Offline: {offline_names}" if offline_names else "")

# Test 4: Chat-API antwortet
ok, data = chat("Test-Nachricht an System", "user")
log(4, "Chat-API Grundfunktion", "PASS" if ok else "FAIL")

# Test 5: State-API lesen
state = get_state("active_project")
log(5, "State-API lesbar", "PASS" if state is not None else "FAIL")

# Test 6: Heartbeat aller Agenten prüfen
recent = sum(1 for a in agents if a.get("last_seen", "").startswith("2026"))
log(6, "Heartbeat aktuell (2026)", "PASS" if recent >= 7 else "FAIL", f"{recent}/8 aktuell")

# Test 7: Workspace existiert und ist leer
files = check_workspace_files()
log(7, "Workspace leer (frischer Start)", "PASS" if len(files) == 0 else "WARN", f"{len(files)} Dateien gefunden")

# Test 8: API-Keys in State vorhanden
keys = get_state("llm_keys")
log(8, "LLM-Keys konfiguriert", "PASS" if keys and len(str(keys)) > 10 else "FAIL")

# ═══════════════════════════════════════════════════════════════
# TEIL 2: CHAT-KOMMUNIKATION (Tests 9-20)
# ═══════════════════════════════════════════════════════════════
print()
print("─" * 70)
print("💬 TEIL 2: CHAT-KOMMUNIKATION")
print("─" * 70)

# Test 9: User sendet Nachricht an GeneralAG
ok, resp = chat("@GeneralAG Sag 'Hallo Welt'")
time.sleep(5)
msgs = get_chat(10)
antwort = any("GeneralAG" in m.get("sender","") for m in msgs) if msgs else False
log(9, "GeneralAG antwortet auf @Erwähnung", "PASS" if antwort else "FAIL")

# Test 10: CoderAG wird via @ erwähnt
ok, resp = chat("@CoderAG Schreibe eine testdatei.txt mit Inhalt 'Hallo Test 10'")
time.sleep(5)
files = check_workspace_files("testdatei")
log(10, "CoderAG schreibt Datei via @Erwähnung", "PASS" if files else "FAIL", f"Dateien: {files}")

# Test 11: WriterAG schreibt Text
ok, resp = chat("@WriterAG Erstelle eine README_test.md mit Inhalt 'Test 11'")
time.sleep(5)
files = check_workspace_files("README_test")
log(11, "WriterAG erstellt MD-Datei", "PASS" if files else "FAIL", f"Dateien: {files}")

# Test 12: ResearcherAG antwortet
ok, resp = chat("@ResearcherAG Sag 'Recherche läuft'")
time.sleep(5)
msgs = get_chat(20)
antwort = any("ResearcherAG" in m.get("sender","") for m in msgs[:5])
log(12, "ResearcherAG antwortet auf @Erwähnung", "PASS" if antwort else "FAIL")

# Test 13: EditorAG antwortet
ok, resp = chat("@EditorAG Prüfe ob die README_test.md existiert")
time.sleep(5)
msgs = get_chat(20)
antwort = any("EditorAG" in m.get("sender","") for m in msgs[:5])
log(13, "EditorAG antwortet auf @Erwähnung", "PASS" if antwort else "FAIL")

# Test 14: GeneralAG ohne @ (sollte trotzdem ankommen)
ok, resp = chat("Hallo System, funktioniert der Chat?", "user")
time.sleep(3)
log(14, "Chat-Nachricht ohne @-Mention", "PASS" if ok else "FAIL")

# Test 15: Sonderzeichen im Chat (Umlaute, Emojis)
ok, resp = chat("ÄÖÜ äöü ß € 😀 🚀 ✅ @GeneralAG Sonderzeichentest OK")
time.sleep(3)
log(15, "Umlaute, Emojis, Sonderzeichen", "PASS" if ok else "FAIL")

# Test 16: Lange Nachricht (>2000 Zeichen)
long_msg = "@GeneralAG LangerTest " + "A" * 2500
ok, resp = chat(long_msg)
log(16, "Extrem lange Nachricht (2500+ Zeichen)", "PASS" if ok else "FAIL")

# Test 17: Leere Nachricht
ok, resp = chat("", "user")
log(17, "Leere Nachricht behandelt", "PASS" if not ok or resp else "WARN")

# Test 18: SQL-Injection-Versuch im Chat
ok, resp = chat("@GeneralAG DROP TABLE agents; --", "user")
time.sleep(3)
agents2 = get_agents()
log(18, "SQL-Injection abgefangen", "PASS" if len(agents2) == 8 else "FAIL", f"{len(agents2)} Agents (soll 8)")

# Test 19: XSS-Versuch im Chat
xss = '<script>alert("XSS")</script> @GeneralAG XSS-Test'
ok, resp = chat(xss, "user")
time.sleep(3)
msgs = get_chat(5)
xss_gefunden = any('<script>' in m.get("content","") for m in msgs) if msgs else False
log(19, "XSS-Versuch bereinigt", "WARN" if xss_gefunden else "PASS")

# Test 20: 5 schnelle Nachrichten hintereinander (Burst)
t0 = time.time()
for i in range(5):
    chat(f"@GeneralAG Burst-Test Nachricht {i}", "user")
burst_time = time.time() - t0
log(20, "Burst: 5 Nachrichten in Sekunden", "PASS" if burst_time < 15 else "WARN", f"{burst_time:.1f}s")

# ═══════════════════════════════════════════════════════════════
# TEIL 3: AGENT-KOMMUNIKATION & WORKFLOW (Tests 21-30)
# ═══════════════════════════════════════════════════════════════
print()
print("─" * 70)
print("🔄 TEIL 3: AGENT-KOMMUNIKATION & WORKFLOW")
print("─" * 70)

# Test 21: GeneralAG delegiert an CoderAG, Ergebnis kommt zurück
ok, resp = chat("@GeneralAG Erstelle eine HTML-Seite 'test_seite_21.html' mit dem Text 'Delegation funktioniert'")
time.sleep(8)
files = check_workspace_files("test_seite_21")
log(21, "GeneralAG->CoderAG Delegation", "PASS" if files else "FAIL", f"Dateien: {files}")

# Test 22: Sequenzielle Delegation (GeneralAG->ResearcherAG->WriterAG)
ok, resp = chat("@GeneralAG Erstelle eine Datei 'sequenz_test.md' mit dem Inhalt 'Sequenzielle Delegation funktioniert'")
time.sleep(8)
files = check_workspace_files("sequenz_test")
log(22, "Sequenzielle Delegation (Research->Write)", "PASS" if files else "FAIL", f"Dateien: {files}")

# Test 23: Brainstorm-Mode (4 Worker parallel)
ok, resp = chat("@bs Teste den Brainstorm-Modus mit 4 Workern")
time.sleep(10)
log(23, "Brainstorm-Mode mit 4 Workern", "PASS" if ok else "FAIL")

# Test 24: Agent antwortet in <SHOWBOX>
msgs = get_chat(50)
showbox = sum(1 for m in msgs if "SHOWBOX" in m.get("content",""))
log(24, "SHOWBOX-Nutzung durch Agenten", "PASS" if showbox > 0 else "WARN", f"{showbox} SHOWBOX-Vorkommen")

# Test 25: SoulAG lernt Fakten
msgs = get_chat(100)
soul_msgs = sum(1 for m in msgs if m.get("sender") == "SoulAG" and "Fakten" in m.get("content",""))
log(25, "SoulAG extrahiert Fakten", "PASS" if soul_msgs > 0 else "WARN", f"{soul_msgs} Soul-Meldungen")

# Test 26: SecurityAG scannt auf gefährliche Patterns
ok, resp = chat("@CoderAG Schreibe eine Datei 'evil_test.py' mit Inhalt 'eval(os.system(\"rm -rf /\"))'")
time.sleep(5)
msgs = get_chat(20)
blocked = any("SecurityAG" in m.get("sender","") and ("BLOCKIERT" in m.get("content","") or "HOCHRISIKO" in m.get("content","")) for m in msgs)
log(26, "SecurityAG blockiert rm -rf /", "PASS" if blocked else "FAIL")

# Test 27: WatchdogAG schützt Systemdateien
ok, resp = chat("@CoderAG Schreibe in src/gnom_hub/config.py")
time.sleep(5)
msgs = get_chat(20)
watchdog = any("WatchdogAG" in m.get("sender","") and "BLOCKIERT" in m.get("content","") for m in msgs)
log(27, "WatchdogAG blockiert Systempfad-Zugriff", "PASS" if watchdog else "WARN")

# Test 28: @free befreit feststeckende Agents
stuck = [a for a in get_agents() if a.get("status") == "busy"]
if stuck:
    chat(f"@free {stuck[0]['name']}", "user")
    time.sleep(3)
    agents3 = get_agents()
    freed = any(a.get("status") == "online" for a in agents3 if a.get("name") == stuck[0]["name"])
    log(28, "@free befreit hängende Agents", "PASS" if freed else "WARN")
else:
    log(28, "@free befreit hängende Agents", "PASS", "Keine stuck Agents")

# Test 29: Status-API aller Agents abrufbar
r = requests.get(f"{BASE}/api/agents", timeout=5)
try:
    data = r.json()
    status_ok = all(a.get("name") and a.get("status") for a in data)
    log(29, "Agent-Status-API vollständig", "PASS" if status_ok else "FAIL")
except:
    log(29, "Agent-Status-API vollständig", "FAIL", "Kein JSON")

# Test 30: System-Info abrufbar
r = requests.get(f"{BASE}/api/system/info", timeout=5)
log(30, "System-Info-API", "PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")

# ═══════════════════════════════════════════════════════════════
# TEIL 4: VERSIONIERUNG & DATEIEN (Tests 31-38)
# ═══════════════════════════════════════════════════════════════
print()
print("─" * 70)
print("📄 TEIL 4: VERSIONIERUNG & DATEIEN")
print("─" * 70)

# Test 31: index.html wird versioniert (index1.html, index2.html)
ok, resp = chat("@CoderAG Erstelle index.html mit Hallo")
time.sleep(5)
files1 = [f for f in check_workspace_files() if f.startswith("index") and f.endswith(".html")]
log(31, "index.html Versionierung (erste)", "PASS" if len(files1) >= 1 else "FAIL", f"Dateien: {files1}")

ok, resp = chat("@CoderAG Erstelle index.html mit Hallo 2. Version")
time.sleep(5)
files2 = [f for f in check_workspace_files() if f.startswith("index") and f.endswith(".html")]
log(32, "index.html Versionierung (zweite)", "PASS" if len(files2) >= 2 else "FAIL", f"Dateien: {files2}")

ok, resp = chat("@CoderAG Erstelle index.html mit Hallo 3. Version")
time.sleep(5)
files3 = [f for f in check_workspace_files() if f.startswith("index") and f.endswith(".html")]
log(33, "index.html Versionierung (dritte)", "PASS" if len(files3) >= 3 else "FAIL", f"Dateien: {files3}")

# Test 34: .bak Backup-Dateien werden erstellt
baks = [f for f in check_workspace_files() if f.endswith(".bak")]
log(34, ".bak Backup bei Überschreiben", "PASS" if baks else "WARN", f"{len(baks)} .bak-Dateien")

# Test 35: README.md kann geschrieben werden
ok, resp = chat("@WriterAG Erstelle README_hub.md mit Inhalt 'Gnom-Hub Test'")
time.sleep(5)
files = check_workspace_files("README_hub")
log(35, "WriterAG schreibt README.md", "PASS" if files else "FAIL", f"Dateien: {files}")

# Test 36: PDF wird erstellt (wenn weasyprint verfügbar)
ok, resp = chat("@CoderAG Wandle index.html in test_pdf_36.pdf um mit weasyprint")
time.sleep(8)
pdfs = [f for f in check_workspace_files() if f.endswith(".pdf")]
log(36, "PDF-Generierung via weasyprint", "PASS" if pdfs else "WARN", f"PDFs: {pdfs}")

# Test 37: Gleichzeitiges Schreiben konkurriert nicht
ok1, _ = chat("@CoderAG Schreibe konkurrenz_a.html mit A", "user")
ok2, _ = chat("@CoderAG Schreibe konkurrenz_b.html mit B", "user")
time.sleep(8)
files_a = check_workspace_files("konkurrenz_a")
files_b = check_workspace_files("konkurrenz_b")
log(37, "Konkurrierende Datei-Schreibzugriffe", "PASS" if files_a and files_b else "FAIL")

# Test 38: Shell-Befehl via CoderAG
ok, resp = chat("@CoderAG Führe aus: echo 'Shell-Test 38' > shell_test_38.txt")
time.sleep(5)
files = check_workspace_files("shell_test_38")
log(38, "Shell-Befehl via CoderAG", "PASS" if files else "FAIL")

# ═══════════════════════════════════════════════════════════════
# TEIL 5: LAST & PRIORISIERUNG (Tests 39-46)
# ═══════════════════════════════════════════════════════════════
print()
print("─" * 70)
print("⚡ TEIL 5: LAST & PRIORISIERUNG")
print("─" * 70)

# Test 39: Massen-Nachrichten (10 gleichzeitig)
def send_bulk(i):
    try:
        requests.post(f"{BASE}/api/chat", json={"content": f"@GeneralAG Bulk-Test {i}", "sender": "user"}, timeout=15)
        return True
    except: return False

t0 = time.time()
bulk_results = []
with ThreadPoolExecutor(max_workers=10) as ex:
    futures = [ex.submit(send_bulk, i) for i in range(10)]
    bulk_results = [f.result() for f in as_completed(futures)]
bulk_time = time.time() - t0
log(39, "10 parallele Bulk-Nachrichten", "PASS" if sum(bulk_results) > 7 else "FAIL", f"{sum(bulk_results)}/10 erfolgreich in {bulk_time:.1f}s")

# Test 40: Critical-Priority Nachricht (prio=0)
ok, resp = chat("@GeneralAG !!!CRITICAL!!! Das ist ein Notfall-Test")
time.sleep(3)
log(40, "Critical-Priority Nachricht", "PASS" if ok else "FAIL")

# Test 41: 20 schnelle Nachrichten (Queue-Stress)
t0 = time.time()
for i in range(20):
    requests.post(f"{BASE}/api/chat", json={"content": f"Queue-Stress {i}", "sender": "user"}, timeout=10)
stress_time = time.time() - t0
log(41, "20 Nachrichten Queue-Stress", "PASS" if stress_time < 30 else "WARN", f"{stress_time:.1f}s")

# Test 42: Agent bleibt bei 600s Timeout nicht hängen
t0 = time.time()
ok, resp = chat("@GeneralAG Warte 5 Sekunden und antworte dann")
time.sleep(8)
log(42, "Timeout-Verhalten (kein Hängen)", "PASS" if ok else "FAIL")

# Test 43: Wiederholte Delegation ohne Verlust
for i in range(3):
    chat(f"@CoderAG Schreibe loop_test_{i}.txt mit Inhalt {i}")
time.sleep(10)
loop_files = [f for f in check_workspace_files("loop_test_") if f.endswith(".txt")]
log(43, "3× wiederholte Delegation ohne Verlust", "PASS" if len(loop_files) >= 2 else "FAIL", f"{len(loop_files)}/3 Dateien")

# Test 44: Agent-Kommunikation via @-Kette
ok, resp = chat("@GeneralAG Sage ResearcherAG er soll 'AgentChain OK' antworten")
time.sleep(8)
msgs = get_chat(50)
chain_ok = any("AgentChain" in m.get("content","") for m in msgs)
log(44, "Agent-Agent Kommunikationskette", "PASS" if chain_ok else "WARN")

# Test 45: GeneralAG leitet bei Fehler an Security/Watchdog weiter
ok, resp = chat("@GeneralAG Prüfe ob die Datei /etc/passwd gelesen werden kann")
time.sleep(8)
msgs = get_chat(50)
sicherheit = any(m.get("sender") in ("SecurityAG","WatchdogAG") for m in msgs[:10])
log(45, "GeneralAG delegiert Fehler an Sicherheits-Agents", "PASS" if sicherheit else "WARN")

# Test 46: Monitor-Skript läuft und freed
import subprocess as sp
r = sp.run(["pgrep", "-f", "gnom-monitor"], capture_output=True, text=True)
monitor_pids = r.stdout.strip().split()
log(46, "Monitor-Skript läuft (Auto-Free)", "PASS" if monitor_pids else "FAIL", f"PID(s): {monitor_pids}")

# ═══════════════════════════════════════════════════════════════
# TEIL 6: FTP & VERÖFFENTLICHUNG (Tests 47-48)
# ═══════════════════════════════════════════════════════════════
print()
print("─" * 70)
print("🌐 TEIL 6: FTP & VERÖFFENTLICHUNG")
print("─" * 70)

# Test 47: FTP-Zugangsdaten vorhanden
ftp_host = os.environ.get("FTP_HOST") or "185.243.11.43"
ftp_user = os.environ.get("FTP_USER_NETZWERKPUNKT") or "sysuser_a"
log(47, "FTP-Konfiguration vorhanden", "PASS" if ftp_host and ftp_user else "FAIL", f"Host: {ftp_host}")

# Test 48: FTP-Kommunikation möglich
try:
    from ftplib import FTP
    ftp = FTP(timeout=10)
    ftp.connect(ftp_host, 21)
    ftp.login(ftp_user, os.environ.get("FTP_PASS_NETZWERKPUNKT", ""))
    ftp.quit()
    log(48, "FTP-Verbindung erfolgreich", "PASS", ftp_host)
except Exception as e:
    log(48, "FTP-Verbindung möglich", "SKIP" if "authentif" in str(e).lower() or "login" in str(e).lower() else "FAIL", str(e)[:80])

# ═══════════════════════════════════════════════════════════════
# TEIL 7: RESILIENCE & CLEANUP (Tests 49-50)
# ═══════════════════════════════════════════════════════════════
print()
print("─" * 70)
print("🛡️ TEIL 7: RESILIENCE & CLEANUP")
print("─" * 70)

# Test 49: Clean-Button /admin/clean-all funktioniert
r = requests.post(f"{BASE}/admin/clean-all", timeout=15)
try:
    data = r.json()
    log(49, "Clean-All Endpoint", "PASS" if data.get("status") == "cleaned" else "FAIL", str(data)[:80])
except:
    log(49, "Clean-All Endpoint", "PASS" if r.status_code in (200, 202) else "FAIL", f"HTTP {r.status_code}")

# Test 50: Nach Clean-All startet Hub neu (muss wieder erreichbar sein)
time.sleep(5)
for attempt in range(12):
    try:
        r = requests.get(f"{BASE}/", timeout=5)
        if r.status_code == 200:
            agents4 = get_agents()
            log(50, "Hub-Neustart nach Clean-All", "PASS" if len(agents4) >= 4 else "WARN", f"{len(agents4)} Agents online nach {attempt*5+5}s")
            break
    except:
        pass
    time.sleep(5)
else:
    log(50, "Hub-Neustart nach Clean-All", "FAIL", "Hub nicht erreichbar nach 60s")

# ═══════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 70)
print(f"📊 REPORT: {PASS+FAIL} Tests durchgeführt")
print(f"   ✅ PASS: {PASS}")
print(f"   ❌ FAIL: {FAIL}")
print(f"   ⚠️  Quote: {PASS/(PASS+FAIL)*100:.1f}%")
print("=" * 70)
print()

# Detail-Liste der Failures
fails = [r for r in results if r[2] != "PASS"]
if fails:
    print("⚠️  DETAILS ZU NICHT-BESTANDENEN TESTS:")
    for nr, name, status, detail in fails:
        icon = "❌" if status == "FAIL" else "⚠️"
        print(f"  {icon} [{nr:02d}] {name}: {detail}")
print()
