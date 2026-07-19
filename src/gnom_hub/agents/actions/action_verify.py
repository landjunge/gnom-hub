# action_verify.py — [VERIFY: path|path2|must_contain=X|min_bytes=N]
"""Lightweight Definition-of-Done check for multi-file agent deliveries."""
from __future__ import annotations

import os
import re

from gnom_hub.core.security.path_validator import _safe


def handle_verify(ans: str, matches, agent, perms, wd) -> str:
    agent_name = (agent or {}).get("name") if isinstance(agent, dict) else str(agent or "?")
    for m in matches:
        raw = (m.group(1) or "").strip()
        if not raw:
            ans = ans.replace(m.group(0), f"[VERIFY FAIL: leere Angabe ({agent_name})]")
            continue

        paths: list[str] = []
        must_contain: list[str] = []
        min_bytes = 1
        for part in re.split(r"[|,]", raw):
            part = part.strip()
            if not part:
                continue
            low = part.lower()
            if low.startswith("must_contain="):
                must_contain.append(part.split("=", 1)[1])
            elif low.startswith("min_bytes="):
                try:
                    min_bytes = max(0, int(part.split("=", 1)[1]))
                except ValueError:
                    pass
            else:
                paths.append(part)

        if not paths:
            ans = ans.replace(m.group(0), "[VERIFY FAIL: keine Pfade]")
            continue

        ok_lines = []
        fail_lines = []
        for rel in paths:
            fp = _safe(wd, rel, perms or ["read"], agent_name=agent_name)
            if not fp or not os.path.isfile(fp):
                fail_lines.append(f"missing:{rel}")
                continue
            size = os.path.getsize(fp)
            if size < min_bytes:
                fail_lines.append(f"too_small:{rel}({size}<{min_bytes})")
                continue
            if must_contain and not any(p.lower().endswith(".png") for p in [rel]):
                try:
                    text = open(fp, encoding="utf-8", errors="ignore").read()
                except OSError as e:
                    fail_lines.append(f"read_error:{rel}:{e}")
                    continue
                for needle in must_contain:
                    if needle not in text:
                        fail_lines.append(f"missing_text:{rel}:«{needle}»")
                        break
                else:
                    ok_lines.append(f"ok:{rel}({size}b)")
            else:
                ok_lines.append(f"ok:{rel}({size}b)")

        if fail_lines:
            msg = (
                f"[VERIFY FAIL ({agent_name})] "
                + "; ".join(fail_lines)
                + ((" | " + "; ".join(ok_lines)) if ok_lines else "")
            )
        else:
            msg = f"[VERIFY OK ({agent_name})] " + "; ".join(ok_lines)
        ans = ans.replace(m.group(0), msg)
    return ans
