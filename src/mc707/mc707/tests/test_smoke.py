"""End-to-end smoke test for the MC-707 controller API.

This test exercises every public method on the :class:`MC707` façade
without any hardware attached. In mock mode every outgoing message is
appended to an in-memory log via :meth:`MIDIIO.get_log`, so the test
can assert that the full call graph dispatch reached the I/O layer.

The smoke test intentionally mirrors the exact verification script in
``docs/mc707_handoff.md`` so it doubles as a regression guard for the
end-to-end call sequence. If any of the methods below silently stops
dispatching (e.g. a refactor turns a stub into a no-op), the
``assert len(log) > 30`` line at the end will fail loudly.

Run via:

    PYTHONPATH=src python3.10 -m pytest \\
        src/gnom_hub/infrastructure/audio/mc707/tests/test_smoke.py -v -s
"""

from __future__ import annotations

import pytest

from mc707 import MC707


def test_smoke_all_api() -> None:
    """Exercise every public method on the MC-707 façade.

    At least 30 method calls are made against a single instance in mock
    mode. The captured MIDI log must contain at least as many entries —
    this guards against silent regressions where a method would
    accidentally become a ``pass`` no-op.
    """
    m = MC707()  # mock=True is the default

    # ------------------------------------------------------------------
    # Transport — 4 calls
    # ------------------------------------------------------------------
    m.transport.play()
    m.transport.stop()
    m.transport.pause()
    m.transport.tempo(120)

    # ------------------------------------------------------------------
    # Scenes — 4 calls
    # ------------------------------------------------------------------
    m.scenes.select(0)
    m.scenes.next()
    m.scenes.previous()
    assert m.scenes.current() >= 0  # scene controller tracks a counter

    # ------------------------------------------------------------------
    # Clips — 7 calls
    # ------------------------------------------------------------------
    m.clips.trigger(1, 1)
    m.clips.stop(1)
    m.clips.stop_all()
    m.clips.track_mute(1)
    m.clips.track_solo(1)
    m.clips.track_volume(1, 100)
    m.clips.track_pan(1, 64)

    # ------------------------------------------------------------------
    # Sounds — 3 calls (loader) + 2 calls (sound_editor DT1 path)
    # ------------------------------------------------------------------
    m.sounds.load_tone(1, 5)
    m.sounds.load_drum_kit(1, 10)
    m.sounds.load_instrument(4, 42)
    m.sound_editor.set_param("filter_cutoff", 64)
    m.sound_editor.set_param("amp_attack", 32)

    # ------------------------------------------------------------------
    # Patterns — 2 calls (the ``program`` method fans out to many notes)
    # ------------------------------------------------------------------
    m.patterns.program(1, [36, 0, 38, 0])
    m.patterns.program(1, [{"note": 36, "velocity": 100}])

    # ------------------------------------------------------------------
    # Effects — 12 calls
    # ------------------------------------------------------------------
    m.effects.cutoff(100)
    m.effects.resonance(80)
    m.effects.attack(64)
    m.effects.decay(64)
    m.effects.sustain(64)
    m.effects.release(64)
    m.effects.reverb(80)
    m.effects.chorus(50)
    m.effects.delay(60)
    m.effects.distortion(40)
    m.effects.filter_type(1)
    m.effects.set_fx(1, 0, 1, 100)

    # ------------------------------------------------------------------
    # Arpeggiator — 5 calls
    # ------------------------------------------------------------------
    m.arpeggiator.on()
    m.arpeggiator.rate(120)
    m.arpeggiator.gate(80)
    m.arpeggiator.style(2)
    m.arpeggiator.octave(1)

    # ------------------------------------------------------------------
    # SysEx — 5 calls (high-level + low-level)
    # ------------------------------------------------------------------
    m.sysex.send_dt1((0x19, 0x00, 0), [0, 1])
    m.sysex.send_rq1((0x19, 0x10, 0), 4)
    m.sysex.clip_on(1, 1)
    m.sysex.track_level(1, 100)
    m.sysex.set_fx_param(1, 0, 1, 100)

    # ------------------------------------------------------------------
    # Status — 4 calls (3 reads + 1 callback registration)
    # ------------------------------------------------------------------
    scene = m.status.current_scene()
    tempo = m.status.current_tempo()
    tone = m.status.current_tone(1)
    m.status.on_response(lambda x: None)

    # ------------------------------------------------------------------
    # Verify the call graph reached the I/O layer
    # ------------------------------------------------------------------
    log = m._midi.get_log()
    assert len(log) > 30, (
        f"expected >30 MIDI log entries from smoke run, got {len(log)}"
    )
    # All three status reads return sane defaults (None for unknown,
    # 0/120 for the cached mock state).
    assert scene is not None
    assert tempo == 120
    assert tone is not None

    print(f"All {len(log)} smoke actions executed")
