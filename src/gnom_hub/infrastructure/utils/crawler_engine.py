import re, json, random, requests, time; from .smart_crawl import smart_request, rotate_user_agent, _load, _save, _dom
def crawl_simple(url, timeout=15):
    t = re.sub(r'<[^>]+>', ' ', requests.get(url, timeout=timeout, headers={"User-Agent": rotate_user_agent()}).text)
    return re.sub(r'\s+', ' ', t).strip()[:3000]
def crawl_smart(url, timeout=20): return smart_request(url)
def crawl_data(url, timeout=20):
    time.sleep(random.uniform(1.0, 2.5))
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": rotate_user_agent(), "Accept": "application/json, text/html, */*"})
        db, dom = _load(), _dom(url)
        db.setdefault(dom, {"blocks": 0, "last": 0})["last"] = time.time(); _save(db)
        if "json" in r.headers.get("Content-Type", ""): return json.dumps(r.json(), indent=2, ensure_ascii=False)[:3000]
        html, result = r.text, ""
        for t in re.findall(r'<table.*?</table>', html, re.DOTALL)[:3]: result += re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' | ', t)).strip() + "\n\n"
        for l in re.findall(r'<(?:ul|ol).*?</(?:ul|ol)>', html, re.DOTALL)[:5]: result += re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', re.sub(r'<li[^>]*>', '• ', l))).strip() + "\n"
        return (result.strip() if result.strip() else re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip())[:3000]
    except Exception as e: return f"[DATA-FEHLER] {str(e)[:100]}"
