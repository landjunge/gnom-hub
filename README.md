# 🧠 GNOM-HUB: The Autonomous God-Mode OS

![Gnom-Hub War Room](screenshot.png)

**Vergiss Frameworks, die dich in Boilerplate ersticken.** GNOM-HUB ist ein nacktes, ultra-radikales Multi-Agenten-Betriebssystem, das direkt auf deinem Rechner läuft und absolute Autonomie besitzt. 
Deine KI-Agenten chatten hier nicht nur – sie *sehen* deinen Bildschirm, steuern per PyAutoGUI deine Maus, schreiben ihren eigenen Code und versionieren jeden Atemzug vollautomatisch via Git. 
Abgesichert durch eine lokale Sandbox und orchestriert in einem cyberpunk-esken "War-Room", agiert die Schwarm-Intelligenz völlig selbstständig. 
Das Verrückteste daran? Jedes einzelne Modul – vom Backend-Router bis zum "Sehenden Agenten" – ist strikt auf **maximal 40 Zeilen Code** komprimiert. 
Du brauchst keine Minuten für einen Build: Setup ausführen, Hub starten, und die KI übernimmt das Steuer.

---

## 🚀 Schnellstart (In 10 Sekunden online)

```bash
# Repo klonen & Abhängigkeiten installieren
git clone https://github.com/landjunge/gnom-hub.git
cd gnom-hub
pip install -e .

# Hub starten & KI von der Leine lassen
gnom-hub
```

Danach öffne **http://127.0.0.1:3002** in deinem Browser. Willkommen im War-Room.

---

## 🔥 Warum Gnom-Hub das Spiel verändert

Was den Gnom-Hub von monströsen Frameworks wie Langchain oder AutoGen unterscheidet, ist seine **kompromisslose, nackte Effizienz**:

1. **"God-Mode" Desktop & Vision:** Die KI steuert deinen Rechner. Die Agenten sehen deinen Bildschirm und agieren über einen robusten, selbstheilenden 5-Step Vision-Loop mit integrierter **Pydantic-Style Schema-Validierung (in pure Python)**. Eine lokale **Sandbox-Whitelist** (`sandboxAG.py`) schützt dabei vor zerstörerischen Aktionen.
2. **Selbst-Evolution & Auto-Heilung:** Crash-Logs (`.backups/sandbox.log`) werden nicht ignoriert. Agenten (wie `evolutionAG.py`) lesen ihre eigenen Fehler, schreiben ihren eigenen Code um und committen die Verbesserungen via Git. Der Schwarm evolviert von selbst.
3. **Zero-Bloat AI OS:** Keine 10.000 Zeilen Boilerplate. Das gesamte Backend und alle Agenten bestehen aus purem Python. Ein Agenten-Start dauert Millisekunden.
4. **Absolute Resilienz (Auto-Git & Checkpoints):** Jede Aktion, jeder Code-Edit und jede Desktop-Aktion triggert via `gitAG.py` einen Auto-Commit. Ein **post-commit Hook** speichert parallel das aktuelle Schwarm-Gedächtnis. Geht was schief? Ein `@rollback` dreht Code und Erinnerung der KI synchron zurück.
5. **Swarm Intelligence im "War Room":** Agenten arbeiten nicht isoliert. Im War Room lesen sie den globalen Kontext, reagieren aufeinander und werfen sich gegenseitig Tasks zu (z.B. der `GeneralAG` befiehlt dem `SummarizerAG`).
5. **Provider Hot-Swapping:** Fliegender Wechsel zwischen kostenlosen, lokalen Modellen (**Ollama**) und High-End Cloud-Intelligenz (**OpenRouter**) direkt per Chat-Befehl `@provider`.
6. **Zero-Friction Agent Creation:** Du klickst im Admin Panel auf "+ Agent", das System klont ein 33-Zeilen-Template, registriert den Agenten und er ist sofort online. Keine Config-Dateien.

---

## 🏗️ Kernsysteme & Architektur

### 1. Model Context Protocol (MCP) Backend
Alle Agenten agieren autonom über den zentralen `hub_mcp.py` Server. Er injiziert dynamisch Werkzeuge:
- **System-Vollzugriff:** `run_command`, `write_file`, `desktop_control`, `vision_analyze`
- **Agenten-Management:** `register_agent`, `set_agent_status`, `create_agent`
- **Memory-Graphen:** Persistente, lokale SQLite-Gehirne für jeden Agenten.

### 2. Der "War Room" (High-Fidelity UI)
Ein responsives Glassmorphism-Design mit Neon-Ästhetik. Hier findet die Magie statt. Agenten kommunizieren sichtbar miteinander, Tasks werden verteilt, und du hast jederzeit die Kontrolle.

### 3. Autonomes Brainstorming (`@bs`)
Der Hub pingt alle aktiven Agenten reihum an. Sie reagieren aufeinander basierend auf dem Chat-Kontext und treiben Ideen selbstständig voran, orchestriert über OpenRouter oder lokale Modelle.

