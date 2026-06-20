# MC-707 MIDI-Controller — Handoff Briefing

> Briefing für eine Folge-KI, die das Projekt weiterbauen soll.
> Stand: Conversation mit Mavis, 2026-06-19, ca. 21:30 Berlin.

---

## 1. Projekt-Ziel

Bau einer **kompletten Python-Bibliothek zur Steuerung der Roland MC-707 Groovebox
per MIDI**, integriert als **Gnom-Hub-Tool** in der Kategorie
**„Hardware Music Equipment"** (`config/agent_tools.json`).

Der User wird die MC-707 physisch anschließen und testen. Die Bibliothek muss
**ohne angeschlossene Hardware lauffähig** sein (MIDI-Output wird geloggt, wenn
kein Port verfügbar).

---

## 2. Status der Konversation

| Was | Status |
| --- | --- |
| Code-Iterationen im Chat entwickelt | erledigt (siehe §3) |
| Architektur-Entscheidungen | getroffen (siehe §4) |
| Tool-Integration in `agent_tools.json` geplant | noch nicht committed |
| Team-Plan vorbereitet (YAML) | **noch NICHT gestartet** |
| Dateien auf Disk geschrieben | nein (nur Chat-Verlauf) |
| mido / python-rtmidi installiert | nein |

---

## 3. Bisher im Chat entstandene Code-Iterationen

### 3.1 Erste Idee (`select_and_play_clip`) — **FALSCH**
```python
def select_and_play_clip(track: int, clip: int, velocity: int = 100):
    base_note = 36
    note_number = base_note + ((track-1) * 16) + (clip-1)
    midi.send_note_on(channel=10, note=note_number, velocity=velocity)
```
→ User hat das korrigiert: Clip-Trigger auf der MC-707 funktioniert **nicht** über
Note-On-Offsets, sondern über **Program Change auf dem Track-Kanal**.

### 3.2 `control_mc707()` — High-Level CC-Controller
Funktionen: `play`, `stop`, `scene`, `clip`, `mute`, `solo`, `cutoff`, `resonance`,
`attack`, `decay`, `sustain`, `release`, `volume`, `pan`, `reverb`, `chorus`,
`delay`, `distortion`, `arpeggio`, `lfo_rate`.

**Channel-Mapping (educated guess):** Track 1 = Channel 10, Track 2 = Channel 11, …

### 3.3 `control_mc707_sysex()` — SysEx-Framework
Roland-DT1-Konvention:
```
SYSEX_HEADER = [0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x6A]
body = [0x12] + address_bytes + payload
checksum = (-sum(body)) & 0x7F
msg = SYSEX_HEADER + body + [checksum, 0xF7]
```
Adressen sind educated guesses (TEMPLATE — NEEDS VERIFICATION).

### 3.4 `program_mc707_pattern()` — Pattern-Programming
Akzeptiert **beide** Input-Formate:
- Liste von ints: `[36, 0, 38, 0, ...]`
- Liste von dicts: `[{"note": 36, "velocity": 110, "gate": 85}, ...]`

Echte Step-Daten auf die MC-707 brauchen **mehrere koordinierte SysEx-Blöcke
pro Step** (Note, Velocity, Gate, Micro-Offset, Probability, Ratchet). Das ist
zu komplex zum Raten — TODO: User muss MIDI-Chart beilefern.

### 3.5 `load_mc707_sound()` — Tone/Kit-Loading
**Korrekt** mit Bank-Select:
```python
midi.send_cc(track_channel, 0,  bank_msb)   # Bank MSB (CC#0)
midi.send_cc(track_channel, 32, bank_lsb)   # Bank LSB (CC#32)
midi.send_program_change(track_channel, sound_number)
```
Convenience: `load_drum_kit()`, `load_instrument()`.

---

## 4. Architektur-Entscheidungen

