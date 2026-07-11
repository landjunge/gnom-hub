"""Mermaid-Subgraph-Serializer: TKG-Subset → Mermaid `graph TD` Markup.

Phase 2 des TKG-Plans: §1.4 (RetrievalEngineer), §2.3 (Mermaid-Integration).

Konsumenten:
- `RetrievalEngine.query()` liefert `RetrievalResult.mermaid` als String
- `GET /api/memory/graph?layer=hot` (Phase 3) wird denselben Serializer nutzen

Konventionen:
- Entity-Nodes: `e_<id>["name (type)"]`, klassen-stilisiert nach `type`
- Fact-Nodes:   `f_<id>["text..."]`
- Relations:    Solid edges `-->|"predicate"|`
- Mentions:     Dotted edges `-.->|"mentions"|`
- Type-Colors:  per `classDef` (mermaid-konform)
"""
from __future__ import annotations

import re
from typing import Iterable

from gnom_hub.memory_tkg.models import Entity, Fact, Mention, Relation

# Type-Colors (Mermaid classDef — semantic, nicht UI-spezifisch).
# Standard-Mermaid-Farben (kompatibel mit Live-Editor).
_TYPE_CLASSES: dict[str, str] = {
    "person":    "fill:#ffe1e1,stroke:#c33,color:#000",
    "agent":     "fill:#e1f0ff,stroke:#369,color:#000",
    "code_id":   "fill:#e8e1ff,stroke:#639,color:#000",
    "file":      "fill:#fff4e1,stroke:#c90,color:#000",
    "bug":       "fill:#ffd6d6,stroke:#a33,color:#000",
    "concept":   "fill:#e1ffe1,stroke:#393,color:#000",
    "event":     "fill:#f0e1ff,stroke:#939,color:#000",
    "url":       "fill:#e1f4ff,stroke:#369,color:#000",
    "date":      "fill:#f4f4f4,stroke:#999,color:#000",
    "model":     "fill:#ffe1f4,stroke:#c39,color:#000",
    "tool":      "fill:#e1f9ff,stroke:#399,color:#000",
    "default":   "fill:#ffffff,stroke:#666,color:#000",
}

_NODE_ID_RE = re.compile(r"[^A-Za-z0-9_]")


def _safe_id(prefix: str, raw_id: str) -> str:
    """Mermaid-Node-IDs müssen alphanumerisch + underscore sein."""
    safe = _NODE_ID_RE.sub("_", str(raw_id))
    return f"{prefix}_{safe}"


def _shorten(text: str, max_len: int = 60) -> str:
    """Kürzt Text fürs Mermaid-Label; escaped Pipe/Anführungszeichen."""
    if not text:
        return ""
    text = text.replace('"', "'").replace("\n", " ").replace("\r", " ")
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text


def _truncate_label(text: str, max_len: int = 80) -> str:
    """Längerer Text für Fact-Labels (Quotes, max 80 chars)."""
    return _shorten(text, max_len)


def _entity_label(entity: Entity) -> str:
    label = f"{entity.name} ({entity.type})" if entity.type else entity.name
    return _shorten(label, 50)


def _fact_label(fact: Fact) -> str:
    return _truncate_label(fact.text)


