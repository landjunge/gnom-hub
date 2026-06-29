import json, re as _re
from gnom_hub.agents.agent_names import normalize_showbox_name

# Hinweis (2026-06-18): Die hier ausgeführten Befehle werden VOR der Ausführung
# durch `is_command_safe_and_whitelisted` (gatekeeper.py) gegen eine Risiko-
# Liste geprüft. `rm -rf /`, `mkfs`, `curl|sh`, `eval(`, `subprocess(..., shell=True)`
# werden hart geblockt. Der frühere vollständige SHELL_BLOCK ist damit durch
# eine gezielte Whitelist+Blacklist-Hybrid-Lösung ersetzt.


def handle_shell(ans, ms, ag, perms, bs, wd):
    for m in ms:
        c, o = m.group(1).strip(), m.group(0)
        if "run" not in perms:
            ans = ans.replace(o, f"[System: {ag['name']} hat keine SHELL-Berechtigung.]")
            continue

        # Befehl vor Ausführung gegen die Gatekeeper-Whitelist prüfen.
        try:
            from gnom_hub.core.security.gatekeeper import is_command_safe_and_whitelisted
            is_safe, severity, reason = is_command_safe_and_whitelisted(c, agent=ag)
        except Exception as e:
            ans = ans.replace(o, f"[Shell-Prüfung fehlgeschlagen: {str(e)[:80]}]")
            continue

        if not is_safe:
            ans = ans.replace(o, f"[Shell blockiert ({severity}): {reason}]")
            continue

        try:
            from gnom_hub.infrastructure.process.sandbox import run_in_sandbox
            r = run_in_sandbox(c, agent=ag, timeout=30)
            ans = ans.replace(o, f"[Shell ({c}):\n{(r.stdout+r.stderr)[:1500]}]")
        except Exception as e:
            ans = ans.replace(o, f"[Shell-Fehler: {str(e)[:80]}]")
    return ans
def handle_crawl(ans, ms, ag, perms):
    for m in ms:
        u, o = m.group(1).strip(), m.group(0)
        if "crawl" not in perms: ans = ans.replace(o, f"[System: {ag['name']} hat keine CRAWL-Berechtigung.]"); continue
        try:
            from gnom_hub.infrastructure.utils.crawler_engine import crawl_smart, crawl_data
            t = crawl_data(u) if "data" in ag["name"].lower() else crawl_smart(u)
            ans = ans.replace(o, f"[Crawl-Ergebnis ({u[:60]}):\n{t[:3000]}]")
        except Exception as e: ans = ans.replace(o, f"[Crawl-Fehler: {str(e)[:80]}]")
    return ans
def handle_showbox(ans, ms):
    from gnom_hub.core.json_sanitizer import _sanitize_json
    from gnom_hub.core.security.hmac_signer import generate_signature
    from gnom_hub.db import save_showbox_presentation, set_active_showbox
    for full, idx, raw in ms:
        try:
            d = _sanitize_json(raw.strip())
            if isinstance(d, list):
                slides = d
                d = {"slides": d}
            else:
                d.pop("sig", None)
                slides = d.get("slides", [])

            # Prevent style bleeding by scoping global elements to .sb-layer-body
            cleaned_slides = []
            for sld in slides:
                if isinstance(sld, str):
                    sld = _re.sub(r'\bbody\b', '.sb-layer-body', sld, flags=_re.I)
                    sld = _re.sub(r'\bhtml\b', '.sb-layer-body', sld, flags=_re.I)
                    sld = _re.sub(r'(?<!\w)\*(?!\w)', '.sb-layer-body *', sld)
                cleaned_slides.append(sld)
            slides = cleaned_slides
            d["slides"] = slides
            
            d["sig"] = generate_signature("Gnom", json.dumps(d, separators=(',', ':'), sort_keys=True))

            # Map index/name
            presentation_name = idx.strip() if idx else ""
            if presentation_name.isdigit() and 1 <= int(presentation_name) <= 7:
                presentation_name = f"Showbox {presentation_name}"
            elif not presentation_name:
                presentation_name = "Latest Update"

            # Normalize Agent-Namen: 'general_ag'/'general-ag'/'generalag' → 'generalAG'
            # Damit Konsistenz über alle 8 Agenten
            presentation_name = normalize_showbox_name(presentation_name)

            # Save to SQLite database
            # buttons=d.get('buttons'): ohne diesen Parameter droppt save_showbox_presentation
            # das buttons[]-Array → UI-Klicks landen als Text im Chat statt als klickbarer
            # Button. Alle 5 anderen Caller (chat_legacy, showbox endpoint) passen buttons
            # bereits korrekt — nur action_exec hatte den Fix vergessen.
            save_showbox_presentation(presentation_name, slides, sender="Agent", buttons=d.get("buttons") if isinstance(d, dict) else None)
            set_active_showbox(presentation_name)
            
            ans = ans.replace(full, f"<SHOWBOX{':'+idx if idx else ''}>{json.dumps(d)}</SHOWBOX>")
        except Exception as e: ans = ans.replace(full, f"[Showbox-Fehler: {e}]")
    return ans

