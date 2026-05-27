# swarm_coordinator.py — Coordinates team workflows and gathers results
import time, threading, re
from .infrastructure.database.agent_repo import SQLiteAgentRepository as AR
from .infrastructure.database.state_repo import SQLiteStateRepository as SR
from gnom_hub.agents.role_tools import _llm; from gnom_hub.chat.brainstorm.brainstorm import _collect_worker_responses, dispatch
from gnom_hub.chat.brainstorm.brainstorm_helpers import post, get_workspace_dir; from gnom_hub.action_handlers import process_actions; from gnom_hub.soul import get_soul
def _wait(ar, workers, timeout=40):
    t0 = time.time()
    while time.time() - t0 < timeout and any(a.active_job for a in ar.get_all() if a.name in workers): time.sleep(2)
def _dispatch(ar, sr, ans):
    nxt = []
    for a in ar.get_all():
        if a.name.lower() in {"soulag", "generalag", "securityag", "watchdogag"}:
            continue
        aj = next((m.group(2).strip() for m in re.finditer(r'@(\w+)[\s→>:\-]+(.+)', ans) if m.group(1).lower() == a.name.lower()), "")
        if aj:
            ar.update_active_job(a.name, aj); nxt.append(a.name)
            time.sleep(1.5); dispatch(aj, target=a.name)
    if nxt: sr.set_value("active_workflow", f"Team-Workflow aktiv: {' → '.join(nxt)}")
    return nxt
def _eval(ar, task, history):
    sys_p = "Du bist GeneralAG. Führe Ergebnisse des Team-Workflows zusammen. Wenn unvollständig, weise nächste Schritte zu im Format '@AgentName -> Aufgabe'. Wenn fertig, schreibe '[WRITE: dateiname]inhalt[/WRITE]'."
    ans = _llm(sys_p, f"Hauptaufgabe: {task}\n\nWorker-Ergebnisse:\n{history}")
    gen = next((a for a in ar.get_all() if a.role == "general" or a.name.lower() == "generalag"), None)
    if gen: post(gen.name, process_actions(ans, {"name": gen.name}, (get_soul(gen.name) or {}).get("permissions", []), False, get_workspace_dir()))
    return ans
def run_swarm_coordinator(task, workers):
    ar, sr = AR(), SR(); all_res, cur = [], list(workers)
    for _ in range(4):
        if not cur: break
        _wait(ar, cur); new_resp = _collect_worker_responses(cur)
        if new_resp: all_res.append(new_resp)
        cur = _dispatch(ar, sr, _eval(ar, task, "\n\n".join(all_res)))
    sr.set_value("active_workflow", None)
    try:
        from gnom_hub.soul import run_evolution; run_evolution(task, "\n\n".join(all_res))
        post(next((a.name for a in ar.get_all() if a.role == "general" or a.name.lower() == "generalag"), "GeneralAG"), "Der Workflow ist beendet. War das Ergebnis gut? Bitte gib uns Feedback im Dashboard!")
    except Exception: pass
def start_coordinator(task, workers):
    if workers: SR().set_value("active_workflow", f"Team-Workflow aktiv: {' → '.join(workers)}"); threading.Thread(target=run_swarm_coordinator, args=(task, workers), daemon=True).start()
