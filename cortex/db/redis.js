// ============================================================================
//  Cortex v2 — Redis Client
//  Fast cache layer for hot data: agent status, recent chat, pipes, tasks
// ============================================================================

const Redis = require('ioredis');

let redis = null;
let isConnected = false;

const PREFIX = 'cortex:';

// ---------------------------------------------------------------------------
//  Connection
// ---------------------------------------------------------------------------
function initRedis(options = {}) {
  const {
    host = process.env.REDIS_HOST || '127.0.0.1',
    port = process.env.REDIS_PORT || 6379,
    password = process.env.REDIS_PASSWORD || undefined,
    db = process.env.REDIS_DB || 0,
  } = options;

  redis = new Redis({
    host,
    port: parseInt(port),
    password,
    db: parseInt(db),
    retryStrategy: (times) => Math.min(times * 200, 5000),
    maxRetriesPerRequest: 3,
    lazyConnect: false,
  });

  redis.on('connect', () => {
    isConnected = true;
    console.log(`[Cortex/Redis] Connected to ${host}:${port}`);
  });

  redis.on('error', (err) => {
    if (isConnected) {
      console.error('[Cortex/Redis] Error:', err.message);
    }
    isConnected = false;
  });

  redis.on('close', () => {
    isConnected = false;
  });

  return redis;
}

function getRedis() {
  return redis;
}

function connected() {
  return isConnected;
}

// ---------------------------------------------------------------------------
//  Agent Status (Hash per agent, 60s TTL)
// ---------------------------------------------------------------------------
async function setAgentStatus(agentId, { status = 'idle', activity = '', pid, port }) {
  if (!isConnected) return;
  const key = `${PREFIX}agents:${agentId}`;
  await redis.hmset(key, {
    status,
    activity,
    pid: pid || '',
    port: port || '',
    lastSeen: new Date().toISOString(),
  });
  await redis.expire(key, 60); // 60s heartbeat TTL
}

async function getAgentStatus(agentId) {
  if (!isConnected) return null;
  const key = `${PREFIX}agents:${agentId}`;
  const data = await redis.hgetall(key);
  if (!data || !data.status) return null;
  return data;
}

async function getAllAgentStatuses() {
  if (!isConnected) return {};
  const keys = await redis.keys(`${PREFIX}agents:*`);
  const result = {};
  for (const key of keys) {
    const agentId = key.replace(`${PREFIX}agents:`, '');
    // Skip the registry key
    if (agentId === 'registry') continue;
    result[agentId] = await redis.hgetall(key);
  }
  return result;
}

// ---------------------------------------------------------------------------
//  Recent Chat (List, max 200, FIFO)
// ---------------------------------------------------------------------------
async function pushChat(message) {
  if (!isConnected) return;
  const key = `${PREFIX}chat:recent`;
  await redis.rpush(key, JSON.stringify(message));
  await redis.ltrim(key, -200, -1); // Keep last 200
}

async function getRecentChat(limit = 50) {
  if (!isConnected) return [];
  const key = `${PREFIX}chat:recent`;
  const items = await redis.lrange(key, -limit, -1);
  return items.map(i => { try { return JSON.parse(i); } catch { return null; } }).filter(Boolean);
}

// ---------------------------------------------------------------------------
//  Active Tasks (Sorted Set, score = priority)
// ---------------------------------------------------------------------------
async function setTask(taskId, task) {
  if (!isConnected) return;
  await redis.hset(`${PREFIX}tasks:${taskId}`, {
    data: JSON.stringify(task),
    updatedAt: new Date().toISOString(),
  });
  await redis.zadd(`${PREFIX}tasks:active`, task.priority || 5, taskId);
}

async function getTask(taskId) {
  if (!isConnected) return null;
  const data = await redis.hget(`${PREFIX}tasks:${taskId}`, 'data');
  return data ? JSON.parse(data) : null;
}

async function getActiveTasks() {
  if (!isConnected) return [];
  const ids = await redis.zrevrange(`${PREFIX}tasks:active`, 0, -1);
  const tasks = [];
  for (const id of ids) {
    const task = await getTask(id);
    if (task && task.status !== 'done' && task.status !== 'cancelled') {
      tasks.push(task);
    }
  }
  return tasks;
}

async function removeTask(taskId) {
  if (!isConnected) return;
  await redis.del(`${PREFIX}tasks:${taskId}`);
  await redis.zrem(`${PREFIX}tasks:active`, taskId);
}

// ---------------------------------------------------------------------------
//  Message Pipes (List per agent)
// ---------------------------------------------------------------------------
async function pipeSend(recipient, message) {
  if (!isConnected) return;
  const key = `${PREFIX}pipe:${recipient}`;
  await redis.rpush(key, JSON.stringify({
    ...message,
    timestamp: new Date().toISOString(),
    read: false,
  }));
}

async function pipeRead(recipient, unreadOnly = true) {
  if (!isConnected) return [];
  const key = `${PREFIX}pipe:${recipient}`;
  const items = await redis.lrange(key, 0, -1);
  // Clear the pipe after reading
  if (unreadOnly) {
    await redis.del(key);
  }
  return items.map(i => { try { return JSON.parse(i); } catch { return null; } }).filter(Boolean);
}

// ---------------------------------------------------------------------------
//  Current Context (Hash)
// ---------------------------------------------------------------------------
async function setContext(ctx) {
  if (!isConnected) return;
  const key = `${PREFIX}context:current`;
  await redis.hmset(key, Object.fromEntries(
    Object.entries(ctx).map(([k, v]) => [k, typeof v === 'object' ? JSON.stringify(v) : String(v)])
  ));
  await redis.expire(key, 86400); // 24h
}

async function getContext() {
  if (!isConnected) return {};
  const key = `${PREFIX}context:current`;
  return await redis.hgetall(key);
}

// ---------------------------------------------------------------------------
//  Distributed Locks (SET NX PX)
// ---------------------------------------------------------------------------
async function lock(resource, owner, ttlMs = 30000) {
  if (!isConnected) return false;
  const key = `${PREFIX}locks:${resource}`;
  const result = await redis.set(key, owner, 'PX', ttlMs, 'NX');
  return result === 'OK';
}

async function unlock(resource, owner) {
  if (!isConnected) return false;
  const key = `${PREFIX}locks:${resource}`;
  const current = await redis.get(key);
  if (current === owner) {
    await redis.del(key);
    return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
//  Metrics
// ---------------------------------------------------------------------------
async function incrementMetric(name) {
  if (!isConnected) return;
  await redis.incr(`${PREFIX}metrics:${name}`);
}

async function getMetrics() {
  if (!isConnected) return {};
  const keys = await redis.keys(`${PREFIX}metrics:*`);
  const result = {};
  for (const key of keys) {
    const name = key.replace(`${PREFIX}metrics:`, '');
    result[name] = parseInt(await redis.get(key) || '0');
  }
  return result;
}

// ---------------------------------------------------------------------------
//  Cleanup
// ---------------------------------------------------------------------------
async function disconnect() {
  if (redis) {
    await redis.quit();
    isConnected = false;
  }
}

module.exports = {
  initRedis,
  getRedis,
  connected,
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
  // Metrics
  incrementMetric,
  getMetrics,
  // Lifecycle
  disconnect,
};
