// ============================================================================
//  Cortex v2 — Proactive Recall Service
//  Automatically surfaces relevant memories when context matches
// ============================================================================

const memory = require('./memory');
const decisions = require('./decisions');
const tasks = require('./tasks');
const store = require('../db/store');
const { extractKeywords } = require('../filter');

// ---------------------------------------------------------------------------
//  Recall — Find relevant memories for a given input
// ---------------------------------------------------------------------------

/**
 * Perform proactive recall on a message.
 * Returns relevant memories, decisions, and overdue tasks.
 * @param {string} message - The incoming chat message
 * @param {Object} opts
 * @returns {Promise<{memories: Array, decisions: Array, tasks: Array, hasRecalls: boolean}>}
 */
async function recall(message, { minScore = 0.4, limit = 3 } = {}) {
  if (!message || message.length < 10) {
    return { memories: [], decisions: [], tasks: [], hasRecalls: false };
  }

  const results = await Promise.allSettled([
    // 1. Vector search in memories
    memory.vectorSearch(message, { limit, minScore }),

    // 2. Search decisions
    decisions.searchDecisions(message, 2),

    // 3. Check overdue tasks
    tasks.getOverdueTasks(24),
  ]);

  const foundMemories = results[0].status === 'fulfilled' ? results[0].value : [];
  const foundDecisions = results[1].status === 'fulfilled' ? results[1].value : [];
  const overdueTasks = results[2].status === 'fulfilled' ? results[2].value : [];

  // Mark recalled memories
  for (const mem of foundMemories) {
    if (mem.id) await memory.recordRecall(mem.id);
  }

  const hasRecalls = foundMemories.length > 0 || foundDecisions.length > 0 || overdueTasks.length > 0;

  return {
    memories: foundMemories,
    decisions: foundDecisions,
    tasks: overdueTasks.slice(0, 3),
    hasRecalls,
  };
}

/**
 * Check if a message contradicts any existing decision.
 * Simple keyword-based check (not LLM).
 * @param {string} message
 * @returns {Promise<Array>}
 */
async function checkContradictions(message) {
  const keywords = extractKeywords(message);
  if (keywords.length < 2) return [];

  const recentDecisions = await decisions.getDecisions(20);
  const contradictions = [];

  // Simple heuristic: if message contains negation + decision keywords
  const negations = ['nicht', 'kein', 'nie', 'stop', 'cancel', 'abort', 'revert', 'undo', 'doch nicht'];
  const hasNegation = negations.some(n => message.toLowerCase().includes(n));

  if (!hasNegation) return [];

  for (const decision of recentDecisions) {
    const decisionKeywords = extractKeywords(`${decision.title} ${decision.outcome}`);
    const overlap = keywords.filter(k => decisionKeywords.includes(k));

    if (overlap.length >= 2) {
      contradictions.push({
        decision,
        overlappingKeywords: overlap,
        warning: `⚠️ Möglicher Widerspruch zur Entscheidung: "${decision.title}"`,
      });
    }
  }

  return contradictions;
}

/**
 * Format recalls for display in chat.
 * @param {Object} recalls
 * @returns {string|null}
 */
function formatRecalls(recalls) {
  if (!recalls.hasRecalls) return null;

  const parts = [];

  if (recalls.memories.length > 0) {
    parts.push('**💡 Relevante Erinnerungen:**');
    for (const mem of recalls.memories) {
      const score = mem.score ? ` (${Math.round(mem.score * 100)}%)` : '';
      const summary = mem.summary || mem.content.substring(0, 120);
      parts.push(`• ${summary}${score}`);
    }
  }

  if (recalls.decisions.length > 0) {
    parts.push('');
    parts.push('**📋 Relevante Entscheidungen:**');
    for (const dec of recalls.decisions) {
      parts.push(`• **${dec.title}** → ${dec.outcome}`);
    }
  }

  if (recalls.tasks.length > 0) {
    parts.push('');
    parts.push('**⏰ Offene Aufgaben:**');
    for (const task of recalls.tasks) {
      const age = Math.round((Date.now() - new Date(task.createdAt).getTime()) / 3600000);
      parts.push(`• ${task.title} (seit ${age}h offen)`);
    }
  }

  return parts.join('\n');
}

module.exports = { recall, checkContradictions, formatRecalls };
