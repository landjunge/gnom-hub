from fastapi import FastAPI
import uvicorn
import os

from .routes_memory import router as memory_router
from .routes_agents import router as agents_router

# Haupt-App initialisieren
app = FastAPI(title="GNOM-HUB")

# Routen aus den Modulen registrieren
app.include_router(memory_router)
app.include_router(agents_router)

@app.get("/")
def root():
    """Status-Check Route für den Hub."""
    return {"message": "GNOM-HUB", "version": "0.1.0"}

def main():
    """Einstiegspunkt zum Starten des API-Servers."""
    uvicorn.run("gnom_hub.hub_app:app", host="127.0.0.1", port=3002)

def stop():
    """Beendet alle laufenden GNOM-HUB Prozesse."""
    os.system("pkill -f gnom-hub")
