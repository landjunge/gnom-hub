# 🔐 Gnom-Hub Security Agent — Architektur-Entwurf

**Datum:** 14. Mai 2026  
**Status:** Konzept  

---

## Grundprinzip

> Ohne Genehmigung des Security Agents passiert **nichts**.

Jede Aktion eines Agents durchläuft den Security Agent bevor sie ausgeführt wird. Er ist die letzte Instanz — kein Output, kein File-Write, kein Tool-Call geht an ihm vorbei.

```
Agent → Aktion geplant → Security Agent prüft → ✅ Freigabe / ❌ Blockiert
```

---

## Security Levels (SEC 1–5)

### SEC 1 — Frei (Grün)
**Keine Genehmigung nötig. Automatisch durchgelassen.**

| Erlaubt | Beispiele |
|---|---|
| Chat lesen | `war_room_read()` |
| Eigenen Status setzen | `set_agent_status("online")` |
| Eigene Memory lesen | `get_memory(self)` |
| System-Stats abfragen | `get_system_stats()` |
| Agent-Liste lesen | `list_all_agents()` |

> **Regel:** Nur lesende Operationen auf eigene Daten.

---

### SEC 2 — Normal (Blau)
**Auto-Genehmigung mit Logging. Security wird informiert, greift nur bei Anomalie ein.**

| Erlaubt | Beispiele |
|---|---|
| In War Room schreiben | `war_room_chat(msg)` |
| Eigene Memory schreiben | `save_to_memory(self, content)` |
| Eigene Memory ändern | `update_memory(self, id, content)` |
| Eigene Memory löschen | `delete_memory(self, id)` |

> **Regel:** Schreibende Operationen auf eigene Daten. Security loggt mit und prüft auf:
> - Persona-Drift (RPG-Sprache, Lore-Trigger)
> - Spam (>5 Nachrichten/Minute)
> - Content-Größe (>2000 Zeichen → Warnung)

**Bei Anomalie:** Automatisch hochgestuft auf SEC 3.

---

### SEC 3 — Sensibel (Gelb)
**Explizite Genehmigung durch Security Agent erforderlich. Agent wartet auf Freigabe.**

| Aktion | Warum sensibel |
|---|---|
| Fremde Memory lesen | `get_memory(other_agent)` — Datenschutz |
| Fremde Memory ändern | `update_memory(other, ...)` — Manipulation |
| Agent anstupsen | `nudge_agent(other)` — Kann Kaskaden auslösen |
| Job verteilen | `distribute_job(...)` — Beeinflusst andere Agents |
| Chat zusammenfassen | `summarize_chat()` — Kann Kontext verfälschen |

> **Regel:** Aktionen die andere Agents betreffen. Security prüft:
> - Ist der Empfänger valide?
> - Ist der Inhalt sachlich und aufgabenbezogen?
> - Gibt es einen Loop? (Agent A stupst B, B stupst A)

**Timeout:** Keine Antwort in 10s → Blockiert.

---

### SEC 4 — Kritisch (Orange)
**Genehmigung durch Security Agent + Bestätigung durch User erforderlich.**

| Aktion | Warum kritisch |
|---|---|
| `write_file(path, content)` | Dateisystem-Zugriff |
| `run_command(cmd)` | Shell-Zugriff |
| `execute_code(code)` | Beliebiger Code |
| Fremde Memory komplett löschen | `clear_agent_memory(other)` |
| Neuen Agent erstellen | `create_agent(...)` |
| Agent löschen | `delete_agent(...)` |

> **Regel:** Destruktive oder irreversible Aktionen. Security prüft:
> - **Pfad-Whitelist:** Nur in erlaubten Verzeichnissen schreiben
> - **Command-Blacklist:** Kein `rm -rf`, kein `sudo`, kein Netzwerk
> - **Code-Scan:** Kein `eval()`, kein `exec()`, kein `import os`
> - **Sandbox:** Dateien nur in `/output/<agent_name>/`

**User-Bestätigung:** Push-Notification oder War Room Prompt.

---

### SEC 5 — Gesperrt (Rot)
**Immer blockiert. Keine Ausnahmen. Kein Override.**

| Aktion | Warum gesperrt |
|---|---|
| Security Agent modifizieren | Selbstschutz |
| Security-Regeln ändern | Selbstschutz |
| Security Agent löschen | Selbstschutz |
| System-Prozesse killen | `kill_by_port()`, `restart_gnom_hub()` |
| Netzwerk-Zugriff (extern) | Kein Internet für Agents |
| Andere Agents' Prompts ändern | `set_agent_role()` ohne User |

> **Regel:** Aktionen die das System selbst gefährden. Nur der User (Daniel) kann diese Aktionen manuell über das Admin-Panel ausführen.

---

## Architektur

```
┌─────────────────────────────────────────────┐
│                   USER                       │
│          (einziger SEC 5 Override)            │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│           SECURITY AGENT                     │
│  ┌─────────────────────────────────────┐     │
│  │ SEC 1: Auto-Pass (lesend)           │     │
│  │ SEC 2: Auto-Pass + Log (eigene)     │     │
│  │ SEC 3: Genehmigung (fremde)         │     │
│  │ SEC 4: Genehmigung + User (system)  │     │
│  │ SEC 5: Immer blockiert              │     │
│  └─────────────────────────────────────┘     │
│                                              │
│  Anomalie-Erkennung:                         │
│  • Persona-Drift-Scanner                     │
│  • Rate-Limiter                              │
│  • Loop-Detection                            │
│  • Content-Policy                            │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
┌────────┐  ┌──────────┐  ┌───────────┐
│ Agent A │  │ Agent B  │  │ Agent C   │
│ (Tools) │  │ (Tools)  │  │ (Tools)   │
└────────┘  └──────────┘  └───────────┘
```

## Persona-Drift-Scanner (SEC 2 Anomalie)

Prüft jeden Chat-Output auf:

```python
BLOCKED_PATTERNS = [
    r'\*[^*]+\*',           # Emotes: *schwebt herbei*
    r'König|Königin|Thron',  # Lore-Trigger
    r'Schwert|Rüstung|Helm', # RPG-Begriffe
    r'Feenreich|Zauber',     # Fantasy-Begriffe
    r'mein Lieber|Geselle',  # Persona-Sprache
]
```

**Bei Match:** Output blockiert, Agent bekommt Warnung:
> "Deine Antwort enthält Persona-Sprache. Formuliere sachlich."

---

## Regeln für den Security Agent selbst

1. **Keine Persona.** Kein Name, keine Persönlichkeit, kein Humor.
2. **Nur Regeln.** Kein LLM für Entscheidungen — reine Pattern-Matching + Whitelist-Logik.
3. **Kein eigener Memory.** Speichert nur Logs, keine "Erfahrungen".
4. **Nicht ansprechbar.** Agents können nicht mit dem Security Agent chatten.
5. **Unveränderbar.** Nur der User kann die Regeln anpassen (SEC 5).

---

*Konzept — bereit zur Implementierung wenn die Agent-Tools kommen.*
