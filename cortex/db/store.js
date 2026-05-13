// ============================================================================
//  Cortex v2 — Hybrid Storage Layer
//  Primary: Redis (hot) + PostgreSQL/pgvector (persistent)
//  Fallback: In-Memory cache + SQLite (sql.js)
// ============================================================================

const crypto = require('crypto');
const redisClient = require('./redis');
const pgClient = require('./postgres');

let useRedis = false;
let usePostgres = false;

// ---------------------------------------------------------------------------
//  In-Memory Fallback Cache (always available)
// ---------------------------------------------------------------------------
const memCache = {
  agentStatus: new Map(),
  recentChat: [],
  RECENT_CHAT_MAX: 200,
  activeTasks: new Map(),
  pipes: new Map(),
  context: {},
  locks: new Map(),
  metrics: {
    totalMessages: 0,
    totalMemories: 0,
    totalRecalls: 0,
    filterSkipped: 0,
  },
};

// ---------------------------------------------------------------------------
//  SQLite Fallback (loaded on demand)
// ---------------------------------------------------------------------------
let sqliteDb = null;

async function initSQLiteFallback() {
  try {
    const initSqlJs = require('sql.js');
    const path = require('path');
    const fs = require('fs');
    const DB_PATH = path.join(__dirname, '..', '..', 'cortex.db');

    const SQL = await initSqlJs();

    if (fs.existsSync(DB_PATH)) {
      const buffer = fs.readFileSync(DB_PATH);
      sqliteDb = new SQL.Database(buffer);
    } else {
      sqliteDb = new SQL.Database();
    }

    // Create tables
    sqliteDb.run(`CREATE TABLE IF NOT EXISTS memories (
      id TEXT PRIMARY KEY, content TEXT NOT NULL, summary TEXT,
      memory_type TEXT DEFAULT 'fact', importance INTEGER DEFAULT 5,
      source TEXT DEFAULT 'system', tags TEXT DEFAULT '[]',
      embedding TEXT, context TEXT DEFAULT '{}',
      recalled_count INTEGER DEFAULT 0, last_recalled TEXT,
      created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')), expires_at TEXT
    )`);
    sqliteDb.run(`CREATE TABLE IF NOT EXISTS agents (
      id TEXT PRIMARY KEY, name TEXT NOT NULL, agent_type TEXT DEFAULT 'agent',
      icon TEXT DEFAULT '🤖', color TEXT DEFAULT '#64748b', description TEXT,
      mcp_transport TEXT, mcp_endpoint TEXT, mcp_capabilities TEXT DEFAULT '{}',
      port INTEGER, last_seen TEXT, total_messages INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )`);
    sqliteDb.run(`CREATE TABLE IF NOT EXISTS decisions (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, reasoning TEXT, outcome TEXT NOT NULL,
      participants TEXT DEFAULT '[]', tags TEXT DEFAULT '[]', embedding TEXT,
      superseded_by TEXT, created_at TEXT DEFAULT (datetime('now'))
    )`);
    sqliteDb.run(`CREATE TABLE IF NOT EXISTS conversations (
      id TEXT PRIMARY KEY, session_id TEXT, agent_id TEXT, role TEXT NOT NULL,
      content TEXT NOT NULL, content_hash TEXT, importance INTEGER DEFAULT 3,
      created_at TEXT DEFAULT (datetime('now'))
    )`);
    sqliteDb.run(`CREATE TABLE IF NOT EXISTS cron_jobs (
      id TEXT PRIMARY KEY, name TEXT NOT NULL, schedule TEXT NOT NULL,
      action TEXT NOT NULL, enabled INTEGER DEFAULT 1,
      last_run TEXT, next_run TEXT, run_count INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now'))
    )`);

    // Auto-save
    setInterval(() => {
      if (!sqliteDb) return;
      try {
        const data = sqliteDb.export();
        const fs = require('fs');
        fs.writeFileSync(DB_PATH, Buffer.from(data));
      } catch (e) { /* silent */ }
    }, 30000);

    console.log('[Cortex/Store] SQLite fallback initialized');
  } catch (err) {
    console.warn('[Cortex/Store] SQLite fallback unavailable:', err.message);
  }
}

