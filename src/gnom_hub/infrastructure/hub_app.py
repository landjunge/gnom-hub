import os, sys, uvicorn, signal, time

def main():
    from gnom_hub.infrastructure.logging_setup import setup_logging
    setup_logging(level="INFO")

    # ── Pre-Start Total Kill: räumt Waisen + alte Hubs auf ──
    # Verhindert dass nach Tagen/Wochen 20+ Waisen-Prozesse rumliegen.
    # Wird auch vom start_gnom_hub.sh gemacht — hier als Defense-in-Depth
    # falls jemand den Hub manuell startet.
    _total_kill_pre_start()

    # ── Auto-Reconcile: stelle sicher dass Desktop-Keys in DB sind ──
    # Verhindert dass Provider-Keys (z.B. MiniMax) "verschwinden" weil ein
    # Side-Effect (z.B. service-card inline-key save) die DB überschreibt.
    try:
        from gnom_hub.infrastructure.llm.key_reconciler import reconcile_keys_on_startup, force_minimax_routing
        stats = reconcile_keys_on_startup()
        if stats.get("added", 0) > 0:
            print(f"[Startup] Key-Reconcile: {stats['added']} key(s) merged from Desktop → DB")
        # Optional: MiniMax-M3 als Default-Provider setzen. Auskommentiert
        # standardmäßig. Aktivieren via env: GNOM_HUB_FORCE_MINIMAX=1
        if os.environ.get("GNOM_HUB_FORCE_MINIMAX") == "1":
            if force_minimax_routing():
                print("[Startup] Force-Routing: all 8 agents → minimax/MiniMax-M3")
    except Exception as e:
        print(f"[Startup] Reconcile skipped: {e}", file=sys.stderr)

    uvicorn.run("gnom_hub.api.app:app", host="127.0.0.1", port=int(os.environ.get("GNOM_HUB_PORT", 3002)))
    if os.environ.get("GNOM_HUB_RESTART") == "true":
        print("[Gnom-Hub] Graceful shutdown complete. Exiting with code 42 to request restart.")
        sys.exit(42)


def _total_kill_pre_start() -> int:
    """Defense-in-Depth: killt alle gnom_hub/agents-Prozesse vor dem Start.

    Wird auch von start_gnom_hub.sh gemacht. Hier als Fallback falls jemand
    den Hub manuell startet (python3 -m gnom_hub). Returns: Anzahl gekillter
    Prozesse.
    """
    import subprocess
    try:
        # 1. Sammle alle PIDs
        result = subprocess.run(
            ["pgrep", "-f", "gnom_hub|agents.run_agent"],
            capture_output=True, text=True, timeout=3
        )
        pids = [int(p) for p in result.stdout.split() if p.strip().isdigit()]
        # Aktueller Prozess nicht killen
        pids = [p for p in pids if p != os.getpid()]
        if not pids:
            return 0

        # 2. SIGTERM an alle
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
        time.sleep(2)

        # 3. SIGKILL für Überlebende
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

        # 4. Port-Cleanup
        for port in [3002, 3003, 3004, 3005, 3006, 3012]:
            try:
                r = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                                   capture_output=True, text=True, timeout=2)
                for pid in r.stdout.split():
                    if pid.strip().isdigit():
                        try: os.kill(int(pid), signal.SIGKILL)
                        except: pass
            except: pass

        print(f"[Pre-Start] Total-Kill: {len(pids)} Prozess(e) geräumt")
        return len(pids)
    except Exception as e:
        print(f"[Pre-Start] Total-Kill skipped: {e}", file=sys.stderr)
        return 0
