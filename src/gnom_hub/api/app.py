import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gnom_hub.api.router import router as api_router
from gnom_hub.chat import chat_commands
from gnom_hub.infrastructure.process.process_manager import kill_background_agents, start_background_agents


async def start_openrouter_updater():
    import asyncio
    while True:
        try:
            from gnom_hub.api.endpoints.llm_models import check_and_update_models
            print("Running scheduled free-model check (OpenRouter + OpenCode-Zen)...")
            await check_and_update_models()
            print("Scheduled model check complete.")
        except asyncio.CancelledError:
            print("Model updater cancelled.")
            break
        except Exception as e:
            print(f"Error in background model updater: {e}")
        # Stündlich aktualisieren
        await asyncio.sleep(3600)


async def start_invalid_keys_reverifier():
    """Re-verifiziert `# UNGÜLTIG:`-Keys in api_keys.txt periodisch.

    Defense-in-Depth: `sync_desktop_keys()` liest nur aktive Zeilen.
    Ohne diesen Loop bleibt ein einmal als invalid markierter Key für immer
    disabled, auch wenn der Provider ihn inzwischen wieder akzeptiert
    (Billing-Reset, revoke→re-grant, temp outage).

    Throttle (30 min) lebt in `reverify_invalid_keys()` selbst.
    """
    import asyncio

    from gnom_hub.infrastructure.llm.desktop_syncer import reverify_invalid_keys
    # Initial-Delay damit Hub-Startup nicht durch 10+ HTTP-Calls ausgebremst wird
    await asyncio.sleep(60)
    while True:
        try:
            r = await reverify_invalid_keys()
            if r.get("recovered"):
                print(f"🔑 [KEY-REVERIFY] Recovered {len(r['recovered'])} key(s): {r['recovered']}")
            elif r.get("checked"):
                print(f"🔑 [KEY-REVERIFY] Checked {r['checked']} invalid key(s) — none recovered.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in invalid-keys reverifier: {e}")
        await asyncio.sleep(30 * 60)  # 30 Minuten

