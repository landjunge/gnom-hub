from fastapi import FastAPI
import uvicorn
import os

from .routes_memory import router as memory_router
from .routes_agents import router as agents_router

app = FastAPI(title="GNOM-HUB")

app.include_router(memory_router)
app.include_router(agents_router)

@app.get("/")
def root():
    return {"message": "GNOM-HUB", "version": "0.1.0"}

def main():
    p = int(os.environ.get("GNOM_HUB_PORT", 3002))
    uvicorn.run("gnom_hub.hub_app:app", host="127.0.0.1", port=p)

def stop():
    os.system("pkill -f gnom-hub")
