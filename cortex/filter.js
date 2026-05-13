// ============================================================================
//  Cortex v2 — Intelligent Filter (LLM-based via OpenRouter)
//  Classifies incoming messages by importance and type.
// ============================================================================

const OpenAI = require('openai');

let openaiClient = null;

function getClient() {
  if (openaiClient) return openaiClient;
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) return null;
  
  openaiClient = new OpenAI({
    apiKey,
    baseURL: 'https://openrouter.ai/api/v1',
  });
  return openaiClient;
}

/**
 * @typedef {Object} FilterResult
 * @property {'decision'|'fact'|'event'|'task'|'insight'|'chat'|'skip'} type
 * @property {number} importance - 1-10
 * @property {boolean} persist - Should this go to long-term storage?
 * @property {string[]} tags - Auto-detected tags
 * @property {string|null} taskAction - If task detected, what action
 * @property {string} reason - Why this classification was chosen
 */

/**
 * Classify a message for storage importance using an LLM.
 * @param {string} content - The message content
 * @param {Object} meta - Metadata (role, agent, session)
 * @returns {Promise<FilterResult>}
 */
async function classify(content, meta = {}) {
  if (!content || typeof content !== 'string') {
    return { type: 'skip', importance: 0, persist: false, tags: [], taskAction: null, reason: 'empty' };
  }

  const text = content.trim();

  // -- Fast skip for noise & very short messages to save API calls --
  if (/^\s*$/.test(text) || text.length < 5 || /^[?!.]+$/.test(text)) {
    return { type: 'skip', importance: 0, persist: false, tags: [], taskAction: null, reason: 'noise_or_too_short' };
  }

  const client = getClient();
  if (!client) {
    console.warn('[Cortex/Filter] No OPENROUTER_API_KEY found, returning default skip.');
    return { type: 'skip', importance: 0, persist: false, tags: [], taskAction: null, reason: 'no_api_key' };
  }

  const roleStr = meta.role === 'agent' ? `(Gesendet von Agent: ${meta.agent || 'unbekannt'})` : `(Gesendet vom User)`;

  const prompt = `
Du bist der intelligente Speicher-Filter des Cortex v2 Systems.
Analysiere die folgende Nachricht auf ihre Bedeutung für das Langzeitgedächtnis.

Bewerte die Nachricht und antworte AUSSCHLIESSLICH mit einem JSON-Objekt, ohne Markdown oder Text drumherum.
Das JSON-Objekt muss folgende Struktur exakt einhalten:
{
  "importance": <Zahl von 1 bis 10>,
  "memory_type": "<'fact' | 'decision' | 'event' | 'task' | 'ignore'>",
  "summary": "<Kurze Zusammenfassung der Bedeutung, max 15 Wörter>",
  "tags": ["<tag1>", "<tag2>", "<tag3>"]
}

Richtlinien für Wichtigkeit (importance):
- WICHTIG: Nachrichten vom User sollen grundsätzlich eine höhere Priorität bekommen als Nachrichten von Agenten.
- WICHTIG: Bevorzuge die Speicherung der ursprünglichen Nachricht des Users. Wenn es sich um die Antwort/Bestätigung eines Agenten handelt (z.B. "Verstanden", "Ist notiert"), stufe die Wichtigkeit auf 1-4 herab.
- 1-4: Chat, Grundrauschen, irrelevante Floskeln, Agenten-Bestätigungen (werden ignoriert)
- 5-6: Normale Fakten, nützliche Infos, kleine Tasks
- 7-8: Wichtige Fakten, Regeln, Verbote, Entscheidungen ("muss", "darf nie", "ab sofort")
- 9-10: Kritische Architektur-Entscheidungen, Systemwarnungen ("ENTSCHEIDUNG", "WICHTIG")

Nachricht ${roleStr}: "${text}"
  `;

  try {
    const response = await client.chat.completions.create({
      model: 'xiaomi/mimo-v2-flash',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.1,
    });

    let resultStr = response.choices[0].message.content.trim();
    // Defensive parsing in case the model wraps it in markdown
    if (resultStr.startsWith('```json')) {
      resultStr = resultStr.replace(/```json/gi, '').replace(/```/g, '').trim();
    } else if (resultStr.startsWith('```')) {
      resultStr = resultStr.replace(/```/g, '').trim();
    }

    const result = JSON.parse(resultStr);

    let type = result.memory_type || 'ignore';
    if (type === 'ignore') type = 'skip';

    const importance = typeof result.importance === 'number' ? result.importance : 3;
    const persist = importance >= 5;

    let taskAction = null;
    if (type === 'task') taskAction = 'create';

    return {
      type: type === 'ignore' ? 'skip' : type,
      importance,
      persist,
      tags: Array.isArray(result.tags) ? result.tags.map(t => String(t).toLowerCase()) : [],
      taskAction,
      reason: result.summary || 'llm_classified',
    };
  } catch (error) {
    console.error('[Cortex/Filter] LLM classification failed:', error.message);
    // Fallback if API or JSON parse fails
    return { type: 'chat', importance: 3, persist: false, tags: [], taskAction: null, reason: 'api_error_fallback' };
  }
}

function extractKeywords(text) {
  if (!text) return [];
  const lower = text.toLowerCase();
  const stopWords = new Set(['der', 'die', 'das', 'ein', 'eine', 'und', 'oder', 'aber', 'in', 'von', 'mit', 'für', 'auf', 'ist', 'sind']);
  return lower.replace(/[^a-zäöüß0-9\s@_-]/g, ' ').split(/\s+/).filter(w => w.length > 2 && !stopWords.has(w)).slice(0, 20);
}

module.exports = { classify, extractKeywords };
