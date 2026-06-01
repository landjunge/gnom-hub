import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from gnom_hub.infrastructure.process.process_manager import start_background_agents, kill_background_agents
from gnom_hub.api.router import router as api_router
from gnom_hub.chat import chat_commands

async def start_openrouter_updater():
    import asyncio
    while True:
        try:
            from gnom_hub.api.endpoints.llm_models import check_and_update_models
            print("Running scheduled OpenRouter free models check...")
            await check_and_update_models()
            print("Scheduled OpenRouter free models check complete.")
        except Exception as e:
            print(f"Error in background openrouter updater: {e}")
        await asyncio.sleep(2 * 3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from gnom_hub.db.schema import init_database
    init_database()

    # ── Datei-Integritätsprüfung (ZWC-Signaturen) ──────────────────────────
    try:
        from gnom_hub.core.security.integrity import verify_system_files, is_integrity_enabled
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
                except Exception:
                    pass
            else:
                print("✅ [INTEGRITÄT] Alle Systemdateien unverändert.")
    except Exception as e:
        print(f"⚠️ Fehler bei Integritätsprüfung: {e}")

    # Prompt validation check in SUPERGNOM_MODE
    from gnom_hub.core.config import CONFIG_DIR
    if os.getenv("SUPERGNOM_MODE", "False").lower() == "true":
        try:
            import json, hashlib
            from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
            manifest_path = CONFIG_DIR / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                corrupted = []
                for name, expected_hash in manifest.items():
                    found = False
                    for k, v in AGENT_DEFINITIONS.items():
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


    start_background_agents()
    
    import asyncio
    updater_task = asyncio.create_task(start_openrouter_updater())
    
    yield
    
    updater_task.cancel()
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
if FRONT.exists(): app.mount("/static", StaticFiles(directory=str(FRONT)), name="static")

@app.get("/api/health")
def api_health():
    return {"status": "ok"}

@app.get("/")
def root():
    p = FRONT / "index.html"
    return FileResponse(str(p), headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}) if p.exists() else {"message": "GNOM-HUB", "version": "0.3.0"}
