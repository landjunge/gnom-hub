import os, uvicorn

def main():
    uvicorn.run("gnom_hub.api.app:app", host="127.0.0.1", port=int(os.environ.get("GNOM_HUB_PORT", 3002)))
