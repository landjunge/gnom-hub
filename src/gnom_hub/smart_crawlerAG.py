"""smart_crawlerAG: Intelligenter Crawler mit Anti-Blocking (39 Zeilen)."""
import time, random, requests, re
from .smart_crawl import rotate_user_agent, get_random_delay, check_for_block
from .smart_crawl import _load, _save, _dom
from .router import ask_router
from .gitAG import auto_commit

def smart_request(url: str) -> str:
    """Anti-Block Crawl mit Memory und Rate-Limiting."""
    domain = _dom(url)
    db = _load()
    info = db.get(domain, {"blocks": 0, "last": 0})
    delay = get_random_delay(info["blocks"])
    wait = max(0, info["last"] + delay - time.time())
    if wait > 0: time.sleep(wait)
    headers = {
        "User-Agent": rotate_user_agent(),
        "Accept": "text/html,*/*",
        "Accept-Language": "de,en;q=0.5",
        "Referer": f"https://google.com/search?q={domain}",
        "DNT": "1",
    }
    try:
        r = requests.get(url, timeout=20, headers=headers)
        info["last"] = time.time()
        if check_for_block(r):
            info["blocks"] += 1
            db[domain] = info; _save(db)
            time.sleep(5)
            return f"Blockiert: {domain} (Status {r.status_code}, Blocks: {info['blocks']})"
        if info["blocks"] > 0: info["blocks"] -= 1
        db[domain] = info; _save(db)
        text = re.sub(r'<[^>]+>', ' ', r.text)
        auto_commit(".")
        return re.sub(r'\s+', ' ', text).strip()[:8000]
    except Exception as e:
        info["blocks"] += 1
        db[domain] = info; _save(db)
        time.sleep(5)
        return f"Blockiert: {str(e)}"

def smart_crawl(command: str) -> str:
    """Haupteinstiegspunkt für generalAG."""
    try:
        resp = ask_router(command, "Extrahiere nur die URL aus dem Befehl. Gib NUR die URL zurück.", agent_name="smart_crawlerAG")
        url = resp.strip()
        if not url.startswith("http"):
            return "❌ Keine valide URL gefunden."
        return smart_request(url)
    except:
        return "❌ Crawl fehlgeschlagen."
