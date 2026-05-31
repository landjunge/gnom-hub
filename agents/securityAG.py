"""SecurityAG Agent."""
import asyncio
from gnom_hub.agents.agent_base import BaseAgent
from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
from gnom_hub.core.security.hmac_signer import generate_signature

import os

def seal_content(agent: str, content: str, fname: str = "") -> str:
    from gnom_hub.soul.zwc_soul import add_agent_metadata
    sig = add_agent_metadata(agent, "")
    if not fname:
        return content + sig
    
    ext = os.path.splitext(fname)[1].lower()
    if ext == ".py":
        return content + f"\n# {sig}"
    elif ext in (".html", ".xml", ".md"):
        return content + f"\n<!-- {sig} -->"
    elif ext in (".js", ".ts", ".css"):
        return content + f"\n/* {sig} */"
    elif ext in (".sh", ".yml", ".yaml", ".toml", ".env", ".ini"):
        return content + f"\n# {sig}"
    else:
        return content + sig

def verify_seal(sealed_content: str) -> bool:
    from gnom_hub.soul.zwc_soul import decode_soul
    soul = decode_soul(sealed_content)
    return soul is not None and "agent" in soul

async def main():
    cfg = AGENT_DEFINITIONS["securityag"]
    await BaseAgent(cfg["name"], cfg["description"], cfg["capabilities"][0], sys_prompt=cfg["sys_prompt"], poll=15).run()

if __name__ == "__main__":
    asyncio.run(main())
