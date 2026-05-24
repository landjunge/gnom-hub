def smart_crawl(cmd):
    from .router import ask_router
    from .smart_crawl import smart_request
    try:
        resp = ask_router(cmd, "Extrahiere nur die URL aus dem Befehl. Gib NUR die URL zurück.", agent_name="GeneralAG")
        url = resp.strip()
        if not url.startswith("http"): return "❌ Keine valide URL gefunden."
        return smart_request(url)
    except Exception as e: return f"❌ Crawl fehlgeschlagen: {e}"
def data_crawl(cmd):
    from .router import ask_router
    from .crawler_engine import rotate_user_agent, _load, _save, _dom
    import requests, time
    try:
        resp = ask_router(cmd, "Extrahiere nur die reine URL. Kein Zusatztext.", agent_name="GeneralAG")
        url = resp.strip()
        if not url.startswith("http"): return "❌ Keine valide URL gefunden."
        headers = {"User-Agent": rotate_user_agent(), "Accept": "application/json, text/html, */*"}
        r = requests.get(url, timeout=20, headers=headers)
        db, dom = _load(), _dom(url)
        db.setdefault(dom, {"blocks": 0, "last": 0})["last"] = time.time(); _save(db)
        html = r.text[:12000]
        return ask_router(f"URL: {url}\nHTML: {html}", "Extrahiere alle strukturierten Daten (Tabellen, Listen, Preise, JSON). Gib sauberes Ergebnis.", agent_name="GeneralAG")
    except Exception as e: return f"❌ Data-Crawl Fehler: {str(e)}"
def web_crawl(cmd):
    from .router import ask_router
    from .crawler_engine import rotate_user_agent, _load, _save, _dom
    import requests, time, re
    try:
        resp = ask_router(cmd, "Extrahiere nur die reine URL. Kein Zusatztext.", agent_name="GeneralAG")
        url = resp.strip()
        if not url.startswith("http"): return "❌ Keine valide URL gefunden."
        r = requests.get(url, timeout=15, headers={"User-Agent": rotate_user_agent()})
        db, dom = _load(), _dom(url)
        db.setdefault(dom, {"blocks": 0, "last": 0})["last"] = time.time(); _save(db)
        text = re.sub(r'<[^>]+>', ' ', r.text)
        return re.sub(r'\s+', ' ', text).strip()[:8000]
    except Exception as e: return f"❌ Web-Crawl Fehler: {str(e)}"
