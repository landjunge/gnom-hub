# Gnom-Hub ARCHITECTURE

> last_verified_against: a92ee3278fdb6544a50d8e0b0043d0068652062d
> last_verified_date: 2026-06-22
> status: active (verifiziert gegen src/ + routing.txt + CHANGELOG.md)
> previous_snapshot: docs/archive/2026-06-19-initial-snapshot/ARCHITECTURE.md

Diese Datei ist die **Source of Truth** für die Gnom-Hub-Architektur.
Sie wurde am 2026-06-22 verifiziert (Commit `a92ee3278`). Bei Drift
zwischen dieser Datei und dem Code gewinnt der Code — und diese Datei
muss nachgezogen werden.

Quickstart + Marketing: `README.md` / `README.de.md`.

---

## 1. Die 8 Gnome

`src/gnom_hub/core/agent_names.py:15-27` ist **frozen contract** — die
Namen, Farben und Avatare sind nicht verhandelbar.

| Name         | Kategorie | Farbe     | Rolle in einem Satz                              | Definiert in                  |
|--------------|-----------|-----------|--------------------------------------------------|-------------------------------|
| SoulAG       | System    | #00e5ff   | Default-Entry-Point für User-Chats, verteilt     | `core/agent_names.py:15-27`   |
| WatchdogAG   | System    | #00e5ff   | Recovery + Health-Checks                         | `core/agent_names.py:15-27`   |
| GeneralAG    | System    | #00e5ff   | Generische Admin-/Tool-Tasks                     | `core/agent_names.py:15-27`   |
| SecurityAG   | System    | #00e5ff   | Permissions-/Role-Management                     | `core/agent_names.py:15-27`   |
| WriterAG     | Worker    | #ffa500   | Texterstellung                                   | `core/agent_names.py:15-27`   |
| CoderAG      | Worker    | #ffa500   | Code-Generierung / -Refactor                     | `core/agent_names.py:15-27`   |
| ResearcherAG | Worker    | #ffa500   | Web-Recherche                                     | `core/agent_names.py:15-27`   |
| EditorAG     | Worker    | #ffa500   | Text-Überarbeitung / -Korrektur                  | `core/agent_names.py:15-27`   |

Farb-System: 4 System-Gnome teilen sich Cyan `#00e5ff`, 4 Worker-Gnome
teilen sich Orange `#ffa500`. Visuelle Trennung im Frontend.

Avatar-Mapping (z.B. SoulAG → showbox icon): `core/agent_names.py:43-52`.

---

## 2. Agent-Rollen im Detail

### SoulAG — Entry-Point für User-Chats
**Code-Pfad:** `src/gnom_hub/api/endpoints/chat_legacy.py:75`
(`@router.post("/api/chat")`).
Wenn der User-Call keinen `@<agent>`-Target enthält, geht der Chat
**immer** zu SoulAG (`chat_legacy.py:171-175`). SoulAG entscheidet
dann, ob die Anfrage an einen Worker (Writer/Coder/Researcher/Editor)
oder einen System-Agent delegiert wird.

### GeneralAG — Admin-/Tool-Tasks
Aufgerufen aus `src/gnom_hub/api/endpoints/admin_config.py:94` für
Generierungs-/Config-Tasks die keinen spezialisierten Worker haben.

### WatchdogAG — Recovery
Zwei Recovery-Loops laufen parallel (siehe §7).

### SecurityAG — Permissions
Permissions-Matrix (Role × Action). Implementierungsstand siehe §9.

### Worker (WriterAG / CoderAG / ResearcherAG / EditorAG)
Spezialisierte Auftragsbearbeitung. Werden über SoulAG-Delegation oder
direkten `@<agent>`-Override angesprochen.

---

## 3. LLM-Routing

**Konfigurationsdatei:** `config/routing.txt`

**Format:** `agent_name = provider | model`

**Aktueller Stand (alle 8 Agents identisch konfiguriert):**

```
soulag     = openrouter | meta-llama/llama-3.3-70b-instruct:free
watchdogag = openrouter | meta-llama/llama-3.3-70b-instruct:free
generalag  = openrouter | meta-llama/llama-3.3-70b-instruct:free
securityag = openrouter | meta-llama/llama-3.3-70b-instruct:free
writerag   = openrouter | meta-llama/llama-3.3-70b-instruct:free
coderag    = openrouter | meta-llama/llama-3.3-70b-instruct:free
researcherag = openrouter | meta-llama/llama-3.3-70b-instruct:free
editorag   = openrouter | meta-llama/llama-3.3-70b-instruct:free
```

Alle 8 Agents laufen aktuell über dasselbe OpenRouter-Free-Modell.
Per-Agent-Spezialisierung ist **möglich** (Format erlaubt es), aber
**nicht aktiv**.

---

## 4. Provider-Chain

Es gibt **zwei parallele Registries** für LLM-Provider:

