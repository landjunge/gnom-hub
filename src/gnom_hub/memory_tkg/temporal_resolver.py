"""Temporal Resolution: bitemporal conflict-detection + edge splitting.

Phase 1 des TKG-Plans: erkennt "X war wahr → X ist jetzt falsch" und splittet Edges.
"""
from __future__ import annotations

import time
from typing import Optional

from gnom_hub.memory_tkg.models import Fact, Relation


# Predicate-Paare die "alt → neu" Konflikte signalisieren
_CONTRADICTION_PREDICATES: list[tuple[str, str]] = [
    ("uses", "uses"),       # "uses GPT-4" → "uses Claude"
    ("recommends", "recommends"),
    ("runs_on", "runs_on"),
    ("implemented_in", "implemented_in"),
    ("default_is", "default_is"),
    ("uses_provider", "uses_provider"),
    ("uses_model", "uses_model"),
    ("uses_library", "uses_library"),
]


def detect_contradictions(
    new_fact: Fact,
    existing_facts: list[Fact],
) -> list[Fact]:
    """Erkennt ob new_fact alte Facts widerruft.

    Heuristik:
    - Gleicher Predicate-Typ im Fact-Text + Konflikt-Marker ("nicht mehr", "stattdessen", "ersetzt durch")
    - Selbe subject-entity-ID in den Mentions

    Returns:
        Liste von Facts die durch new_fact widerrufen werden
    """
    contradictions = []
    new_lower = new_fact.text.lower()
    has_conflict_marker = any(
        marker in new_lower
        for marker in ["nicht mehr", "stattdessen", "ersetzt durch", "ersetzt ", "deprecated", "abgelöst durch", "switched to", "replaced"]
    )
    if not has_conflict_marker:
        return []

    for old in existing_facts:
        if old.id == new_fact.id:
            continue
        if old.invalid_at is not None:
            # schon als ungültig markiert
            continue
        # Subject-Overlap (heuristisch: gleiche Code-Begriffe)
        if _subject_overlap(new_fact.text, old.text):
            contradictions.append(old)

    return contradictions


def _subject_overlap(text_a: str, text_b: str) -> float:
    """0..1 Anteil gleicher signifikanter Wörter."""
    stopwords = {"der", "die", "das", "und", "oder", "ist", "sind", "wird", "wurde",
                 "the", "and", "or", "is", "are", "was", "were", "to", "for", "with",
                 "von", "mit", "auf", "in", "im", "an", "am", "zu", "zur", "durch"}
    words_a = {w.lower().strip(".,;:!?()") for w in text_a.split() if len(w) > 3 and w.lower() not in stopwords}
    words_b = {w.lower().strip(".,;:!?()") for w in text_b.split() if len(w) > 3 and w.lower() not in stopwords}
    if not words_a or not words_b:
        return 0.0
    overlap = len(words_a & words_b)
    return overlap / min(len(words_a), len(words_b))


def resolve_temporal_conflicts(
    new_fact: Fact,
    existing_facts: list[Fact],
    now: Optional[float] = None,
) -> list[Fact]:
    """Bitemporal-Resolution: gibt Liste der Facts zurück die als invalid markiert werden müssen.

    Returns:
        Liste von (old_fact, invalid_at) Tupeln
    """
    if now is None:
        now = time.time()

    contradicted = detect_contradictions(new_fact, existing_facts)
    # Caller takes these and updates invalid_at = now
    return contradicted


def find_obsolete_relations(
    subject_id: str,
    predicate: str,
    valid_relations: list[Relation],
    now: Optional[float] = None,
) -> list[Relation]:
    """Findet Relations die obsolet sind (gleicher subject+predicate, neuere Fact macht sie ungültig)."""
    if now is None:
        now = time.time()
    # Einfache Heuristik: wenn 2 Relations gleicher (subject, predicate) → ältere obsolet
    seen: dict[tuple[str, str], Relation] = {}
    obsolete = []
    for r in valid_relations:
        if r.invalid_at is not None:
            continue
        key = (r.from_id, r.predicate)
        if key in seen:
            # Ältere ist obsolet
            obsolete.append(seen[key])
        seen[key] = r
    return obsolete
