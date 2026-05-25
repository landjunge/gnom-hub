import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from gnom_hub.infrastructure.database.schema import create_tables
from gnom_hub.infrastructure.process.psutil_mgr import start_background_agents, kill_background_agents
from gnom_hub.presentation.api.router import router as api_router
from gnom_hub import chat_commands

async def start_openrouter_updater():
    import asyncio
    while True:
        try:
            from gnom_hub.presentation.api.v1.llm_models import check_and_update_models
            print("Running scheduled OpenRouter free models check...")
            await check_and_update_models()
            print("Scheduled OpenRouter free models check complete.")
        except Exception as e:
            print(f"Error in background openrouter updater: {e}")
        await asyncio.sleep(2 * 3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    from gnom_hub.db import init_db
    init_db()
    start_background_agents()
    
    import asyncio
    updater_task = asyncio.create_task(start_openrouter_updater())
    
    yield
    
    updater_task.cancel()
    kill_background_agents()

app = FastAPI(title="GNOM-HUB", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"], allow_headers=["*"]
)

app.include_router(api_router)
app.include_router(chat_commands.router)

FRONT = Path(__file__).parent.parent.parent.parent / "frontend"
if FRONT.exists(): app.mount("/static", StaticFiles(directory=str(FRONT)), name="static")

@app.get("/api/health")
def api_health():
    return {"status": "ok"}

@app.get("/")
def root():
    p = FRONT / "index.html"
    return FileResponse(str(p), headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}) if p.exists() else {"message": "GNOM-HUB", "version": "0.3.0"}
