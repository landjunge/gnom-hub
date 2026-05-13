// ============================================================================
//  Cortex v2 — Memory Service
//  CRUD + hybrid search (PostgreSQL pgvector primary, SQLite fallback)
// ============================================================================

const store = require('../db/store');
const embeddings = require('../embeddings');

// ---------------------------------------------------------------------------
//  Create Memory
// ---------------------------------------------------------------------------
async function createMemory({ content, summary, type = 'fact', importance = 5, source = 'system', tags = [], context = {} }) {
  const id = store.genId();

  // Dedup check
  if (store.isPostgres()) {
    const dupId = await store.pg.checkDuplicate(content);
    if (dupId) {
      store.memCache.metrics.filterSkipped++;
      return { id: dupId, deduplicated: true };
    }
  } else {
    const dup = await store.queryOne(`SELECT id FROM memories WHERE content = ?`, content);
    if (dup) {
      store.memCache.metrics.filterSkipped++;
      return { id: dup.id, deduplicated: true };
    }
  }

  // Generate embedding
  const embedding = await embeddings.embed(content);

  try {
    if (store.isPostgres()) {
      await store.pg.insertMemory({
        id, content, summary, type, importance, source, tags, embedding, context,
      });
    } else {
      await store.execute(
        `INSERT INTO memories (id, content, summary, memory_type, importance, source, tags, embedding, context, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))`,
        id, content, summary || null, type, importance, source,
        JSON.stringify(tags), embedding ? JSON.stringify(embedding) : null,
        JSON.stringify(context)
      );
    }
  } catch (err) {
    console.error('[Cortex/Memory] Insert error:', err.message);
    return { id, deduplicated: false, error: err.message };
  }

  store.memCache.metrics.totalMemories++;
  return { id, deduplicated: false };
}

// ---------------------------------------------------------------------------
//  Search Memories (hybrid: keyword + vector)
// ---------------------------------------------------------------------------
async function searchMemories(query, { limit = 10, type, minImportance, source } = {}) {
  const queryEmbedding = await embeddings.embed(query);

  if (store.isPostgres() && queryEmbedding) {
    // PostgreSQL native vector search — much faster and more accurate
    const vectorResults = await store.pg.vectorSearchMemories(queryEmbedding, {
      limit, type, minImportance, minScore: 0.2,
    });
    return vectorResults.map(formatMemoryPg);
  }

  // Fallback: SQLite keyword + JS-side vector re-ranking
  const keywords = query.toLowerCase().split(/\s+/).filter(w => w.length > 2);
  let sql = `SELECT * FROM memories WHERE 1=1`;
  const params = [];

  if (type) { sql += ` AND memory_type = ?`; params.push(type); }
  if (minImportance) { sql += ` AND importance >= ?`; params.push(minImportance); }
  if (source) { sql += ` AND source = ?`; params.push(source); }
  if (keywords.length > 0) {
    const clauses = keywords.map(() => `LOWER(content) LIKE ?`);
    sql += ` AND (${clauses.join(' OR ')})`;
    params.push(...keywords.map(k => `%${k}%`));
  }
  sql += ` ORDER BY importance DESC, created_at DESC LIMIT ?`;
  params.push(limit * 3);

  const keywordResults = await store.queryAll(sql, ...params);

  if (!queryEmbedding || keywordResults.length === 0) {
    return keywordResults.slice(0, limit).map(formatMemory);
  }

  // Re-rank by vector similarity
  const withScores = keywordResults.map(row => {
    let score = 0;
    if (row.embedding) {
      try {
        const emb = JSON.parse(row.embedding);
        score = embeddings.cosineSimilarity(queryEmbedding, emb);
      } catch {}
    }
    return { ...row, score, hybridScore: score * 0.6 + (row.importance / 10) * 0.4 };
  });

  withScores.sort((a, b) => b.hybridScore - a.hybridScore);
  return withScores.slice(0, limit).map(formatMemory);
}

// ---------------------------------------------------------------------------
//  Pure Vector Search (for proactive recall)
// ---------------------------------------------------------------------------
async function vectorSearch(query, { limit = 5, minScore = 0.3 } = {}) {
  const queryEmbedding = await embeddings.embed(query);
  if (!queryEmbedding) return [];

  if (store.isPostgres()) {
    const results = await store.pg.vectorSearchMemories(queryEmbedding, { limit, minScore });
    return results.map(r => ({
      ...formatMemoryPg(r),
      score: Math.round(parseFloat(r.score) * 100) / 100,
    }));
  }

  // SQLite fallback: brute-force cosine similarity
  const rows = await store.queryAll(
    `SELECT id, content, summary, memory_type, importance, source, tags, embedding, created_at
     FROM memories WHERE embedding IS NOT NULL ORDER BY created_at DESC LIMIT 1000`
  );

  return rows
    .map(row => {
      try {
        const emb = JSON.parse(row.embedding);
        const score = embeddings.cosineSimilarity(queryEmbedding, emb);
        return { ...row, score };
      } catch { return null; }
    })
    .filter(r => r && r.score >= minScore)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map(r => ({ ...formatMemory(r), score: Math.round(r.score * 100) / 100 }));
}

