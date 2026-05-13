from fastapi import FastAPI
import uvicorn, os
from .routes_memory import router as memory_router
from .routes_agents import router as agents_router
from .routes_nudge import router as nudge_router
from .routes_registry import router as registry_router
from .routes_chat import router as chat_router
from .routes_audio import router as audio_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GNOM-HUB")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(memory_router)
app.include_router(agents_router)
app.include_router(nudge_router)
app.include_router(registry_router)
app.include_router(chat_router)
app.include_router(audio_router)

@app.get("/")
def root(): return {"message": "GNOM-HUB", "version": "0.2.0"}
def main(): uvicorn.run("gnom_hub.hub_app:app", host="127.0.0.1", port=int(os.environ.get("GNOM_HUB_PORT", 3002)))
def stop(): os.system("pkill -f gnom-hub")
