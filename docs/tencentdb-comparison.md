# TencentDB Agent Memory — Fit-Analyse für gnom-hub

**Status:** Entwurf
**Branch:** `experimental/tencentdb-agent-memory` im Fork (`/Users/landjunge/gnom-hub-fork/`)
**Geschrieben:** 2026-06-29
**Quellen:** `tencentdb-agent-memory/README.md`, `index.ts`, `openclaw.plugin.json`, `SKILL.md`

---

## TL;DR

TencentDB-Agent-Memory ist ein reifer TypeScript-Plugin für OpenClaw / Hermes mit zwei Kernideen: **Memory-Layering** (L0-L3 Pyramide aus Conversation→Atom→Scenario→Persona) und **Context-Offload** (Tool-Logs in `refs/*.md` auslagern, kompakte Mermaid-Task-Canvas im Kontext halten, Drill-Down über `node_id`).

Für gnom-hub ist **genau eine** dieser Ideen unmittelbar portierbar und löst ein konkretes Problem: der **Context-Offload-Pattern** für die wachsenden Tool-Logs unserer 8 Agents. Alles andere (LLM-Extraktion, Persona-Pipeline, Hermes-Gateway, Hybrid-Retrieval) ist aus drei Gründen nicht sinnvoll adoptierbar: TypeScript-vs-Python, OpenClaw-Hook-Modell vs. FastAPI-Middleware, und gnom-hub hat bereits eine eigene Memory-Architektur in `~/.mavis/agents/*/memory/`.

**Empfehlung:** Offload-Pattern als reines Python-Modul `src/gnom_hub/memory/offload.py` portieren (~300 LOC, 1-2 Tage). Rest ignorieren.

---

## Was TencentDB-Agent-Memory konkret ist

- **Runtime-Stack:** TypeScript, läuft als Plugin auf OpenClaw (≥ 2026.3.13) oder Hermes. OpenClaw-Hooks (`before_prompt_build`, `agent_end`, `before_message_write`, `gateway_stop`) treiben die Lifecycle-Logik.
- **Speicher:** SQLite + `sqlite-vec` lokal, alternativ Tencent-Cloud-Vector-DB (TCVDB). Keine externe Abhängigkeit für Default-Betrieb.
- **Retrieval:** Hybrid — BM25 (jieba für zh, en-tokenizer) + Vektor + Reciprocal-Rank-Fusion.
- **Memory-Pyramide:**
  - **L0** Conversation-Rohdaten als JSONL
  - **L1** Atomic Facts via LLM-Extraktion (alle N Turns, default 5), mit Dedup via Vektor-Ähnlichkeit
  - **L2** Scenario-Blöcke als Markdown (LLM-aggregiert, N=50 Trigger)
  - **L3** Persona als `persona.md` (LLM-synthetisiert, N=50)
- **Drill-Down:** Jede obere Schicht verlinkt über `node_id`/`result_ref` deterministisch zurück zur Rohschicht. Keine irreversiblen Kompressionen.
- **Context-Offload (separates Subsystem, default aus):**
  - Tool-Logs werden nach `refs/*.md` ausgelagert sobald Kontext-Ratio 0.5 (mild) bzw. 0.85 (aggressiv) überschreitet.
  - Im Kontext bleibt nur eine Mermaid-Graph mit `node_id`-annotierten Knoten.
  - Bei Bedarf greift der Agent per `node_id` auf die Rohdatei zu — "vollständige Rückverfolgbarkeit, kompakte Repräsentation".
- **Auto-Recall:** Im `before_prompt_build`-Hook werden basierend auf User-Prompt Top-5 L1-Atoms + L3-Persona-Block als `<relevant-memories>` ans System-Prompt prependet. Limit: 3 Tool-Calls/turn (tdai_memory_search + tdai_conversation_search zusammen).

---

## Gnom-Hub-Schmerzpunkte (relevant für Bewertung)

Aus Session-Historie und Memory-Topics:

1. **Delegation-Halluzination** — GeneralAG delegiert nicht zuverlässig an CoderAG (LLM halluziniert "erst Workspace prüfen" als Vorbedingung). Manchmal geht die Worker-Kette komplett verloren.
2. **Kontext-Overflow** — Lange CoderAG/WriterAG-Sessions akkumulieren Tool-Logs ohne Offload-Mechanismus. Nach ~20 Turns wird das System-Prompt zu groß, der Hub verliert Antwortqualität.
3. **Action-Handler-Fehler** — `[WRITE:.../pfad]`-Tags aus Agent-Outputs werden im Frontend-Response angezeigt, aber `process_actions` / `handle_write` führen sie nicht aus. Datei wird nicht geschrieben, obwohl Tag korrekt geparst wird.

