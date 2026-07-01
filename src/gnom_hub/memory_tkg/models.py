"""Dataclasses für das TKG-System (v4 simplified, MENTIONS-aware).

Schlank: 4 Dataclasses, keine Validierungs-Logik.
Validierung passiert im Backend (kuzu_backend.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

Layer = Literal["hot", "warm", "cold"]


@dataclass
class Entity:
    id: str
    name: str
    type: str
    importance: float = 0.5
    last_seen: float = 0.0
    properties: dict = field(default_factory=dict)


@dataclass
class Fact:
    id: str
    text: str
    embedding: np.ndarray | None
    importance: float = 0.5
    valid_at: float = 0.0
    invalid_at: float | None = None  # None = aktuell gültig
    layer: Layer = "warm"


@dataclass
class Relation:
    """RELATES_TO edge: Fact → Fact (bitemporal)."""
    from_id: str
    to_id: str
    predicate: str
    valid_at: float = 0.0
    invalid_at: float | None = None


@dataclass
class Mention:
    """MENTIONS edge: Fact → Entity (strukturell, kein Bitemporal nötig)."""
    fact_id: str
    entity_id: str
    confidence: float = 1.0
