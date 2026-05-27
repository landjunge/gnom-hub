import subprocess, sys, time, socket, os
BANNER = """\033[32m
          ██████╗  ███╗   ██╗ ██████╗ ███╗   ███╗
         ██╔════╝  ████╗  ██║██╔═══██╗████╗ ████║
         ██║  ███╗ ██╔██╗ ██║██║   ██║██╔████╔██║
         ██║   ██║ ██║╚██╗██║██║   ██║██║╚██╔╝██║
         ╚██████╔╝ ██║ ╚████║╚██████╔╝██║ ╚═╝ ██║
          ╚═════╝  ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝\033[0m"""
INFO = """\033[1m                    H U B\033[0m
\033[33m   API:\033[0m       http://127.0.0.1:{api}
\033[33m   Frontend:\033[0m  frontend/index.html"""
def _free(start):
    for p in range(start, start + 1000):
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1', p)) != 0: return p
    return start
def main():
    while True:
        api_p = _free(3002)
        os.environ["GNOM_HUB_PORT"] = str(api_p)
        print(BANNER); print(INFO.format(api=api_p))
        api = subprocess.Popen([sys.executable, "-c", "from gnom_hub.infrastructure.hub_app import main; main()"])
        time.sleep(1)
        from gnom_hub.infrastructure.pulse import start_pulse; start_pulse()
        try:
            ret = api.wait()
            if ret == 42: print("\n\033[33m[Gnom-Hub] Restarting...\033[0m"); continue
            break
        except KeyboardInterrupt:
            print("\nBeende..."); api.terminate(); break

if __name__ == "__main__": main()