### Registry 1: Provider-Implementierungen
**Datei:** `src/gnom_hub/infrastructure/llm/providers.py:23-474`
- Enthält `PROVIDERS` dict mit konkreten Client-Implementierungen
- Reihenfolge ist die **Fallback-Kette**

### Registry 2: Provider-Info (Metadaten)
**Datei:** `src/gnom_hub/core/provider_registry.py`
- Dataclass `ProviderInfo` mit alphabetisch ~30+ Einträgen
- Wird für UI-Listen / Discovery benutzt, **nicht** für Routing

### Tatsächliche Aufruf-Kette (effective)

1. **OpenRouterClient** — `src/gnom_hub/infrastructure/llm/openrouter.py:4-117`
   - Hat ein working-models-memory (welche Free-Models gerade antworten)
   - Fallback durch alle Free-Models wenn eins nicht antwortet
2. **OpenRouter Free Models** — `src/gnom_hub/core/config.py:98-106`
   - `OPENROUTER_FREE_MODELS` = 7 Modelle
3. **OllamaClient** — `src/gnom_hub/infrastructure/llm/ollama.py:7-31`
   - Letzter Fallback, lokal, kein API-Key nötig

Die effektive Kette ergibt sich aus `routing.txt` →
`providers.py` → `OpenRouterClient.ask` Fallback → `OllamaClient`.

Es gibt **keine** explizite `PROVIDER_CHAIN`-Konstante; die Kette ist
implizit aus den genannten Quellen zusammengesetzt.

---

## 5. Chat-Flow

**Entry-Point:** `src/gnom_hub/api/endpoints/chat_legacy.py:75`
(`POST /api/chat`)

**Dispatch-Logik:**

1. User schickt Chat ohne `@<agent>` → geht zu **SoulAG**
   (`chat_legacy.py:171-175`)
2. User schickt Chat mit `@<agent>` → direkter Override zum genannten
   Agent
3. SoulAG analysiert Anfrage → delegiert ggf. an Worker (WriterAG /
   CoderAG / ResearcherAG / EditorAG) oder System-Agent (GeneralAG /
   WatchdogAG / SecurityAG)

**Helper-Funktion für Dispatch:**
`chat_legacy.py:132-176` (komplette Dispatch-Logik)

---

## 6. Backend-Topologie

### FastAPI-App
**Datei:** `src/gnom_hub/api/app.py` (1-292)

- **Lifespan-Handler:** `app.py:1-292` — startet beim Boot:
  - Recovery+Watchdog-Loop (siehe §7)
  - Pulse-Thread (siehe §7)
  - Frontend-Mount (Avatare + /static)
- **Index-Route:** `app.py:289-292` → serviert `index.html`
- **Static-Mount:** `app.py:268-273`

### Router-Wiring
**Top-Level:** `src/gnom_hub/api/router.py:1-5` (ApiRouter-Wrapper)

**Endpoint-Inklusionen:** `src/gnom_hub/api/endpoints/router.py:1-22`
- Sammelt alle `@router.post(...)`-Endpoints
- Mountet sie unter dem ApiRouter

### Module unter `src/gnom_hub/api/endpoints/`
- `chat_legacy.py` — Chat-Endpoint (§5)
- `admin_config.py` — Admin-Config-Tools (ruft GeneralAG:94)
- Weitere Endpoints siehe `endpoints/router.py`

---

## 7. Recovery-Loops (Defense-in-Depth)

**Wichtige Klärstellung:** Es laufen **zwei** Recovery-Loops parallel,
nicht einer. Dies wurde im vorherigen Drift-Bericht
(`docs/COMPLETE_SYSTEM_ANALYSIS.md`) falsch dargestellt — korrigiert
am 2026-06-22.

### Loop 1 — Hauptloop (häufig)
**Datei:** `src/gnom_hub/api/app.py:28-132`
- **Intervall:** alle **30 Sekunden**
- **Aufruf:** `recover_stuck_messages()` direkt
- **Lebenszyklus:** gestartet im `lifespan` von FastAPI

### Loop 2 — Pulse-Throttle (seltener)
**Datei:** `src/gnom_hub/infrastructure/pulse.py:58-77`
- **Intervall:** alle **5 Minuten** via `_maybe_recover_stuck`
- **Aufruf:** `recover_stuck_messages()` mit Throttle
- **Lebenszyklus:** Pulse-Thread gestartet in `app.py:237-238`
  (`start_pulse()`)

### Was macht `recover_stuck_messages()`?
**Definition:** `src/gnom_hub/agents/swarm/swarm_comms.py:725`
Setzt hängende Swarm-Messages auf einen Fehlerstatus zurück, damit
sie nicht ewig im "running"-State bleiben.

### Warum zwei Loops?
- Loop 1 fängt **schnell** die meisten Stuck-Messages (30s).
- Loop 2 ist ein **Sicherheitsnetz** für Edge-Cases, in denen Loop 1
  übersprungen wurde (z.B. während Watchdog-Restart). Throttle
  verhindert Last-Spitzen.

---

## 8. Frontend-Pfade

