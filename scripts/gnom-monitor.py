import os
import time

import requests

PORT = os.environ.get("GNOM_HUB_PORT", "3002")
BASE = f"http://127.0.0.1:{PORT}"
log = open('/tmp/gnom-monitor.log', 'a')

def chat(c):
    try:
        r = requests.post(f'{BASE}/api/chat', json={'content': c, 'sender': 'user'}, timeout=15)
        return r.status_code == 200
    except Exception as e:
        log.write(f'Chat error: {e}\n')
        log.flush()
        return False

log.write(f'=== Monitor v2 started: {time.strftime("%H:%M:%S")} ===\n')
log.flush()

while True:
    try:
        r = requests.get(f'{BASE}/api/agents', timeout=5)
        agents = r.json() if r.status_code == 200 else []
        now = time.time()
        
        for a in agents:
            name = a.get('name', '?')
            status = a.get('status', '')
            last_seen = a.get('last_seen', '')
            
            if status == 'busy' and last_seen:
                try:
                    ts_str = last_seen.replace('Z', '+00:00')
                    from datetime import datetime
                    ts = datetime.fromisoformat(ts_str).timestamp()
                    mins = (now - ts) / 60
                    if mins > 2:
                        log.write(f'{time.strftime("%H:%M:%S")} {name} stuck {mins:.0f}min -> @@free\n')
                        log.flush()
                        chat(f'@@free {name}')
                except Exception as e:
                    log.write(f'{name} parse error: {e} | raw={last_seen}\n')
                    log.flush()
        
        time.sleep(20)
    except Exception as e:
        log.write(f'Loop error: {e}\n')
        log.flush()
        time.sleep(30)
