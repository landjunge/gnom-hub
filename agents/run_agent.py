"""Universal agent runner."""
import argparse
import asyncio
import sys
from gnom_hub.agents.agent_base import BaseAgent
from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS

async def main():
    parser = argparse.ArgumentParser(description="Run a Gnom-Hub agent.")
    parser.add_argument("--name", required=True, help="Name of the agent to run (e.g. CoderAG or coderag)")
    args = parser.parse_args()
    
    agent_key = args.name.lower()
    if agent_key not in AGENT_DEFINITIONS:
        print(f"Error: Agent '{args.name}' not found in definitions.", file=sys.stderr)
        print(f"Available agents: {', '.join(AGENT_DEFINITIONS.keys())}", file=sys.stderr)
        sys.exit(1)
        
    cfg = AGENT_DEFINITIONS[agent_key]
    await BaseAgent(
        cfg["name"],
        cfg["description"],
        cfg["capabilities"][0],
        sys_prompt=cfg["sys_prompt"],
        poll=15
    ).run()

if __name__ == "__main__":
    asyncio.run(main())
