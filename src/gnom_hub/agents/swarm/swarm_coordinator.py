# swarm_coordinator.py — Coordinates team workflows and gathers results
import logging
import time, threading, re
from typing import List, Dict, Tuple, Set
from gnom_hub.db.agent_repo import SQLiteAgentRepository as AR
from gnom_hub.db.state_repo import SQLiteStateRepository as SR
from gnom_hub.agents.role_tools import _llm
from gnom_hub.chat.brainstorm.brainstorm import _collect_worker_responses, dispatch
from gnom_hub.chat.brainstorm.brainstorm_helpers import post, get_workspace_dir
from gnom_hub.agents.actions.action_handlers import process_actions
from gnom_hub.soul import get_soul

logger = logging.getLogger(__name__)


class WorkerCompletionTracker:
    """
    Ersetzt das blockierende _wait()-Pattern durch ein Event-basiertes System.
    """

    def __init__(self, worker_names: List[str], timeout: float = 40.0):
        self._pending  = set(worker_names)
        self._lock     = threading.Lock()
        self._done_evt = threading.Event()
        self._timeout  = timeout
        self._results  : Dict[str, dict] = {}

    def mark_done(self, agent_name: str, result: dict) -> None:
        """
        Vom Agenten aufgerufen wenn er fertig ist.
        Kein DB-Poll nötig – direkter In-Process-Callback.
        """
        with self._lock:
            self._pending.discard(agent_name)
            self._results[agent_name] = result
            if not self._pending:
                self._done_evt.set()

    def wait(self) -> Tuple[bool, Dict[str, dict]]:
        """
        Blockiert maximal `timeout` Sekunden.
        Gibt (completed: bool, results: dict) zurück.
        """
        completed = self._done_evt.wait(timeout=self._timeout)

        if not completed:
            with self._lock:
                missing = list(self._pending)
            logger.warning(
                "Coordinator-Timeout nach %.0fs – noch ausstehend: %s",
                self._timeout, missing
            )

        return completed, self._results.copy()

    @property
    def pending(self) -> Set[str]:
        with self._lock:
            return self._pending.copy()


# ── Globale Tracker-Registry ───────────────────────────────────────────────
_trackers: Dict[str, WorkerCompletionTracker] = {}
_registry_lock = threading.Lock()


def register_tracker(context_id: str, tracker: WorkerCompletionTracker) -> None:
    with _registry_lock:
        _trackers[context_id] = tracker


def signal_completion(context_id: str, agent_name: str, result: dict) -> None:
    """Agenten-seitige API: 'Ich bin fertig mit context_id X'."""
    with _registry_lock:
        tracker = _trackers.get(context_id)
    if tracker:
        tracker.mark_done(agent_name, result)
    else:
        logger.debug(
            "signal_completion: kein Tracker für context_id=%s", context_id
        )


def cleanup_tracker(context_id: str) -> None:
    with _registry_lock:
        _trackers.pop(context_id, None)


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
    from gnom_hub.db import get_active_project
    proj = get_active_project() or "default"
    
    for _ in range(4):
        if not cur: break
        
        # Erstelle einen Tracker für diese Runde von Workern
        tracker = WorkerCompletionTracker(cur, timeout=40.0)
        register_tracker(proj, tracker)
        try:
            # Warte eventgesteuert (kein Busy-Loop!)
            tracker.wait()
        finally:
            cleanup_tracker(proj)
            
        new_resp = _collect_worker_responses(cur)
        if new_resp: all_res.append(new_resp)
        cur = _dispatch(ar, sr, _eval(ar, task, "\n\n".join(all_res)))
        
    sr.set_value("active_workflow", None)
    try:
        from gnom_hub.soul import run_evolution; run_evolution(task, "\n\n".join(all_res))
        post(next((a.name for a in ar.get_all() if a.role == "general" or a.name.lower() == "generalag"), "GeneralAG"), "Der Workflow ist beendet. War das Ergebnis gut? Bitte gib uns Feedback im Dashboard!")
    except Exception as e: logging.getLogger(__name__).error('Fehler in Evolution und Workflow-Abschluss: %s', e)


def start_coordinator(task, workers):
    if workers: SR().set_value("active_workflow", f"Team-Workflow aktiv: {' → '.join(workers)}"); threading.Thread(target=run_swarm_coordinator, args=(task, workers), daemon=True).start()
