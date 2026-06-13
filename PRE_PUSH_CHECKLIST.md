# PRE-PUSH CHECKLIST
## Vor jedem `git push` lesen und abarbeiten!

---

## SCHRITT 0: BACKUP ALLER DATENBANKEN ERSTELLEN

```bash
./scripts/backup_all_dbs.sh pre-push
```

→ Erstellt unveränderlichen Snapshot in `dev/backups_datenbanken/<timestamp>_pre-push/`
→ _INDEX.md wird automatisch aktualisiert
→ **Niemals überschrieben** — jeder Push bekommt eigenen Snapshot

---

## SCHRITT 1: HUB STOPPEN + MONITOR KILLEN

```bash
# Alle Gnom-Hub-Prozesse killen
pkill -f "gnom_hub" 2>/dev/null
pkill -f "gnom-monitor" 2>/dev/null
pkill -f "agents\\." 2>/dev/null
sleep 2
```

---

## SCHRITT 2: DATENBANK LEEREN (NUR UNNÖTIGES LÖSCHEN)

Ziel: Nur `state`, `agents`, `agent_messages` (leer), `soul_memory` und `agent_capabilities` behalten.
Alles andere sind Laufzeitdaten.

```bash
DB=~/.gnom-hub/data/gnomhub.db
python3 -c "
import sqlite3
db = sqlite3.connect('$DB')
c = db.cursor()

# ESSENTIAL (behalten):
#   state      — LLM-Keys, Presets, Routing-Konfiguration
#   agents     — Agenten-Definitionen
#   agent_capabilities — Registrierte Fähigkeiten
#   soul_memory — Gelernte Fakten (optional löschen = frischer Start)

# UNNÖTIGE LAUFZEITDATEN (löschen):
c.execute('DELETE FROM chat')
c.execute('DELETE FROM agent_messages')
c.execute('DELETE FROM swarm_callbacks')
c.execute('DELETE FROM blockade_log')
c.execute('DELETE FROM audit_log')
c.execute('DELETE FROM capabilities')
c.execute('DELETE FROM showbox_presentations')
c.execute('DELETE FROM explainable_outputs')
c.execute('DELETE FROM token_budget_logs')
c.execute('DELETE FROM token_budget_alerts')
c.execute('DELETE FROM graceful_degradation_failures')
c.execute('DELETE FROM workflows')
c.execute('DELETE FROM workflow_tasks')
c.execute('DELETE FROM prompt_versions')

# Optional: soul_memory leeren für komplett frischen Start
# c.execute('DELETE FROM soul_memory')

# Agents auf online + last_seen zurücksetzen
from datetime import datetime, timezone
now = datetime.now(timezone.utc).isoformat()
c.execute(\"UPDATE agents SET status='online', active_job=NULL, last_seen=?, circuit_state='CLOSED', consecutive_failures=0\", (now,))

db.commit()
db.close()
print('DB Cleanup OK')
"
```

**WICHTIG:** `soul_memory` löschen = Agenten verlieren alle gelernten Fakten.
Nur löschen wenn ein komplett frischer Start gewünscht ist.

---

## SCHRITT 3: BACKUP-DATEIEN + CACHE ENTFERNEN

```bash
cd /Users/landjunge/gnom-hub

# Backup-Dateien
find . -name "*.bak" -type f -delete
find . -name "*.pyc" -type f -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# .DS_Store überall
find . -name ".DS_Store" -type f -delete

# Logs (nicht die leeren Verzeichnisse)
rm -rf logs/*.txt logs/*.log 2>/dev/null
rm -f /tmp/gnom-hub-restart.log /tmp/gnom-monitor*.log 2>/dev/null

# Agent-PID-Dateien (alten Zustand nicht committen)
rm -f ~/.gnom-hub/run/*.pid 2>/dev/null
```

---

## SCHRITT 4: PERSÖNLICHE DATEN AUS .env ENTFERNEN

`.env` ist in `.gitignore` — trotzdem checken ob keine Secrets im Code sind:

```bash
# Suche nach API-Keys die versehentlich im Code gelandet sind
rg -i "sk-[a-z0-9]" --include="*.py" --include="*.md" --include="*.html" --include="*.json" --include="*.js" src/ agents/ tests/ config/

# Prüfe auch FTP-Zugangsdaten
rg -i "ftp_user\|ftp_pass\|FTP_USER\|FTP_PASS" src/ agents/ tests/ 2>/dev/null
```

**Wenn was gefunden wird: Vor Push entfernen!** API-Keys gehören NUR in `.env`.

