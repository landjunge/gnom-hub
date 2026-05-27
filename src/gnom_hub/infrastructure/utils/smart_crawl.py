import os, json, time, random, re, requests, threading; from urllib.parse import urlparse; from gnom_hub.core.config import DATA_DIR
_lock, _DB = threading.Lock(), DATA_DIR / "domains.json"
_UA = ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/125.0", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0", "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Firefox/128.0", "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Safari/605.1.15", "Mozilla/5.0 (Windows NT 10.0; Win64) Firefox/127.0"]
def rotate_user_agent(): return random.choice(_UA)
def _dom(url): return urlparse(url).netloc
def _load():
    with _lock:
        if _DB.exists():
            try: return json.load(open(_DB))
            except: pass
    return {}
def _save(d):
    with _lock: json.dump(d, open(_DB, "w"), indent=2)
def check_for_block(r):
    if r.status_code in (403, 429, 503): return True
    return any(s in r.text[:2000].lower() for s in ["cloudflare", "captcha", "cf-browser", "access denied"])
def smart_request(url):
    dom, db = urlparse(url).netloc, _load()
    info = db.get(dom, {"blocks": 0, "last": 0}); delay = random.uniform(1.2, 4.5) * min(1 + info["blocks"] * 0.8, 10)
    since = time.time() - info["last"]
    if since < delay: time.sleep(delay - since)
    if info["blocks"] >= 3: time.sleep(random.uniform(8, 15))
    h = {"User-Agent": random.choice(_UA), "Accept": "text/html,*/*", "Accept-Language": "de,en;q=0.5", "Referer": f"https://google.com/search?q={dom}", "DNT": "1"}
    try:
        r = requests.get(url, timeout=20, headers=h); info["last"] = time.time()
        if check_for_block(r):
            info["blocks"] += 1; db[dom] = info; _save(db)
            return f"[BLOCK×{info['blocks']}] {dom} — Fallback: ultra-slow" if info["blocks"] >= 3 else f"[BLOCK] {dom} (Status {r.status_code}, #{info['blocks']})"
        if info["blocks"] > 0: info["blocks"] -= 1
        db[dom] = info; _save(db)
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', r.text)).strip()[:3000]
    except Exception as e: return f"[FEHLER] {str(e)[:100]}"
