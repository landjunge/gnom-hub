# mc707

A pure-Python library for controlling the **Roland MC-707 Groovebox**
over MIDI. Mock-first, hardware-ready.

## Why

* **Mock-first** — the library runs without a physical MC-707. Every
  outgoing MIDI message is captured in an in-memory log so the entire
  API is exercisable from CI, tests, and exploration.
* **Structured Sound definitions** — Tones are first-class Pydantic
  models with round-trip JSON persistence. No more "remember which
  SysEx byte is the filter cutoff".
* **Layered architecture** — `io` (MIDI / SysEx), `models` (data),
  `control` (high-level API), `persistence` (disk), `registry`
  (in-memory). Easy to extend, easy to test.
* **Standalone-installable** — `pip install mc707` works. Inside the
  Gnom-Hub project the same package is re-exported via a thin shim at
  `gnom_hub.infrastructure.audio.mc707`, so existing code keeps
  working unchanged.

## Install

### Standalone

```bash
pip install mc707
```

Or, from a checkout of this repo:

```bash
pip install -e src/mc707
```

For the optional WebUI dependencies:

```bash
pip install mc707[ui]
```

### Inside Gnom-Hub

`mc707` is already a dependency of `gnom-hub` via the local
`src/mc707/` layout. Import as usual:

```python
from gnom_hub.infrastructure.audio.mc707 import MC707, Sound  # via shim
# or, equivalently:
from mc707 import MC707, Sound  # direct
```

Both forms resolve to the same objects.

## Quick start

```python
from mc707 import MC707, Sound, FilterParams

# Mock mode by default — no hardware required
m = MC707()

# High-level controllers
m.transport.play()
m.clips.trigger(1, 1)
m.scenes.next()
m.arpeggiator.on()

# Live tone editing via SysEx DT1
sound = Sound(
    name="Sub-Bass",
    category="bass",
    filter=FilterParams(cutoff=48, resonance=30),
)
m.sound_editor.apply(sound)

# Persist to ~/.mc707/sounds/sub_bass.json
m.sound_store.save(sound)

# Or a custom directory
m = MC707(sound_dir="/path/to/my/sounds")

# Real hardware
m = MC707(port_name="MC-707 MIDI OUT", mock=False)
```

## Architecture

```
mc707/
├── facade.py           # MC707 class (entry point)
├── io/                 # MIDI + SysEx
│   ├── midi.py         # MIDIIO wrapper around mido
│   └── sysex.py        # Roland SysEx DT1/RQ1 framing
├── models/             # Pydantic data models
│   └── sound.py        # Sound + 5 sub-models
├── control/            # High-level controllers
│   ├── transport.py    # play / stop / tempo / clock
│   ├── scenes.py       # scene selection
│   ├── clips.py        # clip trigger, track mixer
│   ├── sounds.py       # bank-select loader (legacy)
│   ├── sound_editor.py # SysEx DT1 tone editor
│   ├── patterns.py     # step sequencer
│   ├── effects.py      # filter / envelope / MFX
│   ├── arpeggiator.py  # arp on/off + parameters
│   └── status.py       # cached state read-backs
├── persistence/        # Disk-backed state
│   └── sound_store.py  # JSON persistence for Sounds
└── registry/           # In-memory named caches
    └── sound_registry.py
```

## Verification status

The following MC-707-specific values are **EDUCATED GUESSES** derived
from general Roland conventions and need verification against the
official *MC-707 MIDI Implementation Chart*:

| Area | Module | What needs verifying |
|---|---|---|
| Bank-Select layout | `control/sounds.py` | "Bank 0 = Preset, Bank 1 = User" split; drum-kit vs instrument bank slots; track → MIDI channel mapping (track 8 currently lands on ch 17 → clamped) |
| SysEx tone-edit addresses | `control/sound_editor.py` | All `PARAM_ADDRESSES` entries; the `(0x18, 0x00..0x40, offset)` layout |
| Wave / filter / LFO-target IDs | `models/sound.py` | Enum-to-ID mapping tables (`_WAVE_TO_ID`, `_FILTER_TO_ID`, `_LFO_TARGET_TO_ID`) |
| SysEx DT1/RQ1 framing | `io/sysex.py` | Verified against the Roland spec; only the per-application addresses are guesses |