---

## SCHRITT 5: README AKTUALISIEREN

### README.md (Englisch)
```bash
# Test-Anzahl prüfen
cd /Users/landjunge/gnom-hub
TEST_COUNT=$(/Users/landjunge/gnom-hub/.venv/bin/python -m pytest tests/ --collect-only -q 2>&1 | tail -1 | grep -oP '^\d+')
echo "Tests: $TEST_COUNT"
```

- [ ] Test-Badge in README.md aktualisieren: `[![Tests](https://img.shields.io/badge/Tests-${TEST_COUNT}-blue.svg)]`
- [ ] Test-Badge in README.de.md aktualisieren (gleicher Wert)
- [ ] Changelog in `CHANGELOG.md` ergänzen falls neue Features
- [ ] Version in `pyproject.toml` prüfen (major.minor.patch)

### Badges (README.md Zeile 7)
```
Aktuell:  [![Tests](https://img.shields.io/badge/Tests-154-blue.svg)]
```
in beiden READMEs aktualisieren.

---

## SCHRITT 6: TESTS LAUFEN LASSEN

```bash
cd /Users/landjunge/gnom-hub && /Users/landjunge/gnom-hub/.venv/bin/python -m pytest tests/ -v --tb=short 2>&1 | tee /tmp/test-results.txt
```

**Bedingungen:**
- ✅ ALLE Tests müssen passen (0 failed)
- ⚠️ 2 Intentional Failures sind akzeptiert: `test_unsafe_path_instant_blocked` + `test_generalag_shell_blocked`
  (wurden bewusst geändert — Tests müssen angepasst sein)
- ❌ Jeder andere Failure = STOPP, nicht pushen!

---

## SCHRITT 7: INSTALL/UNINSTALL TESTEN

### Uninstall testen
```bash
cd /Users/landjunge/gnom-hub && python3 uninstall.py
```
- [ ] Sollte nach Bestätigung fragen
- [ ] Entfernt `.venv/`, Logs, Caches
- [ ] Lässt Quellcode + Workspace intakt

### Install testen
```bash
cd /Users/landjunge/gnom-hub && python3 install.py
```
- [ ] Erstellt `.venv/`
- [ ] Installiert Dependencies aus `pyproject.toml`
- [ ] Startet den Hub nicht automatisch (nur Setup)

### Hub-Start testen
```bash
cd /Users/landjunge/gnom-hub && nohup .venv/bin/python -m gnom_hub &>/tmp/gnom-hub-install-test.log &
sleep 15
curl -s http://127.0.0.1:3002/api/agents | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'OK: {len(d)} Agents') if d else print('FAIL: Keine Agents')"
```
- [ ] Alle 8 Agenten sind online
- [ ] Port 3002 antwortet
- [ ] `curl /api/agents` liefert JSON mit 8 Agenten

```bash
pkill -f "gnom_hub" 2>/dev/null  # Test-Hub beenden
```

---

## SCHRITT 8: GIT CLEANEN + COMMITTEN

```bash
cd /Users/landjunge/gnom-hub

# Status prüfen
git status

# Ungewollte Änderungen reverten
# git checkout -- src/gnom_hub/...

# Nur gewollte Dateien stagen
git add -A

# Änderungen reviewen
git diff --cached --stat

# Committen (folge vorhandenem Stil)
git commit -m "Kurze, prägnante Beschreibung der Änderungen"

# Log prüfen
git log --oneline -5
```

---

## SCHRITT 9: LETZTER CHECK VOR PUSH

- [ ] **KEINE API-Keys** im Commit (nur in `.env`)
- [ ] **KEINE `.bak`- oder Backup-Dateien** im Commit
- [ ] **KEINE `__pycache__/`** im Commit
- [ ] **KEINE `.DS_Store`** im Commit
- [ ] **KEINE Logdateien** im Commit
- [ ] **KEINE `.pid`-Dateien** im Commit
- [ ] **opencode.jsonc** nur committen wenn gewünscht
- [x] `.gitignore` deckt alles ab? → prüfen mit `git status`

```bash
# Finaler Dry-Run: was würde gepusht werden?
git push --dry-run
```

---

## SCHRITT 10: PUSH

```bash
git push
```

---

## NOTFALL: PUSH RÜCKGÄNGIG

```bash
# Letzten Commit rückgängig (local)
git reset --soft HEAD~1

# Remote zurücksetzen (nur wenn wirklich nötig)
# git push --force-with-lease origin HEAD~1:main
```