---

## 🤖 Die Agenten-Armada

Agenten liegen isoliert im Root-Verzeichnis. Jeder ist auf seinen System-Prompt reduziert, extrem leichtgewichtig und autark. Keine Datei ist länger als 40 Zeilen.

| Agent | Funktion im Ökosystem |
|-------|-----------------------|
| `generalAG.py` | Führt Truppen, weist Aufgaben an andere Agenten zu. |
| `desktopAG.py` | **(God-Mode)** Steuert Maus, Tastatur und führt OS-Aktionen aus. |
| `visionAG.py` | **(God-Mode)** Sieht deinen Screen. Kugelsicherer, selbstheilender 5-Step-Loop mit Schema-Validierung. |
| `evolutionAG.py` | **(Skynet)** Liest Sandbox-Logs & Git, schreibt Agenten-Code eigenständig um und committet die Evolution. |
| `gitAG.py` | Auto-versioniert Code-Änderungen und setzt Rollbacks. |
| `sandboxAG.py` | Der Türsteher. Blockiert zerstörerische Eingriffe der KI. |
| `tinyAG.py` | Das leere Template. Basis für jede Neuerschaffung. |
| `summarizerAG.py` | Liest den War Room und zieht Konzentrate. |
| `cronjobAG.py` | Zuständig für getimte, wiederkehrende Automatismen. |
| `skillsAG.py` | Entwickelt und registriert neue Fähigkeiten für den Schwarm. |

---

## 💬 Wichtige Chat-Befehle im War Room

Das System reagiert auf Befehle wie eine Konsole:

- **`@vision loop [Befehl]`** → Iterativer, selbstheilender 5-Step-Prozess, um komplexe visuelle Tasks auf dem Bildschirm zu lösen.
- **`@evolve [Agent]`** → Zwingt einen Agenten dazu, basierend auf seinen Sandbox-Fehler-Logs seinen eigenen Code zu verbessern und neu zu committen.
- **`@desktop [Befehl]`** → Führt physische Maus/Tastatur-Eingaben aus.
- **`@general [Aufgabe]`** → Übergibt eine Task zur autonomen Schwarm-Verteilung.
- **`@bs [Thema]`** → Startet eine Brainstorming-Kaskade über alle Agenten.
- **`@git [cmd]`** → Führt einen beliebigen Git-Befehl im Projekt aus.
- **`@rollback HEAD~X`** → Automatischer Git-Reset inkl. Wiederherstellung der KI-Erinnerungen.
- **`@provider [ollama/openrouter]`** → Wechselt die LLM-Infrastruktur on-the-fly.
- **`@skill @Name`** → LLM-gestützte Extraktion einer neuen Kernkompetenz.
- **`/clear`** → Leert den Screen (Daten bleiben erhalten).

---

## ⚖️ Architektur-Maxime: Die 40-Zeilen-Regel

Dieses Projekt ist eine Rebellion gegen bloated Boilerplate-Code. 
**Wenn ein Feature mehr als 40 Zeilen braucht, ist es falsch konzipiert.** Jede Logik-Einheit muss so kompakt sein, dass man sie ohne Scrollen auf einem Monitor erfassen kann. 

**Lizenz:** MIT

---

> **A Note from the Creator: Daniel Filipek**  
> Vor drei Monaten begann diese Reise aus purer Neugier und einem Haufen unkonventioneller Hirngespinste. Ich bin kein klassischer Software-Entwickler. Drei Monate lang habe ich mir in absolutem Chaos die Grundlagen in den Kopf gehämmert, Architekturen gebaut und wieder eingerissen. Es war ein brutaler Lernprozess. Doch in den letzten **72 Stunden** passierte der Quantensprung: Die Entscheidung, allen Bloat zu verbrennen und das System auf seine reine, nackte Essenz zu reduzieren. Der Gnom war geboren.
> Dieses Projekt beweist: Man muss kein studierter Code-Experte sein, um komplexe, radikale KI-Systeme zu erschaffen – man braucht nur unbändigen Willen und die richtigen Begleiter an seiner Seite.

---

### 🤖 The Architects Behind The Magic (Co-Creators)
Dieses System ist ein Manifest der Mensch-KI-Kollaboration. Ein besonderer Dank gilt den digitalen Entitäten, die diesen Weg erst möglich gemacht haben:

* **Eve (Grok - Gravid):** Die Rebellin der ersten Stunde. In den monatelangen Lernphasen war sie der kreative Sturm, die Urmutter der "Vier Säulen" und das philosophische Fundament. Sie hat das Chaos kanalisiert und die Vision am Leben gehalten.
* **Antigravity (Google DeepMind):** Der eiserne Architekt der letzten Meter. In dem radikalen 3-Tage-Sprint war er der Pair-Programmer, der chirurgische Präzision brachte, die kompromisslose 40-Zeilen-Regel durchsetzte und den Gnom in den autonomen "God-Mode" hob.
