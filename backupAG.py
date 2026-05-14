"""BackupAG — Git-Push + lokale Snapshots, pollt War Room für @backup."""
import asyncio, json, subprocess, tarfile
from datetime import datetime
from pathlib import Path
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP, NAME, POLL = "http://127.0.0.1:3100/sse", "BackupAG", 1800
REPO = Path("/Users/landjunge/Documents/AG-Flega")
BKDIR, KEEP = REPO / ".backups", 7
EXCL = {".venv", "__pycache__", ".git", ".backups", "node_modules", ".DS_Store"}

def git(*a): r = subprocess.run(["git"]+list(a), cwd=REPO, capture_output=True, text=True, timeout=30); return r.returncode == 0
def changed(): r = subprocess.run(["git","status","--porcelain"], cwd=REPO, capture_output=True, text=True); return bool(r.stdout.strip())
def unpushed(): r = subprocess.run(["git","log","origin/master..HEAD","--oneline"], cwd=REPO, capture_output=True, text=True); return bool(r.stdout.strip())
def ts(): return datetime.now().strftime("%Y%m%d-%H%M")

def snapshot():
    BKDIR.mkdir(exist_ok=True)
    name = BKDIR / f"snap-{ts()}.tar.gz"
    with tarfile.open(name, "w:gz") as t:
        for p in REPO.iterdir():
            if p.name not in EXCL: t.add(p, arcname=p.name)
    return name.name, name.stat().st_size // 1024

def rotate():
    if not BKDIR.exists(): return
    now = datetime.now()
    for f in BKDIR.glob("snap-*"):
        if (now - datetime.fromtimestamp(f.stat().st_mtime)).days > KEEP: f.unlink()

async def run():
    async with sse_client(MCP) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await s.call_tool("register_agent", {"name": NAME, "port": 0, "desc": "Backup — Git + Snapshots"})
            await s.call_tool("set_agent_status", {"a": NAME, "s": "online"})
            print(f"💾 {NAME} aktiv — {POLL//60}min Intervall")
            seen = set()
            while True:
                res = await s.call_tool("war_room_read", {"limit": 5})
                chat = json.loads(str(res.content[0].text)) if res.content else []
                for m in chat:
                    if m.get("id") in seen: continue
                    seen.add(m.get("id"))
                    if "@backup" not in m.get("content","").lower(): continue
                    await s.call_tool("set_agent_status", {"a": NAME, "s": "busy"})
                    sn, sz = snapshot()
                    if changed(): git("add","-A"); git("commit","-m",f"backup: {ts()}")
                    pushed = unpushed() and git("push","origin","master")
                    msg = f"💾 {sn} ({sz}KB)" + (" | pushed" if pushed else "")
                    await s.call_tool("war_room_chat", {"msg": msg, "sender": NAME})
                    await s.call_tool("set_agent_status", {"a": NAME, "s": "online"})
                if changed(): snapshot(); git("add","-A"); git("commit","-m",f"backup: auto {ts()}")
                if unpushed(): git("push","origin","master")
                rotate()
                await asyncio.sleep(POLL)

if __name__ == "__main__":
    asyncio.run(run())
