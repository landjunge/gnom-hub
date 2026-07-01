import json

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from gnom_hub.core.config import FRONTEND_DIR
from gnom_hub.db import delete_showbox_presentation, get_active_showbox, get_showbox_presentations, save_showbox_presentation, set_active_showbox

router = APIRouter()
THEMES_PATH = FRONTEND_DIR / "themes.js"

class ThemesData(BaseModel):
    content: str

class PresentationData(BaseModel):
    name: str
    slides: list
    sender: str = None
    buttons: list = None

class ActiveData(BaseModel):
    name: str

@router.get("/api/showbox/themes")
def get_themes():
    try:
        presentations = get_showbox_presentations()
        def get_order_key(p):
            name = p["name"]
            if name.startswith("Showbox ") and name[8:].isdigit():
                return (0, int(name[8:]))
            return (1, name)
        presentations.sort(key=get_order_key)
        slides_list = [p["slides"] for p in presentations]
        js_content = f"window.showboxes = {json.dumps(slides_list, indent=2)};"
        return Response(content=js_content, media_type="application/javascript")
    except Exception as e:
        return Response(content=f"// Error: {e}", media_type="application/javascript")

@router.post("/api/showbox/themes")
def save_themes(data: ThemesData):
    try:
        if THEMES_PATH.parent.exists():
            THEMES_PATH.write_text(data.content, encoding="utf-8")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/api/showbox/presentations")
def get_presentations():
    return get_showbox_presentations()

@router.post("/api/showbox/presentations")
def save_presentation(data: PresentationData):
    res = save_showbox_presentation(data.name, data.slides, data.sender, data.buttons)
    if res:
        set_active_showbox(data.name)
        return {"status": "ok", "presentation": res}
    raise HTTPException(status_code=500, detail="Failed to save presentation")

@router.delete("/api/showbox/presentations/{name}")
def delete_presentation(name: str):
    success = delete_showbox_presentation(name)
    if success:
        # If deleted active, reset active state
        if get_active_showbox() == name:
            set_active_showbox("")
        return {"status": "ok"}


