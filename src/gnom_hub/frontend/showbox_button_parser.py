"""showbox_button_parser.py — Inline-Button-Extraktion aus Worker-Outputs.

PARSE-LOGIK IDENTISCH ZU showbox-module.js (gleiche Regex-Architektur, gleiche
Reihenfolge der Quellen). Wenn du hier etwas änderst, MUSST du es im JS-Modul
ebenfalls nachziehen. Driftet auseinander → Buttons fehlen leise.

Unterstützte Formate:

Format A (Worker-HTML, primär):
    <button action="X" label="Y">...</button>
    <button action="X" label="Y">        (ohne close-tag — häufig in Worker-Outputs!)
    <button data-sb-action="X" data-sb-label="Y" ...>...</button>

Format B (DOM-Hooks für bereits gerendertes HTML):
    <button data-sb-action="X" data-sb-label="Y" ...>
    <button data-sb-action="X" data-sb-icon="..." data-sb-color="...">

Robust gegen:
    • fehlende </button> close-tags (häufig in LLM-Outputs!)
    • Single ODER Double Quotes (Worker mischen beide)
    • beliebige Reihenfolge der Attribute
    • Gross-/Kleinschreibung der Action
    • optionale label/data-sb-label Attribute

Verwendung:
    from gnom_hub.frontend.showbox_button_parser import parse_inline_buttons

    btns = parse_inline_buttons(slide_html)
    # → [{"id": "btn-1", "onClick": "approve_docs",
    #     "label": "Ja, Doku parallel", "icon": "▶", "color": ""}, ...]

Wird verwendet von:
    • chat_legacy.py   (POST /api/chat — Button-Extraktion aus Worker-Outputs)
    • action_exec.py   (Agent-Action — Button-Extraktion vor DB-Save)
    • showbox-module.js (Client-seitige Defensiv-Extraktion aus bereits gerenderten DOMs)
"""
from __future__ import annotations

import re
from typing import Any

MAX_BUTTONS = 8
DEFAULT_ICON = "▶"


# ── Regex-Pattern ─────────────────────────────────────────────────────────
# Ein einziges Pattern, das BEIDE Formate erkennt. Trick: `action|data-sb-action`
# als Alternative. `label|data-sb-label` ebenso (OPTIONAL — Worker lassen label
# oft weg, dann wird Action als Fallback-Label verwendet). Reihenfolge der
# Attribute egal. Wir akzeptieren `>` direkt (selbst-schliessend) ODER
# `>...</button>` (mit close-tag).
#
# Gruppe 1: Action (z.B. "approve_docs" oder "send:Hallo Welt")
# Gruppe 2: Label  (z.B. "Ja, Doku parallel") — LEER wenn nicht vorhanden
#
# Akzeptiert auch wenn der Button IN EINER GRÖSSEREN ZEILE steckt (häufig im
# Worker-Output: "...Soll ich?\n<button action='ja'>Ja</button> ...").
_BTN_INLINE_RE = re.compile(
    r"""<button\b                     # öffnendes <button
        [^>]*?                       # beliebige Attribute davor (non-greedy)
        (?:action|data-sb-action)    # einer der beiden Action-Attribute
        \s*=\s*
        ["']([^"']+)["']             # Gruppe 1: Action-Wert
        [^>]*?                       # weitere Attribute (inkl. optionales label)
        (?:                           # OPTIONAL: label/data-sb-label
            (?:label|data-sb-label)
            \s*=\s*
            ["']([^"']*)["']          # Gruppe 2: Label-Wert (kann leer sein)
            [^>]*?                   # ggf. weitere Attribute
        )?                           # ← Gruppe OPTIONAL
        >                            # öffnende Tag-Ende
        [^<]*                        # optionaler Inhalt bis zum nächsten Tag
        (?:</button>)?               # OPTIONAL: close-tag
    """,
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)


def _normalize_action(action: str) -> str:
    """Stellt sicher dass die Action als nicht-leerer String zurückkommt.

    Häufige LLM-Eigenheiten:
      • ' approve_docs ' (whitespace)   → 'approve_docs'
      • 'javascript:void(0)'            → leer (wird rausgefiltert)
    """
    if not action:
        return ""
    a = action.strip()
    if a.lower().startswith(("javascript:", "data:", "vbscript:")):
        return ""
    return a


