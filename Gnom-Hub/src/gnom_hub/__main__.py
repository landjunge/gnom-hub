import subprocess, sys, time, socket, os

def get_port(start, end=4000):
    for p in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', p)) != 0: return p
    return start

def main():
    api_p, mcp_p = get_port(3002), get_port(3100)
    os.environ["GNOM_HUB_PORT"] = str(api_p)
    os.environ["GNOM_MCP_PORT"] = str(mcp_p)
    print(f"\n=== Starte GNOM-HUB (Port {api_p}) & MCP (Port {mcp_p}) ===\n")
    
    api = subprocess.Popen([sys.executable, "-c", "from gnom_hub.hub_app import main; main()"])
    time.sleep(1)
    mcp = subprocess.Popen([sys.executable, "-c", "from gnom_hub.hub_mcp import main; main()"])
    
    try:
        api.wait()
        mcp.wait()
    except KeyboardInterrupt:
        print("\nBeende Server...")
        api.terminate()
        mcp.terminate()

if __name__ == "__main__":
    main()
