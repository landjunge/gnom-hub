// ============================================================================
//  Cortex v2 — PostgreSQL Client
//  Persistent storage for memories, agents, decisions with pgvector
// ============================================================================

const { Pool } = require('pg');
const pgvector = require('pgvector/pg');
const fs = require('fs');
const path = require('path');

let pool = null;

// ---------------------------------------------------------------------------
//  Connection
// ---------------------------------------------------------------------------
async function initPostgres(options = {}) {
  const {
    host = process.env.PG_HOST || '127.0.0.1',
    port = process.env.PG_PORT || 5432,
    database = process.env.PG_DATABASE || 'cortex_v2',
    user = process.env.PG_USER || process.env.USER || 'postgres',
    password = process.env.PG_PASSWORD || undefined,
  } = options;

  pool = new Pool({
    host,
    port: parseInt(port),
    database,
    user,
    password,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
  });

  pool.on('error', (err) => {
    console.error('[Cortex/PG] Pool error:', err.message);
  });

  // Test connection
  try {
    const client = await pool.connect();
    // Register pgvector type
    await pgvector.registerTypes(client);
    client.release();
    console.log(`[Cortex/PG] Connected to ${database}@${host}:${port}`);
  } catch (err) {
    console.error('[Cortex/PG] Connection failed:', err.message);
    throw err;
  }

  return pool;
}

// ---------------------------------------------------------------------------
//  Run Migrations
// ---------------------------------------------------------------------------
async function runMigrations() {
  const migrationDir = path.join(__dirname, 'migrations');

  if (!fs.existsSync(migrationDir)) {
    console.log('[Cortex/PG] No migrations directory found');
    return;
  }

  const files = fs.readdirSync(migrationDir)
    .filter(f => f.endsWith('.sql'))
    .sort();

  for (const file of files) {
    const sql = fs.readFileSync(path.join(migrationDir, file), 'utf-8');
    try {
      await pool.query(sql);
      console.log(`[Cortex/PG] Migration applied: ${file}`);
    } catch (err) {
      // Ignore "already exists" errors
      if (err.code === '42P07' || err.code === '42710') {
        console.log(`[Cortex/PG] Migration already applied: ${file}`);
      } else {
        console.error(`[Cortex/PG] Migration failed: ${file}:`, err.message);
      }
    }
  }
}

// ---------------------------------------------------------------------------
//  Query Helpers
// ---------------------------------------------------------------------------
function getPool() {
  return pool;
}

async function query(sql, params = []) {
  if (!pool) throw new Error('PostgreSQL not initialized');
  return pool.query(sql, params);
}

async function queryAll(sql, params = []) {
  const result = await query(sql, params);
  return result.rows;
}

async function queryOne(sql, params = []) {
  const result = await query(sql, params);
  return result.rows[0] || null;
}

async function execute(sql, params = []) {
  const result = await query(sql, params);
  return { changes: result.rowCount };
}

// ---------------------------------------------------------------------------
//  Memory Operations (with pgvector)
// ---------------------------------------------------------------------------
async function insertMemory({ id, content, summary, type, importance, source, tags, embedding, context }) {
  const sql = `
    INSERT INTO memories (id, content, summary, memory_type, importance, source, tags, embedding, context)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ON CONFLICT (id) DO NOTHING
    RETURNING id
  `;
  const embeddingValue = embedding ? pgvector.toSql(embedding) : null;
  const result = await query(sql, [
    id, content, summary, type, importance, source,
    tags || [], embeddingValue, context || {},
  ]);
  return result.rows[0];
}

async function vectorSearchMemories(embedding, { limit = 5, minScore = 0.3, type, minImportance } = {}) {
  let sql = `
    SELECT *, 1 - (embedding <=> $1) AS score
    FROM memories
    WHERE embedding IS NOT NULL
  `;
  const params = [pgvector.toSql(embedding)];
  let paramIdx = 2;

  if (type) {
    sql += ` AND memory_type = $${paramIdx++}`;
    params.push(type);
  }
  if (minImportance) {
    sql += ` AND importance >= $${paramIdx++}`;
    params.push(minImportance);
  }

  sql += ` AND 1 - (embedding <=> $1) >= $${paramIdx++}`;
  params.push(minScore);

  sql += ` ORDER BY embedding <=> $1 LIMIT $${paramIdx}`;
  params.push(limit);

  const result = await query(sql, params);
  return result.rows;
}

async function keywordSearchMemories(keywords, { limit = 10, type, minImportance, source } = {}) {
  let sql = `SELECT * FROM memories WHERE 1=1`;
  const params = [];
  let idx = 1;

  if (type) {
    sql += ` AND memory_type = $${idx++}`;
    params.push(type);
  }
  if (minImportance) {
    sql += ` AND importance >= $${idx++}`;
    params.push(minImportance);
  }
  if (source) {
    sql += ` AND source = $${idx++}`;
    params.push(source);
  }
  if (keywords && keywords.length > 0) {
    // Use trigram similarity for fuzzy matching
    const searchText = keywords.join(' ');
    sql += ` AND content ILIKE $${idx++}`;
    params.push(`%${searchText}%`);
  }

  sql += ` ORDER BY importance DESC, created_at DESC LIMIT $${idx}`;
  params.push(limit);

  return (await query(sql, params)).rows;
}

async function checkDuplicate(content) {
  const result = await queryOne(
    'SELECT id FROM memories WHERE content = $1 LIMIT 1',
    [content]
  );
  return result ? result.id : null;
}

