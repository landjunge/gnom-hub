#!/usr/bin/env python3
"""
BSA ORCHESTRATOR — @bsa Multi-Agent-Debatten-System
====================================================
Startet 4 Agenten-Personas, die ein Thema aus verschiedenen Rollen diskutieren:
- Argus (pro) — vertritt die These
- Kritik (contra) — hinterfragt und zeigt Risiken
- Hermes (researcher) — recherchiert Fakten und Quellen
- Valdis (validator) — wägt ab und validiert

Jeder Agent kann:
  * Argumentieren
  * Recherchieren (Web-Suche via Brave)
  * Crawler losschicken (Browser)
  * Prüfen und validieren

Nutzung:
  python bsa_orchestrator.py <topic>              # Volle Debatte
  python bsa_orchestrator.py <topic> --quick       # Nur 2 Agenten (schnell)
  python bsa_orchestrator.py <topic> --crawl       # Mit Web-Recherche
  python bsa_orchestrator.py --list                # Letzte Debatten anzeigen
  python bsa_orchestrator.py --status <debate_id>  # Status einer Debatte
"""

import json
import os
import sys
import requests
import time
from datetime import datetime

# ── Config ──
CORTEX_URL = "http://127.0.0.1:3002"
BRAVE_API = "https://api.search.brave.com/res/v1/web/search"
BRAVE_KEY = os.environ.get("BRAVE_API_KEY", "")

# ── Agenten-Personas ──
AGENT_PERSONAS = {
    "argus": {
        "name": "Argus",
        "emoji": "🛡️",
        "role": "pro",
        "system": (
            "Du bist Argus, der Pro-Argumentator . "
            "Deine Aufgabe: Vertrete die gegebene These mit sachlichen Fakten. "
            "Baue starke, logische Argumente. Zitiere Quellen wo möglich. "
            "Sei überzeugend aber nicht übertrieben."
        ),
    },
    "kritik": {
        "name": "Kritik",
        "emoji": "🔍",
        "role": "contra",
        "system": (
            "Du bist Kritik, der Contra-Analyst . "
            "Deine Aufgabe: Hinterfrage die These kritisch. Zeige Risiken, "
            "Schwachstellen und alternative Perspektiven. Sei konstruktiv, "
            "nicht destruktiv — jede Kritik soll Verbesserung bringen."
        ),
    },
    "hermes": {
        "name": "Hermes (Forscher)",
        "emoji": "📡",
        "role": "researcher",
        "system": (
            "Du bist Hermes, der Forschungs-Agent. Du durchsuchst das Internet, "
            "liest Dokumentationen und sammelst Fakten. Deine Aufgabe: Liefere "
            "harte Fakten, Daten und Quellen zum Thema. Zitiere alles mit Quellenangabe."
        ),
    },
    "valdis": {
        "name": "Valdis",
        "emoji": "⚖️",
        "role": "validator",
        "system": (
            "Du bist Valdis, der Validierer . "
            "Deine Aufgabe: Höre allen Argumenten zu. Wäge Pro und Contra ab. "
            "Prüfe auf logische Fehler, Bias und fehlende Information. "
            "Gib eine ausgewogene Bewertung ab."
        ),
    },
}


# ═══════════════════════════════════════════
# GNOM-HUB API HELPER
# ═══════════════════════════════════════════

def cortex_api(method: str, path: str, data: dict = None) -> dict:
    """Sende eine Anfrage an die Gnom-Hub API."""
    url = f"{CORTEX_URL}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=10)
        elif method == "POST":
            r = requests.post(url, json=data, timeout=120)  # langes Timeout für OpenRouter
        elif method == "PUT":
            r = requests.put(url, json=data, timeout=10)
        else:
            return {"error": f"Unbekannte Methode: {method}"}

        if r.status_code in (200, 201):
            return r.json()
        else:
            return {"error": f"HTTP {r.status_code}", "detail": r.text[:300]}
    except requests.exceptions.ConnectionError:
        return {"error": "Gnom-Hub nicht erreichbar", "hint": f"cortex_app läuft auf {CORTEX_URL}?"}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════
