#!/usr/bin/env python3
"""
Gnom-Hub Demo Video Generator
================================
Generates a short demo video of the Gnom-Hub dashboard using:
  • Playwright (headless Chromium) for screenshot capture
  • gTTS for text-to-speech narration
  • FFmpeg for final video assembly

Pipeline:
    1. Launch headless Chromium via Playwright
    2. Open dashboard at http://127.0.0.1:3002
    3. Capture full-page screenshot
    4. Generate MP3 narration from script text
    5. Combine image + audio into MP4 via ffmpeg

Usage:
    python generate_demo.py

Requirements (pip):
    playwright>=1.40
    gTTS>=2.5
System:
    ffmpeg (must be on PATH)
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

from gtts import gTTS
from playwright.async_api import async_playwright

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DASHBOARD_URL: str = "http://127.0.0.1:3002"
OUTPUT_DIR: Path = Path("/Users/landjunge/gnom-hub/docs/demo_video")
SCREENSHOT_PATH: Path = OUTPUT_DIR / "dashboard_screenshot.png"
AUDIO_PATH: Path = OUTPUT_DIR / "narration.mp3"
VIDEO_PATH: Path = OUTPUT_DIR / "demo_video.mp4"
VIEWPORT: dict[str, int] = {"width": 1920, "height": 1080}
SETTLE_DELAY_MS: int = 2000

NARRATION_SCRIPT: str = (
    "Welcome to the Gnom-Hub. "
    "A live multi-agent orchestration system with eight heartbeat-green agents. "
    "SoulAG coordinates, GeneralAG delegates, CoderAG builds, "
    "WriterAG documents, ResearcherAG investigates, EditorAG polishes, "
    "SecurityAG guards, and WatchdogAG monitors. "
    "All systems operational. Dashboard live at port 3002."
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("demo-generator")


# ---------------------------------------------------------------------------
# Step 1–3: Screenshot capture
# ---------------------------------------------------------------------------
async def capture_dashboard_screenshot() -> None:
    """Launch headless Chromium, open dashboard, capture full-page screenshot."""
    log.info("Launching headless Chromium...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport=VIEWPORT)
        page = await context.new_page()

        log.info("Navigating to %s", DASHBOARD_URL)
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        # Let glassmorphism animations / agent-card fade-ins settle.
        await page.wait_for_timeout(SETTLE_DELAY_MS)

        log.info("Capturing screenshot → %s", SCREENSHOT_PATH)
        await page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)

        await context.close()
        await browser.close()


# ---------------------------------------------------------------------------
# Step 4: TTS narration
# ---------------------------------------------------------------------------
def generate_narration_audio() -> None:
    """Render narration script to MP3 via gTTS."""
    log.info("Synthesizing narration via gTTS...")
    tts = gTTS(text=NARRATION_SCRIPT, lang="en", slow=False)
    tts.save(str(AUDIO_PATH))
    log.info("Audio saved → %s", AUDIO_PATH)


# ---------------------------------------------------------------------------
# Step 5: Combine via ffmpeg
# ---------------------------------------------------------------------------
def assemble_video() -> None:
    """Stitch static screenshot + narration audio into MP4 using ffmpeg."""
    cmd: list[str] = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(SCREENSHOT_PATH),
        "-i", str(AUDIO_PATH),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(VIDEO_PATH),
    ]
    log.info("Running ffmpeg to assemble video...")
    result = subprocess.run(cmd, check=False, capture_output=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )
    log.info("✅ Video ready → %s", VIDEO_PATH)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        await capture_dashboard_screenshot()
        generate_narration_audio()
        assemble_video()
    except subprocess.CalledProcessError as exc:
        log.error("ffmpeg failed (rc=%s): %s", exc.returncode, exc.stderr.decode(errors="ignore"))
        return 1
    except Exception as exc:  # noqa: BLE001
        log.exception("Demo generation failed: %s", exc)
        return 1
    log.info("🎬 Demo complete: %s", VIDEO_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
