// ============================================================================
//  Cortex v2 — Main Engine
//  Observes, filters, stores, recalls. Single entry point for all services.
// ============================================================================

const store = require('./db/store');
const filter = require('./filter');
const { initEmbeddings } = require('./embeddings');

let memoryService, agentService, taskService, pipeService, decisionService, cronService, recallService;
let broadcastFn = null;
let initialized = false;

async function init(options = {}) {
  const { openaiKey, agentsConfig, broadcast } = options;

  // 1. Initialize hybrid storage (Redis + PostgreSQL, fallback to in-memory + SQLite)
  await store.initStore(options);

  // 2. Load services
  memoryService = require('./services/memory');
  agentService = require('./services/agents');
  taskService = require('./services/tasks');
  pipeService = require('./services/pipe');
  decisionService = require('./services/decisions');
  cronService = require('./services/cron');
  recallService = require('./services/recall');

  // 3. Initialize embeddings
  initEmbeddings(openaiKey || process.env.OPENAI_API_KEY);

  // 4. Sync agents from config
  if (agentsConfig) await agentService.syncFromFile(agentsConfig);

  // 5. Init cron
  await cronService.init();
  cronService.onCronExec((jobId, action) => {
    console.log(`[Cortex/Cron] Executing job ${jobId}:`, action);
  });

  broadcastFn = broadcast || null;

  // Wire public API
  cortex.memory = {
    create: memoryService.createMemory,
    search: memoryService.searchMemories,
    vectorSearch: memoryService.vectorSearch,
    get: memoryService.getMemory,
    getRecent: memoryService.getRecentMemories,
    update: memoryService.updateMemory,
    delete: memoryService.deleteMemory,
  };
  cortex.agents = {
    register: agentService.registerAgent,
    heartbeat: agentService.heartbeat,
    get: agentService.getAgent,
    getAll: agentService.getAllAgents,
    getStatus: agentService.getAgentStatus,
    getAllStatuses: agentService.getAllAgentStatuses,
    remove: agentService.removeAgent,
    sync: agentService.syncFromFile,
    incrementMessages: agentService.incrementMessages,
  };
  cortex.tasks = {
    create: taskService.createTask,
    update: taskService.updateTask,
    complete: taskService.completeTask,
    get: taskService.getTask,
    getActive: taskService.getActiveTasks,
    getOverdue: taskService.getOverdueTasks,
  };
  cortex.decisions = {
    create: decisionService.createDecision,
    get: decisionService.getDecisions,
    search: decisionService.searchDecisions,
    supersede: decisionService.supersedeDecision,
  };
  cortex.pipe = {
    send: pipeService.send,
    read: pipeService.read,
    broadcast: pipeService.broadcast,
  };
  cortex.cron = {
    create: cronService.createJob,
    list: cronService.listJobs,
    toggle: cronService.toggleJob,
    delete: cronService.deleteJob,
  };
  cortex.recallHelpers = {
    checkContradictions: recallService.checkContradictions,
    formatRecalls: recallService.formatRecalls,
  };

  initialized = true;
  console.log('[Cortex v2] ✨ Engine initialized');
  return cortex;
}

async function observe(content, meta = {}) {
  if (!initialized) return { stored: false, classification: null };
  const { role = 'user', agent = 'conductor', session = 'default' } = meta;

  await store.pushChat({ content, role, agent, session, timestamp: new Date().toISOString() });

  const classification = await filter.classify(content, { role, agent });
  if (!classification.persist) return { stored: false, classification };

  const result = await memoryService.createMemory({
    content, type: classification.type, importance: classification.importance,
    source: agent || role, tags: classification.tags, context: { role, agent, session },
  });

  if (classification.type === 'task' && classification.taskAction === 'create') {
    await taskService.createTask({ title: content.substring(0, 120), description: content, source: agent || role, tags: classification.tags });
  }
  if (classification.type === 'decision') {
    await decisionService.createDecision({ title: content.substring(0, 120), outcome: content, participants: agent ? [agent] : [], tags: classification.tags });
  }
  if (agent && agent !== 'system' && agent !== 'user') {
    await agentService.incrementMessages(agent);
  }

  return { stored: true, classification, memoryId: result.id, deduplicated: result.deduplicated };
}

async function recall(message, opts = {}) {
  if (!initialized) return { memories: [], decisions: [], tasks: [], hasRecalls: false };
  return recallService.recall(message, opts);
}

async function search(query, opts = {}) {
  if (!initialized) return [];
  return memoryService.searchMemories(query, opts);
}

function stats() {
  if (!initialized) return { version: '2.0.0', status: 'initializing' };
  const memStats = memoryService.getStats();
  return {
    version: '2.0.0',
    engine: 'cortex-v2',
    storage: {
      postgres: store.isPostgres() ? '✅' : '❌ (SQLite fallback)',
      redis: store.isRedis() ? '✅' : '❌ (in-memory fallback)',
    },
    metrics: store.getMetrics(),
    uptime: process.uptime(),
  };
}

const cortex = {
  init, observe, recall, search, stats,
  memory: {}, agents: {}, tasks: {}, decisions: {}, pipe: {}, cron: {},
  filter: { classify: filter.classify, extractKeywords: filter.extractKeywords },
  cache: { getRecentChat: (...a) => store.getRecentChat(...a), getContext: () => store.getContext(), setContext: (c) => store.setContext(c) },
  recallHelpers: {},
};

module.exports = cortex;