@router.post("/api/showbox/llm_routing")
def push_llm_routing_showbox():
    """Generiert eine Showbox die live zeigt welcher Agent welches LLM nutzt.

    Wird vom Frontend regelmäßig aufgerufen (oder per Hotkey) und als
    "LLM-Routing" Presentation persistiert + aktiv gesetzt. So sieht der
    User sofort: alle 8 Agents + Provider + Model + Key-Validität.
    """
    from gnom_hub.db.state_repo import SQLiteStateRepository
    db = SQLiteStateRepository()
    kdb = db.get_value("llm_keys", {}) or {}
    adb = db.get_value("llm_agents", {}) or {}
    if not isinstance(kdb, dict):
        kdb = {}
    if not isinstance(adb, dict):
        adb = {}

    # Provider-Stats: wie viele Agents pro Provider
    provider_count: dict[str, int] = {}
    for v in adb.values():
        if isinstance(v, dict):
            p = v.get("provider", "?")
            provider_count[p] = provider_count.get(p, 0) + 1

    # Key-Validität pro Provider
    provider_valid: dict[str, tuple[bool, int]] = {}
    for v in kdb.values():
        if isinstance(v, dict) and v.get("provider"):
            p = v["provider"]
            cur = provider_valid.get(p, (False, 0))
            provider_valid[p] = (cur[0] or bool(v.get("valid")), cur[1] + 1)

    # ── Slide 1: Übersicht ──
    overview_lines = ["# 🧠 LLM-Routing — Live\n",
                      f"**{len(adb)} Agents** | **{len(kdb)} Provider-Keys** in DB\n"]
    for pvd, cnt in sorted(provider_count.items(), key=lambda x: -x[1]):
        valid, n_keys = provider_valid.get(pvd, (False, 0))
        status = "✅" if valid and n_keys > 0 else "❌"
        overview_lines.append(f"- {status} **{pvd}** — {cnt} Agent(s), {n_keys} Key(s)")
    overview_lines.append("\n*Auto-refresh: jeder Agent-Call aktualisiert die Stats.*")
    overview_slide = "\n".join(overview_lines)

    # ── Slide 2..N: ein Slide pro Agent ──
    agent_slides: list[str] = []
    ROLE_LABELS = {
        "soulag": "🧠 Orchestrator", "generalag": "👑 Coordinator",
        "watchdogag": "🛡️ Watchdog", "securityag": "🛡️ Security",
        "coderag": "💻 Code", "writerag": "✍️ Write",
        "researcherag": "🔍 Research", "editorag": "📝 Edit",
    }
    for ag_name, role in ROLE_LABELS.items():
        cfg = adb.get(ag_name, {})
        provider = cfg.get("provider", "—") if isinstance(cfg, dict) else "—"
        model = cfg.get("model", "—") if isinstance(cfg, dict) else "—"
        # Check if provider has valid key
        valid, n_keys = provider_valid.get(provider, (False, 0))
        status = "✅" if valid and n_keys > 0 else "❌"
        slide = (
            f"# {status} {ag_name}\n\n"
            f"**Rolle:** {role}  \n"
            f"**Provider:** `{provider}`  \n"
            f"**Model:** `{model}`  \n"
            f"**Key-Status:** {'valid' if valid else 'MISSING/INVALID'} ({n_keys} key(s))"
        )
        agent_slides.append(slide)

    # ── Live-Output-Slides: letzte echte LLM-Antwort pro Agent ──
    # Holt aus chat-Tabelle die letzten N non-user messages, mit Sender +
    # Provider-Info. So sieht der User im Showbox WAS der Agent tatsächlich
    # geantwortet hat — nicht nur die Konfiguration.
    live_slides: list[str] = []
    try:
        from gnom_hub.db.connection import get_db_conn
        from gnom_hub.soul.zwc_soul import strip_zwc
        with get_db_conn() as _conn:
            for ag_name, role in ROLE_LABELS.items():
                # Letzte Nachricht von diesem Agent
                r = _conn.execute(
                    "SELECT content, timestamp FROM chat "
                    "WHERE LOWER(sender) = ? AND content IS NOT NULL AND content != '' "
                    "ORDER BY id DESC LIMIT 1",
                    (ag_name.lower(),)
                ).fetchone()
                if not r:
                    continue
                content = strip_zwc(str(r["content"]))[:400]
                ts = str(r["timestamp"])[:19] if r["timestamp"] else "?"
                cfg = adb.get(ag_name, {})
                provider = cfg.get("provider", "—") if isinstance(cfg, dict) else "—"
                model = cfg.get("model", "—") if isinstance(cfg, dict) else "—"
                # Erste Zeile = "Headline", Rest = Antwort
                first_line = content.split("\n", 1)[0][:120]
                rest = content[len(first_line):].strip()[:280] if "\n" in content else ""
                slide = (
                    f"# 💬 {ag_name} — letzte Antwort\n\n"
                    f"**{role}** | `{provider}` / `{model}` | {ts}\n\n"
                    f"> {first_line}\n"
                )
                if rest:
                    slide += f"\n```\n{rest}\n```"
                live_slides.append(slide)
    except Exception as e:
        # Fallback: leere Live-Sektion statt Crash
        live_slides.append(f"# ⚠️ Live-Output\n\nFehler beim Laden: {e}")

    # ── Slide N+1: Troubleshooting ──
    trouble_lines = ["# 🔧 Troubleshooting\n",
                     "**Falls ein Agent `❌` zeigt:**\n",
                     "1. Check `/api/llm/keys` — ist der Provider-Key dort?\n"
                     "2. Check `~/Desktop/api_keys.txt` — Sync-Quelle\n"
                     "3. Save-Button (Header) drücken → schreibt alle pending Settings\n"
                     "4. Restart-Hook fügt fehlende Desktop-Keys automatisch wieder hinzu\n",
                     "**Endpoints:**\n",
                     "- `GET /api/llm/agents` — aktuelle Zuweisungen\n"
                     "- `GET /api/llm/keys` — Keys in DB (nach Sync)\n"
                     "- `POST /api/llm/agents {mode, group, dry_run:true}` — Vorschau\n"
                     "- `POST /api/llm/llm_routing_showbox` — diese Showbox refreshen"]
    trouble_slide = "\n".join(trouble_lines)

    slides = [overview_slide] + agent_slides + live_slides + [trouble_slide]

    # Persist + activate
    save_showbox_presentation("LLM-Routing", slides, sender="System", buttons=[
        {"label": "🔄 Refresh", "action": "refresh_llm_routing"},
        {"label": "💾 Save All", "action": "global_save"},
        {"label": "🧪 Test MiniMax-M3", "action": "test_minimax"},
    ])
    # Auto-activate NUR wenn keine pending Decision blockt. Trotzdem: die
    # aktive Showbox wird bei jeder Agent-Antwort mit <SHOWBOX>-Tag wieder
    # überschrieben — das ist das Standard-Verhalten. Wir aktualisieren die
    # LLM-Routing-Slides, lassen die Active-Showbox aber unangetastet
    # (User kann manuell in der Sidebar umschalten).
    # set_active_showbox("LLM-Routing")  # ← bewusst auskommentiert
    return {
        "status": "ok",
        "presentation": "LLM-Routing",
        "slides_count": len(slides),
        "providers": provider_count,
        "keys_count": len(kdb),
        "note": "Use sidebar to switch to LLM-Routing — auto-active is overridden by agent <SHOWBOX> tags",
    }


