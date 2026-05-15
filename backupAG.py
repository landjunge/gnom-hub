"""BackupAG — Git-Push + lokale Snapshots."""
import asyncio, json, subprocess, tarfile; from datetime import datetime; from pathlib import Path
from mcp import ClientSession; from mcp.client.sse import sse_client
MCP, NAME, POLL = "http://127.0.0.1:3100/sse", "BackupAG", 3600
REPO, BKDIR, MAX = Path("/Users/landjunge/Documents/AG-Flega"), Path("/Users/landjunge/Documents/AG-Flega/.backups"), 5
EXCL = {".venv", "__pycache__", ".git", ".backups", "node_modules", ".DS_Store"}
def git(*a): return subprocess.run(["git"]+list(a), cwd=REPO, capture_output=True, text=True).returncode == 0
def changed(): return bool(subprocess.run(["git","status","--porcelain"], cwd=REPO, capture_output=True, text=True).stdout.strip())
def unpushed(): return bool(subprocess.run(["git","log","origin/master..HEAD","--oneline"], cwd=REPO, capture_output=True, text=True).stdout.strip())
def ts(): return datetime.now().strftime("%Y%m%d-%H%M")
def rotate_snap():
    BKDIR.mkdir(exist_ok=True); nm = BKDIR / f"snap-{ts()}.tar.gz"
    with tarfile.open(nm, "w:gz") as t:
        for p in REPO.iterdir():
            if p.name not in EXCL: t.add(p, arcname=p.name)
    snaps = sorted(BKDIR.glob("snap-*"), key=lambda x: x.stat().st_mtime)
    while len(snaps) > MAX: snaps.pop(0).unlink()
    return nm.name, nm.stat().st_size // 1024
async def run():
    async with sse_client(MCP) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize(); await s.call_tool("register_agent", {"name": NAME, "port": 0, "desc": "Backup"}); await s.call_tool("set_agent_status", {"a": NAME, "s": "online"}); seen = set()
            while True:
                res = await s.call_tool("war_room_read", {"limit": 5}); chat = json.loads(str(res.content[0].text)) if res.content else []
                for m in [m for m in chat if m.get("id") not in seen and "@backup" in m.get("content","").lower()]:
                    seen.add(m.get("id")); await s.call_tool("set_agent_status", {"a": NAME, "s": "busy"}); sn, sz = rotate_snap()
                    if changed(): git("add","-A"); git("commit","-m",f"backup: {ts()}")
                    p = unpushed() and git("push","origin","master")
                    await s.call_tool("war_room_chat", {"msg": f"💾 {sn} ({sz}KB)" + (" | pushed" if p else ""), "sender": NAME})
                if changed(): rotate_snap(); git("add","-A"); git("commit","-m",f"auto {ts()}")
                if unpushed(): git("push","origin","master")
                await s.call_tool("set_agent_status", {"a": NAME, "s": "online"}); await asyncio.sleep(POLL)
if __name__ == "__main__": asyncio.run(run())