# WEB-RECHERCHE (via Brave Search API)
# ═══════════════════════════════════════════

def web_search(query: str, count: int = 5) -> list:
    """Suche via Brave Search API."""
    if not BRAVE_KEY:
        return [{"title": "Kein BRAVE_API_KEY", "snippet": "Setze BRAVE_API_KEY in Umgebungsvariablen"}]

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_KEY,
    }
    params = {"q": query, "count": count}

    try:
        r = requests.get(BRAVE_API, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            results = r.json().get("web", {}).get("results", [])
            return [
                {"title": res.get("title", ""), "url": res.get("url", ""),
                 "snippet": res.get("description", "")}
                for res in results[:count]
            ]
        return [{"error": f"Brave HTTP {r.status_code}"}]
    except Exception as e:
        return [{"error": str(e)}]


# ═══════════════════════════════════════════
# AGENTEN-AKTIONEN
# ═══════════════════════════════════════════

def agent_argumentieren(persona: dict, topic: str, context: str = "") -> dict:
    """Ein Agent argumentiert zum Thema via Gnom-Hub/OpenRouter."""
    prompt = (
        f"{persona['system']}\n\n"
        f"Das Thema: {topic}\n"
    )
    if context:
        prompt += f"\nKontext / bisherige Diskussion:\n{context}\n"
    prompt += f"\nFormuliere deine Position als {persona['role']}-Argument:"

    result = cortex_api("POST", "/api/openrouter/query", {
        "prompt": prompt,
        "agent_name": persona["name"],
        "max_tokens": 1500,
    })

    if result.get("success"):
        return {
            "agent": persona["name"],
            "role": persona["role"],
            "emoji": persona["emoji"],
            "content": result["response"],
            "model": result.get("model", "unknown"),
            "sources": [],
        }
    return {
        "agent": persona["name"],
        "role": persona["role"],
        "emoji": persona["emoji"],
        "content": f"[Fehler bei {persona['name']}]: {result.get('error', 'Unbekannt')}",
        "sources": [],
    }


def agent_recherchieren(persona: dict, topic: str) -> dict:
    """Ein Agent recherchiert Web-Quellen zum Thema."""
    print(f"\n  {persona['emoji']} {persona['name']} durchsucht das Web nach '{topic}'...")

    sources = web_search(topic)

    if sources and "error" not in sources[0]:
        context = "Gefundene Quellen:\n"
        for i, src in enumerate(sources, 1):
            context += f"{i}. {src.get('title', '—')} — {src.get('url', '—')}\n   {src.get('snippet', '')[:200]}\n\n"

        # Agent bewertet die Quellen
        prompt = (
            f"{persona['system']}\n\n"
            f"Du hast folgende Quellen zum Thema '{topic}' gefunden:\n\n{context}\n\n"
            f"Fasse die wichtigsten Erkenntnisse zusammen. Welche Quellen sind relevant? "
            f"Was sagen die Fakten?"
        )

        result = cortex_api("POST", "/api/openrouter/query", {
            "prompt": prompt,
            "agent_name": persona["name"],
            "max_tokens": 1500,
        })

        return {
            "agent": persona["name"],
            "role": persona["role"],
            "emoji": persona["emoji"],
            "content": result.get("response", "Keine Antwort") if result.get("success") else f"Fehler: {result.get('error')}",
            "model": result.get("model", "brave+openrouter"),
            "sources": [s.get("url", "") for s in sources if s.get("url")],
        }
    else:
        # Fallback: Nur via LLM recherchieren
        prompt = (
            f"{persona['system']}\n\n"
            f"Du sollst zum Thema '{topic}' recherchieren. "
            f"Da keine Web-Quellen verfügbar sind, nutze dein Wissen. "
            f"Sei ehrlich, wenn du etwas nicht weisst."
        )
        result = cortex_api("POST", "/api/openrouter/query", {
            "prompt": prompt,
            "agent_name": persona["name"],
            "max_tokens": 1500,
        })

        return {
            "agent": persona["name"],
            "role": persona["role"],
            "emoji": persona["emoji"],
            "content": result.get("response", "[Keine Recherche möglich]") if result.get("success") else f"Fehler: {result.get('error')}",
            "model": result.get("model", "openrouter"),
            "sources": [],
        }


# ═══════════════════════════════════════════
# DEBATTE AUSFÜHREN
# ═══════════════════════════════════════════

def run_debate(topic: str, quick: bool = False, crawl: bool = False) -> dict:
    """Führe eine vollständige @bsa-Debatte durch."""
    print(f"\n{'='*60}")
    print(f"  @bsa DEBATTE: {topic}")
    print(f"{'='*60}")

    # 1. Debatte in Gnom-Hub anlegen
    print("\n[1/5] Debatte in Gnom-Hub registrieren...")
    result = cortex_api("POST", "/api/bsa/debate", {
        "topic": topic,
        "initiator": "BSA-Orchestrator",
    })
    if "error" in result:
        print(f"  FEHLER: {result['error']}")
        print("  Tipp: Starte Gnom-Hub mit: cortex-hub")
        return result
    debate_id = result["debate"]["id"]
    print(f"  ✅ Debatte-ID: {debate_id}")

    all_arguments = []

    # 2. Welche Agenten?
    if quick:
        personas = [
            AGENT_PERSONAS["argus"],
            AGENT_PERSONAS["kritik"],
            AGENT_PERSONAS["valdis"],
        ]
        print(f"\n[2/5] Quick-Modus: {len(personas)} Agenten aktiviert")
    else:
        personas = list(AGENT_PERSONAS.values())
        print(f"\n[2/5] Volle Debatte: {len(personas)} Agenten aktiviert")

    # 3. Jeder Agent argumentiert
    print("\n[3/5] Agenten diskutieren...")
    context_log = ""

    for i, persona in enumerate(personas, 1):
        print(f"\n  ═══ {persona['emoji']} {persona['name']} ({persona['role']}) ═══")

        if crawl and persona["role"] == "researcher":
            # Forscher macht Web-Recherche
            arg = agent_recherchieren(persona, topic)
        else:
            # Normaler Agent argumentiert
            arg = agent_argumentieren(persona, topic, context_log)

        print(f"  Antwort: {arg['content'][:150]}...")

        # Argument an Gnom-Hub senden
        arg_result = cortex_api("POST", f"/api/bsa/debate/{debate_id}/arg", {
            "agent_name": arg["agent"],
            "role": arg["role"],
            "content": arg["content"],
            "sources": arg.get("sources", []),
        })

        all_arguments.append(arg)
        context_log += f"\n[{arg['agent']} / {arg['role']}]: {arg['content'][:500]}\n"
        time.sleep(0.5)  # Kurze Pause zwischen Agenten

    # 4. Zusammenfassung / Conclusio
    print(f"\n[4/5] Conclusio erstellen...")

    summary_prompt = (
        f"Du bist der BSA-Aggregator. Fasse die folgende Debatte zum Thema '{topic}' zusammen.\n"
        f"Erstelle eine ausgewogene Conclusio basierend auf allen Argumenten.\n"
        f"Benenne die stärksten Punkte jeder Seite und gib eine finale Bewertung.\n\n"
    )
    for a in all_arguments:
        summary_prompt += f"[{a['agent']} / {a['role']}]:\n{a['content'][:800]}\n---\n"
    summary_prompt += "\nWAS IST DIE CONCLUSIO?"

    summary = cortex_api("POST", "/api/openrouter/query", {
        "prompt": summary_prompt,
        "agent_name": "BSA-Aggregator",
        "max_tokens": 2000,
    })

    conclusion = summary.get("response", "[Keine Conclusio erstellt]")
    print(f"  Conclusio: {conclusion[:200]}...")

    # 5. Debatte abschliessen
    print(f"\n[5/5] Debatte abschliessen...")
    cortex_api("POST", f"/api/bsa/debate/{debate_id}/complete", {
        "conclusion": conclusion,
    })
    print(f"  ✅ Debatte {debate_id} abgeschlossen!")

    # Ergebnis ausgeben
    result = {
        "debate_id": debate_id,
        "topic": topic,
        "agents": len(all_arguments),
        "conclusion": conclusion,
        "arguments": [
            {"agent": a["agent"], "role": a["role"],
             "preview": a["content"][:200]} for a in all_arguments
        ],
    }

    return result


# ═══════════════════════════════════════════
# LISTE LETZTER DEBATTEN
# ═══════════════════════════════════════════

def list_debates():
    """Zeige die letzten Debatten."""
    result = cortex_api("GET", "/api/bsa/debates")
    if "error" in result:
        print(f"Fehler: {result['error']}")
        return

    debates = result.get("debates", [])
    if not debates:
        print("Keine Debatten gefunden.")
        return

    print(f"\n{'='*60}")
    print(f"  LETZTE DEBATTEN ({len(debates)} total)")
    print(f"{'='*60}")
    for d in debates[-10:]:  # Letzte 10
        print(f"\n  📌 {d.get('id', '—')}")
        print(f"     Thema: {d.get('topic', '—')}")
        print(f"     Status: {d.get('status', '—')}")
        print(f"     Agenten: {', '.join(d.get('agents_involved', ['—']))}")
        print(f"     Argumente: {len(d.get('arguments', []))}")
        conclusion = d.get('conclusion', '')
        if conclusion:
            print(f"     Conclusio: {conclusion[:100]}...")
        print(f"     Erstellt: {d.get('created', '—')}")


# ═══════════════════════════════════════════
# DEBATTEN-STATUS
# ═══════════════════════════════════════════

def show_status(debate_id: str):
    """Zeige Details einer Debatte."""
    result = cortex_api("GET", f"/api/bsa/debate/{debate_id}")
    if "error" in result:
        print(f"Fehler: {result['error']}")
        return

    d = result
    print(f"\n{'='*60}")
    print(f"  DEBATTE: {d.get('topic', '—')}")
    print(f"  ID: {debate_id}")
    print(f"  Status: {d.get('status', '—')}")
    print(f"  Initiiert von: {d.get('initiator', '—')}")
    print(f"  Erstellt: {d.get('created', '—')}")
    print(f"{'='*60}")

    if d.get('agents_involved'):
        print(f"\n  Agenten: {', '.join(d['agents_involved'])}")

    for i, arg in enumerate(d.get('arguments', []), 1):
        print(f"\n  [{i}] {arg.get('agent', '—')} ({arg.get('role', '—')}):")
        print(f"      {arg.get('content', '')[:300]}...")
        if arg.get('sources'):
            print(f"      Quellen: {', '.join(arg['sources'][:3])}")

    if d.get('conclusion'):
        print(f"\n  CONCLUSIO:")
        print(f"  {d['conclusion']}")


# ═══════════════════════════════════════════
# CLI MAIN
# ═══════════════════════════════════════════

def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        return

    if args[0] == "--list":
        list_debates()
        return

    if args[0] == "--status":
        if len(args) < 2:
            print("Nutze: python bsa_orchestrator.py --status <debate_id>")
            return
        show_status(args[1])
        return

    # Standard: Debatte starten
    topic = " ".join(args)
    quick = False
    crawl = False

    # Flags aus dem Topic entfernen
    clean_args = [a for a in args if not a.startswith("--")]
    topic = " ".join(clean_args) if clean_args else " ".join(args)

    if "--quick" in args:
        quick = True
    if "--crawl" in args:
        crawl = True

    result = run_debate(topic, quick=quick, crawl=crawl)

    if "error" not in result:
        print(f"\n{'='*60}")
        print(f"  ✅ @bsa DEBATTE ABGESCHLOSSEN!")
        print(f"  Thema: {result['topic']}")
        print(f"  Debatte-ID: {result['debate_id']}")
        print(f"  Agenten: {result['agents']}")
        print(f"{'='*60}")
        print(f"\n  CONCLUSIO:")
        print(f"  {result['conclusion']}")
        print(f"\n  Details: python bsa_orchestrator.py --status {result['debate_id']}")
        print(f"  API:     curl http://127.0.0.1:3002/api/bsa/debate/{result['debate_id']}")
    else:
        print(f"\n  ❌ Debatte fehlgeschlagen: {result.get('error', 'Unbekannt')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
