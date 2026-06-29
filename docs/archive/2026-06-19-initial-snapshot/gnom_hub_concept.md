> ⚠️ HISTORISCH — Stand 19.06.2026, NICHT synchron mit Code.
> Aktuelle Source of Truth: docs/ARCHITECTURE.md

# GNOM-HUB – Konsolidiertes Konzeptdokument (v0.1)

Dieses Dokument fasst das Konzept für die Web-App **gnom-hub** zusammen, die als zentrale Steuerungskonsole (Single-Page-Application) für das GNOM-Agenten-Ökosystem dient.

---

## 1. Vision
Der **gnom-hub** dient als browserbasierte „Kommandobrücke“ für den Swarm. Er visualisiert die Kommunikation der Agenten in Echtzeit, zeigt deren Health-Status und ermöglicht das Ausführen von Quick Actions. 
* **Minimalistischer Stack:** Reines HTML, CSS (Vanilla) und Javascript. Keine Frameworks, keine externen Build-Tools.

---

## 2. Architektur & Qualität
* **Modularität:** Javascript-Module (z. B. `warRoom.js`, `agentStatus.js`) sind strikt nach Zuständigkeit getrennt.
* **Entwicklungsrichtlinie:** Keine künstlichen Zeilenbeschränkungen – Fokus auf Lesbarkeit, Wartbarkeit und saubere Code-Strukturierung.
* **Design:** Dark Mode als Default (basierend auf der existierenden `dark_mode.css`) für optimale Ergonomie und Barrierefreiheit.
* **Metadaten:** Steganografische Signaturen beweisen die Herkunft jeder Codezeile.

---

## 3. Funktionsumfang (Module)

### A. Dashboard
* Visualisierung aller aktiven Agenten (General, Coder, Researcher, Writer, Editor, Soul) als Kachel-Karten.
* Anzeige von:
  * Name und aktueller Rolle
  * Status (Aktiv, IDLE, Blockiert, Offline)
  * Letzter Aktivität (Timestamp)
  * Health-Meter (0–100 % Leistungsscore)

### B. War Room (Chat & Logs)
* Tab-Ansicht mit dem Echtzeit-Chatverlauf und Systemereignissen.
* Verlaufssuche und Filter nach Agenten.

### C. Quick Actions
* Zentrale Schaltflächen für globale Aktionen (z. B. *„Alle Agenten pausieren“*, *„Workspace scannen“*).

### D. Showbox-Integration
* Live-Anzeige von generierten Ergebnissen (HTML, Markdown) über die Showbox-Schnittstelle.

---

## 4. Dokumentation
* Das Projekt wird über ein standardisiertes Dokumenten-Trio im Root gepflegt:
  * `README.md` (Setup, Vision, Architektur)
  * `CHANGELOG.md` (Chronologische Versionsübersicht)
  * `CONTRIBUTING.md` (Richtlinien für Erweiterungen)