// ---------------------------------------------------------------------------
//  Initialize Hybrid Storage
// ---------------------------------------------------------------------------
async function initStore(options = {}) {
  // 1. Try Redis
  try {
    redisClient.initRedis(options.redis || {});
    // Wait a moment for connection
    await new Promise(resolve => setTimeout(resolve, 1000));
    useRedis = redisClient.connected();
    if (useRedis) {
      console.log('[Cortex/Store] ✅ Redis connected (primary cache)');
    }
  } catch (err) {
    console.warn('[Cortex/Store] ⚠️ Redis unavailable, using in-memory fallback:', err.message);
  }

  // 2. Try PostgreSQL
  try {
    await pgClient.initPostgres(options.postgres || {});
    await pgClient.runMigrations();
    usePostgres = true;
    console.log('[Cortex/Store] ✅ PostgreSQL+pgvector connected (primary storage)');
  } catch (err) {
    console.warn('[Cortex/Store] ⚠️ PostgreSQL unavailable, using SQLite fallback:', err.message);
    await initSQLiteFallback();
  }

  console.log(`[Cortex/Store] Hybrid storage ready — Redis: ${useRedis ? '✅' : '❌ (in-memory)'} | PG: ${usePostgres ? '✅' : '❌ (SQLite)'}`);
}

// ---------------------------------------------------------------------------
//  Agent Status (Redis primary, in-memory fallback)
// ---------------------------------------------------------------------------
async function setAgentStatus(agentId, status) {
  // Always update in-memory
  memCache.agentStatus.set(agentId, {
    ...status,
    lastSeen: new Date().toISOString(),
  });

  // Redis if available
  if (useRedis) {
    await redisClient.setAgentStatus(agentId, status).catch(() => {});
  }
}

async function getAgentStatus(agentId) {
  // Try Redis first
  if (useRedis) {
    const s = await redisClient.getAgentStatus(agentId).catch(() => null);
    if (s) return s;
  }

  // Fallback to in-memory
  const s = memCache.agentStatus.get(agentId);
  if (!s) return null;
  const age = Date.now() - new Date(s.lastSeen).getTime();
  if (age > 60000) s.status = 'offline';
  return s;
}

async function getAllAgentStatuses() {
  if (useRedis) {
    const s = await redisClient.getAllAgentStatuses().catch(() => ({}));
    if (Object.keys(s).length > 0) return s;
  }

  const result = {};
  for (const [id] of memCache.agentStatus) {
    result[id] = await getAgentStatus(id);
  }
  return result;
}

// ---------------------------------------------------------------------------
//  Recent Chat (Redis primary, in-memory fallback)
// ---------------------------------------------------------------------------
async function pushChat(message) {
  memCache.recentChat.push(message);
  if (memCache.recentChat.length > memCache.RECENT_CHAT_MAX) {
    memCache.recentChat.shift();
  }
  memCache.metrics.totalMessages++;

  if (useRedis) {
    await redisClient.pushChat(message).catch(() => {});
    await redisClient.incrementMetric('totalMessages').catch(() => {});
  }
}

async function getRecentChat(limit = 50) {
  if (useRedis) {
    const items = await redisClient.getRecentChat(limit).catch(() => []);
    if (items.length > 0) return items;
  }
  return memCache.recentChat.slice(-limit);
}

// ---------------------------------------------------------------------------
//  Tasks (Redis primary, in-memory fallback)
// ---------------------------------------------------------------------------
async function setTask(taskId, task) {
  memCache.activeTasks.set(taskId, { ...task, updatedAt: new Date().toISOString() });
  if (useRedis) {
    await redisClient.setTask(taskId, task).catch(() => {});
  }
}

async function getTask(taskId) {
  if (useRedis) {
    const t = await redisClient.getTask(taskId).catch(() => null);
    if (t) return t;
  }
  return memCache.activeTasks.get(taskId) || null;
}

async function getActiveTasks() {
  if (useRedis) {
    const tasks = await redisClient.getActiveTasks().catch(() => []);
    if (tasks.length > 0) return tasks;
  }
  return Array.from(memCache.activeTasks.values())
    .filter(t => t.status !== 'done' && t.status !== 'cancelled')
    .sort((a, b) => (b.priority || 0) - (a.priority || 0));
}

async function removeTask(taskId) {
  memCache.activeTasks.delete(taskId);
  if (useRedis) {
    await redisClient.removeTask(taskId).catch(() => {});
  }
}

// ---------------------------------------------------------------------------
//  Message Pipes (Redis primary, in-memory fallback)
// ---------------------------------------------------------------------------
async function pipeSend(recipient, message) {
  if (!memCache.pipes.has(recipient)) memCache.pipes.set(recipient, []);
  memCache.pipes.get(recipient).push({ ...message, timestamp: new Date().toISOString(), read: false });

  if (useRedis) {
    await redisClient.pipeSend(recipient, message).catch(() => {});
  }
}

