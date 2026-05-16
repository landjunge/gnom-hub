import re
from pathlib import Path
from .provider_switchAG import llm_call
from .gitAG import auto_commit, git_cmd
from .evaluatorAG import evaluate_job
from .sandboxAG import safe_run_command

def evolve_agent(agent_name: str) -> str:
    """@evolve – liest Eval, Logs + Git und schreibt besseren Code (max 40 Zeilen)."""
    # Letzte Git-History und Sandbox-Fehler laden
    history = git_cmd(".", "log --oneline -5")
    
    try:
        logs = Path(".backups/sandbox.log").read_text()[-500:] # Letzte Fehler
    except:
        logs = "Keine Logs vorhanden."
        
    prompt = f"""
    Agent: {agent_name}
    Sandbox-Fehlerlogs: {logs}
    Git-History: {history}
    Schreibe verbesserten Code für {agent_name}.py.
    Regeln:
    - Maximal 40 Zeilen!
    - Nur die Imports verwenden, die nötig sind.
    - Gib NUR den rohen Python-Code aus, ohne Erklärung, ohne Markdown Fences.
    """
    
    try:
        new_code = llm_call(prompt, system="Du bist der Evolution-Agent. Output ist ausschließlich roher Python-Code.")
        
        # Fences killen (falls das LLM trotzdem redet)
        new_code = re.sub(r'```(?:python)?\s*|\s*```', '', new_code, flags=re.DOTALL).strip()
        
        # Sicher überschreiben im richtigen Ordner
        path = Path(__file__).parent / f"{agent_name}.py"
        path.write_text(new_code)
        
        auto_commit(".", message=f"Evolution: {agent_name} self-improved")
        return f"✅ {agent_name} evolviert – neuer Code in {path.name} committed!"
        
    except Exception as e:
        safe_run_command(f"echo 'Evolution Error: {str(e)}' >> .backups/sandbox.log", "evolutionAG")
        return f"❌ Evolution fehlgeschlagen: {str(e)}"
