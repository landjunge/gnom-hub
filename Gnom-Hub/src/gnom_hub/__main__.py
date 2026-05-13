import subprocess, sys, time, socket, os
BANNER = """\033[32m
          ██████╗  ███╗   ██╗ ██████╗ ███╗   ███╗
         ██╔════╝  ████╗  ██║██╔═══██╗████╗ ████║
         ██║  ███╗ ██╔██╗ ██║██║   ██║██╔████╔██║
         ██║   ██║ ██║╚██╗██║██║   ██║██║╚██╔╝██║
         ╚██████╔╝ ██║ ╚████║╚██████╔╝██║ ╚═╝ ██║
          ╚═════╝  ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝\033[0m"""
INFO = """\033[1m                    H U B\033[0m
\033[90m   ─────────────────────────────\033[0m
\033[33m   API:\033[0m       http://127.0.0.1:{api}
\033[33m   MCP SSE:\033[0m   http://127.0.0.1:{mcp}/sse
\033[33m   Frontend:\033[0m  frontend/index.html
\033[90m   ─────────────────────────────\033[0m
\033[36m   MCP-URL in Agent eintragen,
   Integrations-Prompt aus README.md\033[0m
\033[90m   ─────────────────────────────\033[0m"""

def _free(start):
    for p in range(start, start + 1000):
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1', p)) != 0: return p
    return start

def main():
    api_p, mcp_p = _free(3002), _free(3100)
    os.environ["GNOM_HUB_PORT"], os.environ["GNOM_MCP_PORT"] = str(api_p), str(mcp_p)
    print(BANNER); print(INFO.format(api=api_p, mcp=mcp_p))
    api = subprocess.Popen([sys.executable, "-c", "from gnom_hub.hub_app import main; main()"])
    time.sleep(1)
    from gnom_hub.hub_pulse import start_pulse; start_pulse()
    mcp = subprocess.Popen([sys.executable, "-c", "from gnom_hub.hub_mcp import main; main()"])
    try: api.wait(); mcp.wait()
    except KeyboardInterrupt: print("\nBeende..."); api.terminate(); mcp.terminate()

if __name__ == "__main__": main()