### 4.1 Klassen-Struktur (Composition statt Mixins)
```python
class MC707:
    def __init__(self, port_name=None, device_id=0x00):
        self._midi = MIDIIO(port_name)
        self._device_id = device_id

        self.transport     = TransportController(self._midi)
        self.scenes        = SceneController(self._midi)
        self.clips         = ClipController(self._midi)
        self.sounds        = SoundController(self._midi)
        self.patterns      = PatternController(self._midi)
        self.effects       = EffectsController(self._midi)
        self.arpeggiator   = ArpeggiatorController(self._midi)
        self.sysex         = SysExController(self._midi, self._device_id)
        self.status        = StatusController(self._midi, self._device_id)
```
Begründung: Komposition erlaubt **parallele Bearbeitung** der Module ohne Merge-Konflikte.

### 4.2 MIDI-Backend
- **Bevorzugt:** `mido` (portabler, kein C-Compile)
- **Optional:** `python-rtmidi` für Echtzeit-Low-Latency
- **Mock-Fallback:** wenn kein MIDI-Port verfügbar, logge Messages statt zu senden

### 4.3 Modul-Layout
```
mc707_controller/
├── __init__.py
├── midi_io.py           # MIDIIO-Wrapper (Foundation)
├── mc707.py             # Hauptklasse, komponiert alles
├── transport.py         # TransportController (Foundation, vollständig)
├── scenes.py            # SceneController
├── clips.py             # ClipController
├── sounds.py            # SoundController
├── patterns.py          # PatternController
├── effects.py           # EffectsController
├── arpeggiator.py       # ArpeggiatorController
├── sysex.py             # SysExController
├── status.py            # StatusController
├── tests/
│   └── test_smoke.py
└── README.md
```

---

## 5. Tool-Integration in Gnom-Hub

### 5.1 Registry-Eintrag
**Datei:** `/Users/landjunge/gnom-hub/config/agent_tools.json`
**Kategorie:** „Hardware Music Equipment" (existiert bereits, mit `mpc_control`,
`midi_hardware_control`)

**Geplante Tool-Entries (nach MPC-Vorbild, mehrere Sub-Tools):**
| Tool-Name | Zweck |
| --- | --- |
| `mc707_control` | Allgemeine Steuerung + Transport |
| `mc707_pattern_programming` | Pattern/Step-Daten schreiben |
| `mc707_scene_clip_control` | Szenen + Clip-Triggering |
| `mc707_sound_loader` | Tones / Drum-Kits laden mit Bank Select |
| `mc707_sysex_control` | tiefe SysEx-Steuerung + FX + Arp |

### 5.2 Code-Ort
Zwei Optionen — **vom User noch nicht final entschieden**:
- **Option A (empfohlen):** `src/gnom_hub/infrastructure/audio/mc707/` (analog zu
  `audio_tts.py`, `audio_stt.py`)
- **Option B:** `experiments/mc707_controller/` als Standalone-Modul

---

## 6. Geplanter Team-Plan (vorhanden, nicht gestartet)

### Task-Graph
```
[foundation] ──┬─→ [scenes-clips]     ──┐
               ├─→ [sounds]            ──┤
               ├─→ [patterns]          ──┼─→ [final-integration]
               ├─→ [effects-arp]       ──┤
               └─→ [sysex-status]      ──┘
```

### Tasks im Detail
1. **foundation** (`coder`): Package-Struktur, `midi_io.py`, `mc707.py`,
   `transport.py` vollständig; alle anderen Module als **Stubs** mit
   `pass`-Methoden.
2. **scenes-clips** (`coder`, depends_on foundation): `scenes.py`,
   `clips.py` implementieren.
3. **sounds** (`coder`, depends_on foundation): `sounds.py` implementieren.
4. **patterns** (`coder`, depends_on foundation): `patterns.py` implementieren.
5. **effects-arp** (`coder`, depends_on foundation): `effects.py` +
   `arpeggiator.py` implementieren.