Nicht-Speicher-Probleme (zur Abgrenzung): `MAX_DEPTH=3`, SIGHUP-Kill beim Launcher, sentence-transformers-Konflikt, install.py .env-Überschreibung. Diese sind alle bereits gefixt oder Code-spezifisch — kein Memory-Thema.

---

## Fit-Matrix pro Problem

| Problem | TencentDB-Lösung | Fit | Begründung | Empfehlung |
|---|---|---|---|---|
| **Delegation-Halluzination** | L3-Persona speichert erfolgreiche Routing-Patterns, L2-Scenario-Blöcke fassen wiederkehrende Workflows zusammen | 🟡 gering | TencentDB ist **reaktiv**: es erkennt Muster *nachdem* sie passiert sind. gnom-hubs Problem ist **in-flight**: GeneralAG halluziniert *während* der LLM-Generation. Persona-Memory würde nächstes Mal helfen, nicht dieses Mal. | **Nicht adoptieren.** Stattdessen deterministische Routing-Tabelle in `soulag_general`-Code einführen — Delegation als Daten, nicht als Prompt-Anweisung. |
| **Kontext-Overflow** | Context-Offload: `refs/*.md` + Mermaid-Canvas mit `node_id`-Drill-Down | 🟢 **stark** | Direkt passend. Genau das, was gnom-hub fehlt. Pattern ist host-neutral und in ~300 LOC Python portierbar. | **Adoptieren.** Reines Python-Modul `src/gnom_hub/memory/offload.py` + Mermaid-Generator + node_id-Resolver. Trigger: Token-Count > 50% Context-Window. |
| **Action-Handler-Fehler** | nichts — TencentDB hat keine Action-Handler-Abstraktion | 🔴 keiner | Das ist ein gnom-hub-spezifischer Bug in `src/gnom_hub/agent/action_handler.py` o.ä., nicht ein Memory-Problem. | **Separat debuggen.** Steht nicht in Verbindung mit Memory-Architektur. |
| **Memory-Layer-Architektur generell** | L0-L3 Pyramide mit HOT/MID/COLD-Trennung | 🟡 konzeptuell | gnom-hub hat bereits `MEMORY.md` (HOT), Topic-Files (Projekt), User-Memory (cross-project). TencentDBs Pyramid ist konzeptuell verwandt aber code-mäßig nicht portierbar (TS vs Python, Hook-basiert vs. Library). | **Dokumentieren, nicht implementieren.** Falls wir unsere Tier-Regeln formalisieren wollen: 1-Seite-Markdown mit "Was gehört in HOT vs Topic vs User-Memory" reicht. |

---

## Konkreter Plan: Context-Offload portieren

**Scope:** Nur den Offload-Subsystem-Teil, NICHT die Memory-Pyramide.

**Was wir bauen:**

1. `src/gnom_hub/memory/offload.py` — Kernklasse `ContextOffloader`
   - Hält ein Soft-Token-Budget (Default: 50% des `max_tokens` aus Config).
   - Bei `agent_end`-Hook: prüft kumulierte Tool-Outputs der aktuellen Session.
   - Wenn Budget überschritten: schreibt die ältesten Tool-Outputs nach `~/.gnom-hub/sessions/<session_id>/refs/<node_id>.md`, ersetzt sie im Kontext durch einen Mermaid-Knoten `N1["tool: bash, summary: ran pytest"]`.

2. `src/gnom_hub/memory/mermaid_canvas.py` — Generator für die Task-Canvas
   - Baut einen gerichteten Graphen: User→Agent→Tool→Result als Mermaid-`graph LR`.
   - Jeder Knoten hat `node_id` (UUID-Short).
   - Begrenzung: max 20 Knoten / 200 Tokens im injizierten Canvas-Block.

3. `src/gnom_hub/memory/node_resolver.py` — Lookup-Service
   - Beim Recall: wenn Agent `recall_node(node_id)` aufruft, lädt `refs/<node_id>.md` und gibt Inhalt zurück.
   - Optional: in den nächsten Prompt als `<expanded-context>` injiziert, mit `node_id`-Annotation.

4. Integration in `src/gnom_hub/agent/runner.py` oder equivalent:
   - Im Agent-Loop nach jedem Tool-Call: `offloader.maybe_offload(tool_output)`.
   - Vor dem nächsten LLM-Call: `offloader.inject_canvas(system_prompt)`.

**Aufwand:** ~300 LOC Python + ~150 LOC Tests. 1-2 Tage Arbeit.

**Risiko:** Niedrig. Offload ist additive Funktionalität, kann per Config-Flag `offload.enabled=false` deaktiviert werden. Kein Bruch bestehender Memory-Pfade.

