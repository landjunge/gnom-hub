// ============================================================================
//  Cortex v2 — Embedding Service
//  Generates vector embeddings for semantic search.
//  Uses OpenAI text-embedding-3-small (1536 dimensions).
//  Falls back to simple TF-IDF-like keyword vectors when no API key.
// ============================================================================

const crypto = require('crypto');

// ---------------------------------------------------------------------------
//  Embedding Cache (in-memory, avoids redundant API calls)
// ---------------------------------------------------------------------------
const embeddingCache = new Map();
const CACHE_MAX = 5000;

// ---------------------------------------------------------------------------
//  OpenAI Embedding (primary)
// ---------------------------------------------------------------------------
let openaiClient = null;

function initEmbeddings(apiKey) {
  if (apiKey) {
    try {
      const OpenAI = require('openai');
      openaiClient = new OpenAI({
        apiKey,
        baseURL: 'https://openrouter.ai/api/v1',
      });
      console.log('[Cortex/Embed] OpenRouter embeddings enabled (text-embedding-3-small)');
    } catch (err) {
      console.warn('[Cortex/Embed] OpenAI SDK not available, using local fallback');
    }
  } else {
    console.log('[Cortex/Embed] No API key — using local keyword embeddings');
  }
}

/**
 * Generate embedding for text.
 * @param {string} text
 * @returns {Promise<number[]|null>} 1536-dim vector or null
 */
async function embed(text) {
  if (!text || typeof text !== 'string') return null;

  const trimmed = text.trim().substring(0, 8000); // Max 8K chars
  const cacheKey = crypto.createHash('md5').update(trimmed).digest('hex');

  // Check cache
  if (embeddingCache.has(cacheKey)) {
    return embeddingCache.get(cacheKey);
  }

  let vector = null;

  // Try OpenAI
  if (openaiClient) {
    try {
      const resp = await openaiClient.embeddings.create({
        model: 'openai/text-embedding-3-small',
        input: trimmed,
      });
      vector = resp.data[0].embedding;
    } catch (err) {
      console.warn('[Cortex/Embed] OpenAI error, falling back:', err.message);
      vector = localEmbed(trimmed);
    }
  } else {
    vector = localEmbed(trimmed);
  }

  // Cache it
  if (vector) {
    if (embeddingCache.size >= CACHE_MAX) {
      // Evict oldest entry
      const firstKey = embeddingCache.keys().next().value;
      embeddingCache.delete(firstKey);
    }
    embeddingCache.set(cacheKey, vector);
  }

  return vector;
}

// ---------------------------------------------------------------------------
//  Local Fallback — Simple bag-of-words hash embedding
//  Not as good as OpenAI, but works offline and is instant.
//  Produces a 1536-dim vector (matching OpenAI dimensions for pgvector compat).
// ---------------------------------------------------------------------------
function localEmbed(text) {
  const DIM = 1536;
  const vector = new Float32Array(DIM).fill(0);
  const lower = text.toLowerCase();
  const words = lower.replace(/[^a-zäöüß0-9\s]/g, ' ').split(/\s+/).filter(w => w.length > 1);

  if (words.length === 0) return Array.from(vector);

  // Hash each word into multiple vector positions
  for (const word of words) {
    const hash = crypto.createHash('sha256').update(word).digest();
    for (let i = 0; i < 16; i++) {
      const pos = ((hash[i * 2] << 8) | hash[i * 2 + 1]) % DIM;
      const sign = (hash[(i + 16) % 32] & 1) ? 1 : -1;
      vector[pos] += sign * (1 / Math.sqrt(words.length));
    }
  }

  // Normalize to unit vector
  let norm = 0;
  for (let i = 0; i < DIM; i++) norm += vector[i] * vector[i];
  norm = Math.sqrt(norm);
  if (norm > 0) {
    for (let i = 0; i < DIM; i++) vector[i] /= norm;
  }

  return Array.from(vector);
}

/**
 * Cosine similarity between two vectors.
 * @param {number[]} a
 * @param {number[]} b
 * @returns {number} -1 to 1
 */
function cosineSimilarity(a, b) {
  if (!a || !b || a.length !== b.length) return 0;

  let dot = 0, normA = 0, normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }

  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom === 0 ? 0 : dot / denom;
}

/**
 * Find top-K most similar vectors from a list.
 * @param {number[]} query - Query vector
 * @param {Array<{id: string, embedding: number[]}>} candidates
 * @param {number} topK
 * @returns {Array<{id: string, score: number}>}
 */
function topKSimilar(query, candidates, topK = 5) {
  if (!query || candidates.length === 0) return [];

  const scored = candidates
    .filter(c => c.embedding)
    .map(c => ({
      id: c.id,
      score: cosineSimilarity(query, c.embedding),
    }))
    .sort((a, b) => b.score - a.score);

  return scored.slice(0, topK);
}

// ---------------------------------------------------------------------------
//  Exports
// ---------------------------------------------------------------------------
module.exports = {
  initEmbeddings,
  embed,
  localEmbed,
  cosineSimilarity,
  topKSimilar,
};
