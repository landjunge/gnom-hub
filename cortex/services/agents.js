// ============================================================================
//  Cortex v2 — Agent Registry Service
//  PostgreSQL primary, SQLite fallback. Redis for live status.
// ============================================================================

const store = require('../db/store');

// ---------------------------------------------------------------------------
//  Register / Update Agent
// ---------------------------------------------------------------------------
async function registerAgent({ id, name, type = 'agent', icon = '🤖', color = '#64748b', description = '', port = null, mcp_transport, mcp_endpoint, mcp_capabilities }) {
  if (store.isPostgres()) {
    await store.pg.upsertAgent({
      id, name, type, icon, color, description, port,
      mcp_transport, mcp_endpoint, mcp_capabilities,
    });
  } else {
    const existing = await store.queryOne('SELECT id FROM agents WHERE id = ?', id);
    if (existing) {
      await store.execute(
        `UPDATE agents SET name=?, agent_type=?, icon=?, color=?, description=?,
         port=?, mcp_transport=?, mcp_endpoint=?, mcp_capabilities=?,
         last_seen=datetime('now'), updated_at=datetime('now') WHERE id=?`,
        name, type, icon, color, description, port,
        mcp_transport||null, mcp_endpoint||null, JSON.stringify(mcp_capabilities||{}), id
      );
    } else {
      await store.execute(
        `INSERT INTO agents (id, name, agent_type, icon, color, description, port, mcp_transport, mcp_endpoint, mcp_capabilities, last_seen)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))`,
        id, name, type, icon, color, description, port,
        mcp_transport||null, mcp_endpoint||null, JSON.stringify(mcp_capabilities||{})
      );
    }
  }

  await store.setAgentStatus(id, { status: 'idle', activity: 'registered', port });
  return { id, registered: true };
}

// ---------------------------------------------------------------------------
//  Heartbeat
// ---------------------------------------------------------------------------
async function heartbeat(agentId, { status = 'idle', activity = '', pid, port } = {}) {
  await store.setAgentStatus(agentId, { status, activity, pid, port });

  if (store.isPostgres()) {
    await store.pg.execute('UPDATE agents SET last_seen = NOW() WHERE id = $1', [agentId]);
  } else {
    await store.execute(`UPDATE agents SET last_seen = datetime('now') WHERE id = ?`, agentId);
  }

  return { ok: true };
}

// ---------------------------------------------------------------------------
//  Get Agent(s)
// ---------------------------------------------------------------------------
async function getAgent(id) {
  let row;
  if (store.isPostgres()) {
    row = await store.pg.getAgent(id);
  } else {
    row = await store.queryOne('SELECT * FROM agents WHERE id = ?', id);
  }
  if (!row) return null;
  const liveStatus = await store.getAgentStatus(id);
  return formatAgent(row, liveStatus);
}

async function getAllAgents() {
  let rows;
  if (store.isPostgres()) {
    rows = await store.pg.getAllAgents();
  } else {
    rows = await store.queryAll('SELECT * FROM agents ORDER BY name');
  }
  const result = [];
  for (const row of rows) {
    const liveStatus = await store.getAgentStatus(row.id);
    result.push(formatAgent(row, liveStatus));
  }
  return result;
}

async function getAgentStatus(id) {
  return store.getAgentStatus(id);
}

async function getAllAgentStatuses() {
  return store.getAllAgentStatuses();
}

async function incrementMessages(agentId) {
  if (store.isPostgres()) {
    await store.pg.incrementAgentMessages(agentId);
  } else {
    await store.execute('UPDATE agents SET total_messages = total_messages + 1 WHERE id = ?', agentId);
  }
}

async function removeAgent(id) {
  if (store.isPostgres()) {
    const r = await store.pg.deleteAgent(id);
    return r.changes > 0;
  }
  const r = await store.execute('DELETE FROM agents WHERE id = ?', id);
  return r.changes > 0;
}

async function syncFromFile(agentsConfig) {
  for (const [id, config] of Object.entries(agentsConfig)) {
    await registerAgent({
      id,
      name: config.name,
      icon: config.icon,
      color: config.color,
      port: config.port,
      description: config.desc || config.description || '',
    });
  }
  console.log(`[Cortex/Agents] Synced ${Object.keys(agentsConfig).length} agents from config`);
}

// ---------------------------------------------------------------------------
//  Format
// ---------------------------------------------------------------------------
function formatAgent(row, liveStatus) {
  const caps = row.mcp_capabilities;
  return {
    id: row.id,
    name: row.name,
    type: row.agent_type,
    icon: row.icon,
    color: row.color,
    description: row.description,
    port: row.port,
    mcp: {
      transport: row.mcp_transport,
      endpoint: row.mcp_endpoint,
      capabilities: typeof caps === 'string' ? safeParse(caps, {}) : (caps || {}),
    },
    status: liveStatus?.status || 'unknown',
    activity: liveStatus?.activity || '',
    lastSeen: row.last_seen,
    totalMessages: row.total_messages,
  };
}

function safeParse(str, fallback) {
  try { return JSON.parse(str); } catch { return fallback; }
}

module.exports = {
  registerAgent, heartbeat,
  getAgent, getAllAgents, getAgentStatus, getAllAgentStatuses,
  incrementMessages, removeAgent, syncFromFile,
};
