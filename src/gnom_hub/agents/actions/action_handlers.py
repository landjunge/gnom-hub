# action_handlers.py — Dispatcher für alle Action-Tags
import re

from gnom_hub.core.security.gatekeeper import verify_cmd, verify_write

from .action_browser import handle_browser
from .action_desktop import handle_desktop
from .action_exec import handle_crawl, handle_shell, handle_showbox
from .action_screenshot import handle_screenshot
from .action_verify import handle_verify
from .action_video import handle_screen_record, handle_video_edit, handle_video_merge
from .action_write import handle_read, handle_write


# ── Context-Offload Helpers (recovert aus experimental/tencentdb-agent-memory) ──
# Symbolischer Kurzzeitspeicher + node_id Drill-Down — siehe docs/tencentdb-comparison.md
def _maybe_offload_diff(before: str, after: str, tool_name: str, agent_name: str) -> None:
    """Context-Offload: schreibe das neu hinzugefügte Tool-Output-Stück auf Disk.

    Best-effort: wenn Offload deaktiviert ist oder was crasht, brechen wir
    den Agent-Loop nicht ab.
    """
    if not before or after == before or len(after) <= len(before):
        return
    try:
        from gnom_hub.core.config import Config as _Cfg
        if not getattr(_Cfg, "OFFLOAD_ENABLED", False):
            return
    except Exception:
        return
    try:
        from gnom_hub.memory.offload import (
            OffloadConfig as _OffCfg,
        )
        from gnom_hub.memory.offload import (
            get_offloader as _get_offloader,
        )
        _ocfg = _OffCfg(
            enabled=True,
            mild_offload_ratio=_Cfg.OFFLOAD_MILD_RATIO,
            aggressive_compress_ratio=_Cfg.OFFLOAD_AGGRESSIVE_RATIO,
            data_dir=_Cfg.OFFLOAD_DATA_DIR,
            max_tokens=_Cfg.OFFLOAD_MAX_TOKENS,
        )
        _off = _get_offloader(agent_name or "default", _ocfg)
        _new_tail = after[len(before):]
        if _new_tail.strip():
            _off.maybe_offload(tool_name=tool_name, content=_new_tail, summary=tool_name)
    except Exception:
        pass