@router.post("/api/showbox/live_chat")
def push_live_chat_showbox(message: str = ""):
    """Eine dedizierte LIVE-CHAT Showbox.

    Wird vom Frontend (oder via /api/chat-Integration) aufgerufen um
    eine neue Slide mit dem letzten Agent-Output anzuhängen. Diese Showbox
    wird **immer** als active gesetzt, damit der User JEDE Agent-Antwort
    live mit Provider-Info sieht.
    """
    from gnom_hub.db.connection import get_db_conn
    from gnom_hub.db.state_repo import SQLiteStateRepository
    from gnom_hub.soul.zwc_soul import strip_zwc

    db = SQLiteStateRepository()
    adb = db.get_value("llm_agents", {}) or {}
    if not isinstance(adb, dict):
        adb = {}

    # Letzte Agent-Antwort aus chat-Tabelle
    latest = None
    try:
        with get_db_conn() as conn:
            latest = conn.execute(
                "SELECT sender, content, timestamp FROM chat "
                "WHERE sender != 'user' AND content IS NOT NULL AND content != '' "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
    except Exception as e:
        return {"status": "error", "info": str(e)}

    if not latest:
        return {"status": "ok", "info": "No agent messages yet"}

    sender = str(latest["sender"])
    raw = str(latest["content"])
    content = strip_zwc(raw)
    ts = str(latest["timestamp"])[:19] if latest["timestamp"] else ""
    cfg = adb.get(sender, {})
    provider = cfg.get("provider", "—") if isinstance(cfg, dict) else "—"
    model = cfg.get("model", "—") if isinstance(cfg, dict) else "—"

    # Existierende Live-Chat Showbox erweitern (sonst neu anlegen)
    from gnom_hub.db import get_showbox_presentations
    existing = next((p for p in get_showbox_presentations() if p.get("name") == "Live-LLM"), None)
    if existing:
        slides = list(existing.get("slides", []))
    else:
        slides = []

    # Neue Slide anhängen (max 20 behalten damit Showbox nicht explodiert)
    slide_md = (
        f"# 💬 {sender} via {provider}/{model}\n\n"
        f"**{ts}**\n\n"
        f"```\n{content[:600]}\n```"
    )
    slides.append(slide_md)
    slides = slides[-20:]

    # Erste Slide: Header mit "Watch Live!"
    if not existing:
        header = (
            "# 🔴 LIVE — LLM-Output\n\n"
            "Jede Agent-Antwort erscheint hier automatisch.\n"
            "Provider + Model werden aus der aktiven Routing-Config gelesen.\n"
            "Maximal 20 letzte Antworten sichtbar — ältere werden überschrieben."
        )
        slides.insert(0, header)

    save_showbox_presentation(
        "Live-LLM", slides, sender="System",
        buttons=[
            {"label": "🔄 Refresh", "action": "refresh_live_chat"},
            {"label": "🗑️ Clear", "action": "clear_live_chat"},
        ]
    )
    set_active_showbox("Live-LLM")
    return {
        "status": "ok",
        "presentation": "Live-LLM",
        "slides_count": len(slides),
        "latest_sender": sender,
        "provider": provider,
        "model": model,
    }


@router.post("/api/showbox/test_minimax")
def test_minimax_showbox():
    """Triggert einen echten MiniMax-M3 Call und zeigt Antwort in Showbox.

    So kann der User direkt in der Showbox SEHEN dass MiniMax-M3 funktioniert
    und welche Antwort kommt. Liefert konkrete Beweise dass das LLM aktiv ist.

    WICHTIG: ruft MiniMax DIREKT auf, nicht via ask_router() — denn wenn
    SoulAG grad auf einen anderen Provider gesetzt ist (z.B. durch Auto-Route
    oder Test) würde der ask_router auf dem landen statt auf MiniMax. Wir
    wollen hier den BEWEIS dass MiniMax-M3 funktioniert.
    """
    import time

    from gnom_hub.db import get_showbox_presentations
    from gnom_hub.db.state_repo import SQLiteStateRepository
    from gnom_hub.infrastructure.router.router import _build_sys
    from gnom_hub.infrastructure.router.router_call import _try_keys
    from gnom_hub.soul.zwc_soul import strip_zwc

    db = SQLiteStateRepository()
    provider = "minimax"
    model = "MiniMax-M3"
    kdb = db.get_value("llm_keys", {}) or {}
    sys_prompt = "Du bist SoulAG. Antworte kurz und konkret."
    user_prompt = "Antworte mit genau 3 Wörtern: 'MiniMax-M3 funktioniert'"
    sys_prompt = _build_sys("soulag", sys_prompt, "SoulAG")
    msgs = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Echter MiniMax-Call — direkt, ohne Routing
    t0 = time.time()
    try:
        ans = _try_keys(provider, model, kdb, msgs, "SoulAG")
    except Exception as e:
        return {"status": "error", "info": f"Direct MiniMax call failed: {e}"}
    lat = (time.time() - t0) * 1000
    if not ans:
        return {"status": "error", "info": "MiniMax-M3 returned empty (check key + endpoint)"}
    content = strip_zwc(str(ans))[:500]
    provider_used, model_used, latency = provider, model, lat

    # Showbox erstellen
    existing = next((p for p in get_showbox_presentations() if p.get("name") == "MiniMax-Live"), None)
    if existing:
        slides = list(existing.get("slides", []))
    else:
        slides = []

    slide_md = (
        f"# 🧪 MiniMax-M3 Test\n\n"
        f"**Provider:** `{provider_used}`  \n"
        f"**Model:** `{model_used}`  \n"
        f"**Latency:** {latency:.0f}ms\n\n"
        f"**Frage:** Antworte mit genau 3 Wörtern: 'MiniMax-M3 funktioniert'\n\n"
        f"**Antwort:**\n```\n{content}\n```\n\n"
        f"✅ Echtes LLM hat geantwortet."
    )
    slides.append(slide_md)
    slides = slides[-10:]
    if not existing:
        slides.insert(0, "# 🧪 MiniMax-M3 Live-Tests\n\nKlicke 'Test' im Header um einen echten LLM-Call zu triggern.")

    save_showbox_presentation("MiniMax-Live", slides, sender="System", buttons=[
        {"label": "🔄 Test", "action": "test_minimax"},
        {"label": "🗑️ Clear", "action": "clear_minimax"},
    ])
    set_active_showbox("MiniMax-Live")
    return {
        "status": "ok",
        "presentation": "MiniMax-Live",
        "provider": provider_used,
        "model": model_used,
        "latency_ms": latency,
        "content_preview": content[:100],
    }


# ── Clear-Endpoints (von Showbox-Buttons referenziert) ──
@router.post("/api/showbox/clear_live_chat")
def clear_live_chat():
    """Löscht die Live-LLM Showbox (reset auf nur Header-Slide)."""
    header = (
        "# 🔴 LIVE — LLM-Output\n\n"
        "Jede Agent-Antwort erscheint hier automatisch.\n"
        "Provider + Model werden aus der aktiven Routing-Config gelesen.\n"
        "Maximal 20 letzte Antworten sichtbar — ältere werden überschrieben."
    )
    save_showbox_presentation(
        "Live-LLM", [header], sender="System",
        buttons=[
            {"label": "🔄 Refresh", "action": "refresh_live_chat"},
            {"label": "🗑️ Clear", "action": "clear_live_chat"},
        ]
    )
    return {"status": "ok", "presentation": "Live-LLM", "slides_count": 1}


@router.post("/api/showbox/clear_minimax")
def clear_minimax():
    """Löscht die MiniMax-Live Showbox (reset auf nur Header-Slide)."""
    header = "# 🧪 MiniMax-M3 Live-Tests\n\nKlicke 'Test' im Header um einen echten LLM-Call zu triggern."
    save_showbox_presentation(
        "MiniMax-Live", [header], sender="System",
        buttons=[
            {"label": "🔄 Test", "action": "test_minimax"},
            {"label": "🗑️ Clear", "action": "clear_minimax"},
        ]
    )
    return {"status": "ok", "presentation": "MiniMax-Live", "slides_count": 1}


@router.get("/api/showbox/active")
def get_active():
    return {"active": get_active_showbox()}

@router.post("/api/showbox/active")
def set_active(data: ActiveData):
    set_active_showbox(data.name)
    return {"status": "ok"}
