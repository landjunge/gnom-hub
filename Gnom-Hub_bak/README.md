# Gnom-Hub Cortex

Gnom-Hub — das zentrale Nervensystem.

## Installation

Um Cortex zu installieren, lade dieses Repository herunter und führe im Hauptverzeichnis folgenden Befehl aus:

```bash
pip install -e .
```

Dies installiert Cortex und alle benötigten Abhängigkeiten. Die Option `-e` (editable) bedeutet, dass du den Code bearbeiten kannst und die Änderungen direkt wirksam werden.

## Starten

Sobald das Paket installiert ist, stehen dir die folgenden Terminal-Befehle global zur Verfügung:

1. **Cortex Hub starten (FastAPI Server):**
   ```bash
   cortex-hub
   ```

2. **Cortex MCP Server starten:**
   ```bash
   cortex-mcp
   ```

3. **Cortex Pulse (Monitoring) starten:**
   ```bash
   cortex-pulse
   ```

## Struktur

* `src/cortex/` - Der Quellcode der Cortex-Engine
* `docs/` - Dokumentation