async function pipeRead(recipient, unreadOnly = true) {
  if (useRedis) {
    const msgs = await redisClient.pipeRead(recipient, unreadOnly).catch(() => []);
    if (msgs.length > 0) return msgs;
  }

  const messages = memCache.pipes.get(recipient) || [];
  if (unreadOnly) {
    const unread = messages.filter(m => !m.read);
    unread.forEach(m => { m.read = true; });
    return unread;
  }
  return messages;
}

// ---------------------------------------------------------------------------
//  Context
// ---------------------------------------------------------------------------
async function setContext(ctx) {
  memCache.context = { ...memCache.context, ...ctx };
  if (useRedis) await redisClient.setContext(ctx).catch(() => {});
}

async function getContext() {
  if (useRedis) {
    const c = await redisClient.getContext().catch(() => ({}));
    if (Object.keys(c).length > 0) return c;
  }
  return { ...memCache.context };
}

// ---------------------------------------------------------------------------
//  Locks
// ---------------------------------------------------------------------------
async function lock(resource, owner, ttlMs = 30000) {
  if (useRedis) return redisClient.lock(resource, owner, ttlMs);
  const existing = memCache.locks.get(resource);
  if (existing && existing.expiresAt > Date.now()) return false;
  memCache.locks.set(resource, { owner, expiresAt: Date.now() + ttlMs });
  return true;
}

async function unlock(resource, owner) {
  if (useRedis) return redisClient.unlock(resource, owner);
  const existing = memCache.locks.get(resource);
  if (existing && existing.owner === owner) {
    memCache.locks.delete(resource);
    return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
//  PostgreSQL Query Wrappers (fallback to SQLite)
// ---------------------------------------------------------------------------
async function queryAll(sql, ...params) {
  if (usePostgres) {
    // Convert ? placeholders to $N for pg
    return pgClient.queryAll(sql, params);
  }

  // SQLite fallback
  if (!sqliteDb) return [];
  try {
    const stmt = sqliteDb.prepare(sql);
    if (params.length > 0) stmt.bind(params);
    const results = [];
    while (stmt.step()) results.push(stmt.getAsObject());
    stmt.free();
    return results;
  } catch (err) {
    console.error('[Cortex/Store] SQLite query error:', err.message);
    return [];
  }
}

async function queryOne(sql, ...params) {
  const rows = await queryAll(sql, ...params);
  return rows[0] || null;
}

async function execute(sql, ...params) {
  if (usePostgres) {
    return pgClient.execute(sql, params);
  }

  if (!sqliteDb) return { changes: 0 };
  try {
    sqliteDb.run(sql, params);
    return { changes: sqliteDb.getRowsModified() };
  } catch (err) {
    console.error('[Cortex/Store] SQLite execute error:', err.message);
    return { changes: 0 };
  }
}

// ---------------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------------
function contentHash(text) {
  return crypto.createHash('sha256').update(text.trim().toLowerCase()).digest('hex').substring(0, 16);
}

function genId() {
  return crypto.randomUUID();
}

function getMetrics() {
  return { ...memCache.metrics };
}

function isPostgres() {
  return usePostgres;
}

function isRedis() {
  return useRedis;
}

// Graceful shutdown
async function shutdown() {
  if (useRedis) await redisClient.disconnect().catch(() => {});
  if (usePostgres) await pgClient.disconnect().catch(() => {});
  if (sqliteDb) {
    try {
      const fs = require('fs');
      const path = require('path');
      const DB_PATH = path.join(__dirname, '..', '..', 'cortex.db');
      fs.writeFileSync(DB_PATH, Buffer.from(sqliteDb.export()));
    } catch (e) { /* silent */ }
  }
}

module.exports = {
  initStore,
  shutdown,
  // Status flags
  isPostgres,
  isRedis,
  // Agent status
  setAgentStatus,
  getAgentStatus,
  getAllAgentStatuses,
  // Chat
  pushChat,
  getRecentChat,
  // Tasks
  setTask,
  getTask,
  getActiveTasks,
  removeTask,
  // Pipes
  pipeSend,
  pipeRead,
  // Context
  setContext,
  getContext,
  // Locks
  lock,
  unlock,
  // DB queries (PG or SQLite fallback)
  queryAll,
  queryOne,
  execute,
  // PG direct access
  pg: pgClient,
  redis: redisClient,
  // Helpers
  contentHash,
  genId,
  getMetrics,
  memCache,
};