async def start_recovery_and_watchdog_loop(db_path: Path):
    import asyncio
    import time
    from datetime import datetime, timezone

    from gnom_hub.agents.swarm.swarm_comms import recover_stuck_messages
    from gnom_hub.db import get_all_agents, update_agent_status
    from gnom_hub.db.connection import get_db_connection
    from gnom_hub.infrastructure.process.process_manager import _get_proc, restart_single_agent

    check_interval = 30.0
    checkpoint_counter = 0
    restart_tracker = {}

    while True:
        try:
            loop = asyncio.get_running_loop()
            # 1. Stuck messages recovery (Visibility Timeout)
            await loop.run_in_executor(None, recover_stuck_messages, str(db_path), 300.0)

            # 2. Watchdog / heartbeats check
            agents = await loop.run_in_executor(None, get_all_agents)
            now = datetime.now(timezone.utc)

            for agent in agents:
                name = agent.get("name")
                status = agent.get("status")
                last_seen_str = agent.get("last_seen")

                last_seen = None
                if last_seen_str:
                    try:
                        last_seen = datetime.fromisoformat(last_seen_str).replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        pass

                drift = (now - last_seen).total_seconds() if last_seen else 999999
                should_be_online = status in ("online", "busy")

                if status == "degraded":
                    if drift > 60.0:
                        print(f"🔄 [WATCHDOG] Cooldown abgelaufen für Agent {name}. Setze zurück auf online (HALF_OPEN).")
                        def recover_degraded(n):
                            conn = get_db_connection()
                            try:
                                conn.execute("""
                                    UPDATE agents
                                    SET status = 'online', circuit_state = 'HALF_OPEN', consecutive_failures = 0, last_seen = ?
                                    WHERE name = ?
                                """, (datetime.now(timezone.utc).isoformat(), n))
                                conn.commit()
                            finally:
                                conn.close()
                        await loop.run_in_executor(None, recover_degraded, name)

                elif should_be_online:
                    proc = _get_proc(name)
                    need_restart = False
                    reason = ""
                    limit = 600.0 if status == "busy" else 120.0
                    if not proc:
                        need_restart = True
                        reason = "Prozess fehlt"
                    elif drift > limit:
                        need_restart = True
                        reason = f"reagiert nicht mehr (Drift: {int(drift)}s)"

                    if need_restart:
                        now_ts = time.time()
                        history = [ts for ts in restart_tracker.get(name, []) if now_ts - ts < 600.0]
                        history.append(now_ts)
                        restart_tracker[name] = history

                        if len(history) >= 3:
                            print(f"🚨 [WATCHDOG] Agent {name} ist in einer Crash-Schleife (3 Restarts in 10 Min). Versetze in Quarantäne...")
                            await loop.run_in_executor(None, update_agent_status, name, "quarantined")
                        else:
                            print(f"⚠️ [WATCHDOG] Agent {name} {reason}. Starte neu (Restart {len(history)}/3 in 10 Min)...")
                            await loop.run_in_executor(None, restart_single_agent, name)

            # 3. WAL Checkpoint (TRUNCATE) every 10 minutes
            checkpoint_counter += 1
            if checkpoint_counter >= 20:  # 20 * 30s = 10 minutes
                checkpoint_counter = 0
                def do_checkpoint():
                    conn = get_db_connection()
                    try:
                        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                        print("✅ [SQLITE] WAL checkpoint (TRUNCATE) erfolgreich ausgeführt.")
                        # Callbacks älter als 24h löschen
                        cutoff = time.time() - 86400.0
                        deleted = conn.execute("DELETE FROM swarm_callbacks WHERE received_at < ?", (cutoff,)).rowcount
                        if deleted > 0:
                            print(f"🧹 [SQLITE] {deleted} veraltete Swarm-Callbacks bereinigt.")
                        conn.commit()
                    except Exception as e:
                        print(f"Fehler bei SQLite-Checkpoint/Cleanup: {e}")
                    finally:
                        conn.close()

                await loop.run_in_executor(None, do_checkpoint)

        except Exception as e:
            print(f"Fehler im Watchdog/Recovery-Loop: {e}")

        await asyncio.sleep(check_interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from gnom_hub.db.schema import init_database
    init_database()
    from gnom_hub.db.message_queue import init_message_queue
    init_message_queue()

    # ── Datei-Integritätsprüfung (ZWC-Signaturen) ──────────────────────────
    try:
        from gnom_hub.core.security.integrity import is_integrity_enabled, verify_system_files
        if is_integrity_enabled():
            from pathlib import Path as _Path
            _root = _Path(__file__).parent.parent.parent.parent.resolve()
            tampered = verify_system_files(_root)
            if tampered:
                print(f"⚠️ [SICHERHEITSWARNUNG] {len(tampered)} Systemdatei(en) manipuliert: {tampered}")
                # Warnung in Chat schreiben
                try:
                    from gnom_hub.db import add_chat_message, get_active_project
                    proj = get_active_project()
                    msg = (
                        f"🚨 **[INTEGRITÄTSALARM]** {len(tampered)} Systemdatei(en) wurden seit dem letzten "
                        f"`@system save` verändert:\n" +
                        "\n".join(f"• `{f}`" for f in tampered) +
                        "\n\nFalls du selbst Änderungen gemacht hast: `@system save` um den neuen Stand zu sichern. "
                        "Falls nicht — mögliche Manipulation!"
                    )
                    add_chat_message(proj, "WatchdogAG", "watchdogag", "chat", msg)
                except Exception as e:
                    print(f"⚠️ Integritäts-Chat-Nachricht fehlgeschlagen: {e}")
            else:
                print("✅ [INTEGRITÄT] Alle Systemdateien unverändert.")
    except Exception as e:
        print(f"⚠️ Fehler bei Integritätsprüfung: {e}")

    # Prompt validation check in SUPERGNOM_MODE
    from gnom_hub.core.config import CONFIG_DIR
    if os.getenv("SUPERGNOM_MODE", "False").lower() == "true":
        try:
            import hashlib
            import json

            from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
            manifest_path = CONFIG_DIR / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
                corrupted = []
                for name, expected_hash in manifest.items():
                    found = False
                    for _k, v in AGENT_DEFINITIONS.items():
                        if v["name"].lower() == name.lower():
                            found = True
                            p_bytes = v["sys_prompt"].encode("utf-8")
                            current_hash = hashlib.sha256(p_bytes).hexdigest()
                            if current_hash != expected_hash:
                                corrupted.append(v["name"])
                            break
                    if not found:
                        corrupted.append(name)
                if corrupted:
                    print(f"⚠️ [WARNUNG] Prompt-Integritätsverletzung erkannt! Modifizierte Agenten: {', '.join(corrupted)}")
                else:
                    print("✅ Prompt-Integritätsprüfung erfolgreich: Alle Hashes stimmen überein.")
            else:
                print("⚠️ [WARNUNG] Keine prompt manifest.json gefunden. Integritätsprüfung übersprungen.")
        except Exception as e:
            print(f"⚠️ Fehler bei Prompt-Integritätsprüfung: {e}")


    # ── Auto-Update Check (non-blocking, nur Check) ──
    try:
        import subprocess
        from pathlib import Path
        repo = Path(__file__).parent.parent.resolve()
        if (repo / ".git").exists():
            subprocess.run(
                ["git", "fetch", "--dry-run"],
                cwd=str(repo), capture_output=True, text=True, timeout=10
            )
            # Nur Info, kein Auto-Pull
            print("🔄 Git-Repo erreichbar")
    except Exception as e:
        print(f"⚠️ Git-Check fehlgeschlagen: {e}")

    # ── Background-Agents in eigenem Thread starten damit Hub-Startup nicht blockt ──
    import threading
    def _start_agents_async():
        try:
            start_background_agents()
        except Exception as e:
            print(f"⚠️ Agent-Start fehlgeschlagen: {e}")
    threading.Thread(target=_start_agents_async, daemon=True).start()
    # Kurz warten damit Agenten connecten können
    import time
    time.sleep(2)

    # ── Default Showbox mit 8 Buttons sicherstellen ──
    try:
        from gnom_hub.db.showbox_repo import ensure_default_showbox
        ensure_default_showbox()
    except Exception as e:
        print(f"⚠️ ensure_default_showbox fehlgeschlagen: {e}")

    from gnom_hub.infrastructure.pulse import start_pulse
    start_pulse()

    import asyncio

    from gnom_hub.core.config import DB_PATH
    # User-Mandat 2026-06-28 06:34 — OpenRouter-Updater RAUS.
    # (Vorher: updater_task = asyncio.create_task(start_openrouter_updater()))
    # Wir nutzen NUR MiniMax, kein 401-Spam alle 60min.
    recovery_task = asyncio.create_task(start_recovery_and_watchdog_loop(DB_PATH))
    reverify_task = asyncio.create_task(start_invalid_keys_reverifier())

    yield

    recovery_task.cancel()
    reverify_task.cancel()
    kill_background_agents()

app = FastAPI(title="GNOM-HUB", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:*",
        "http://localhost:*",
        f"http://127.0.0.1:{os.environ.get('GNOM_HUB_PORT', '3002')}",
        f"http://localhost:{os.environ.get('GNOM_HUB_PORT', '3002')}",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Hub-Secret"],
    allow_credentials=True
)

app.include_router(api_router)
app.include_router(chat_commands.router)

AVATARS_DIR = Path(__file__).parent.parent / "config" / "avatars"
if AVATARS_DIR.exists(): app.mount("/static/avatars", StaticFiles(directory=str(AVATARS_DIR)), name="avatars")

FRONT = Path(__file__).parent.parent / "frontend"
# FRONTEND_DIR also defined in core.config.Config — keep in sync
if FRONT.exists(): app.mount("/static", StaticFiles(directory=str(FRONT)), name="static")

# Force no-cache for all static files (prevents stale JS/CSS)
from starlette.middleware.base import BaseHTTPMiddleware


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
app.add_middleware(NoCacheStaticMiddleware)

@app.get("/api/health")
def api_health():
    return {"status": "ok"}

@app.get("/")
def root():
    p = FRONT / "index.html"
    return FileResponse(str(p), headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}) if p.exists() else {"message": "GNOM-HUB", "version": "0.3.0"}
