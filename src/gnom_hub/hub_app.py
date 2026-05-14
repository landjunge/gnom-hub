from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn, os
from pathlib import Path
from .routes_memory import router as memory_router
from .routes_agents import router as agents_router
from .routes_nudge import router as nudge_router
from .routes_registry import router as registry_router
from .routes_chat import router as chat_router
from .routes_audio import router as audio_router
from .routes_admin import router as admin_router
from .chat_commands import router as ideas_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GNOM-HUB")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for r in [memory_router, agents_router, nudge_router, registry_router, chat_router, audio_router, admin_router, ideas_router]:
    app.include_router(r)

FRONT = Path(__file__).parent.parent.parent / "frontend"
if FRONT.exists(): app.mount("/static", StaticFiles(directory=str(FRONT)), name="static")

@app.get("/")
def root():
    idx = FRONT / "index.html"
    if idx.exists(): return FileResponse(str(idx))
    return {"message": "GNOM-HUB", "version": "0.3.0"}
def main(): uvicorn.run("gnom_hub.hub_app:app", host="127.0.0.1", port=int(os.environ.get("GNOM_HUB_PORT", 3002)))