def _handle_offload_recall(ans: str) -> str:
    """Behandle ``[OFFLOAD_RECALL:node_id]`` Action-Tags — erlaubt Agenten,
    einen ausgelagerten Tool-Output per node_id zurück in den Kontext zu holen.
    """
    pattern = re.compile(r"\[OFFLOAD_RECALL:\s*([a-fA-F0-9]+)\s*\]")
    if not pattern.search(ans):
        return ans

    def _resolve_node_text(node_id: str) -> str:
        from gnom_hub.memory.node_resolver import resolve_node
        for _sid in _candidate_session_ids():
            _content = resolve_node(node_id, _sid)
            if _content is not None:
                return _content
        return ""

    def _candidate_session_ids() -> list:
        from pathlib import Path as _P

        from gnom_hub.core.config import Config as _Cfg
        candidates: list[str] = ["default"]
        try:
            _data_root = _P(_Cfg.OFFLOAD_DATA_DIR)
            if _data_root.is_dir():
                for _child in _data_root.iterdir():
                    if _child.is_dir():
                        candidates.append(_child.name)
        except Exception:
            pass
        return candidates

    def _replace(match: re.Match) -> str:
        _node_id = match.group(1).lower()
        _content = _resolve_node_text(_node_id)
        if not _content:
            return (
                f"[System: Offload-Node '{_node_id}' nicht gefunden. "
                "Verwende [OFFLOAD_RECALL:<8-hex-chars>] mit der "
                "node_id aus der OFFLOAD-CANVAS.]"
            )
        _max_inline = 4096
        if len(_content) > _max_inline:
            _truncated = (
                _content[:_max_inline]
                + f"\n\n[truncated at {_max_inline} chars; "
                f"full content on disk for node {_node_id}]"
            )
        else:
            _truncated = _content
        return f"[Offload Recall node={_node_id}]\n{_truncated}\n[/Offload Recall]"

    return pattern.sub(_replace, ans)


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
        # ── Filename-Validierung (User-Mandat 2026-07-12 02:50 — LLM-Halluzination-Schutz) ──
        # LLM-Agenten (WatchdogAG/SecurityAG/ResearcherAG) produzieren manchmal
        # [WRITE: <scope-check-text>]-Tags mit dem GANZEN Scope-Check-Text als
        # Filename (z.B. "], 0 [READ:], 0 [RUN:], 0 research-triggers. Workspace
        # `default` STILL..."). Das Regex matcht den ersten `]` und nimmt den
        # ganzen Text als Pfad → Trash-Files/Dirs.
        # Schutz: Pfad muss
        #   1. < 200 Zeichen
        #   2. keine `[`, `]`, neue Zeilen, Backticks
        #   3. KEIN "Block-Wort" wie "kein", "trigger", "read", "run", "scope"
        #   4. (optional) Datei-Extension haben
        invalid = False
        if len(fn) > 200:
            invalid = True
            reason = "filename zu lang"
        elif any(c in fn for c in '[]\n\r\t`'):
            invalid = True
            reason = "ungültige Zeichen (Klammern/Backticks/Newlines)"
        elif any(w in fn.lower() for w in ['kein ', 'no ', 'trigger', 'read:', 'run:', 'scope', 'style-review', 'passiv']):
            invalid = True
            reason = "Filename sieht nach Scope-Check-Text aus, nicht nach Datei"
        if invalid:
            _audit_security(agent, perms, "write", fn[:80], "denied")
            ans = ans.replace(
                m.group(0),
                f"[System: {agent.get('name','?')} hat versucht, einen ungültigen Filename zu schreiben — {reason}. Aktion blockiert.]",
            )
            continue
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
            # Filename-Validierung (gleiche Logik wie oben — Schutz vor
            # LLM-Halluzination: WatchdogAG/SecurityAG packen Scope-Check-Text
            # in [WRITE:]-Tags → Trash-Dirs im Workspace. User-Mandat
            # 2026-07-12 02:50)
            invalid = False
            if len(fn) > 200:
                invalid = True
                reason = "filename zu lang"
            elif any(c in fn for c in '[]\n\r\t`'):
                invalid = True
                reason = "ungültige Zeichen"
            elif any(w in fn.lower() for w in ['kein ', 'no ', 'trigger', 'read:', 'run:', 'scope', 'style-review', 'passiv']):
                invalid = True
                reason = "Filename sieht nach Scope-Check-Text aus"
            if invalid:
                _audit_security(agent, perms, "write", fn[:80], "denied")
                ans = ans.replace(
                    m.group(0),
                    f"[System: {agent.get('name','?')} hat versucht, einen ungültigen Filename zu schreiben — {reason}. Aktion blockiert.]",
                )
                continue
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
            ans = ans.replace(m.group(0), "[Gatekeeper: Befehlsausführung verweigert.]")
    for m in re.finditer(r"\[DESKTOP:\s*(.*?)\]", ans, re.DOTALL):
        desktop_ms.append(m)
    # ── SecurityAG-Audit: [CRAWL:] pre-dispatch (Refactor-Schritt 4) ────────
    # Permission-Check für CRAWL liegt in handle_crawl() selbst; hier nur Hook
    # für SecurityAG-Audit. Bei "allowed"-Permission audit, sonst "denied".
    crawl_matches_pre = list(re.finditer(r"\[CRAWL:\s*(.*?)\]", ans))
    for m in crawl_matches_pre:
        url = m.group(1).strip()
        if "crawl" in perms or "godmode" in perms:
            _audit_security(agent, perms, "crawl", url, "allowed")
        else:
            _audit_security(agent, perms, "crawl", url, "denied")
    # ── Showbox-Tag-Extraktion (FIX C 2026-07-12: VOR handle_write verschoben) ─
    # Vorher lief handle_write zuerst → wenn [WRITE: <bad-filename>] Müll
    # produziert, wurde die Showbox nie persistiert. Nachher: Showbox wird
    # IMMER zuerst gespeichert, dann erst handle_write ausgeführt.
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
    # WICHTIG (Fix A, 2026-07-12): KEIN `$`-Anchor mehr — wenn das LLM nach dem
    # `}` noch was auf der gleichen Zeile schreibt ("Done ✓", "Datei gespeichert")
    # schlug der Match fehl und die Showbox wurde nicht persistiert. Reihenfolge
    # ist nicht greedy → erstes `}` matched, alles dahinter wird ignoriert.
    for arrow in ("→", "->", "→", "->"):
        for m in re.finditer(
            rf"\[\s*{re.escape(arrow)}\s*[Ss]howbox:\s*([^\]\n]{{1,40}})\]\s*\{{([\s\S]*?)\}}",
            ans,
        ):
            name = m.group(1).strip()
            payload = "{" + m.group(2) + "}"
            show_ms.append((m.group(0), name, payload))
    # → Showbox / -> Showbox Plain-Body-Pattern (Fix A, 2026-07-12) — analog zu
    # chat_legacy.py:_ARROW_SHOWBOX_PLAIN_RE. Header-only / ASCII-Box ohne
    # {...}-Body wird auch geparst (Plain-Text nach Header als Content).
    for arrow in ("→", "->", "→", "->"):
        for m in re.finditer(
            rf"\[\s*{re.escape(arrow)}\s*[Ss]howbox:\s*([^\]\n]{{1,40}})\]\s*(.*)",
            ans,
            re.DOTALL,
        ):
            name = m.group(1).strip()
            raw = m.group(2).strip()
            if not raw:
                # Header ohne Inhalt (Edge-Case) — als leere Slide speichern
                payload = ""
            elif raw.startswith("{"):
                # Schon JSON-Body → nicht doppelt wrappen
                payload = raw
            else:
                # Plain-Text-Body (ASCII-Box) → als einzelner Slide wrappen
                payload = raw
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
    for _full, idx, _payload in show_ms:
        pres_name = (idx or "<anonymous>").strip()
        if "showbox_write" in perms or "godmode" in perms:
            _audit_security(agent, perms, "showbox", pres_name, "allowed")
        else:
            _audit_security(agent, perms, "showbox", pres_name, "denied")
    ans = handle_showbox(ans, show_ms, agent=agent, perms=perms)
    ans = handle_write(ans, w_ms, agent, perms, bs_mode, wd)
    ans = handle_read(ans, r_ms, wd, perms, agent=agent)
    # Screenshots after writes so HTML exists on disk
    shot_ms = list(re.finditer(r"\[SCREENSHOT:\s*([^\]]+)\]", ans, re.IGNORECASE))
    if shot_ms:
        ans = handle_screenshot(ans, shot_ms, agent, perms, wd)
    verify_ms = list(re.finditer(r"\[VERIFY:\s*([^\]]+)\]", ans, re.IGNORECASE))
    if verify_ms:
        ans = handle_verify(ans, verify_ms, agent, perms, wd)
    ans = handle_shell(ans, sh_ms, agent, perms, bs_mode, wd)
    ans = handle_crawl(ans, crawl_matches_pre, agent, perms)
    # ── Permission-Tag-Extraktion (SecurityAG Kernrolle 1+2) ──────────────
    # Tag-Formate: [GRANT_PERM: agent=X path=Y ...], [REVOKE_PERM: ...], [LIST_PERMS: agent=X]
    # Handler in action_exec.py — Permission-Check passiert dort (db_write erforderlich).
    from .action_exec import handle_grant_perm, handle_list_perms, handle_revoke_perm
    grant_ms = list(re.finditer(r"\[GRANT_PERM:\s*([^\]]+)\]", ans))
    revoke_ms = list(re.finditer(r"\[REVOKE_PERM:\s*([^\]]+)\]", ans))
    list_ms = list(re.finditer(r"\[LIST_PERMS:\s*([^\]]+)\]", ans))
    ans = handle_grant_perm(ans, grant_ms, agent, perms)
    ans = handle_revoke_perm(ans, revoke_ms, agent, perms)
    ans = handle_list_perms(ans, list_ms, agent, perms)
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
    # ── Context-Offload: [OFFLOAD_RECALL:node_id] Action-Tag ─────────────
    # Agenten können ausgelagerte Tool-Outputs per node_id zurückholen.
    ans = _handle_offload_recall(ans)
    return handle_browser(ans, browser_matches, agent, perms, wd)
