# ftp_sync.py — HTML index sync + upload
import os, re; from pathlib import Path
from .ftp_deploy import upload

def sync_index(wd):
    from agents.securityAG import seal_content
    from gnom_hub.zwc_soul import strip_zwc
    wd = Path(wd); idx = wd / "index.html"
    if not idx.exists(): return
    files = [f for f in os.listdir(wd) if f.endswith((".html", ".md")) and f != "index.html" and not f.startswith(".")]
    cards = []
    for f in sorted(files):
        ext = f.split(".")[-1]; t = f.replace(f".{ext}", "").replace("_", " ").title()
        i = "🏠" if "landing" in f else ("⚡" if ext == "html" else "📘")
        c = "html" if ext == "html" else "md"
        cards.append(f'<a href="{f}" class="card {c}" target="_blank"><div class="icon">{i}</div><div class="title">{t}</div><div class="desc">{t} Seite.</div><span class="tag {c}-tag">{ext.upper()}</span></a>')
    html = re.sub(r'(<div class="grid">)(.*?)(</div>)', r'\1\n        ' + "\n        ".join(cards) + r'\n    \3', strip_zwc(idx.read_text(encoding="utf-8")), flags=re.DOTALL)
    idx.write_text(seal_content("System", html, "index.html"), encoding="utf-8")
    upload(idx, "index.html")
    for f in files: upload(wd / f, f)
