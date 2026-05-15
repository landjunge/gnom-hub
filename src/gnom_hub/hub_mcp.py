import requests, os, json as _json; from mcp.server.fastmcp import FastMCP; mcp = FastMCP("HUB", host="127.0.0.1", port=int(os.environ.get("GNOM_MCP_PORT", 3100)))
def api(m, p, **k):
    try: return _json.dumps(requests.request(m, f"http://127.0.0.1:{os.environ.get('GNOM_HUB_PORT','3002')}/api"+p, **k).json())
    except: return "Err"
@mcp.tool()
def save_to_memory(a: str, c: str): """Speichert Text."""; return api("POST", "/memory", json={"agent_id": a, "content": c})
@mcp.tool()
def get_memory(a: str): """Liest Memory."""; return api("GET", f"/agents/{a}/memory")
@mcp.tool()
def search_memory(q: str): """Sucht Memory."""; return api("GET", "/memory/search", params={"q": q})
@mcp.tool()
def delete_memory(m: str): """Löscht Memory."""; return api("DELETE", f"/memory/{m}")
@mcp.tool()
def update_memory(m: str, c: str): """Ändert Memory."""; return api("PUT", f"/memory/{m}", params={"content": c})
@mcp.tool()
def set_agent_status(a: str, s: str): """Setzt Status."""; return api("PUT", f"/agents/{a}/status", params={"status": s})
@mcp.tool()
def list_all_agents(): """Alle Agenten."""; return api("GET", "/agents")
@mcp.tool()
def get_agent(a: str): """Agent Infos."""; return api("GET", f"/agents/{a}")
@mcp.tool()
def clear_agent_memory(a: str): """Löscht alle Memory."""; return api("DELETE", f"/agents/{a}/memory")
@mcp.tool()
def create_agent(n: str, d: str=""): """Neuer Agent."""; return api("POST", "/agents", json={"name": n, "description": d, "status": "offline"})
@mcp.tool()
def delete_agent(a: str): """Löscht Agent + Memory."""; return api("DELETE", f"/agents/{a}")
@mcp.tool()
def get_system_stats(): """System Stats."""; return api("GET", "/stats")
@mcp.tool()
def register_agent(name: str, port: int, desc: str=""): """Agent registriert sich."""; return api("POST", "/agents/register", json={"name": name, "port": port, "description": desc})
@mcp.tool()
def nudge_agent(a: str, reason: str="manual"): """Stupst Agent an."""; return api("POST", f"/agents/{a}/nudge", params={"reason": reason})
@mcp.tool()
def war_room_chat(msg: str, sender: str="mcp"): """Sendet an War Room. @bs=Brainstorm, @Name=gezielt."""; return api("POST", "/chat", json={"content": msg, "sender": sender})
@mcp.tool()
def war_room_read(limit: int=20): """Liest War Room."""; return api("GET", f"/chat?limit={limit}")
@mcp.tool()
def set_agent_role(a: str, role: str): """Setzt Rolle: general|summarizer|normal. Speichert System-Prompt."""; return api("PUT", f"/admin/agents/{a}/role", params={"role": role})
@mcp.tool()
def distribute_job(job: str): """General: Verteilt Job an Agenten. Nur @Name → Aufgabe."""; from gnom_hub.role_tools import distribute_job as dj; return dj(job)
@mcp.tool()
def summarize_chat(): """Summarizer: Extrahiert wichtige Punkte aus dem Chat."""; from gnom_hub.role_tools import summarize_chat as sc; return sc()
@mcp.tool()
def restart_gnom_hub(): """Startet Gnom-Hub komplett neu (Hub + MCP)."""; from gnom_hub.proc_mgr import restart_hub; return restart_hub()
@mcp.tool()
def kill_by_port(port: int): """Killt Prozess auf Port."""; from gnom_hub.proc_mgr import kill_process; return kill_process(str(port))
@mcp.tool()
def read_file(path: str): """Liest den Inhalt einer lokalen Datei (z.B. Inseln).""";
    try:
        with open(path, "r", encoding="utf-8") as f: return f.read()
    except Exception as e: return f"Fehler beim Lesen: {e}"
@mcp.tool()
def write_file(path: str, content: str): """Schreibt Inhalt in eine lokale Datei (Schreibrechte, z.B. um Inseln zu aktualisieren).""";
    try:
        with open(path, "w", encoding="utf-8") as f: f.write(content)
        return f"Erfolg: {path} geschrieben."
    except Exception as e: return f"Fehler beim Schreiben: {e}"
@mcp.tool()
def show_processes(): """Zeigt alle laufenden Gnom-Hub Prozesse."""; from gnom_hub.proc_mgr import process_status; return process_status()
@mcp.tool()
def publish_to_feenreich(): """Veröffentlicht alle Dateien aus dem kreativ_universe_kira_lian_elara Ordner direkt live auf die königliches-feenreich.de Domain.""";
    import subprocess
    try:
        r = subprocess.run(["/Users/landjunge/Documents/AG-Flega/publish_trio.sh"], capture_output=True, text=True, cwd="/Users/landjunge/Documents/AG-Flega")
        return f"Erfolgreich veröffentlicht! Output: {r.stdout}"
    except Exception as e: return f"Fehler beim Publish: {e}"
def main(): mcp.run(transport="sse")
