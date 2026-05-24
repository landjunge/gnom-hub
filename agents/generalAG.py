"""GeneralAG Agent."""
import asyncio
from gnom_hub.agent_base import BaseAgent

async def main():
    await BaseAgent("GeneralAG", "Task distribution, coordination", "@job", sys_prompt=None, poll=15).run()

if __name__ == "__main__": asyncio.run(main())
