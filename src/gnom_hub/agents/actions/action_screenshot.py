# action_screenshot.py — [SCREENSHOT: path] for workspace HTML/files
"""Capture a full-page screenshot of a local HTML file or URL into the workspace.

Syntax:
  [SCREENSHOT: relative/or/abs/path.html]
  [SCREENSHOT: relative/path.html | out=shots/x.png | width=1440]

Requires Playwright + Chromium (same stack as browser action).
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

from gnom_hub.core.security.path_validator import _safe


def handle_screenshot(ans: str, matches, agent, perms, wd) -> str:
    agent_name = (agent or {}).get("name") if isinstance(agent, dict) else str(agent or "?")
    for m in matches:
        raw = (m.group(1) or "").strip()
        if not raw:
            ans = ans.replace(m.group(0), f"[System: {agent_name} — leerer SCREENSHOT-Pfad.]")
            continue

        # Parse "path | out=... | width=..."
        parts = [p.strip() for p in raw.split("|")]
        src = parts[0]
        out_rel = None
        width = 1440
        height = 900
        for p in parts[1:]:
            if p.lower().startswith("out="):
                out_rel = p.split("=", 1)[1].strip()
            elif p.lower().startswith("width="):
                try:
                    width = max(320, min(2560, int(p.split("=", 1)[1])))
                except ValueError:
                    pass
            elif p.lower().startswith("height="):
                try:
                    height = max(240, min(2000, int(p.split("=", 1)[1])))
                except ValueError:
                    pass

        if "write" not in (perms or []) and "godmode" not in (perms or []):
            ans = ans.replace(
                m.group(0),
                f"[System: {agent_name} hat keine WRITE-Berechtigung für Screenshots.]",
            )
            continue

        # Resolve source
        src_url = None
        src_path = None
        if src.startswith("http://") or src.startswith("https://") or src.startswith("file://"):
            src_url = src
            if src.startswith("file://"):
                parsed = urlparse(src)
                src_path = Path(parsed.path)
        else:
            sp = _safe(wd, src, perms or [], agent_name=agent_name)
            if not sp or not os.path.isfile(sp):
                ans = ans.replace(
                    m.group(0),
                    f"[System: Screenshot-Quelle nicht gefunden/blockiert: {src}]",
                )
                continue
            src_path = Path(sp)
            src_url = src_path.resolve().as_uri()

        # Output path (default: same dir as source, .png)
        if not out_rel:
            if src_path is not None:
                try:
                    rel = src_path.resolve().relative_to(Path(wd).resolve())
                    out_rel = str(rel.with_suffix(".png"))
                except ValueError:
                    out_rel = src_path.stem + ".png"
            else:
                out_rel = "screenshot.png"
        op = _safe(wd, out_rel, perms or [], agent_name=agent_name)

        if not op:
            ans = ans.replace(m.group(0), f"[System: Screenshot-Ziel blockiert: {out_rel}]")
            continue

        try:
            os.makedirs(os.path.dirname(op) or ".", exist_ok=True)
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1.25,
                )
                page.goto(src_url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(500)
                page.screenshot(path=op, full_page=True)
                browser.close()
            size = os.path.getsize(op)
            r = (
                f"[System: Screenshot gespeichert: {os.path.abspath(op)} "
                f"({size} bytes, {width}x{height})]"
            )
        except Exception as e:
            r = f"[System-Fehler Screenshot: {type(e).__name__}: {e}]"
        ans = ans.replace(m.group(0), r)
    return ans
