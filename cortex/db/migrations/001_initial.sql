-- ============================================================================
--  Cortex v2 — PostgreSQL Schema Migration 001
--  Initial tables: memories, agents, conversations, decisions, cron_jobs
--  Requires: pgvector extension, pg_trgm extension
-- ============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
--  MEMORIES — Long-term intelligent memory storage
-- ============================================================================
CREATE TABLE IF NOT EXISTS memories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content         TEXT NOT NULL,
    summary         TEXT,
    memory_type     VARCHAR(32) NOT NULL DEFAULT 'fact',
    importance      SMALLINT NOT NULL DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    source          VARCHAR(64) NOT NULL DEFAULT 'system',
    tags            TEXT[] DEFAULT '{}',
    embedding       vector(1536),
    context         JSONB DEFAULT '{}',
    recalled_count  INT DEFAULT 0,
    last_recalled   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ
);

-- Vector index (HNSW for fast ANN search)
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Standard indexes
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(source);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_content_trgm ON memories USING GIN(content gin_trgm_ops);

-- ============================================================================
--  AGENTS — Persistent agent registry
-- ============================================================================
CREATE TABLE IF NOT EXISTS agents (
    id                TEXT PRIMARY KEY,
    name              VARCHAR(128) NOT NULL,
    agent_type        VARCHAR(32) DEFAULT 'agent',
    icon              VARCHAR(8) DEFAULT '🤖',
    color             VARCHAR(16) DEFAULT '#64748b',
    description       TEXT,
    mcp_transport     VARCHAR(16),
    mcp_endpoint      TEXT,
    mcp_capabilities  JSONB DEFAULT '{}',
    port              INT,
    last_seen         TIMESTAMPTZ,
    total_messages    INT DEFAULT 0,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
--  CONVERSATIONS — Compressed chat history
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      VARCHAR(64),
    agent_id        TEXT REFERENCES agents(id) ON DELETE SET NULL,
    role            VARCHAR(16) NOT NULL,
    content         TEXT NOT NULL,
    content_hash    VARCHAR(64),
    embedding       vector(1536),
    importance      SMALLINT DEFAULT 3,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conv_agent ON conversations(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conv_hash ON conversations(content_hash);
CREATE INDEX IF NOT EXISTS idx_conv_embedding ON conversations
    USING hnsw (embedding vector_cosine_ops);

-- ============================================================================
--  DECISIONS — Explicit decisions (highest importance)
-- ============================================================================
CREATE TABLE IF NOT EXISTS decisions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    reasoning       TEXT,
    outcome         TEXT NOT NULL,
    participants    TEXT[] DEFAULT '{}',
    tags            TEXT[] DEFAULT '{}',
    embedding       vector(1536),
    superseded_by   UUID REFERENCES decisions(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_embedding ON decisions
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_decisions_tags ON decisions USING GIN(tags);

-- ============================================================================
--  CRON_JOBS — Scheduled tasks
-- ============================================================================
CREATE TABLE IF NOT EXISTS cron_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(128) NOT NULL,
    schedule        VARCHAR(64) NOT NULL,
    action          JSONB NOT NULL DEFAULT '{}',
    enabled         BOOLEAN DEFAULT true,
    last_run        TIMESTAMPTZ,
    next_run        TIMESTAMPTZ,
    run_count       INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
--  Utility: Auto-update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to memories and agents
DROP TRIGGER IF EXISTS trg_memories_updated ON memories;
CREATE TRIGGER trg_memories_updated BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trg_agents_updated ON agents;
CREATE TRIGGER trg_agents_updated BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
