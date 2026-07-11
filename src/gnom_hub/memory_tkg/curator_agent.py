"""CuratorAgent: TKG-Curator der Texte in Entities+Relations umwandelt.

Phase 1 des TKG-Plans: Orchestrator über entity_extractor + temporal_resolver + KuzuDBBackend.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from gnom_hub.memory_tkg.entity_extractor import extract_entities
from gnom_hub.memory_tkg.kuzu_backend import KuzuDBBackend
from gnom_hub.memory_tkg.models import Entity, Fact, Mention, Relation
from gnom_hub.memory_tkg.temporal_resolver import resolve_temporal_conflicts


@dataclass
class CuratorReport:
    """Resultat eines curate()-Calls."""
    text: str
    entities_extracted: list[Entity] = field(default_factory=list)
    facts_created: list[Fact] = field(default_factory=list)
    facts_invalidated: list[Fact] = field(default_factory=list)
    relations_created: list[Relation] = field(default_factory=list)
    mentions_created: list[Mention] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class CuratorAgent:
    """Aktive LLM-driven Wissens-Kurierung: Texte → TKG."""

    def __init__(self, backend: KuzuDBBackend, llm_call: callable | None = None):
        self.backend = backend
        self.llm_call = llm_call
        self._processed_count = 0

    def curate(
        self,
        text: str,
        source: str = "user",
        invalidation_predicate: str = "replaced_by",
    ) -> CuratorReport:
        """Hauptmethode: Text → Entities + Facts + Relations → TKG.

        Args:
            text: Input-Text (User-Message, Agent-Output, Fact-Claim)
            source: Wer hat den Text produziert (für Provenance)
            invalidation_predicate: Welche Predicate-Edges markieren alte Facts als ungültig
        """
        report = CuratorReport(text=text)
        now = time.time()

        # 1. Entities extrahieren
        try:
            entities = extract_entities(text, llm_call=self.llm_call)
            report.entities_extracted = entities
        except Exception as e:
            report.errors.append(f"entity_extract: {e}")
            return report

        if not entities:
            return report

        # 2. Entities in TKG upserten
        entity_ids: dict[str, str] = {}  # name → id
        for e in entities:
            try:
                eid = self.backend.upsert_entity(e)
                entity_ids[e.name] = eid
            except Exception as ex:
                report.errors.append(f"upsert_entity({e.name}): {ex}")

        # 3. Fact erstellen aus dem Text
        fact = Fact(
            id=f"f_{int(now*1000)}",
            text=text,
            embedding=None,  # würde in Phase 1.5 gefüllt werden
            importance=0.6,
            valid_at=now,
            invalid_at=None,
            layer="warm",
        )
        try:
            self.backend.upsert_fact(fact)
            report.facts_created.append(fact)
        except Exception as ex:
            report.errors.append(f"upsert_fact: {ex}")
            return report

        # 4. Mentions: jede Entity wird mit der Fact verlinkt
        for e in entities:
            try:
                self.backend.add_mention(Mention(
                    fact_id=fact.id,
                    entity_id=entity_ids.get(e.name, e.id),
                    confidence=0.8,
                ))
                report.mentions_created.append(Mention(
                    fact_id=fact.id,
                    entity_id=entity_ids.get(e.name, e.id),
                ))
            except Exception as ex:
                report.errors.append(f"add_mention({e.name}): {ex}")

        # 5. Relations: jede Entity wird mit "mentioned_in" zur Fact verlinkt
        for e in entities:
            try:
                self.backend.add_relation(Relation(
                    from_id=entity_ids.get(e.name, e.id),
                    to_id=fact.id,
                    predicate="mentioned_in",
                    valid_at=now,
                ))
                report.relations_created.append(Relation(
                    from_id=entity_ids.get(e.name, e.id),
                    to_id=fact.id,
                    predicate="mentioned_in",
                ))
            except Exception as ex:
                report.errors.append(f"add_relation({e.name}->{fact.id}): {ex}")

        # 6. Temporal Resolution: prüfe ob neue Fact alte widerruft
        try:
            existing_facts = self.backend.search_facts_by_vector(
                __import__("numpy").zeros(384), k=1000
            ) if hasattr(self.backend, "search_facts_by_vector") else []
            contradicted = resolve_temporal_conflicts(fact, existing_facts, now=now)
            for old in contradicted:
                # Mark old as invalid
                if old.invalid_at is None:
                    self.backend.conn.execute(
                        "UPDATE Fact SET invalid_at = ? WHERE id = ?",
                        (now, old.id),
                    )
                    old.invalid_at = now
                    report.facts_invalidated.append(old)
        except Exception as ex:
            report.errors.append(f"temporal_resolve: {ex}")

        self._processed_count += 1
        return report

    def stats(self) -> dict:
        """Gibt Curator-Statistiken zurück."""
        return {
            "processed_texts": self._processed_count,
            "backend_type": type(self.backend).__name__,
        }