### Was vom Backend serviert wird

**Root-Level (statisch):**
- `index.html` — Hauptseite, von `app.py:289-292` geroutet
- `demo.html` — Demo-Showcase

**Static-Mount:** `src/gnom_hub/frontend/` unter `/static/`
(`app.py:268-273`). Avatare aus `agent_names.py:43-52` werden hier
gemountet.

### Wo der HTML/JS/CSS-Code liegt
- `index.html`, `demo.html` — direkt im Repo-Root
- `src/gnom_hub/frontend/` — modulare Frontend-Komponenten, JS, CSS
  (genauer Pfad-Baum: `ls src/gnom_hub/frontend/`)

---

## 9. Permissions / Security

### Was real existiert
- Permissions-Matrix wird über `SecurityAG` exposiert
- Aktuelle Implementierungsdetails: siehe `SecurityAG`-Spezialisierung
  und Module unter `src/gnom_hub/api/endpoints/`

### Was NICHT als Implementierung existiert
- `docs/archive/2026-06-19-initial-snapshot/security-agent-konzept.md`
  ist ein **Konzeptpapier** vom 19.06.2026. Es beschreibt die geplante
  Architektur des SecurityAG. Es ist **NICHT** die fertige
  Implementierung. Vor jeder Code-Änderung am SecurityAG gegen den
  aktuellen Code verifizieren — nicht gegen das Konzept.

---

## 10. Test-Landschaft

**Test-Count (verifiziert):**
```
PYTHONPATH=src python3.10 -m pytest --collect-only -q --ignore=tests/integration
→ 593 tests collected in 177.83s (0:02:57)
```
(Quelle: `plan_dd312c4e/ssot-architecture-doc` Run vom 2026-06-22;
**nicht erneut ausführen** — Wert ist verifiziert.)

### Pre-existing Failures (NICHT durch diese Doku verursacht)
- FAISS / Numpy-bezogene Tests (Plattform-/Dependency-Issues)
- `/private/var`-Pfad-Validierungstests (macOS-spezifisch)
Diese Failures sind **nicht** durch ARCHITECTURE.md-Refactors
verschuldet — sie waren vor jedem Refactor schon rot.

---

## 11. Was diese Doku NICHT abdeckt

Ehrliche Lücken:

1. **Vollständiger Endpoint-Katalog.** Diese Doku nennt die wichtigsten
   Endpoints (`chat_legacy`, `admin_config`). Eine vollständige Liste
   steht in `src/gnom_hub/api/endpoints/router.py:1-22` und sollte
   ggf. in einer separaten Datei (`docs/API.md`) erfasst werden.
2. **DB-Schema.** Welche Tabellen, welche Felder, welche Indices —
   siehe `data/`-Verzeichnis und ggf. `docs/schemas/`. Aktuell **nicht**
   in dieser Doku.
3. **Frontend-Komponenten-Baum.** `src/gnom_hub/frontend/` ist ein
   Verzeichnis, aber welche Komponente was tut, ist hier nicht
   dokumentiert.
4. **Deployment.** `install.py`, `run.sh`, `PRE_PUSH_CHECKLIST.md`
   beschreiben den Setup, aber Produktiv-Deployment-Architektur
   (Reverse-Proxy, SSL, Backups) liegt außerhalb dieser Doku.
5. **Provider-API-Keys.** Welche Keys in welcher Env-Var erwartet
   werden — siehe `config/` und `core/config.py`. Secrets selbst
   stehen **nicht** in dieser Doku und sollten es auch nie.

### Empfohlene nächste Schritte
- `docs/API.md` aus `endpoints/router.py` extrahieren
- `docs/DATA_MODEL.md` aus `data/` ableiten
- `docs/FRONTEND.md` aus `src/gnom_hub/frontend/` ableiten
- Frontend-Architektur-Diagramm (ASCII oder visual-page)

---

## Anhang: Verifikations-Trail

| Datum       | Commit   | Was geprüft                                         |
|-------------|----------|-----------------------------------------------------|
| 2026-06-22  | a92ee3278| agent_names.py, chat_legacy.py, app.py, pulse.py,   |
|             |          | providers.py, openrouter.py, ollama.py,             |
|             |          | config.py, routing.txt                              |

Drift-Befunde aus diesem Lauf:
- **ZWEI** Recovery-Loops (korrigiert gegen vorherigen Bericht, der
  nur einen nannte)
- OpenRouter + OpenRouter-Free-Models + Ollama = effektive Kette
- Keine `PROVIDER_CHAIN`-Konstante; Kette ergibt sich implizit

Frühere Snapshots:
- `docs/archive/2026-06-19-initial-snapshot/ARCHITECTURE.md` — Stand
  vor dem 19.06.→22.06.-Refactor, NICHT synchron mit Code.
- `docs/archive/2026-06-22-failed-analysis/COMPLETE_SYSTEM_ANALYSIS.md`
  — Analyse mit 9 Faktenfehlern (Drift-Bericht aus plan_0578567a).