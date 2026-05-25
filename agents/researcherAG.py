"""ResearcherAG Agent."""
import asyncio
from gnom_hub.agent_base import BaseAgent
from gnom_hub.agent_definitions import AGENT_DEFINITIONS

async def main():
    cfg = AGENT_DEFINITIONS["researcherag"]
    await BaseAgent(cfg["name"], cfg["description"], cfg["capabilities"][0], sys_prompt=cfg["sys_prompt"], poll=15).run()

if __name__ == "__main__": asyncio.run(main())
