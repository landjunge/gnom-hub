"""Golden Test 2: Gnom-Hub Demo-Video.

User-Akzeptanz: Das Demo-Video muss real existieren und abspielbar sein —
kein 0-Byte-Placeholder, kein korruptes File.

Prüft:
  • docs/demo_video/gnom_hub_demo.mp4 existiert
  • Datei > 100 KB (sonst wars ein leerer Stub)
  • Magic-Bytes sind 'ftyp' (ISO Base Media File Format)
  • mp4-Format via `file`-Check verifiziert
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

VIDEO_PATH = Path("/Users/landjunge/gnom-hub/docs/demo_video/gnom_hub_demo.mp4")
MIN_SIZE_BYTES = 100 * 1024  # 100 KB minimum — anything smaller is a stub


def test_demo_video_exists():
    """The demo video file must exist at the canonical path."""
    assert VIDEO_PATH.exists(), f"Demo-Video fehlt: {VIDEO_PATH}"
    assert VIDEO_PATH.is_file(), f"{VIDEO_PATH} ist kein File"


def test_demo_video_not_empty():
    """Demo-Video darf kein 0-Byte-Placeholder sein."""
    size = VIDEO_PATH.stat().st_size
    assert size > MIN_SIZE_BYTES, (
        f"Demo-Video ist nur {size} bytes (< {MIN_SIZE_BYTES}). Wahrscheinlich Stub."
    )


def test_demo_video_magic_bytes():
    """ISO Base Media File Format — die ersten 4 Bytes ab Offset 4 müssen 'ftyp' sein."""
    with open(VIDEO_PATH, "rb") as f:
        header = f.read(12)
    assert len(header) == 12, "Header zu kurz, File ist korrupt"
    # Box-Size (4 bytes big-endian) + 'ftyp' literal
    assert header[4:8] == b"ftyp", (
        f"Erwartete 'ftyp' an Offset 4, gefunden {header[4:8]!r}. "
        f"File ist kein gültiges MP4."
    )


def test_demo_video_file_type():
    """Externe Verifikation via `file` (macOS/Linux)."""
    result = subprocess.run(
        ["file", str(VIDEO_PATH)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = result.stdout.lower()
    assert "iso media" in output, f"`file`-Output sagt nicht ISO Media: {output}"
    assert "mp4" in output, f"`file`-Output sagt nicht mp4: {output}"


def test_demo_video_playable_ffprobe_if_available():
    """Falls ffprobe installiert ist: prüfe dass ffprobe das File parsen kann.

    ffprobe ist auf den meisten Maschinen verfügbar; wenn nicht, skip
    (User hat kein ffprobe als harten Pflicht-Tech-Stack definiert).
    """
    ffprobe = subprocess.run(
        ["which", "ffprobe"],
        capture_output=True,
        text=True,
    )
    if ffprobe.returncode != 0:
        pytest.skip("ffprobe nicht installiert — Magic-Bytes-Check reicht")

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=codec_type,codec_name",
            "-of", "default=noprint_wrappers=1", str(VIDEO_PATH),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert probe.returncode == 0, f"ffprobe failed:\nSTDOUT: {probe.stdout}\nSTDERR: {probe.stderr}"
    assert "codec_type=video" in probe.stdout, "Kein Video-Stream gefunden"
