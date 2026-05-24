from contextlib import asynccontextmanager
from fastapi import FastAPI; from fastapi.staticfiles import StaticFiles; from fastapi.responses import FileResponse; import uvicorn, os; from pathlib import Path
from .routes_memory import router as memory_router; from .routes_agents import router as agents_router; from .routes_nudge import router as nudge_router; from .routes_registry import router as registry_router; from .routes_chat import router as chat_router; from .routes_audio import router as audio_router; from .routes_admin import router as admin_router; from .chat_commands import router as ideas_router; from .routes_workspace import router as workspace_router; from .routes_llm import router as llm_router; from .routes_llm_models import router as llm_models_router; from .routes_showbox import router as showbox_router
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(application):
    from .proc_mgr import start_background_agents, kill_background_agents
    start_background_agents()
    yield
    kill_background_agents()

app = FastAPI(title="GNOM-HUB", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:*", "http://127.0.0.1:*"], allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", allow_methods=["*"], allow_headers=["*"])
for r in [memory_router, agents_router, nudge_router, registry_router, chat_router, audio_router, admin_router, ideas_router, workspace_router, llm_router, llm_models_router, showbox_router]: app.include_router(r)
FRONT = Path(__file__).parent.parent.parent / "frontend"
if FRONT.exists(): app.mount("/static", StaticFiles(directory=str(FRONT)), name="static")
@app.get("/")
def root(): return FileResponse(str(FRONT / "index.html")) if (FRONT / "index.html").exists() else {"message": "GNOM-HUB", "version": "0.3.0"}
@app.get("/help")
def get_help(): return FileResponse(str(FRONT / "help.html")) if (FRONT / "help.html").exists() else {"message": "GNOM-HUB Help"}
# Startup/shutdown is handled by the lifespan context manager above
def main():
    from agents.watchdogAG import start_watchdog; start_watchdog()
    uvicorn.run("gnom_hub.hub_app:app", host="127.0.0.1", port=int(os.environ.get("GNOM_HUB_PORT", 3002)))

