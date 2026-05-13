# 🧠 GNOM-HUB

Willkommen bei **GNOM-HUB** – dem minimalistischen, blitzschnellen Memory- und Tool-Orchestrator für lokale KI-Agenten. GNOM-HUB dient als zentrales Gehirn, über das sich Agenten im System registrieren, historische Erinnerungen austauschen und auf mächtige externe Werkzeuge zugreifen können.

---

## 🚀 Installation

Das Projekt ist als sauberes lokales Python-Paket aufgebaut. Navigiere in das Hauptverzeichnis und installiere es im "Editable Mode", damit Änderungen sofort übernommen werden:

```bash
python3.11 -m pip install -e .
```

## ⚡ Starten

Das gesamte System lässt sich unkompliziert mit einem einzigen Befehl starten. Dabei werden parallel die zentrale Hub-API sowie der Standard-konforme MCP-Server hochgefahren:

```bash
python3.11 -m gnom_hub
```

Beide Server laufen im Hintergrund. Mit `Ctrl+C` (oder dem Befehl `gnom-hub-stop`) kannst du das System jederzeit sauber beenden.

---

## ✨ Aktuelle Features

Das System läuft auf zwei getrennten, spezialisierten Ports:

**1. Die Core Hub-API (Port 3002)**
- **Agenten-Management**: Registrieren und Auflisten lokaler Agenten.
- **Memory-CRUD**: Speichern, Suchen und Abrufen von Erinnerungen pro Agent.

**2. Der FastMCP Server (Port 3100)**
- **Standard SSE-Transport**: Jeder gängige MCP-Client kann sich unter `/sse` verbinden.
- **2 Aktive Werkzeuge**:
  - `save_to_memory`: Lässt Agenten neue Informationen direkt in ihr Memory schreiben.
  - `get_memory`: Erlaubt Agenten das Zurücklesen ihrer bisherigen Historie.

Zusätzlich bietet die Hub-API komfortable HTTP-Proxy-Routen (wie `POST /api/tools/get_memory`), um die MCP-Werkzeuge unkompliziert über HTTP zu testen.

---

## 📐 Unsere Philosophie: "Less is More"

Dieses Projekt folgt einer strengen, kompromisslosen Design-Regel, um technische Schulden zu vermeiden und höchste Wartbarkeit zu garantieren:

> **Maximal 40 Zeilen pro Datei. Keine Ausnahmen.**

Wir setzen auf strikte **Modularisierung** anstatt Code in riesigen Dateien zu verstecken. Jedes Modul (`models.py`, `routes_memory.py`, `hub_mcp.py` etc.) hat exakt einen Zweck, verwendet sprechende Variablen, hält sich an PEP-8 und bleibt konsequent unter 40 Zeilen. Das macht den Code extrem robust, fehlerresistent und wunderschön lesbar.

---

## 🛠 Wie man neue Tools hinzufügt

Dank des FastMCP-Frameworks ist das Hinzufügen neuer Werkzeuge denkbar einfach. Füge einfach eine neue Funktion mit dem `@mcp.tool()` Decorator in die Datei `src/gnom_hub/hub_mcp.py` ein:

```python
@mcp.tool()
def search_web(query: str) -> str:
    """Sucht im lokalen Netzwerk nach Informationen."""
    return f"Suchergebnisse für: {query}"
```

Sobald du GNOM-HUB neu startest, ist das Tool sofort für alle verbundenen Agenten nutzbar. Denke nur an die wichtigste Regel: Wenn die Datei durch dein neues Tool die 40-Zeilen-Grenze überschreitet, lagere die Logik in ein neues Modul aus!

---

## 🎯 Nächste Schritte

- Integration eines globalen Such-Tools (`search_memory`).
- Anpassung des Frontend Admin-Panels an die neue, saubere Architektur.
- Erweiterung der MCP-Tool-Bibliothek um dateibasierte Werkzeuge.

---
*GNOM-HUB — Engineered for clarity. Built for agents.*
