# Plan: deterministic-delegation-routing

**Ziel:**
Einführung eines deterministischen Routing-Layers, der auf dem neuen node_id-System und Context-Offload aufbaut, um LLM-basierte Delegations-Halluzinationen grundlegend zu reduzieren.

**Scope (MVP):**

- Neues Modul `agents/routing.py` mit deterministischem Routing + Capability-Matching
- Integration in `action_handlers.py` und `agent_base.py`
- Nutzung von `node_resolver.py` für node_id-basierte Regeln
- Einfache Capability-Deklaration per Config oder Decorator
- Confidence-Schwellen und explizite Fallback-Strategien
- 8–10 neue Tests (Unit + Integration)

**Nicht im Scope:**

- Komplexer Graph-Algorithmus
- Persistenz von Routing-Entscheidungen
- UI oder Visualisierung

**Erfolgskriterien:**

- Alle neuen Tests grün
- Keine Regression in der curated non-slow Suite
- Funktionsfähiger Use-Case mit `[OFFLOAD_RECALL:node_id]` + deterministischem Routing
- Routing-Entscheidungen vollständig nachvollziehbar