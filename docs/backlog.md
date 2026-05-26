# 📋 Gnom-Hub: Konsolidiertes Backlog & Roadmap

Dieses Dokument konsolidiert die kritischen Schwachstellen, offenen Fragen und Verbesserungsvorschläge aus den AI-Analysen (ChatGPT, Claude) und übersetzt sie in konkrete, minimalistische Lösungen.

---

## 🔍 1. README & Positioning (Der "Killer-Usecase")
**Kritik:** Das README wirkt noch zu ideologisch. Einem externen Entwickler fehlt der "Killer-Usecase" und ein brutaler Vorführeffekt.
**Lösungen:**
- [ ] **Concrete Showcases dokumentieren:** 3 konkrete lokale Usecases (z. B. "Lokale Codebase-Governance", "Zero-Trust Web-Recherche", "Projekt-DevOps-Assistent") im README ergänzen.
- [ ] **Vergleichstabelle (Anti-Bloat-Story):**
  | Feature | Gnom-Hub | CrewAI / AutoGen |
  | :--- | :--- | :--- |
  | **Code-Volumen** | ~1800 Zeilen (55 Dateien) | >100.000 Zeilen |
  | **Setup-Zeit** | < 1 Minute (nativ) | > 10 Minuten + Docker |
  | **Modul-Limit** | Streng max. 40 Zeilen | Unbegrenzt (monolithisch) |
  | **Topologie** | Fest (8 Agenten, stabil) | Dynamisch (schwer debuggbar) |
  | **Offline-Fähigkeit** | 100% lokal first | Cloud-lastig |

---

## 🛡️ 2. Sicherheits- & Sandbox-Verfeinerung
**Kritik:** Isolation der Sandbox und Steuerung von Berechtigungen müssen transparenter und robuster sein (Docker Ephemerality, Timeouts).
**Lösungen:**
- [ ] **Docker Sandbox Ephemerality:** Sicherstellen, dass Playwright-Container nach der Ausführung per `--rm` automatisch gelöscht werden (kein Malware-Persistence in `/tmp`).
- [ ] **Browser Session Timeout:** Timeout für Browser-Aufrufe standardmäßig auf 30 Sekunden begrenzen, um Hänger oder Missbrauch zu verhindern.
- [ ] **Zero-Trust Capability Whitelist:** Einführung eines granulareren Berechtigungssystems (z. B. `[WRITE:file]`, `[BROWSER:url]`, `[SHELL:cmd]`) statt globalem "Godmode/Run".

---

## 🔄 3. Swarm-Stabilität & Loop-Prävention
**Kritik:** Gefahr von unendlichen Agent-to-Agent Kaskaden (z. B. GeneralAG ⇆ CoderAG) und Prompt-Race-Conditions bei schnellen Preset-Wechseln.
**Lösungen:**
- [ ] **Max @mention Tiefe:** Ein Zähler im Nachrichten-Payload (z. B. `mention_depth`), der nach maximal 3 Kaskaden weitere automatische Mentions unterbindet.
- [ ] **Globaler Job-Timeout:** Ein automatischer Background-Watcher, der blockierte oder unendliche Jobs nach 5 Minuten hart per `@free` terminiert.
- [ ] **Preset Transaction Lock:** SQLite-Transaktionen (`BEGIN IMMEDIATE TRANSACTION`) bei Preset-Wechseln nutzen, um Race-Conditions mit noch laufenden Worker-Tasks zu verhindern.

---

## 📊 4. Architektur & Observability
**Kritik:** Es fehlen grafische Datenflüsse und tiefere Metriken für Swarm-Interaktionen.
**Lösungen:**
- [ ] **Architektur-Diagramm (Mermaid) im README:** Einbetten eines klaren Flussdiagramms, das das Zusammenspiel der 4 System- und 4 Worker-Agenten zeigt.
- [ ] **Swarm-Aktivitätsgraph im Dashboard:** Visualisierung im Bento-Grid, welcher Agent gerade mit wem kommuniziert (z. B. pulsierender Link zwischen GeneralAG und CoderAG).
- [ ] **Agenten-Paar-Fehlerraten:** Erfassung von Abbrüchen oder Verweigerungen (z. B. SecurityAG verweigert CoderAG-Befehl).

---

## 🧠 5. SoulAG Gedächtnis-Hierarchie
**Kritik:** Unterschiedliche Kontext-Prioritäten verschwimmen im Flach-Retrieval.
**Lösungen:**
- [ ] **Hierarchische Memory-Ebenen:** Aufteilung der Wissensbasis in:
  1. *Session:* Kurzzeit-Fakten (aktueller Chat, hohe Priorität, flüchtig).
  2. *Project:* Projekt-spezifische Erkenntnisse (mittlere Priorität, mittlere Lebensdauer).
  3. *User:* Globale Nutzer-Vorlieben und Schreibstile (dauerhaft).
