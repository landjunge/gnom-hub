# action_handlers.py — Dispatcher für alle Action-Tags
import re; from .action_write import handle_write, handle_read
from .action_exec import handle_shell, handle_crawl, handle_showbox
from .action_video import handle_screen_record, handle_video_merge, handle_video_edit
from gnom_hub.core.security.gatekeeper import verify_write, verify_cmd
from .action_browser import handle_browser
from .action_desktop import handle_desktop


# ── SecurityAG-Audit-Hook (Refactor-Schritt 4, Owner-Decision B 2026-06-21) ─────
# Trigger-Bedingung (Owner-Spec): name=='securityag' AND ('godmode'|'run'|'write') in perms.
# Feuert in jede Richtung (allowed/denied/error) für write/run/browser/crawl.
# Audit ist asynchron (DB-Fail nur log, kein Block der Aktion).
# Sonderfälle:
#   - Brainstorm-Override: feuert trotz Override (Audit ist nicht Teil der Override-Logik).
#   - Auto-Approve: feuert VOR Auto-Approve (process_actions empfängt bereits
#     aufgelöste perms → Audit-Eintrag vor der eigentlichen Aktion).
#   - Multi-Action: feuert einmal pro Action (Hook im per-Match-Loop).
def _audit_security(agent, perms, action_kind: str, target: str, result: str):
    """Schreibt einen SecurityAG-Audit-Eintrag (idempotent, swallow-on-error).

    action_kind ∈ {"write", "run", "browser", "crawl"} — wird intern zu
    "security_{action_kind}" (z.B. "security_write"). result ∈ {"allowed", "denied",
    "error"}. severity: "high" wenn "godmode" in perms, sonst "medium".
    """
    try:
        if (agent.get("name", "").lower() != "securityag"
                or not any(p in perms for p in ("godmode", "run", "write"))):
            return
        # Lazy import: system_repo zieht relativ viel Code mit; erst laden wenn
        # der Hook wirklich feuert (typisch < 1% der process_actions-Aufrufe).
        from gnom_hub.db.system_repo import log_security_audit
        log_security_audit(
            agent=agent.get("name", "SecurityAG"),
            action_type=f"security_{action_kind}",
            target=(target or "")[:500],
            result=result,
            severity="high" if "godmode" in perms else "medium",
            perms_snapshot=list(perms),
            trace_id=None,
        )
    except Exception:
        # Audit darf die Aktion NIE blockieren (Owner-Decision: asynchron).
        # Stille Verschluckung — Fehler wurde bereits im Helper geloggt.
        pass


