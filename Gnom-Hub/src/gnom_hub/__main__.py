import subprocess
import time

def main():
    print("\nStarte GNOM-HUB und MCP Server...")
    
    # Starte beide Prozesse parallel über ihre installierten Befehle
    api_process = subprocess.Popen(["gnom-hub-api"])
    time.sleep(1) # Kurze Pause für bessere Lesbarkeit im Terminal
    mcp_process = subprocess.Popen(["gnom-hub-mcp"])
    
    try:
        # Halte das Hauptskript am Laufen
        api_process.wait()
        mcp_process.wait()
    except KeyboardInterrupt:
        print("\nBeende GNOM-HUB Prozesse...")
        api_process.terminate()
        mcp_process.terminate()

if __name__ == "__main__":
    main()
