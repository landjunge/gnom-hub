-- Gnom-Hub TKG Schema (v4 simplified, MENTIONS-aware)
-- 2 Nodes: Entity, Fact
-- 2 Edges: RELATES_TO (Fact→Fact), MENTIONS (Fact→Entity)
--
-- KuzuDB 0.11.3 Index-Realität:
--   - PK-Spalten bekommen automatisch Hash-Index
--   - Vector-Spalten bekommen HNSW via CREATE_VECTOR_INDEX
--   - KEIN CREATE INDEX für non-PK-Spalten in 0.11.x
-- Effektive Indizes: 2 PK + 1 HNSW = 3 (innerhalb des 4-Indizes-Budgets)

CREATE NODE TABLE Entity (
    id STRING PRIMARY KEY,
    name STRING,
    type STRING,
    importance DOUBLE DEFAULT 0.5,
    last_seen DOUBLE
);

CREATE NODE TABLE Fact (
    id STRING PRIMARY KEY,
    text STRING,
    embedding DOUBLE[384],
    importance DOUBLE DEFAULT 0.5,
    valid_at DOUBLE,
    invalid_at DOUBLE
);

CREATE REL TABLE RELATES_TO (
    FROM Fact TO Fact,
    predicate STRING,
    valid_at DOUBLE,
    invalid_at DOUBLE
);

CREATE REL TABLE MENTIONS (
    FROM Fact TO Entity,
    confidence DOUBLE DEFAULT 1.0
);

-- HNSW Vector-Index (PKs sind auto-indiziert)
CALL CREATE_VECTOR_INDEX(
    'Fact', 'fact_hnsw', 'embedding', metric := 'cosine'
);
