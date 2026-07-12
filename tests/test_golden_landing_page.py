"""Golden Test 1: Gnom-Hub Landing-Page.

User-Akzeptanz: Die 5 Landing-Page-Designs müssen in der Showbox live sein
UND als HTML-Files im Workspace existieren. Wenn dieser Test grün ist, hat
der User etwas zum Anschauen.

Prüft:
  • Hub antwortet (HTTP 200)
  • Showbox-API liefert "gnom-hub-designs" als aktive Präsentation
  • Genau 6 Slides vorhanden (1 Header + 5 Designs)
  • Alle 5 Design-Files existieren und sind valides HTML
  • Mindestens 5 Buttons (User-Mandat: "Buttons sind nicht optional")
"""
from __future__ import annotations

import json
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import pytest

HUB_URL = "http://localhost:3002"
DESIGNS_DIR = Path("/Users/landjunge/gnom-Workspace/default/gnom-hub-designs")
EXPECTED_DESIGNS = [
    "01-cyberpunk",
    "02-glassmorphism",
    "03-brutalist-neon",
    "04-editorial-magazine",
    "05-kinematic-ai",
]
EXPECTED_SHOWBOX = "gnom-hub-designs"


class _HTML5Checker(HTMLParser):
    """Minimal HTML5 well-formedness check."""

    def __init__(self) -> None:
        super().__init__()
        self.tag_count = 0
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tag_count += 1

    def error(self, message):
        self.errors.append(message)


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read())


def _design_mentioned_in_showbox(design_slug: str, showbox: dict) -> bool:
    """A design is present in the showbox if its slug or display name appears
    in any slide title or button label."""
    needle = design_slug[3:]  # "01-cyberpunk" -> "cyberpunk"
    for slide in showbox.get("slides", []):
        title = (slide.get("title") or "").lower()
        if needle in title:
            return True
        content = (slide.get("content") or "").lower()
        if needle in content:
            return True
    for btn in showbox.get("buttons", []):
        if needle in (btn.get("label") or "").lower():
            return True
    return False


def test_hub_is_alive():
    """Hub must answer HTTP 200 on /api/health."""
    with urllib.request.urlopen(f"{HUB_URL}/api/health", timeout=5) as r:
        assert r.status == 200, f"Hub not alive: HTTP {r.status}"


def test_active_showbox_is_gnom_hub_designs():
    """Active showbox must be 'gnom-hub-designs', not the stale 'generalag_r240_system_ready'."""
    data = _get(f"{HUB_URL}/api/showbox/active")
    active = data.get("active", "")
    assert active == EXPECTED_SHOWBOX, (
        f"Active showbox is '{active}', expected '{EXPECTED_SHOWBOX}'. "
        f"User wanted to see the 5 designs, not the previous system-ready message."
    )


def test_gnom_hub_designs_showbox_registered():
    """The 'gnom-hub-designs' presentation must exist and have 6 slides (header + 5 designs)."""
    presentations = _get(f"{HUB_URL}/api/showbox/presentations")
    match = next((p for p in presentations if p["name"] == EXPECTED_SHOWBOX), None)
    assert match is not None, f"Showbox '{EXPECTED_SHOWBOX}' not found in {len(presentations)} presentations"
    assert len(match["slides"]) == 6, f"Expected 6 slides (1 header + 5 designs), got {len(match['slides'])}"


def test_showbox_has_buttons():
    """User-Mandat: 'Buttons sind nicht optional'. Min 5 buttons required."""
    presentations = _get(f"{HUB_URL}/api/showbox/presentations")
    match = next(p for p in presentations if p["name"] == EXPECTED_SHOWBOX)
    assert len(match.get("buttons", [])) >= 5, (
        f"Only {len(match.get('buttons', []))} buttons. User explicitly required buttons."
    )


@pytest.mark.parametrize("design_slug", EXPECTED_DESIGNS)
def test_design_file_exists_and_is_valid_html(design_slug: str):
    """Each design file must exist and parse as HTML (well-formed enough)."""
    path = DESIGNS_DIR / f"{design_slug}.html"
    assert path.exists(), f"Design file missing: {path}"
    content = path.read_text(encoding="utf-8", errors="ignore")
    assert "<html" in content.lower(), f"{path.name} missing <html> tag"
    assert "</html>" in content.lower(), f"{path.name} missing </html> closing tag"
    assert "<title>" in content.lower(), f"{path.name} missing <title>"

    # Light HTML5 well-formedness check (presence of major structural tags)
    checker = _HTML5Checker()
    checker.feed(content)
    assert checker.tag_count > 10, f"{path.name} looks empty ({checker.tag_count} tags)"


@pytest.mark.parametrize("design_slug", EXPECTED_DESIGNS)
def test_each_design_in_showbox(design_slug: str):
    """Every design must be referenced in the showbox (slide title or button)."""
    presentations = _get(f"{HUB_URL}/api/showbox/presentations")
    match = next(p for p in presentations if p["name"] == EXPECTED_SHOWBOX)
    assert _design_mentioned_in_showbox(design_slug, match), (
        f"Design '{design_slug}' not represented in showbox slides/buttons. "
        f"User can't see it."
    )


def test_all_5_designs_have_open_buttons():
    """Every design must have a button that opens it (file:// link or action)."""
    presentations = _get(f"{HUB_URL}/api/showbox/presentations")
    match = next(p for p in presentations if p["name"] == EXPECTED_SHOWBOX)
    buttons = match.get("buttons", [])

    # Either inline <a href="file://..."> in slide content, or a dedicated button per design
    for design_slug in EXPECTED_DESIGNS:
        in_button = any(design_slug[3:] in (b.get("label") or "").lower() for b in buttons)
        if not in_button:
            # Check slide content for file:// link
            slide_html = " ".join(
                (s.get("content") or "") for s in match.get("slides", [])
            )
            assert f"{design_slug}.html" in slide_html, (
                f"Design '{design_slug}' has neither a button nor a file:// link"
            )
