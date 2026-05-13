# Gnom-Hub: Echte Agenten Registry

Diese Tabelle bietet eine bereinigte, reale Übersicht aller **tatsächlich auf dem System existierenden** Agenten. Fiktive Platzhalter wurden entfernt.

### Aktive Agenten im System

| Agent Name | Backend Port | Web-UI Port | Ordner / Pfad | Start-Befehl | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Hermes** | 8787 | - | `~/.hermes` | `hermes --gateway` | AI Gateway & Agent Runtime | 🔴 Belegt |
| **Cortex Hub** | 3002 | 3102 (SSE) | `~/Documents/AG-Flega/cortex` | `cd ~/Documents/AG-Flega/cortex && node index.js` | Zentrales Gedächtnis & Filter | 🔴 Belegt |
| **Paperclip** | 3100 | 13100 | `~/workspace/paperclip` | `cd ~/workspace/paperclip && pnpm run dev` | Task-Management & Plattform | 🔴 Belegt |
| **Tandem** | 8765 | - | `~/hermes-webui/tandem-browser` | `cd ~/hermes-webui/tandem-browser && npm start` | Electron AI Browser | 🔴 Belegt |
| **Antigravity**| N/A | - | `/Applications/Antigravity.app` | `open -a Antigravity` | Google IDE Agent | 🔴 Belegt |
| **OpenClaw** | N/A | - | `~/.openclaw` | `openclaw` | Autonomer Agent + Telegram | 🟢 Frei |

### Core-Infrastruktur / Dienste

| Dienst | Port | Ordner / Pfad | Start-Befehl | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gnom-Hub** | 4200 | `~/Documents/AG-Flega` | `node server.js` | Zentrale Admin- & Steuerungszentrale | 🔴 Belegt |
| **PostgreSQL**| 5432, 54329| - | `brew services start postgresql` | Vektor-Datenbank für Cortex Hub | 🔴 Belegt |
| **Redis** | 6379 | - | `brew services start redis` | In-Memory Cache | 🔴 Belegt |
| **Ollama** | 11434 | - | `ollama serve` | Lokale LLM-Modelle | 🔴 Belegt |

---

## Bekannte Agenten & Frameworks (Internet)

Diese Tabelle listet die gängigsten Open-Source-Tools und Frameworks für die Entwicklung lokaler und autonomer Agenten auf (Stand 2026).

| Agent/Framework Name | Typ | Standard-Port | Beschreibung | GitHub-Link |
| :--- | :--- | :--- | :--- | :--- |
| **LangGraph** | Framework (Stateful) | 8123 (Studio) | State-of-the-Art Framework von LangChain für komplexe, stateful und zyklische Multi-Agenten-Workflows. | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) |
| **CrewAI** | Framework (Multi-Agent) | N/A | Führendes Framework für kollaborative Agenten-Teams (Rollen, Ziele, Delegation). | [joaomdmoura/crewAI](https://github.com/joaomdmoura/crewAI) |
| **AutoGen** | Framework (Conversational) | 8081 (Studio) | Microsofts Event-driven Framework für Multi-Agenten-Dialoge und Problemlösungen. | [microsoft/autogen](https://github.com/microsoft/autogen) |
| **OpenHands** (ehem. OpenDevin) | Autonomous Dev Agent | 3000 | Einer der stärksten autonomen KI-Softwareentwickler (ähnlich Devin). | [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands) |
| **Aider** | CLI Coding Agent | N/A | Extrem beliebter Terminal-basierter Pair-Programming-Agent mit direkter Git-Integration. | [paul-gauthier/aider](https://github.com/paul-gauthier/aider) |
| **Continue.dev** | IDE Extension Agent | N/A | Führender Open-Source Copilot-Ersatz direkt in VS Code und JetBrains. | [continuedev/continue](https://github.com/continuedev/continue) |
| **Smolagents** | Lightweight Framework | N/A | HuggingFaces extrem schlankes "Code-Agent" Framework mit Fokus auf Einfachheit. | [huggingface/smolagents](https://github.com/huggingface/smolagents) |
| **Dify** | LLM App Platform | 5001 | Low-Code/No-Code Plattform zum visuellen Erstellen komplexer Agenten und RAG-Pipelines. | [langgenius/dify](https://github.com/langgenius/dify) |