**Was wir explizit NICHT mitnehmen:**

- LLM-gestützte L1/L2/L3-Extraktion (würde zusätzliche LLM-Calls pro Session erzeugen, ohne dass die 3 dokumentierten Probleme das verlangen)
- BM25/Vector-Hybrid-Retrieval (gnom-hub hat bereits FAISS bzw. TF-IDF-Fallback)
- Hermes-Gateway (Docker, eigener Service) — overkill
- Profile-Sync zu Tencent Cloud (Datenschutz + Kosten)

---

## Was diese Analyse NICHT abdeckt

- Performance-Benchmarks der Offload-Pipeline (müssten wir lokal messen, nicht aus README übernehmen)
- Multi-Session-Konsistenz (TencentDBs Persona aggregiert über Sessions; gnom-hub hat pro-Agent-Memory, anderer Scope)
- Hermes-spezifische Adapter (`hermes-plugin/`) — für gnom-hub irrelevant
- Docker-Build-Pipeline (`docker/`) — irrelevant

---

## Offene Fragen

1. **Wo wird Offload-Storage abgelegt?** `~/.gnom-hub/sessions/<id>/refs/` (analog TencentDB) oder `data/offload/<session_id>/` (gnom-hub-Standard-Pfad)?
2. **Wer ruft `recall_node` auf?** Aktuell hat gnom-hub kein Agent-Tool-Konzept wie OpenClaws `tdai_memory_search`. Müssen wir erst ein Tool-Registry-Konzept bauen, oder reicht eine Helper-Funktion die der Agent-Prompt kennt?
3. **Mermaid-Rendering im Frontend?** Aktuell rendert gnom-hub-Frontend Markdown, aber kein Mermaid. Falls wir Mermaid-Canvas injizieren, muss entweder das Frontend `mermaid.js` einbinden oder wir liefern nur den Plain-Text-Graph.
4. **Trigger-Schwelle:** TencentDB nutzt 50%/85% Context-Window. gnom-hubs Modelle haben verschiedene Limits (M3 hat typisch 200k). Über `cfg.max_tokens` konfigurierbar machen oder fester Default 50%?

---

## Decision

Wenn die 4 offenen Fragen mit Defaults beantwortet sind, ist das Modul in 1-2 Tagen baubar. Sonst: erst die Fragen klären, dann implementieren.

**Default-Antworten falls der User "mach einfach" sagt:**

1. `data/offload/<session_id>/refs/`
2. Tool-Registry light: `offload_recall(node_id)` als registriertes Agent-Tool in `tools/`
3. Frontend bekommt `<script src="mermaid.min.js">` eingebunden, Default aus (User kann in Settings aktivieren)
4. Default 50% via Config `offload.mild_ratio=0.5`

---

## Implementierungs-Erkenntnisse & nächste Priorität (Juni 2026)

Die selektive Portierung aus TencentDB-Agent-Memory hat sich bestätigt:

- Nur die **Context-Offload**-Säule (Mermaid-Task-Canvas + node_id-Drill-Down) war portierbar und sinnvoll.
- Umsetzung in Python: `offload.py` (341 LOC), `mermaid_canvas.py` (258 LOC), `node_resolver.py` (128 LOC).
- 14 neue Tests in `tests/test_offload.py` (alle grün).
- Wire-ins in `core/config.py`, `agents/actions/action_handlers.py`, `agents/agent_base.py`, `agents/tool_registry.py`.
- Neue Action/Tool: `[OFFLOAD_RECALL:node_id]`.
- Security-Hardening: 3-Layer-Path-Traversal-Defense, atomic writes via tmp+rename, Per-Session-Registry.
- Commit `d0f8e95` auf `experimental/tencentdb-agent-memory` (8 Files, bewusst ohne nested-git und ohne dieses Doc).

Die volle Memory-Pyramide bleibt bewusst außen vor (OpenClaw/TS-gebunden, nicht portierbar).

**Nächste Priorität: Deterministisches Delegation-Routing**
Dies ergänzt das neue node_id-basierte Offload-System ideal. Statt probabilistischer LLM-Delegation (klassische Halluzinationsquelle) wird ein explizites, verifizierbares Routing eingeführt (Capability-Graph / node_id-Regeln / Confidence-Schwellen / deterministische Fallbacks).

Das adressiert das fundamentale Action-Halluzinations-Problem **an der Wurzel** und ist komplett unabhängig von externen Memory-Lösungen. Es baut direkt auf dem gerade implementierten `node_resolver` auf und verstärkt den Offload-Effekt (sauberer Context + präzise Actions).

→ Separater Plan `deterministic-delegation-routing` folgt.