def to_mermaid(
    entities: list[Entity],
    facts: list[Fact],
    relations: list[Relation],
    mentions: list[Mention],
) -> str:
    """Serialisiert TKG-Subset als Mermaid `graph TD` Markup.

    Args:
        entities: Entity-Nodes (type-colored)
        facts: Fact-Nodes (mit Text-Label)
        relations: RELATES_TO-Edges (Fact→Fact, labeled by predicate)
        mentions: MENTIONS-Edges (Fact→Entity, dotted)

    Returns:
        Mermaid-Markup-String. Bei leeren Inputs wird leeres `graph TD` zurückgegeben.
    """
    lines: list[str] = ["graph TD"]

    # 1. Entity-Nodes
    entity_ids: set[str] = {e.id for e in entities}
    fact_ids: set[str] = {f.id for f in facts}
    seen_node_ids: set[str] = set()

    for e in entities:
        node_id = _safe_id("e", e.id)
        if node_id in seen_node_ids:
            continue
        seen_node_ids.add(node_id)
        label = _entity_label(e)
        lines.append(f'  {node_id}["{label}"]')

    # 2. Fact-Nodes
    for f in facts:
        node_id = _safe_id("f", f.id)
        if node_id in seen_node_ids:
            continue
        seen_node_ids.add(node_id)
        label = _fact_label(f)
        lines.append(f'  {node_id}["{label}"]')

    # 3. Relations (Fact → Fact, solid + labeled)
    for r in relations:
        if r.from_id not in fact_ids or r.to_id not in fact_ids:
            continue  # Endpoint nicht im Subset → skippen
        from_node = _safe_id("f", r.from_id)
        to_node = _safe_id("f", r.to_id)
        pred = _shorten(r.predicate or "relates", 30)
        lines.append(f'  {from_node} -->|"{pred}"| {to_node}')

    # 4. Mentions (Fact → Entity, dotted)
    for m in mentions:
        if m.fact_id not in fact_ids or m.entity_id not in entity_ids:
            continue
        fact_node = _safe_id("f", m.fact_id)
        ent_node = _safe_id("e", m.entity_id)
        # Confidence als Mini-Label
        conf_label = f"m:{m.confidence:.2f}" if 0.0 <= m.confidence <= 1.0 else "m"
        lines.append(f'  {fact_node} -.->|"{conf_label}"| {ent_node}')

    # 5. classDef-Blöcke (Typ-Farben)
    for etype, style in _TYPE_CLASSES.items():
        lines.append(f"  classDef {etype} {style}")

    # 6. class-Zuweisungen pro Entity-Type
    for e in entities:
        etype = (e.type or "").strip() or "default"
        if etype not in _TYPE_CLASSES:
            etype = "default"
        node_id = _safe_id("e", e.id)
        lines.append(f"  class {node_id} {etype}")

    # Falls-Style: Fact-Node als neutraler Default (kein type)
    for f in facts:
        node_id = _safe_id("f", f.id)
        lines.append(f"  class {node_id} default")

    return "\n".join(lines) + "\n"


def to_mermaid_safe(
    entities: list[Entity],
    facts: list[Fact],
    relations: list[Relation],
    mentions: list[Mention],
) -> str:
    """Wie `to_mermaid` aber fängt alle Exceptions ab und liefert Fallback-String.

    Für Frontend-Code-Pfade: Mermaid-Parser soll nie crashen, nur leer aussehen.
    """
    try:
        return to_mermaid(entities, facts, relations, mentions)
    except Exception:  # noqa: BLE001
        return "graph TD\n  empty[\"(no subgraph — serialization failed)\"]\n"


def merge_subgraph(
    *subgraphs: Iterable[Entity] | Iterable[Fact] | Iterable[Relation] | Iterable[Mention],
) -> tuple[list[Entity], list[Fact], list[Relation], list[Mention]]:
    """Convenience: mehrere Subgraph-Quellen zu einem Tuple deduplizieren."""
    entities: dict[str, Entity] = {}
    facts: dict[str, Fact] = {}
    relations: set[tuple[str, str, str]] = set()
    mentions: set[tuple[str, str]] = set()

    for s in subgraphs:
        s_list = list(s) if not isinstance(s, (list, tuple)) else s
        for item in s_list:
            if isinstance(item, Entity):
                entities[item.id] = item
            elif isinstance(item, Fact):
                facts[item.id] = item
            elif isinstance(item, Relation):
                relations.add((item.from_id, item.predicate, item.to_id))
            elif isinstance(item, Mention):
                mentions.add((item.fact_id, item.entity_id))

    rel_list = [
        Relation(from_id=f, to_id=t, predicate=p)
        for (f, p, t) in relations
    ]
    men_list = [
        Mention(fact_id=f, entity_id=e)
        for (f, e) in mentions
    ]
    return list(entities.values()), list(facts.values()), rel_list, men_list


__all__ = ["to_mermaid", "to_mermaid_safe", "merge_subgraph"]
