import os, sys, uvicorn

def main():
    uvicorn.run("gnom_hub.api.app:app", host="127.0.0.1", port=int(os.environ.get("GNOM_HUB_PORT", 3002)))
    if os.environ.get("GNOM_HUB_RESTART") == "true":
        print("[Gnom-Hub] Graceful shutdown complete. Exiting with code 42 to request restart.")
        sys.exit(42)