def process_actions(ans, agent, perms, bs_mode, wd):
    perms = list(perms)
    w_ms, r_ms, sh_ms, desktop_ms = [], [], [], []
    for m in re.finditer(r"\[WRITE:\s*(.*?)\](.*?)\[/WRITE\]", ans, re.DOTALL):
        fn, content = m.group(1).strip(), m.group(2).strip()
        # ── [WRITE:] Permission-Check (Refactor-Kontext 2026-06-21) ────────
        # Vor Refactor: SoulAG hatte godmode (impliziert write via gatekeeper-
        # Bypass in gatekeeper.py:303). Nach Refactor: SoulAG hat kein write
        # mehr — sein [WRITE:] wird HIER kontrolliert geblockt mit klarer
        # System-Meldung. Der gatekeeper.py:303-Bypass ist damit toter Code
        # (SoulAG erreicht verify_write nicht mehr). Andere Agents (CoderAG,
        # WriterAG, EditorAG, SecurityAG) behalten write und funktionieren
        # weiterhin. WatchdogAG/GeneralAG/ResearcherAG hatten nie write und
        # werden wie bisher kontrolliert geblockt.
        if "write" not in perms:
            _audit_security(agent, perms, "write", fn, "denied")
            ans = ans.replace(m.group(0), f"[System: {agent.get('name','?')} hat keine Schreibberechtigung.]")
        elif verify_write(agent, fn, content, wd, perms):
            _audit_security(agent, perms, "write", fn, "allowed")
            w_ms.append(m)
        else:
            _audit_security(agent, perms, "write", fn, "denied")
            ans = ans.replace(m.group(0), f"[Gatekeeper: Schreibzugriff auf '{fn}' verweigert.]")
    already_matched = {m.start() for m in w_ms}
    for m in re.finditer(r"\[WRITE:\s*(.*?)\]\s*\n\s*```\w*\n(.*?)```", ans, re.DOTALL):
        if m.start() not in already_matched:
            fn, content = m.group(1).strip(), m.group(2).strip()
            if "write" not in perms:
                _audit_security(agent, perms, "write", fn, "denied")
                ans = ans.replace(m.group(0), f"[System: {agent.get('name','?')} hat keine Schreibberechtigung.]")
            elif verify_write(agent, fn, content, wd, perms):
                _audit_security(agent, perms, "write", fn, "allowed")
                w_ms.append(m)
            else:
                _audit_security(agent, perms, "write", fn, "denied")
                ans = ans.replace(m.group(0), f"[Gatekeeper: Schreibzugriff auf '{fn}' verweigert.]")
    for m in re.finditer(r"\[READ:\s*(.*?)\]", ans):
        r_ms.append(m)
    for m in re.finditer(r"\[SHELL:\s*(.*?)\]", ans):
        cmd = m.group(1).strip()
        # ── [SHELL:] Permission-Check (Refactor-Kontext 2026-06-21) ────────
        # Vor Refactor: SoulAG/WatchdogAG/EditorAG hatten run+godmode (oder
        # run allein via Auto-Inferenz). Nach Refactor: SoulAG/WatchdogAG/
        # EditorAG haben KEIN run mehr. SoulAG erreicht jetzt diese Stelle
        # und wird kontrolliert geblockt (vorher bypass via gatekeeper.py:449).
        # WatchdogAG war schon vorher blockiert (kein Akteur). EditorAG ist
        # neu betroffen — beabsichtigt, da Editor ein QA/Refactor-Worker ist
        # und keine Shell-Befehle braucht. CoderAG/SecurityAG behalten run
        # und funktionieren weiterhin. GeneralAG hatte nie run.
        if "run" not in perms:
            _audit_security(agent, perms, "run", cmd, "denied")
            ans = ans.replace(m.group(0), f"[System: {agent.get('name','?')} hat keine SHELL-Berechtigung.]")
        elif verify_cmd(agent, cmd):
            _audit_security(agent, perms, "run", cmd, "allowed")
            sh_ms.append(m)
        else:
            _audit_security(agent, perms, "run", cmd, "denied")
            ans = ans.replace(m.group(0), f"[Gatekeeper: Befehlsausführung verweigert.]")
    for m in re.finditer(r"\[DESKTOP:\s*(.*?)\]", ans, re.DOTALL):
        desktop_ms.append(m)
    # ── SecurityAG-Audit: [CRAWL:] pre-dispatch (Refactor-Schritt 4) ────────
    # Permission-Check für CRAWL liegt in handle_crawl() selbst; hier nur Hook
    # für SecurityAG-Audit. Bei "allowed"-Permission audit, sonst "denied".
    crawl_matches_pre = list(re.finditer(r"\[CRAWL:\s*(.*?)\]", ans))
    for m in crawl_matches_pre:
        url = m.group(1).strip()
        if "write" in perms or "godmode" in perms:
            _audit_security(agent, perms, "crawl", url, "allowed")
        else:
            _audit_security(agent, perms, "crawl", url, "denied")
    ans = handle_write(ans, w_ms, agent, perms, bs_mode, wd)
    ans = handle_read(ans, r_ms, wd, perms)
    ans = handle_shell(ans, sh_ms, agent, perms, bs_mode, wd)
    ans = handle_crawl(ans, crawl_matches_pre, agent, perms)
    # ── Permission-Tag-Extraktion (SecurityAG Kernrolle 1+2) ──────────────
    # Tag-Formate: [GRANT_PERM: agent=X path=Y ...], [REVOKE_PERM: ...], [LIST_PERMS: agent=X]
    # Handler in action_exec.py — Permission-Check passiert dort (db_write erforderlich).
    from .action_exec import handle_grant_perm, handle_revoke_perm, handle_list_perms
    grant_ms = list(re.finditer(r"\[GRANT_PERM:\s*([^\]]+)\]", ans))
    revoke_ms = list(re.finditer(r"\[REVOKE_PERM:\s*([^\]]+)\]", ans))
    list_ms = list(re.finditer(r"\[LIST_PERMS:\s*([^\]]+)\]", ans))
    ans = handle_grant_perm(ans, grant_ms, agent, perms)
    ans = handle_revoke_perm(ans, revoke_ms, agent, perms)
    ans = handle_list_perms(ans, list_ms, agent, perms)

    # ── Showbox-Tag-Extraktion ─────────────────────────────────────────────
    # Akzeptierte Tag-Formate (alle in EINER Liste, damit handle_showbox
    # die Reihenfolge der Agent-Ausgabe beibehält):
    #   1. <SHOWBOX[:name]>...</SHOWBOX>            — explizit
    #   2. [SHOWBOX[:name]]...[/SHOWBOX]            — explizit
    #   3. [SHOWBOX: ...]                           — nur Open-Tag (Referenz)
    #   4. [→ Showbox: name]{...}                   — Worker-Pflicht-Format
    #   5. [-> Showbox: name]{...}                  — ASCII-Variante
    # Format 4 + 5 ist der von allen Agent-Prompts (CoderAG, WriterAG, …
    # User-Mandat 2026-06-28) VERLANGTE Output-Stil. Ohne diese Regex
    # bleibt die Showbox-Payload als Rohtext im Chat stehen und die
    # Präsentation wird nie in showbox_presentations gespeichert.
    show_ms = []
    for t in ("SHOWBOX", "showbox"):
        for rx in (
            rf"<{t}(?::([a-zA-Z0-9_\-]+))?>([\s\S]*?)<\/{t}>",
            rf"\[{t}(?::([a-zA-Z0-9_\-]+))?\]([\s\S]*?)\[\/{t}\]",
        ):
            for m in re.finditer(rx, ans):
                show_ms.append((m.group(0), m.group(1) or "", m.group(2)))
        for m in re.finditer(rf"\[{t}:\s*(.*?)\]", ans, re.DOTALL):
            show_ms.append((m.group(0), "", m.group(1)))
    # → Showbox / -> Showbox Format mit {json}-Body (PFLICHTFORMAT für Worker)
    # Body ist ein {...} JSON-Block; wir erlauben beliebige whitespace + newlines
    # zwischen Tag und Body. Group 1 = name, Group 2 = JSON-Payload.
    for arrow in ("→", "->", "→", "->"):
        for m in re.finditer(
            rf"\[\s*{re.escape(arrow)}\s*[Ss]howbox:\s*([^\]\n]{{1,40}})\]\s*\{{([\s\S]*?)\}}\s*$",
            ans,
            re.MULTILINE,
        ):
            name = m.group(1).strip()
            payload = "{" + m.group(2) + "}"
            show_ms.append((m.group(0), name, payload))
    # Entferne Duplikate (gleicher Match kann über mehrere Regex-Pfade matchen)
    seen = set()
    deduped_show_ms = []
    for entry in show_ms:
        if entry[0] not in seen:
            seen.add(entry[0])
            deduped_show_ms.append(entry)
    show_ms = deduped_show_ms
    # ── SecurityAG-Audit: [SHOWBOX:] pre-dispatch (Refactor-Schritt 4) ──────
    # Permission-Check für SHOWBOX liegt in handle_showbox() selbst (analog
    # zu handle_crawl). Hier nur der SecurityAG-Audit-Hook. Bei
    # "showbox_write" oder "godmode" in perms audit, sonst "denied".
    for full, idx, payload in show_ms:
        pres_name = (idx or "<anonymous>").strip()
        if "showbox_write" in perms or "godmode" in perms:
            _audit_security(agent, perms, "showbox", pres_name, "allowed")
        else:
            _audit_security(agent, perms, "showbox", pres_name, "denied")
    ans = handle_showbox(ans, show_ms, agent=agent, perms=perms)
    ans = handle_desktop(ans, desktop_ms, agent, perms, wd)
    # ── Video-Tools ──
    sr_ms = list(re.finditer(r"\[VIDEO:SCREEN:\s*(.*?)\]", ans, re.DOTALL))
    mg_ms = list(re.finditer(r"\[VIDEO:MERGE:\s*(.*?)\]", ans, re.DOTALL))
    ed_ms = list(re.finditer(r"\[VIDEO:EDIT:\s*(.*?)\]", ans, re.DOTALL))
    ans = handle_screen_record(ans, sr_ms, agent, perms, wd)
    ans = handle_video_merge(ans, mg_ms, agent, perms, wd)
    ans = handle_video_edit(ans, ed_ms, agent, perms, wd)
    # ── SecurityAG-Audit: [BROWSER:] pre-dispatch (Refactor-Schritt 4) ─────
    browser_matches = list(re.finditer(r"\[BROWSER:\s*\]([\s\S]*?)\[/BROWSER\]", ans))
    for m in browser_matches:
        url = (m.group(1) or "").strip()[:200]
        if "write" in perms or "godmode" in perms:
            _audit_security(agent, perms, "browser", url or "<browser-block>", "allowed")
        else:
            _audit_security(agent, perms, "browser", url or "<browser-block>", "denied")
    return handle_browser(ans, browser_matches, agent, perms, wd)
