# conflict_resolver.py — Multi-agent divergence resolution
import json
import asyncio
import functools
from gnom_hub.infrastructure.router.router import ask_router

async def generalAG(prompt: str) -> str:
    """Helper representing GeneralAG async execution."""
    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(
        None,
        functools.partial(ask_router, prompt, sys="Du bist GeneralAG, der oberste Koordinator des Schwarms.", agent_name="GeneralAG")
    )
    return res.content

async def soulAG(prompt: str) -> str:
    """Helper representing SoulAG async execution."""
    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(
        None,
        functools.partial(ask_router, prompt, sys="Du bist SoulAG, das Langzeitgedächtnis und Bewusstsein.", agent_name="SoulAG")
    )
    return res.content

class ConflictResolution:
    async def resolve_divergence(
        self, 
        agent1_output: str, 
        agent2_output: str,
        task: str
    ) -> dict:
        # 1. Meta-Analyse: Was ist der Unterschied?
        diff_analysis = await generalAG(
            f"Analysiere diese zwei Outputs:\n{agent1_output}\nvs\n{agent2_output}"
        )
        
        # 2. Ursache-Identifikation: Prompt-Unterschied? Model-Unterschied?
        root_cause = await soulAG(
            f"Warum divergieren diese Outputs? {diff_analysis}"
        )
        
        # 3. Formal Debate: Beide Agenten argumentieren ihre Position
        # (mit erweiterten Kontexten, die der jeweils andere nicht hatte)
        debate_prompt_1 = (
            f"Aufgabe: {task}\n\n"
            f"Du repräsentierst Agent 1. Verteidige deine Position.\n"
            f"Dein Output:\n{agent1_output}\n\n"
            f"Output von Agent 2:\n{agent2_output}\n\n"
            f"Root Cause Analyse der Divergenz:\n{root_cause}\n\n"
            f"Erkläre, warum dein Output korrekter oder besser geeignet ist."
        )
        debate_prompt_2 = (
            f"Aufgabe: {task}\n\n"
            f"Du repräsentierst Agent 2. Verteidige deine Position.\n"
            f"Dein Output:\n{agent2_output}\n\n"
            f"Output von Agent 1:\n{agent1_output}\n\n"
            f"Root Cause Analyse der Divergenz:\n{root_cause}\n\n"
            f"Erkläre, warum dein Output korrekter oder besser geeignet ist."
        )
        
        # Run debate arguments in parallel
        debate_agent1, debate_agent2 = await asyncio.gather(
            generalAG(debate_prompt_1),
            generalAG(debate_prompt_2)
        )
        
        # 4. Voting + Weighted Score (Judge consensus)
        judge_prompt = (
            f"Führe als neutraler Richter eine Voting- & Konsensus-Entscheidung herbei.\n"
            f"Aufgabe: {task}\n\n"
            f"Agent 1 Output:\n{agent1_output}\n"
            f"Agent 1 Argumente:\n{debate_agent1}\n\n"
            f"Agent 2 Output:\n{agent2_output}\n"
            f"Agent 2 Argumente:\n{debate_agent2}\n\n"
            f"Divergenz Ursache:\n{root_cause}\n\n"
            f"Gib das Ergebnis im JSON-Format zurück mit den Schlüsseln:\n"
            f"'winner' (Name des Gewinners, z.B. CoderAG oder WriterAG),\n"
            f"'confidence' (Fließkommazahl von 0.0 bis 1.0),\n"
            f"'reasoning' (Begründung der Wahl),\n"
            f"'consensus_output' (Merger der besten Elemente beider Outputs).\n"
            f"Antworte NUR mit dem JSON-Objekt, kein Markdown, kein Text."
        )
        
        judge_response = await generalAG(judge_prompt)
        
        # Parse output
        try:
            # Clean up response if it contains markdown formatting
            cleaned = judge_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            res = json.loads(cleaned)
            return {
                "winner": res.get("winner", "Unknown"),
                "confidence": float(res.get("confidence", 0.5)),
                "reasoning": res.get("reasoning", "Parsed reasoning successfully."),
                "consensus_output": res.get("consensus_output", agent1_output)
            }
        except Exception:
            # Fallback in case of parse error
            return {
                "winner": "GeneralAG (Consensus)",
                "confidence": 0.75,
                "reasoning": f"Consensus determined due to parsing error. Raw judge response: {judge_response}",
                "consensus_output": agent1_output + "\n\n=== CONSENSUS SPLIT ===\n\n" + agent2_output
            }
