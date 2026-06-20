"""Tests for the mc707 WebUI backend.

Covers the FastAPI app, all routes, and the WebSocket endpoint.
Tests run via :class:`fastapi.testclient.TestClient` against a mock-mode
MC707 instance — no hardware, no live WebSocket server.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import mc707.ui.state as state_module
from mc707 import (
    MC707,
    PARAM_ADDRESSES,
    Sound,
    SoundEditor,
    SoundRegistry,
    SoundStore,
)
from mc707.ui.app import create_app
from mc707.ui.state import reset_state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app(tmp_path):
    """Fresh FastAPI app with a fresh BackendState per test."""
    reset_state()
    application = create_app(
        mock=True,
        sound_dir=str(tmp_path / "sounds"),
    )
    yield application
    reset_state()


@pytest.fixture
def client(app):
    """TestClient bound to the app fixture."""
    with TestClient(app) as c:
        yield c


# ===========================================================================
# 1. App factory + health
# ===========================================================================


def test_app_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_app_root_serves_index_html(client: TestClient) -> None:
    """The root URL now serves the bundled WebUI (index.html).

    The JSON landing page is exposed at ``/api/info`` instead.
    """
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    body = r.text
    assert "MC-707 WebUI" in body
    assert "Alpine.js" in body or "alpinejs" in body.lower()


def test_app_info_endpoint(client: TestClient) -> None:
    """The original JSON landing is available at /api/info."""
    r = client.get("/api/info")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "mc707-webui"
    assert body["docs"] == "/docs"
    assert body["openapi"] == "/openapi.json"
    assert body["websocket"] == "/ws"
    assert body["ui"] == "/"


def test_static_files_are_served(client: TestClient) -> None:
    """The bundled CSS and JS files resolve under /static/."""
    css = client.get("/static/css/style.css")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]

    api_js = client.get("/static/js/api.js")
    assert api_js.status_code == 200
    assert "javascript" in api_js.headers["content-type"]

    ws_js = client.get("/static/js/ws.js")
    assert ws_js.status_code == 200

    app_js = client.get("/static/js/app.js")
    assert app_js.status_code == 200
    # The main app file should reference the global Alpine store name
    assert "mc707" in app_js.text


def test_app_openapi_available(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert spec["info"]["title"] == "mc707 WebUI"
    # FastAPI doesn't expose top-level tags by default; collect the
    # tag names used inside the path operations instead.
    used_tags: set[str] = set()
    for path_item in spec.get("paths", {}).values():
        for op in path_item.values():
            if isinstance(op, dict) and "tags" in op:
                used_tags.update(op["tags"])
    # Spot-check that our route tags show up
    assert "transport" in used_tags
    assert "sounds" in used_tags
    assert "effects" in used_tags
    assert "arpeggiator" in used_tags


# ===========================================================================
# 2. State snapshot
# ===========================================================================


def test_state_snapshot_in_mock_mode(client: TestClient) -> None:
    r = client.get("/api/state")
    assert r.status_code == 200
    body = r.json()
    assert body["is_mock"] is True
    assert body["registry_size"] == 0
    assert body["registry_names"] == []
    assert "filter_cutoff" in body["known_params"]
    assert "amp_attack" in body["known_params"]
    assert body["cached_params"] == {}


def test_state_snapshot_reflects_registry(client: TestClient) -> None:
    # Register a Sound via the API
    sound = Sound(name="Bass", category="bass")
    r = client.post("/api/sounds", json={"sound": sound.model_dump()})
    assert r.status_code == 200

    # State snapshot now shows it
    r = client.get("/api/state")
    body = r.json()
    assert body["registry_size"] == 1
    assert "Bass" in body["registry_names"]


# ===========================================================================
# 3. Transport
# ===========================================================================


def test_transport_play_stop(client: TestClient) -> None:
    assert client.post("/api/transport/play").status_code == 200
    assert client.post("/api/transport/stop").status_code == 200
    assert client.post("/api/transport/pause").status_code == 200


def test_transport_tempo_validates_range(client: TestClient) -> None:
    # In-range
    r = client.post("/api/transport/tempo", json={"bpm": 128})
    assert r.status_code == 200
    assert r.json() == {"bpm": 128.0}

    # Out-of-range rejected by Pydantic
    r = client.post("/api/transport/tempo", json={"bpm": 999})
    assert r.status_code == 422


# ===========================================================================
# 4. Scenes
# ===========================================================================


def test_scene_select_next_previous_current(client: TestClient) -> None:
    r = client.post("/api/scenes/select", json={"index": 5})
    assert r.status_code == 200
    cur = client.get("/api/scenes/current").json()
    assert cur == {"ok": True, "data": {"index": 5}}

    r = client.post("/api/scenes/next")
    assert r.status_code == 200

    r = client.post("/api/scenes/previous")
    assert r.status_code == 200


def test_scene_select_validates_index(client: TestClient) -> None:
    r = client.post("/api/scenes/select", json={"index": 200})
    assert r.status_code == 422


# ===========================================================================
# 5. Clips
# ===========================================================================


def test_clip_trigger_and_stop(client: TestClient) -> None:
    r = client.post("/api/clips/trigger", json={"track": 1, "clip": 1})
    assert r.status_code == 200
    r = client.post("/api/clips/1/stop")
    assert r.status_code == 200
    r = client.post("/api/clips/stop-all")
    assert r.status_code == 200


def test_clip_mixer_endpoints(client: TestClient) -> None:
    r = client.post("/api/clips/1/mute")
    assert r.status_code == 200
    r = client.post("/api/clips/1/solo")
    assert r.status_code == 200
    r = client.post("/api/clips/1/volume", json={"track": 1, "value": 100})
    assert r.status_code == 200
    r = client.post("/api/clips/1/pan", json={"track": 1, "value": 64})
    assert r.status_code == 200


def test_clip_volume_requires_value(client: TestClient) -> None:
    r = client.post("/api/clips/1/volume", json={"track": 1})
    assert r.status_code == 200
    assert r.json()["ok"] is False


# ===========================================================================
# 6. Sounds — CRUD
# ===========================================================================


def test_sound_crud_round_trip(client: TestClient) -> None:
    sound = Sound(name="Test-Bass", category="bass")
    payload = sound.model_dump()

    # Create
    r = client.post("/api/sounds", json={"sound": payload})
    assert r.status_code == 200

    # List
    r = client.get("/api/sounds")
    assert r.json() == {"names": ["Test-Bass"]}

    # Read
    r = client.get("/api/sounds/Test-Bass")
    assert r.status_code == 200
    assert r.json()["name"] == "Test-Bass"
    assert r.json()["category"] == "bass"

    # Delete
    r = client.delete("/api/sounds/Test-Bass")
    assert r.status_code == 200

    # 404 after delete
    r = client.get("/api/sounds/Test-Bass")
    assert r.status_code == 404


def test_sound_get_unknown_returns_404(client: TestClient) -> None:
    r = client.get("/api/sounds/ghost")
    assert r.status_code == 404


def test_sound_delete_unknown_returns_404(client: TestClient) -> None:
    r = client.delete("/api/sounds/ghost")
    assert r.status_code == 404


# ===========================================================================
# 7. Sounds — Live parameter editing
# ===========================================================================


def test_sound_set_and_get_param(client: TestClient) -> None:
    # Register the sound first
    client.post("/api/sounds", json={"sound": Sound(name="X").model_dump()})

    # Set a single param
    r = client.post(
        "/api/sounds/X/params/filter_cutoff", json={"name": "filter_cutoff", "value": 99}
    )
    assert r.status_code == 200

    # Get it back
    r = client.get("/api/sounds/X/params/filter_cutoff")
    assert r.status_code == 200
    assert r.json() == {"name": "filter_cutoff", "value": 99, "cached": True}


def test_sound_get_param_unknown_returns_404(client: TestClient) -> None:
    client.post("/api/sounds", json={"sound": Sound(name="X").model_dump()})
    r = client.get("/api/sounds/X/params/nonsense")
    assert r.status_code == 404


def test_sound_set_param_unknown_returns_404(client: TestClient) -> None:
    client.post("/api/sounds", json={"sound": Sound(name="X").model_dump()})
    r = client.post(
        "/api/sounds/X/params/nonsense",
        json={"name": "nonsense", "value": 42},
    )
    assert r.status_code == 404


def test_sound_param_value_range_enforced(client: TestClient) -> None:
    client.post("/api/sounds", json={"sound": Sound(name="X").model_dump()})
    r = client.post(
        "/api/sounds/X/params/filter_cutoff",
        json={"name": "filter_cutoff", "value": 200},
    )
    assert r.status_code == 422


def test_sound_get_unset_param_returns_none(client: TestClient) -> None:
    client.post("/api/sounds", json={"sound": Sound(name="X").model_dump()})
    r = client.get("/api/sounds/X/params/amp_attack")
    assert r.status_code == 200
    assert r.json()["value"] is None


def test_sound_list_params_returns_cache(client: TestClient) -> None:
    client.post("/api/sounds", json={"sound": Sound(name="X").model_dump()})
    client.post(
        "/api/sounds/X/params/filter_cutoff",
        json={"name": "filter_cutoff", "value": 77},
    )
    r = client.get("/api/sounds/X/params")
    body = r.json()
    assert body["params"] == {"filter_cutoff": 77}


def test_sound_apply_dispatches_every_param(client: TestClient) -> None:
    sound = Sound(
        name="Apply-Me",
        filter=Sound.model_fields["filter"].default_factory().__class__(
            cutoff=80, resonance=10
        ),
    )
    client.post("/api/sounds", json={"sound": sound.model_dump()})

    r = client.post(
        "/api/sounds/Apply-Me/apply", json={"sound": sound.model_dump()}
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_sound_apply_unknown_sound_returns_404(client: TestClient) -> None:
    sound = Sound(name="Apply-Me")
    r = client.post(
        "/api/sounds/ghost/apply", json={"sound": sound.model_dump()}
    )
    assert r.status_code == 404


# ===========================================================================
# 8. Sounds — Disk persistence
# ===========================================================================


def test_sound_disk_save_and_load(client: TestClient) -> None:
    sound = Sound(name="Persist", category="bass")
    client.post("/api/sounds", json={"sound": sound.model_dump()})

    # Save to disk
    r = client.post("/api/sounds/_disk/Persist/save")
    assert r.status_code == 200
    assert "path" in r.json()["data"]

    # Drop from registry
    client.delete("/api/sounds/Persist")

    # Load from disk
    r = client.post("/api/sounds/_disk/Persist/load")
    assert r.status_code == 200

    # Now back in registry
    r = client.get("/api/sounds/Persist")
    assert r.status_code == 200


def test_sound_disk_list_empty(client: TestClient) -> None:
    r = client.get("/api/sounds/_disk/list")
    assert r.status_code == 200
    assert r.json() == {"names": []}


def test_sound_disk_load_unknown_returns_404(client: TestClient) -> None:
    r = client.post("/api/sounds/_disk/ghost/load")
    assert r.status_code == 404


def test_sound_disk_save_unknown_returns_404(client: TestClient) -> None:
    r = client.post("/api/sounds/_disk/ghost/save")
    assert r.status_code == 404


# ===========================================================================
# 9. Sounds — Legacy bank-select loader
# ===========================================================================


def test_sound_loader_endpoints(client: TestClient) -> None:
    r = client.post(
        "/api/sounds/_loader/tone",
        params={"track": 1, "tone_number": 5, "bank_msb": 0, "bank_lsb": 0},
    )
    assert r.status_code == 200

    r = client.post(
        "/api/sounds/_loader/drum-kit",
        params={"track": 1, "kit_number": 10, "user": False},
    )
    assert r.status_code == 200

    r = client.post(
        "/api/sounds/_loader/instrument",
        params={"track": 4, "tone_number": 42, "user": True},
    )
    assert r.status_code == 200


# ===========================================================================
# 10. Effects
# ===========================================================================


@pytest.mark.parametrize(
    "endpoint,value",
    [
        ("/api/effects/cutoff", 64),
        ("/api/effects/resonance", 32),
        ("/api/effects/attack", 16),
        ("/api/effects/decay", 48),
        ("/api/effects/sustain", 80),
        ("/api/effects/release", 24),
        ("/api/effects/reverb", 40),
        ("/api/effects/chorus", 20),
        ("/api/effects/delay", 60),
        ("/api/effects/distortion", 30),
        ("/api/effects/filter-type", 1),  # 0=LPF 1=HPF 2=BPF 3=Notch
    ],
)
def test_effects_endpoints_dispatch(
    client: TestClient, endpoint: str, value: int
) -> None:
    r = client.post(endpoint, json={"value": value, "track": 1})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_effects_fx_param(client: TestClient) -> None:
    r = client.post(
        "/api/effects/fx-param",
        json={"track": 1, "slot": 0, "param": 5, "value": 100},
    )
    assert r.status_code == 200


# ===========================================================================
# 11. Arpeggiator
# ===========================================================================


def test_arpeggiator_full_lifecycle(client: TestClient) -> None:
    assert client.post("/api/arpeggiator/on").status_code == 200
    assert client.post("/api/arpeggiator/off").status_code == 200
    assert client.post("/api/arpeggiator/rate", json={"rate": 100}).status_code == 200
    assert client.post("/api/arpeggiator/gate", json={"gate": 80}).status_code == 200
    assert client.post("/api/arpeggiator/style", json={"style": 2}).status_code == 200
    assert client.post("/api/arpeggiator/octave", json={"octave": 2}).status_code == 200


# ===========================================================================
# 12. Patterns
# ===========================================================================


def test_pattern_program_ints(client: TestClient) -> None:
    r = client.post(
        "/api/patterns/program",
        json={"track": 1, "steps": [36, 0, 38, 0, 42]},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_pattern_program_dicts(client: TestClient) -> None:
    r = client.post(
        "/api/patterns/program",
        json={
            "track": 1,
            "steps": [
                {"note": 36, "velocity": 100, "gate": 80},
                {"note": 38, "velocity": 110, "gate": 50},
            ],
        },
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ===========================================================================
# 13. Status
# ===========================================================================


def test_status_full_snapshot(client: TestClient) -> None:
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert "scene" in body
    assert "tempo" in body
    assert len(body["tones"]) == 8


def test_status_individual_endpoints(client: TestClient) -> None:
    assert client.get("/api/status/scene").status_code == 200
    assert client.get("/api/status/tempo").status_code == 200
    r = client.get("/api/status/tone/1")
    assert r.status_code == 200
    assert r.json()["data"]["track"] == 1


# ===========================================================================
# 14. SysEx
# ===========================================================================


def test_sysex_dt1_dispatch(client: TestClient) -> None:
    r = client.post(
        "/api/sysex/dt1",
        json={"address": [0x19, 0x00, 0], "payload": [0, 1]},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_sysex_rq1_dispatch(client: TestClient) -> None:
    r = client.post(
        "/api/sysex/rq1",
        json={"address": [0x19, 0x10, 0], "size": 4},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ===========================================================================
# 15. WebSocket — events
# ===========================================================================


def test_websocket_receives_param_change_event(client: TestClient) -> None:
    # Register the sound first
    client.post("/api/sounds", json={"sound": Sound(name="WS").model_dump()})

    with client.websocket_connect("/ws") as ws:
        # Trigger a param change via HTTP
        r = client.post(
            "/api/sounds/WS/params/filter_cutoff",
            json={"name": "filter_cutoff", "value": 88},
        )
        assert r.status_code == 200

        # WebSocket should receive the event
        event = ws.receive_json()
        assert event["type"] == "param_changed"
        assert event["data"]["param"] == "filter_cutoff"
        assert event["data"]["value"] == 88


def test_websocket_receives_transport_event(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        client.post("/api/transport/play")
        event = ws.receive_json()
        assert event["type"] == "transport_changed"
        assert event["data"]["playing"] is True


def test_websocket_receives_scene_event(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        client.post("/api/scenes/select", json={"index": 3})
        event = ws.receive_json()
        assert event["type"] == "scene_changed"
        assert event["data"]["index"] == 3


def test_websocket_receives_clip_event(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        client.post("/api/clips/trigger", json={"track": 2, "clip": 3})
        event = ws.receive_json()
        assert event["type"] == "clip_triggered"
        assert event["data"]["track"] == 2
        assert event["data"]["clip"] == 3


def test_websocket_handles_ping(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.send_text(json.dumps({"action": "ping"}))
        response = ws.receive_json()
        assert response["type"] == "pong"


def test_websocket_handles_subscribe(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.send_text(
            json.dumps({"action": "subscribe", "events": ["param_changed"]})
        )
        response = ws.receive_json()
        assert response["type"] == "subscribed"
        assert "param_changed" in response["data"]["events"]


def test_websocket_two_subscribers_each_get_event(client: TestClient) -> None:
    """Two parallel WS clients both receive the same broadcast."""
    with client.websocket_connect("/ws") as ws1, client.websocket_connect("/ws") as ws2:
        client.post("/api/transport/play")
        e1 = ws1.receive_json()
        e2 = ws2.receive_json()
        assert e1["type"] == e2["type"] == "transport_changed"