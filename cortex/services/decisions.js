// ============================================================================
//  Cortex v2 — Decision Service
//  PostgreSQL+pgvector primary, SQLite fallback
// ============================================================================

const store = require('../db/store');
const embeddings = require('../embeddings');

async function createDecision({ title, reasoning = '', outcome, participants = [], tags = [] }) {
  const id = store.genId();
  const embedding = await embeddings.embed(`${title} ${outcome} ${reasoning}`);

  if (store.isPostgres()) {
    await store.pg.insertDecision({ id, title, reasoning, outcome, participants, tags, embedding });
    // Also store as high-importance memory
    const memContent = `[ENTSCHEIDUNG] ${title}: ${outcome}${reasoning ? ` (Grund: ${reasoning})` : ''}`;
    await store.pg.insertMemory({
      id: store.genId(), content: memContent, type: 'decision',
      importance: 10, source: 'cortex', tags: ['decision', ...tags], embedding, context: {},
    });
  } else {
    await store.execute(
      `INSERT INTO decisions (id, title, reasoning, outcome, participants, tags, embedding, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))`,
      id, title, reasoning, outcome, JSON.stringify(participants), JSON.stringify(tags),
      embedding ? JSON.stringify(embedding) : null
    );
    const memContent = `[ENTSCHEIDUNG] ${title}: ${outcome}${reasoning ? ` (Grund: ${reasoning})` : ''}`;
    await store.execute(
      `INSERT INTO memories (id, content, memory_type, importance, source, tags, embedding, created_at, updated_at)
       VALUES (?, ?, 'decision', 10, 'cortex', ?, ?, datetime('now'), datetime('now'))`,
      store.genId(), memContent, JSON.stringify(['decision', ...tags]),
      embedding ? JSON.stringify(embedding) : null
    );
  }

  return { id, title, outcome };
}

async function getDecisions(limit = 10) {
  if (store.isPostgres()) {
    const rows = await store.pg.getDecisions(limit);
    return rows.map(formatDecisionPg);
  }
  const rows = await store.queryAll(
    'SELECT * FROM decisions WHERE superseded_by IS NULL ORDER BY created_at DESC LIMIT ?', limit
  );
  return rows.map(formatDecision);
}

async function searchDecisions(query, limit = 5) {
  const queryEmbedding = await embeddings.embed(query);

  if (store.isPostgres() && queryEmbedding) {
    const rows = await store.pg.vectorSearchDecisions(queryEmbedding, limit);
    return rows.map(r => ({
      ...formatDecisionPg(r),
      score: Math.round(parseFloat(r.score) * 100) / 100,
    }));
  }

  // SQLite fallback
  if (!queryEmbedding) {
    const rows = await store.queryAll(
      `SELECT * FROM decisions WHERE (LOWER(title) LIKE ? OR LOWER(outcome) LIKE ?) AND superseded_by IS NULL ORDER BY created_at DESC LIMIT ?`,
      `%${query.toLowerCase()}%`, `%${query.toLowerCase()}%`, limit
    );
    return rows.map(formatDecision);
  }

  const rows = await store.queryAll(
    'SELECT * FROM decisions WHERE superseded_by IS NULL AND embedding IS NOT NULL ORDER BY created_at DESC LIMIT 100'
  );
  return rows
    .map(row => {
      const emb = safeParse(row.embedding, null);
      const score = emb ? embeddings.cosineSimilarity(queryEmbedding, emb) : 0;
      return { ...row, score };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map(r => ({ ...formatDecision(r), score: Math.round(r.score * 100) / 100 }));
}

async function supersedeDecision(oldId, newId) {
  if (store.isPostgres()) {
    await store.pg.execute('UPDATE decisions SET superseded_by = $1 WHERE id = $2', [newId, oldId]);
  } else {
    await store.execute('UPDATE decisions SET superseded_by = ? WHERE id = ?', newId, oldId);
  }
}

function formatDecision(row) {
  return {
    id: row.id, title: row.title, reasoning: row.reasoning, outcome: row.outcome,
    participants: safeParse(row.participants, []), tags: safeParse(row.tags, []),
    createdAt: row.created_at,
  };
}

function formatDecisionPg(row) {
  return {
    id: row.id, title: row.title, reasoning: row.reasoning, outcome: row.outcome,
    participants: row.participants || [], tags: row.tags || [],
    createdAt: row.created_at,
  };
}

function safeParse(str, fallback) {
  try { return JSON.parse(str); } catch { return fallback; }
}

module.exports = { createDecision, getDecisions, searchDecisions, supersedeDecision };