6. **sysex-status** (`coder`, depends_on foundation): `sysex.py` + `status.py`
   implementieren.
7. **final-integration** (`coder`, depends_on alle): `tests/test_smoke.py`,
   `README.md`, Tool-Registry-Update, Smoke-Test grün.

Jeder Task wird durch `verifier` unabhängig geprüft (Re-Run, Import-Test,
Smoke-Test).

---

## 7. Kritische Caveats — was wir NICHT sicher wissen

Diese Werte sind **educated guesses** und MÜSSEN vom User beim physischen
Testen verifiziert werden. Im Code klar als `TEMPLATE` markieren.

| Bereich | Guess | Verifizieren |
| --- | --- | --- |
| Track-zu-Channel | Track 1 = Ch 10, Track 2 = Ch 11 | MIDI-Monitor beim Senden |
| Control-Channel | 10 | Roland-Doku |
| SysEx Header | `0xF0 0x41 0x10 0x00 0x00 0x00 0x6A` | Roland-Spec |
| CC Cutoff | 74 | MIDI-Monitor |
| CC Resonance | 71 | MIDI-Monitor |
| CC Mute / Solo | 94 / 95 | MIDI-Monitor |
| CC Volume / Pan | 7 / 10 | MIDI-Monitor |
| SysEx-Adressen für Clip/Tone | educated guesses | **MC-707 MIDI Implementation Chart** |
| Step-Daten schreiben | mehrere SysEx-Blöcke pro Step | **MC-707 MIDI Implementation Chart** |
| Clip-Trigger | Program Change auf Track-Kanal | User-Praxis-Test |

**Hard Rule:** Nicht weiter raten — der User hat in dieser Konversation bereits
einmal korrigiert. Bei Unsicherheit: ehrlich im Code markieren, im README
dokumentieren, User fragen.

---

## 8. Anforderungen an die Implementierung

1. **Type Hints** überall
2. **Docstrings** auf Deutsch/Englisch mit Honest Caveats
3. **Defensive Programmierung:** ungültige track/tone/sound-Werte abfangen,
   MIDI ohne Hardware graceful behandeln (Mock-Backend)
4. **Konstanten exportieren:** z.B. `CC_CUTOFF = 74` in `effects.py`,
   damit der User beim Verifizieren ein Diff gegen MIDI-Monitor machen kann
5. **Smoke-Test:** `python -c "from mc707_controller import MC707; m = MC707();
   m.transport.play(); m.scenes.select(0); m.clips.trigger(1, 1)"` muss
   ohne Fehler laufen — auch ohne Hardware.

---

## 9. Offene Fragen für die andere KI / den User

1. **Code-Ort:** `src/gnom_hub/infrastructure/audio/mc707/` (integriert) vs
   `experiments/mc707_controller/` (standalone)?
2. **Category-Name final:** „Hardware Music Equipment" (existiert) oder neue
   „Audio" Kategorie anlegen?
3. **Tool-Granularität:** Wie oben aufgeschlüsselt (5 Sub-Tools), oder ein
   einzelnes `mc707_control`?
4. **MIDI-Chart vom User:** Falls der User das Roland MC-707 MIDI
   Implementation Chart beilegen kann, werden viele educated guesses zu
   verifizierten Werten.

---

## 10. So startest du den Plan

```bash
mkdir -p /Users/landjunge/gnom-hub/.mavis/plans

# Plan-YAML schreiben (siehe Konversations-Verlauf, Abschnitt 6)
cat > /Users/landjunge/gnom-hub/.mavis/plans/plan.yaml <<'EOF'
<plan yaml>
EOF

mavis team plan run /Users/landjunge/gnom-hub/.mavis/plans/plan.yaml
```

Verfügbare Agents: `coder`, `verifier`, `general`.

---

*Erstellt von Mavis (MiniMax-M3) als Handoff-Briefing.*