> ⚠️ HISTORISCH — Stand 19.06.2026, NICHT synchron mit Code.
> Aktuelle Source of Truth: docs/ARCHITECTURE.md

# Phase 16 – Agent Inspector & Live Optimizer

> Persönliche Planungsdatei. Nicht für die README bestimmt.
> Stand: 2026-05-27

---

## 🧬 Meine Vision

Jeder Agent in Gnom-Hub soll sich anfühlen wie ein **Lebewesen** — nicht wie ein austauschbares Code-Modul.

Ein Agent hat ein Gehirn (System-Prompt, Reasoning-Kette, Gedächtnis) und ein Herz (Persönlichkeit, Tonfall, Risikobereitschaft). Beides zusammen ergibt seinen Charakter. Und genau diesen Charakter will ich **sichtbar, verständlich und einstellbar** machen — ohne dass man dafür Prompt-Engineering verstehen muss.

Das Ziel: Jeder Agent soll wie ein Teammitglied wirken, das man kennenlernen, anpassen und weiterentwickeln kann. Nicht durch kryptische Parameter, sondern durch klare menschliche Begriffe.

---

## 🎛️ Zwei Modi

### Normal-Modus (kommt zuerst)

Für alle Nutzer. Keine technischen Details, keine Token-Zahlen, kein Prompt-Editor.

Stattdessen sieht man **pro Agent** einfache, verständliche Regler und Anzeigen:

| Eigenschaft | Beschreibung | Darstellung |
|---|---|---|
| **Persönlichkeit** | Formell ↔ Locker | Slider oder Skala |
| **Antwortstil** | Knapp ↔ Ausführlich | Slider oder Skala |
| **Gedächtnisstärke** | Wie viel Kontext der Agent einbezieht | Visuelle Anzeige (z.B. Balken) |
| **Kreativität** | Konservativ ↔ Experimentell | Slider oder Skala |
| **Risikobereitschaft** | Vorsichtig ↔ Mutig (bei Codeänderungen, Entscheidungen) | Slider oder Skala |

Der Nutzer dreht an einem Regler, und im Hintergrund werden die System-Prompts, Temperature-Werte und Retrieval-Parameter automatisch angepasst. Der Nutzer merkt davon nichts — er sieht nur, dass sein Agent sich anders verhält.

**Wichtig:** Die Werte sollen nicht beliebig sein. Jeder Slider hat sinnvolle Grenzen, die verhindern, dass ein Agent kaputt konfiguriert wird.

### Experten-Modus (kommt später)

Für Entwickler und Power-User. Zeigt die technischen Innereien:

- Voller System-Prompt (editierbar)
- Token-Verbrauch und Kosten pro Agent
- Reasoning Chain und Confidence Scores live
- Prompt-Versions-Historie mit Diff-Ansicht
- FAISS-Index-Status und Embedding-Statistiken

**Reihenfolge:** Erst das Fundament + Normal-Modus sauber bauen. Experten-Modus ist Luxus und kommt erst, wenn der Normal-Modus sitzt.

---

## 📦 Export / Import von Agenten

Jeder Agent soll als **einzelne Datei exportierbar** sein — inklusive:

- System-Prompt (aktuelle Version)
- Persönlichkeits-Einstellungen (Slider-Werte)
- Relevante Soul-Memory-Fakten (die der Agent gelernt hat)
- Prompt-Versions-Historie (optional)

Das Exportformat soll einfach sein (JSON oder YAML). Man soll einen optimierten Agent auf einem anderen Rechner importieren können und sofort die gleiche Konfiguration haben.

**Use Case:** Ich optimiere meinen CoderAG wochenlang für C#-Spielentwicklung. Dann will ich genau diesen CoderAG auf meinem zweiten Rechner haben — mit einem Klick.

---

## 🎨 Aus Agenten neue Presets machen

Wenn ein Agent gut konfiguriert ist, soll man ihn als **neues Preset speichern** können.

Beispiel:
1. Ich optimiere alle 4 Worker-Agenten für Game-Entwicklung mit Unity
2. Ich klicke "Als Preset speichern"
3. Das System erstellt automatisch ein neues JSON-Preset unter `/config/presets/`
4. Andere Nutzer (oder ich auf einem anderen Rechner) können dieses Preset laden

Das schließt den Kreislauf:
```
Preset laden → Agenten anpassen → Preset speichern → Preset teilen
```

---

## 🏗️ Reihenfolge

1. **Fundament:** Backend-API für Agent-Inspektion (GET/PUT pro Agent: Persönlichkeit, Prompt, Stats)
2. **Normal-Modus UI:** Slider-basiertes Dashboard im Frontend (kein Prompt-Editor)
3. **Export/Import:** JSON-basierter Agent-Export und -Import
4. **Preset-Erstellung:** "Speichere aktuelle Konfiguration als Preset"
5. **Experten-Modus:** Technische Detailansicht (kommt zuletzt)

---

## 💡 Offene Fragen für mich

- Sollen die Slider-Werte pro Sitzung gelten oder persistent in der DB gespeichert werden? → Wahrscheinlich persistent.
- Soll der Export auch Chat-Historie enthalten oder nur Konfiguration? → Eher nur Konfiguration.
- Brauchen wir ein Preset-Rating-System? → Erstmal nicht, aber wäre cool.
- Wie granular sollen die Slider sein? 3 Stufen? 5? Fließend? → Wahrscheinlich 5 Stufen, das reicht.