// ---------------------------------------------------------------------------
//  Agent Operations
// ---------------------------------------------------------------------------
async function upsertAgent({ id, name, type, icon, color, description, port, mcp_transport, mcp_endpoint, mcp_capabilities }) {
  const sql = `
    INSERT INTO agents (id, name, agent_type, icon, color, description, port, mcp_transport, mcp_endpoint, mcp_capabilities, last_seen)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
    ON CONFLICT (id) DO UPDATE SET
      name = EXCLUDED.name,
      agent_type = EXCLUDED.agent_type,
      icon = EXCLUDED.icon,
      color = EXCLUDED.color,
      description = EXCLUDED.description,
      port = EXCLUDED.port,
      mcp_transport = EXCLUDED.mcp_transport,
      mcp_endpoint = EXCLUDED.mcp_endpoint,
      mcp_capabilities = EXCLUDED.mcp_capabilities,
      last_seen = NOW(),
      updated_at = NOW()
    RETURNING id
  `;
  const result = await query(sql, [
    id, name, type || 'agent', icon || '🤖', color || '#64748b',
    description || '', port, mcp_transport, mcp_endpoint,
    mcp_capabilities || {},
  ]);
  return result.rows[0];
}

async function getAllAgents() {
  return queryAll('SELECT * FROM agents ORDER BY name');
}

async function getAgent(id) {
  return queryOne('SELECT * FROM agents WHERE id = $1', [id]);
}

async function deleteAgent(id) {
  return execute('DELETE FROM agents WHERE id = $1', [id]);
}

async function incrementAgentMessages(id) {
  return execute('UPDATE agents SET total_messages = total_messages + 1, last_seen = NOW() WHERE id = $1', [id]);
}

// ---------------------------------------------------------------------------
//  Decision Operations
// ---------------------------------------------------------------------------
async function insertDecision({ id, title, reasoning, outcome, participants, tags, embedding }) {
  const sql = `
    INSERT INTO decisions (id, title, reasoning, outcome, participants, tags, embedding)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    RETURNING id
  `;
  const embeddingValue = embedding ? pgvector.toSql(embedding) : null;
  const result = await query(sql, [
    id, title, reasoning, outcome, participants || [], tags || [], embeddingValue,
  ]);
  return result.rows[0];
}

async function getDecisions(limit = 10) {
  return queryAll(
    'SELECT * FROM decisions WHERE superseded_by IS NULL ORDER BY created_at DESC LIMIT $1',
    [limit]
  );
}

async function vectorSearchDecisions(embedding, limit = 5) {
  const sql = `
    SELECT *, 1 - (embedding <=> $1) AS score
    FROM decisions
    WHERE superseded_by IS NULL AND embedding IS NOT NULL
    ORDER BY embedding <=> $1
    LIMIT $2
  `;
  return queryAll(sql, [pgvector.toSql(embedding), limit]);
}

// ---------------------------------------------------------------------------
//  Cron Operations
// ---------------------------------------------------------------------------
async function getCronJobs(enabledOnly = false) {
  const sql = enabledOnly
    ? 'SELECT * FROM cron_jobs WHERE enabled = true ORDER BY created_at DESC'
    : 'SELECT * FROM cron_jobs ORDER BY created_at DESC';
  return queryAll(sql);
}

async function insertCronJob({ id, name, schedule, action, enabled = true }) {
  return execute(
    `INSERT INTO cron_jobs (id, name, schedule, action, enabled) VALUES ($1, $2, $3, $4, $5)`,
    [id, name, schedule, action, enabled]
  );
}

// ---------------------------------------------------------------------------
//  Stats
// ---------------------------------------------------------------------------
async function getStats() {
  const [memories, agents, decisions, cronJobs, conversations] = await Promise.all([
    queryOne('SELECT COUNT(*) as count FROM memories'),
    queryOne('SELECT COUNT(*) as count FROM agents'),
    queryOne('SELECT COUNT(*) as count FROM decisions'),
    queryOne('SELECT COUNT(*) as count FROM cron_jobs'),
    queryOne('SELECT COUNT(*) as count FROM conversations'),
  ]);

  const byType = await queryAll('SELECT memory_type, COUNT(*) as count FROM memories GROUP BY memory_type');
  const avgImportance = await queryOne('SELECT AVG(importance) as avg FROM memories');

  return {
    memories: parseInt(memories?.count || 0),
    agents: parseInt(agents?.count || 0),
    decisions: parseInt(decisions?.count || 0),
    cronJobs: parseInt(cronJobs?.count || 0),
    conversations: parseInt(conversations?.count || 0),
    byType: Object.fromEntries(byType.map(r => [r.memory_type, parseInt(r.count)])),
    avgImportance: Math.round((parseFloat(avgImportance?.avg) || 0) * 10) / 10,
  };
}

// ---------------------------------------------------------------------------
//  Cleanup
// ---------------------------------------------------------------------------
async function disconnect() {
  if (pool) {
    await pool.end();
    pool = null;
  }
}

module.exports = {
  initPostgres,
  runMigrations,
  getPool,
  query,
  queryAll,
  queryOne,
  execute,
  // Memory
  insertMemory,
  vectorSearchMemories,
  keywordSearchMemories,
  checkDuplicate,
  // Agents
  upsertAgent,
  getAllAgents,
  getAgent,
  deleteAgent,
  incrementAgentMessages,
  // Decisions
  insertDecision,
  getDecisions,
  vectorSearchDecisions,
  // Cron
  getCronJobs,
  insertCronJob,
  // Stats
  getStats,
  // Lifecycle
  disconnect,
};