// ---------------------------------------------------------------------------
//  Get / Update / Delete
// ---------------------------------------------------------------------------
async function getMemory(id) {
  if (store.isPostgres()) {
    const row = await store.pg.queryOne('SELECT * FROM memories WHERE id = $1', [id]);
    return row ? formatMemoryPg(row) : null;
  }
  const row = await store.queryOne('SELECT * FROM memories WHERE id = ?', id);
  return row ? formatMemory(row) : null;
}

async function getRecentMemories(limit = 20) {
  if (store.isPostgres()) {
    const rows = await store.pg.queryAll(
      'SELECT * FROM memories ORDER BY created_at DESC LIMIT $1', [limit]
    );
    return rows.map(formatMemoryPg);
  }
  const rows = await store.queryAll('SELECT * FROM memories ORDER BY created_at DESC LIMIT ?', limit);
  return rows.map(formatMemory);
}

async function updateMemory(id, updates) {
  if (store.isPostgres()) {
    const sets = [];
    const params = [];
    let idx = 1;
    for (const [key, value] of Object.entries(updates)) {
      if (['content', 'summary', 'memory_type', 'importance', 'source'].includes(key)) {
        sets.push(`${key} = $${idx++}`);
        params.push(value);
      }
      if (key === 'tags') {
        sets.push(`tags = $${idx++}`);
        params.push(value);
      }
    }
    if (sets.length === 0) return false;
    params.push(id);
    await store.pg.execute(`UPDATE memories SET ${sets.join(', ')} WHERE id = $${idx}`, params);
    return true;
  }

  const fields = [];
  const params = [];
  for (const [key, value] of Object.entries(updates)) {
    if (['content', 'summary', 'memory_type', 'importance', 'source'].includes(key)) {
      fields.push(`${key} = ?`); params.push(value);
    }
    if (key === 'tags') {
      fields.push('tags = ?'); params.push(JSON.stringify(value));
    }
  }
  if (fields.length === 0) return false;
  fields.push("updated_at = datetime('now')");
  params.push(id);
  await store.execute(`UPDATE memories SET ${fields.join(', ')} WHERE id = ?`, ...params);
  return true;
}

async function deleteMemory(id) {
  if (store.isPostgres()) {
    const r = await store.pg.execute('DELETE FROM memories WHERE id = $1', [id]);
    return r.changes > 0;
  }
  const r = await store.execute('DELETE FROM memories WHERE id = ?', id);
  return r.changes > 0;
}

async function recordRecall(id) {
  if (store.isPostgres()) {
    await store.pg.execute(
      'UPDATE memories SET recalled_count = recalled_count + 1, last_recalled = NOW() WHERE id = $1', [id]
    );
  } else {
    await store.execute(
      `UPDATE memories SET recalled_count = recalled_count + 1, last_recalled = datetime('now') WHERE id = ?`, id
    );
  }
  store.memCache.metrics.totalRecalls++;
}

async function getStats() {
  if (store.isPostgres()) {
    const pgStats = await store.pg.getStats();
    return {
      totalMemories: pgStats.memories,
      byType: pgStats.byType,
      avgImportance: pgStats.avgImportance,
      topRecalled: [],
      cacheMetrics: store.getMetrics(),
    };
  }

  const total = await store.queryOne('SELECT COUNT(*) as count FROM memories');
  const byType = await store.queryAll('SELECT memory_type, COUNT(*) as count FROM memories GROUP BY memory_type');
  const avgImportance = await store.queryOne('SELECT AVG(importance) as avg FROM memories');

  return {
    totalMemories: total?.count || 0,
    byType: Object.fromEntries(byType.map(r => [r.memory_type, r.count])),
    avgImportance: Math.round((avgImportance?.avg || 0) * 10) / 10,
    topRecalled: [],
    cacheMetrics: store.getMetrics(),
  };
}

// ---------------------------------------------------------------------------
//  Format Helpers
// ---------------------------------------------------------------------------
function formatMemory(row) {
  if (!row) return null;
  return {
    id: row.id,
    content: row.content,
    summary: row.summary,
    type: row.memory_type,
    importance: row.importance,
    source: row.source,
    tags: safeParse(row.tags, []),
    recalledCount: row.recalled_count || 0,
    lastRecalled: row.last_recalled,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function formatMemoryPg(row) {
  if (!row) return null;
  return {
    id: row.id,
    content: row.content,
    summary: row.summary,
    type: row.memory_type,
    importance: row.importance,
    source: row.source,
    tags: row.tags || [],
    recalledCount: row.recalled_count || 0,
    lastRecalled: row.last_recalled,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function safeParse(str, fallback) {
  try { return JSON.parse(str); } catch { return fallback; }
}

module.exports = {
  createMemory, searchMemories, vectorSearch,
  getMemory, getRecentMemories, updateMemory, deleteMemory,
  recordRecall, getStats,
};