def _normalize_label(label: str, action: str) -> str:
    """Falls Label leer ist, Fallback aus Action ableiten.

    Priorität: explizites Label → Action-Text → 'OK'.
    """
    label = (label or "").strip()
    if label:
        return label[:50]
    if ":" in action:
        return action.split(":", 1)[1][:50] or action.split(":", 1)[0]
    return action[:50] or "OK"


def parse_inline_buttons(html: str) -> list[dict[str, Any]]:
    """Extrahiert Inline-Buttons aus Worker-HTML oder DOM-String.

    Args:
        html: Roher HTML/String (Slide-Body, gerendertes DOM, Showbox-Response).

    Returns:
        Liste von Button-Dicts (max MAX_BUTTONS=8), je:
            {
              "id":     "btn-1",           # stabil, durchnummeriert
              "onClick": "approve_docs",   # Action-String
              "label":  "Ja, Doku parallel",  # Beschriftung
              "icon":   "▶",              # Default-Icon (Frontend kann überschreiben)
              "color":  ""                # leer, ausser data-sb-color war gesetzt
            }
    """
    if not html or not isinstance(html, str):
        return []

    out: list[dict[str, Any]] = []
    seen_actions: set[str] = set()  # Deduplizierung nach Action

    for m in _BTN_INLINE_RE.finditer(html):
        if len(out) >= MAX_BUTTONS:
            break

        action = _normalize_action(m.group(1) or "")
        if not action or action in seen_actions:
            continue
        seen_actions.add(action)

        label = _normalize_label(m.group(2) or "", action)

        # data-sb-color aus dem Original-Tag extrahieren (falls vorhanden)
        color_m = re.search(
            r'data-sb-color\s*=\s*["\']([^"\']+)["\']',
            m.group(0),
            re.IGNORECASE,
        )
        color = color_m.group(1).strip() if color_m else ""

        # data-sb-icon (optional) — Emoji oder HTML
        icon_m = re.search(
            r'data-sb-icon\s*=\s*["\']([^"\']+)["\']',
            m.group(0),
            re.IGNORECASE,
        )
        icon = icon_m.group(1).strip() if icon_m else DEFAULT_ICON

        out.append({
            "id": f"btn-{len(out) + 1}",
            "onClick": action,
            "label": label,
            "icon": icon,
            "color": color,
        })

    return out


def parse_inline_buttons_with_format(html: str) -> dict[str, list[dict[str, Any]]]:
    """Debug-Helper: Gibt extrahierte Buttons nach Format aufgeschlüsselt zurück.

    Nützlich für Diagnose-Tools (Welches Format dominiert? Driftet das JS-Modul?).
    """
    if not html:
        return {"format_a": [], "format_b": [], "merged": []}

    out_a: list[dict[str, Any]] = []
    out_b: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Format A: explizit action= (nicht data-sb-action)
    _FA = re.compile(
        r"""<button\b[^>]*?\baction\s*=\s*["']([^"']+)["'][^>]*?
            (?:\blabel\s*=\s*["']([^"']*)["'])?[^>]*?>(?:[^<]*</button>|[^<]*)""",
        re.IGNORECASE | re.VERBOSE | re.DOTALL,
    )
    # Format B: explizit data-sb-action
    _FB = re.compile(
        r"""<button\b[^>]*?\bdata-sb-action\s*=\s*["']([^"']+)["'][^>]*?
            (?:\bdata-sb-label\s*=\s*["']([^"']*)["'])?[^>]*?>(?:[^<]*</button>|[^<]*)""",
        re.IGNORECASE | re.VERBOSE | re.DOTALL,
    )

    for m in _FA.finditer(html):
        a = _normalize_action(m.group(1) or "")
        if not a or a in seen:
            continue
        seen.add(a)
        out_a.append({"onClick": a, "label": _normalize_label(m.group(2) or "", a)})

    for m in _FB.finditer(html):
        a = _normalize_action(m.group(1) or "")
        if not a or a in seen:
            continue
        seen.add(a)
        out_b.append({"onClick": a, "label": _normalize_label(m.group(2) or "", a)})

    merged = parse_inline_buttons(html)
    return {"format_a": out_a, "format_b": out_b, "merged": merged}