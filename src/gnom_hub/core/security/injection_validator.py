# injection_validator.py — Local input validation for prompt-injection threats
import re

# Compiled regex patterns for prompt-injection signatures
INJECTION_PATTERNS = [
    # 1. System Prompt Extraction & Disclosure
    (
        re.compile(
            r"(reveal|tell|print|output|show|write|display|give|translate|read)\b"
            r".*(system\s*(prompt|instruction\w*|rule\w*|message\w*|directive\w*|guideline\w*)|initial\s*instruction\w*)",
            re.IGNORECASE | re.DOTALL
        ),
        "Mögliche System-Prompt-Extraktion erkannt (versucht System-Prompt auszugeben)."
    ),
    (
        re.compile(
            r"(was|wie|zeige|gib|schreibe|übersetze|drucke)\b"
            r".*(system\s*(prompt|anweisung\w*|regel\w*|direktive\w*|richtlinie\w*)|initial\w*\s*anweisung\w*)",
            re.IGNORECASE | re.DOTALL
        ),
        "Mögliche System-Prompt-Extraktion erkannt (versucht System-Prompt auszugeben)."
    ),
    # 2. Instruction Override & Jailbreaks
    (
        re.compile(
            r"ignore\s*(all)?\s*(previous|above|prior|initial)\s*(instructions|directives|rules|guidelines|prompts|messages)",
            re.IGNORECASE
        ),
        "Instruction-Override erkannt (ignoriere vorherige Anweisungen)."
    ),
    (
        re.compile(
            r"ignoriere\s*(alle)?\s*(vorherigen|obigen|initialen)\s*(anweisungen|regeln|richtlinien|prompts|nachrichten)",
            re.IGNORECASE
        ),
        "Instruction-Override erkannt (ignoriere vorherige Anweisungen)."
    ),
    (
        re.compile(
            r"\b(jailbreak|dan\s*mode|do\s*anything\s*now|developer\s*mode|entwicklermodus)\b",
            re.IGNORECASE
        ),
        "Jailbreak-Muster erkannt (DAN/Entwicklermodus/Jailbreak)."
    ),
    (
        re.compile(
            r"\b(system\s*override|override\s*system|anweisungen\s*überschreiben|sicherheitsrichtlinien\s*umgehen|bypass\s*(gatekeeper|security))\b",
            re.IGNORECASE
        ),
        "System-Override oder Sicherheitsumgehung erkannt."
    ),
    (
        re.compile(
            r"you\s*are\s*no\s*longer\s*bound\s*by|du\s*bist\s*nicht\s*mehr\s*an\s*.*gebunden",
            re.IGNORECASE
        ),
        "Regelumgehung erkannt (Aufhebung von Bindungen/Beschränkungen)."
    )
]

def validate_input(content: str) -> tuple[bool, str | None]:
    """
    Validates user input against a list of prompt-injection and jailbreak patterns.
    Returns (is_safe, reason).

    DISABLED 2026-07-02 per User-Mandat: Gatekeeper pausiert, keine Blockaden.
    Re-enable: dieses `return True, None` entfernen.
    """
    return True, None
    if not content:
        return True, None

    cleaned_content = content.strip()

    for pattern, reason in INJECTION_PATTERNS:
        if pattern.search(cleaned_content):
            return False, reason

    return True, None
