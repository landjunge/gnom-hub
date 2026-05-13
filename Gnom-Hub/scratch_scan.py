import asyncio
async def scan_network_agents():
    async def chk(p):
        try: _,w=await asyncio.wait_for(asyncio.open_connection('127.0.0.1',p),0.05); w.close(); return p
        except: return None
    return {"open_ports": [p for chunk in range(3000,10001,200) for p in await asyncio.gather(*(chk(p) for p in range(chunk,min(chunk+200,10001)))) if p]}
print(asyncio.run(scan_network_agents()))
