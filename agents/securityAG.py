from gnom_hub.core.security.hmac_signer import seal_content, verify_seal
if __name__ == "__main__": import asyncio; from agents.run_agent import BaseAgent, AGENT_DEFINITIONS; cfg = AGENT_DEFINITIONS["securityag"]; asyncio.run(BaseAgent(cfg["name"], cfg["description"], cfg["capabilities"][0], sys_prompt=cfg["sys_prompt"], poll=15).run())
