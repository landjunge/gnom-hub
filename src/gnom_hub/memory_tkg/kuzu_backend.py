"""KuzuDB-Implementierung des MemoryBackend-Protocols."""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
import kuzu
from gnom_hub.memory_tkg.models import Entity, Fact, Mention, Relation

_SCHEMA = Path(__file__).parent / "graph_schema.cypher"


class KuzuDBBackend:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        for stmt in _split(_SCHEMA.read_text(encoding="utf-8")):
            try:
                self.conn.execute(stmt)
            except RuntimeError as e:
                if "already exists" not in str(e):
                    raise

    def _rows(self, result) -> list[list]:
        out = []
        while result.has_next():
            out.append(result.get_next())
        return out

    def _q(self, query, params, conv) -> list:
        return [conv(r) for r in self._rows(self.conn.execute(query, params))]

    def _q1(self, query, params, conv):
        rows = self._rows(self.conn.execute(query, params))
        return conv(rows[0]) if rows else None

    def _e(self, r):
        return Entity(id=r[0], name=r[1], type=r[2],
                      importance=r[3] or 0.5, last_seen=r[4] or 0.0)

    def _f(self, r):
        emb = np.array(r[2], dtype=np.float64) if r[2] is not None else None
        return Fact(id=r[0], text=r[1], embedding=emb,
                    importance=r[3] or 0.5, valid_at=r[4] or 0.0, invalid_at=r[5])

    def _rel(self, r):
        return Relation(from_id=r[0], to_id=r[1], predicate=r[2],
                       valid_at=r[3] or 0.0, invalid_at=r[4])
    def upsert_entity(self, e: Entity) -> str:
        self.conn.execute(
            "MERGE (e:Entity {id:$id}) "
            "ON CREATE SET e.name=$name, e.type=$type, e.importance=$importance, e.last_seen=$last_seen "
            "ON MATCH SET e.name=$name, e.type=$type, e.importance=$importance, e.last_seen=$last_seen",
            {"id": e.id, "name": e.name, "type": e.type,
             "importance": e.importance, "last_seen": e.last_seen})
        return e.id
    def upsert_fact(self, f: Fact) -> str:
        # KuzuDB 0.11.3: indexed vector prop nicht via SET updatebar.
        base = {"id": f.id, "text": f.text, "importance": f.importance,
                "valid_at": f.valid_at, "invalid_at": f.invalid_at}
        if self.get_fact(f.id) is None:
            self.conn.execute(
                "CREATE (f:Fact {id:$id, text:$text, embedding:$embedding, importance:$importance, valid_at:$valid_at, invalid_at:$invalid_at})",
                {**base, "embedding": f.embedding.tolist() if f.embedding is not None else None})
        else:
            self.conn.execute(
                "MATCH (f:Fact {id:$id}) SET f.text=$text, f.importance=$importance, f.valid_at=$valid_at, f.invalid_at=$invalid_at",
                base)
        return f.id
    def add_relation(self, r: Relation) -> str:
        # Bitemporal-Split: aktiver Edge wird invalidiert, dann neu angelegt.
        self.conn.execute(
            "MATCH (a:Fact {id:$from_id})-[r:RELATES_TO {predicate:$predicate}]->(b:Fact {id:$to_id}) "
            "WHERE r.invalid_at IS NULL SET r.invalid_at=$now",
            {"from_id": r.from_id, "to_id": r.to_id, "predicate": r.predicate, "now": time.time()})
        self.conn.execute(
            "MATCH (a:Fact {id:$from_id}), (b:Fact {id:$to_id}) "
            "CREATE (a)-[r:RELATES_TO {predicate:$predicate, valid_at:$valid_at, invalid_at:$invalid_at}]->(b)",
            {"from_id": r.from_id, "to_id": r.to_id, "predicate": r.predicate,
             "valid_at": r.valid_at, "invalid_at": r.invalid_at})
        return f"{r.from_id}:{r.predicate}:{r.to_id}@{r.valid_at}"
    def add_mention(self, m: Mention) -> str:
        self.conn.execute(
            "MATCH (f:Fact {id:$fact_id}), (e:Entity {id:$entity_id}) "
            "MERGE (f)-[m:MENTIONS]->(e) "
            "ON CREATE SET m.confidence=$confidence "
            "ON MATCH SET m.confidence=$confidence",
            {"fact_id": m.fact_id, "entity_id": m.entity_id, "confidence": m.confidence})
        return f"{m.fact_id}->{m.entity_id}"
    def get_entity(self, id: str) -> Entity | None:
        return self._q1(
            "MATCH (e:Entity {id:$id}) RETURN e.id, e.name, e.type, e.importance, e.last_seen",
            {"id": id}, self._e)
    def get_fact(self, id: str) -> Fact | None:
        return self._q1(
            "MATCH (f:Fact {id:$id}) "
            "RETURN f.id, f.text, f.embedding, f.importance, f.valid_at, f.invalid_at",
            {"id": id}, self._f)
    def find_entities_by_name(self, name: str) -> list[Entity]:
        return self._q(
            "MATCH (e:Entity) WHERE e.name=$name "
            "RETURN e.id, e.name, e.type, e.importance, e.last_seen",
            {"name": name}, self._e)
    def search_facts_by_vector(self, emb: np.ndarray, k: int = 10) -> list[Fact]:
        return self._q(
            "MATCH (f:Fact) WHERE array_cosine_similarity(f.embedding, $embedding) > 0.0 "
            "RETURN f.id, f.text, f.embedding, f.importance, f.valid_at, f.invalid_at "
            "ORDER BY array_cosine_similarity(f.embedding, $embedding) DESC LIMIT $k",
            {"embedding": emb.tolist(), "k": k}, self._f)
    def find_facts_mentioning(self, entity_id: str) -> list[Fact]:
        return self._q(
            "MATCH (f:Fact)-[:MENTIONS]->(e:Entity {id:$entity_id}) "
            "RETURN f.id, f.text, f.embedding, f.importance, f.valid_at, f.invalid_at",
            {"entity_id": entity_id}, self._f)
    def find_relations(self, from_id: str, predicate: str | None = None) -> list[Relation]:
        if predicate:
            q = ("MATCH (a:Fact {id:$from_id})-[r:RELATES_TO {predicate:$predicate}]->(b:Fact) "
                 "RETURN a.id, b.id, r.predicate, r.valid_at, r.invalid_at")
            p = {"from_id": from_id, "predicate": predicate}
        else:
            q = ("MATCH (a:Fact {id:$from_id})-[r:RELATES_TO]->(b:Fact) "
                 "RETURN a.id, b.id, r.predicate, r.valid_at, r.invalid_at")
            p = {"from_id": from_id}
        return self._q(q, p, self._rel)
    def find_facts_valid_at(self, t: float) -> list[Fact]:
        return self._q(
            "MATCH (f:Fact) WHERE f.valid_at <= $t AND (f.invalid_at IS NULL OR f.invalid_at > $t) "
            "RETURN f.id, f.text, f.embedding, f.importance, f.valid_at, f.invalid_at",
            {"t": t}, self._f)
    def count(self) -> int:
        return self.conn.execute("MATCH (n) RETURN count(n)").get_next()[0]
    def close(self) -> None:
        pass  # KuzuDB 0.11.3: kein explizites close, GC übernimmt


def _split(cypher: str) -> list[str]:
    """Kommentar-Zeilen strippen, an ';' splitten."""
    lines = [l for l in cypher.splitlines() if not l.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
