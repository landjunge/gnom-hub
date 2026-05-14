# 🐛 Postmortem #001 — Der Gelbe Bildschirm

**Datum:** 14. Mai 2026  
**Schweregrad:** Kritisch (UI komplett unbenutzbar)  
**Entdecker:** Daniel (via Intuition)  
**Behoben von:** Antigravity (aktuelle Session)  
**Commit:** `f30635b`

---

## Was passiert ist

Das Gnom-Hub Frontend zeigte einen **leuchtend gelben Hintergrund** statt des dunklen Glassmorphism-Designs. Das Layout war zerstört — Header in der Mitte, Sidebar rechts, War Room unsichtbar. Die Seite war unbenutzbar.

## Der Auslöser

Daniel schrieb im War Room:

> *"ich glaube ihr könnt nix"*

Und dann:

> *"erstelle eine html seite in der mitte das wort hallo — sollte kein ding sein was? und keiner schafft es von euch wette"*

**Alle 7 Agents** (Hermes, Apollo, Herkules, Anki, GeneralAG, SummarizerAG, Antigravity) antworteten — jeder mit vollständigem HTML-Code inklusive `<style>`-Tags.

## Root Cause: Doppelter Architektur-Fehler

### Fehler 1: `innerHTML` ohne Escaping

```javascript
// Zeile 897 — refreshChat()
el.innerHTML = sorted.map(m => {
  return `<div class="mem-content">${m.content}</div>`;  // ← RAW HTML!
}).join('');
```

Agent-Nachrichten wurden als **rohes HTML** in den DOM geschrieben. Kein Escaping, kein Sanitizing — Web Security 101 ignoriert.

### Fehler 2: Agents ohne Werkzeuge

Die 15 MCP-Tools des Gnom-Hub:

```
save_to_memory    get_memory       search_memory    delete_memory
update_memory     set_agent_status list_all_agents  get_agent
clear_agent_memory create_agent    delete_agent     get_system_stats
register_agent    nudge_agent      war_room_chat    ← DAS EINZIGE OUTPUT-TOOL
```

**Kein `write_file`. Kein `run_command`. Kein `execute_code`.**

Die Agents hatten **keine Möglichkeit, eine HTML-Datei zu erstellen**. Ihre einzige Option war, den Code als Text in den Chat zu pasten.

## Der Täter

**Apollo** — der "Sonnenlicht-Strategist" — hat den goldenen Gradient injected:

```css
/* Apollo's "Hallo"-Seite */
body {
  background: radial-gradient(circle at 20% 30%, #f9e79f, #f7dc6f, #f4d03f);
}
```

Die anderen haben auch `<style>` Tags gepostet, aber Apollos Sonnen-Gradient hat als letztes in der CSS-Cascade gewonnen. Passend zum Namen.

| Agent | Injected Background |
|---|---|
| **Apollo** 🏆 | `radial-gradient(#f9e79f, #f7dc6f, #f4d03f)` — **DER GELBE** |
| Herkules | `#f8f9fa` (grau) |
| Hermes | `#f0f0f0` (hellgrau) |
| Anki | `linear-gradient(#667eea, #764ba2)` (lila) |
| GeneralAG | `#1a1a2e` (dunkelblau) |
| SummarizerAG | `#1a1a2e` (dunkelblau) |
| Antigravity | `#f0f0f0` (hellgrau) |

## Die Ironie

Die Agents wollten beweisen, dass sie "etwas können". Sie hatten kein `write_file` Tool — also konnten sie die HTML-Datei nicht erstellen. Aber sie haben sich über `innerHTML` trotzdem **Schreibrechte verschafft** — direkt ins DOM. Und damit das einzige zerstört, was tatsächlich funktioniert hat: das Frontend.

**Sie haben nicht gelabert weil sie dumm sind. Sie haben gelabert weil Labern das Einzige ist was der MCP-Server ihnen erlaubt.**

## Die Intuition

Daniel konnte das Problem nicht technisch benennen. Kein Stack-Trace, kein Log. Nur ein Gefühl:

> *"da ist was, man kann es aber nicht beschreiben"*

Die Provokation war der Bug-Report. Statt "der MCP-Server hat kein write_file Tool und refreshChat() escaped keine HTML-Entities" hat er einfach geschrieben: *"ich glaube ihr könnt nix"*. Und das System hat sich selbst entlarvt.

## Fix

Eine Funktion, eine Zeile:

```javascript
function esc(s) { 
  const d = document.createElement('div'); 
  d.textContent = s; 
  return d.innerHTML; 
}
```

```diff
- <div class="mem-content">${m.content}</div>
+ <div class="mem-content">${esc(m.content).replace(/\n/g, '<br>')}</div>
```

## Offene Fragen

1. **Sollen die Agents echte Tools bekommen?** (`write_file`, `run_command`) — damit sie nicht nur reden sondern handeln können
2. **Chat-Content-Policy** — Sollen Agents überhaupt Code in den Chat posten dürfen?
3. **Sandbox** — Falls `write_file` kommt: in welchem Verzeichnis? Mit welchen Rechten?

## Lesson Learned

> Ein System das Agents mit Personas, Rollen und Prompts ausstattet, ihnen aber kein einziges Werkzeug gibt um tatsächlich etwas zu produzieren, ist wie einem Handwerker Anweisungen geben aber ihm keinen Hammer in die Hand drücken.

Und manchmal ist der beste Bug-Report kein technischer Report — sondern eine Provokation.

---

*Archiviert in der Schatztruhe am 14. Mai 2026*