These are marked **TEMPLATE - NEEDS VERIFICATION** in the relevant
module docstrings. Where possible the code falls back to safe defaults
instead of silently using unverified values.

## Limitations & open items

* **`SoundEditor.get_param` / `capture`** are cache-only — they reflect
  values this process wrote via `set_param`, not the current device
  state. A real RQ1 read-back with response framing is **TODO** for a
  future track. The WebUI must label any displayed value as
  "cached, last written by this session" until then.
* **Live device monitoring** (track changes, tempo changes from the
  hardware) requires registering a callback on the MIDI input port
  via `StatusController` — also TODO.

## Tests

```bash
cd src/mc707
python -m pytest mc707/tests/
```

Tests run in mock mode; no MC-707 hardware required.

## WebUI (Track 4)

The package ships with a self-contained web frontend. Start the server
and open the URL in a browser — no KI, agent, or build step required.

### Start

```bash
# Mock mode (default — no hardware needed)
python -m mc707.ui --port 8765

# Real hardware
python -m mc707.ui --port-name "MC-707 MIDI OUT" --no-mock

# Custom sound directory
python -m mc707.ui --sound-dir /path/to/sounds

# Or via uvicorn directly
uvicorn mc707.ui.app:app --host 0.0.0.0 --port 8765 --reload
```

Then open <http://localhost:8765/>.

### What you get

A single-page UI with sections for every controller:

* **Transport** — Play / Stop / Pause + tempo slider (20–300 BPM)
* **Scenes** — 16 scene buttons + prev/next
* **Clips** — 8×16 clip launcher + per-track mixer (Mute / Solo / Volume / Pan)
* **Sounds & Parameters** — load from registry or disk, live-editable
  sliders for all 19 tone parameters (OSC, Filter, Amp Env, Filter Env,
  LFO) grouped by section
* **Effects** — Cutoff, Resonance, ADSR, Reverb, Delay, Chorus, Distortion
* **Arpeggiator** — On/Off + Rate / Gate / Style (Up / Down / UpDown / Random) / Octave
* **Status** — current scene, tempo, per-track tones, sound counts

A clear **MOCK MODE** / **HARDWARE** badge in the header tells you which
backend you're talking to. The WebSocket indicator shows live connection
state and reconnects automatically.

### Architecture

```
mc707/ui/
├── app.py                # FastAPI factory + CORS + /static mount + /
├── state.py              # BackendState singleton + get_state dependency
├── models.py             # 25 Pydantic Request/Response models
├── events.py             # EventBus (in-process pub/sub)
├── ws.py                 # /ws WebSocket endpoint
├── __main__.py           # python -m mc707.ui entry point
├── routes/               # 10 routers, 43 endpoints
└── static/               # Frontend bundle (ships in the wheel)
    ├── index.html        # Alpine.js SPA
    ├── css/style.css     # dark hardware-near theme
    └── js/
        ├── api.js        # REST client
        ├── ws.js         # WebSocket with auto-reconnect
        └── app.js        # Alpine store + methods
```

The frontend uses [Alpine.js](https://alpinejs.dev/) via CDN — no build
step, no npm. Open `/docs` in a browser for the full OpenAPI schema
(54 paths, including 43 REST endpoints and the WebSocket).

### Connection flow

1. Browser loads `/` → `index.html` is served from the package
2. `app.js` runs, calls `GET /api/state` → full snapshot
3. `ws.js` opens `WS /ws` → server pushes state-change events
4. Every user action (button click, slider drag) → `Api.*` REST call →
   backend mutates the controller → `EventBus.publish` →
   `WS /ws` broadcasts the event → UI re-renders

The WebSocket is **firehose**-style — every subscriber gets every event.
Per-client filtering is the client's job (drop events you don't care
about). The `subscribe` / `unsubscribe` actions are accepted today and
are a forward-compat hook for future server-side filtering.

## License

MIT. See `LICENSE` if present in the repo, or assume standard MIT
terms otherwise.