# 💾 Gnom-Hub Backup Agent — Architektur-Entwurf

**Datum:** 14. Mai 2026  
**Status:** Konzept  
**Security Level:** SEC 4 (braucht Security + User-Genehmigung für git push)

---

## Grundprinzip

> Kein Code-Verlust. Nie wieder.

Der Backup Agent sichert automatisch und auf Anfrage — lokal und remote. Er ist der einzige Agent mit `git`-Rechten.

---

## Zwei Modi

### 🔄 Auto-Modus (Cronjob)
Läuft im Hintergrund, reagiert auf Events.

| Trigger | Aktion | Intervall |
|---|---|---|
| Datei geändert in `AG-Flega/` | Lokaler Snapshot | Alle 30 Min |
| Neuer Commit vorhanden | `git push origin master` | Nach jedem Commit |
| Agent-Memory geändert (>10 Einträge) | DB-Export als JSON | Stündlich |
| Mitternacht | Vollbackup (tar.gz) | Täglich 00:00 |

### 📢 Manuell (War Room Command)
Über Chat-Befehle steuerbar.

| Command | Aktion |
|---|---|
| `@backup` | Sofort-Snapshot + Push |
| `@backup status` | Letzter Backup-Zeitpunkt, Größe, Diff-Count |
| `@backup history` | Letzte 10 Backups auflisten |
| `@backup restore <id>` | Früheren Stand wiederherstellen (SEC 4 + User) |

---

## Backup-Strategie

### 1. Git (Remote)

```
Arbeitsverzeichnis: /Users/landjunge/Documents/AG-Flega/
Remote: github.com/landjunge/gnom-hub (master)
```

| Was | Wie |
|---|---|
| Auto-Commit Message | `backup: auto-snapshot YYYY-MM-DD HH:MM` |
| Manuell Commit Message | `backup: manual — <reason>` |
| Branch-Strategie | Nur `master` (kein Feature-Branch-Overhead) |
| Force-Push | ❌ Niemals. Immer `git push` ohne `--force` |

### 2. Lokal (Snapshots)

```
Backup-Verzeichnis: /Users/landjunge/Documents/AG-Flega/.backups/
```

| Typ | Format | Aufbewahrung |
|---|---|---|
| Code-Snapshot | `snapshot-YYYYMMDD-HHMM.tar.gz` | Letzte 7 Tage |
| DB-Export | `db-export-YYYYMMDD-HHMM.json` | Letzte 14 Tage |
| Vollbackup | `full-YYYYMMDD.tar.gz` | Letzte 30 Tage |

**Auto-Rotation:** Älteste Backups werden automatisch gelöscht wenn Limits erreicht.

### 3. Was wird gesichert

| Ja | Nein |
|---|---|
| `frontend/` | `.venv/` |
| `src/gnom_hub/` | `__pycache__/` |
| `*.py` (Agent-Scripts) | `.backups/` (keine Rekursion) |
| `docs/` | `.git/` (hat git selbst) |
| `db.json` (TinyDB) | `node_modules/` |
| `pyproject.toml` | `.DS_Store` |
| `.env` (verschlüsselt) | Temp-Dateien |

---

## Ablauf: Auto-Snapshot

```
1. Prüfe: Hat sich etwas geändert seit letztem Snapshot?
   └─ Nein → Warte 30 Min → Neustart
   └─ Ja ↓

2. Erstelle lokalen Snapshot
   └─ tar.gz nach .backups/

3. Git-Status prüfen
   └─ Uncommitted Changes?
      └─ Ja → git add -A && git commit -m "backup: auto-snapshot"
      └─ Nein → Weiter

4. Unpushed Commits?
   └─ Ja → Security Agent fragen (SEC 4)
      └─ ✅ Genehmigt → git push origin master
      └─ ❌ Blockiert → Loggen, nächster Versuch in 30 Min
   └─ Nein → Fertig

5. Alte Snapshots rotieren (>7 Tage löschen)

6. Status in War Room posten (SEC 2)
   └─ "💾 Backup: 3 Dateien geändert, pushed to GitHub"
```

---

## Ablauf: Restore

```
1. User: @backup restore <id>

2. Security Agent: SEC 4 Check
   └─ ❌ Ohne User-Bestätigung → Blockiert
   └─ ✅ User bestätigt ↓

3. Aktuellen Stand sichern (Safety-Snapshot)
   └─ snapshot-before-restore-YYYYMMDD.tar.gz

4. Restore ausführen
   └─ Lokales Backup: tar entpacken
   └─ Git: git checkout <commit-hash>

5. War Room Meldung
   └─ "💾 Restore abgeschlossen. Safety-Snapshot: <id>"
```

---

## Security-Integration

| Aktion | SEC Level | Wer genehmigt |
|---|---|---|
| Backup-Status lesen | SEC 1 | Niemand (auto) |
| Lokalen Snapshot erstellen | SEC 2 | Security loggt |
| `git commit` | SEC 3 | Security genehmigt |
| `git push` | SEC 4 | Security + User |
| Restore | SEC 4 | Security + User |
| Backup-Rotation (löschen) | SEC 3 | Security genehmigt |
| `.env` sichern | SEC 4 | Security + User (verschlüsselt) |

---

## Konfiguration

```python
BACKUP_CONFIG = {
    "auto_interval_min": 30,
    "snapshot_retention_days": 7,
    "db_export_retention_days": 14,
    "full_backup_retention_days": 30,
    "max_backup_size_mb": 500,
    "git_auto_push": True,
    "git_remote": "origin",
    "git_branch": "master",
    "backup_dir": ".backups",
    "exclude": [
        ".venv", "__pycache__", ".git", 
        ".backups", "node_modules", ".DS_Store"
    ]
}
```

---

## Persona

**Keine.** Wie der Security Agent — rein funktional. Kein Name, kein Charakter. Meldungen sind sachlich:

```
✅  "💾 Snapshot erstellt: 12 Dateien, 847KB"
✅  "💾 Push: 3 Commits → GitHub"  
✅  "💾 Rotation: 2 alte Snapshots gelöscht"
❌  "💾 Push fehlgeschlagen: Remote ahead. Manual merge nötig."
```

---

*Konzept — wird implementiert zusammen mit dem Security Agent.*
