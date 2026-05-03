// ============================================================================
//  GNOM-HUB — Backend Server
//  Zentrale Kommandozentrale des Feenreichs
//  Port 4200 | Express + WebSocket
// ============================================================================

const express = require('express');
const http = require('http');
const { WebSocketServer } = require('ws');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

// ---------------------------------------------------------------------------
//  Configuration
// ---------------------------------------------------------------------------
const PORT = process.env.CONDUCTOR_PORT || 4200;
const CORTEX_URL = process.env.CORTEX_URL || 'http://localhost:3002';
const DEFAULT_MODEL = process.env.DEFAULT_MODEL || 'openai/gpt-4o-mini';
const AGENTS_FILE = path.join(__dirname, 'agents.json');

// ---------------------------------------------------------------------------
//  Agent Registry — loaded from agents.json
// ---------------------------------------------------------------------------
let AGENTS = {};

function loadAgents() {
  try {
    const raw = fs.readFileSync(AGENTS_FILE, 'utf-8');
    AGENTS = JSON.parse(raw);
    console.log(`[Agents] Loaded ${Object.keys(AGENTS).length} agents from agents.json`);
  } catch (err) {
    console.error('[Agents] Failed to load agents.json:', err.message);
    AGENTS = {};
  }
}

function saveAgents() {
  try {
    fs.writeFileSync(AGENTS_FILE, JSON.stringify(AGENTS, null, 2) + '\n', 'utf-8');
  } catch (err) {
    console.error('[Agents] Failed to save agents.json:', err.message);
  }
}

loadAgents();

// System prompt for the Conductor AI
const CONDUCTOR_SYSTEM = `Du bist Gnom-Hub — die zentrale Kommandozentrale des Feenreichs.
Du koordinierst alle Agenten (Hermes, Paperclip, OpenClaw, Agent Zero, Cortex) und hilfst dem König.
Antworte auf Deutsch, kurz und präzise. Du bist loyal, effizient und hast einen leicht futuristischen Ton.
Wenn der User einen Agenten ansprechen will, erkenne das und leite weiter.
Du kannst Agenten starten, stoppen und deren Status abfragen.`;

// ---------------------------------------------------------------------------
//  Express + HTTP Server
// ---------------------------------------------------------------------------
const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const server = http.createServer(app);

// ---------------------------------------------------------------------------
//  WebSocket Server
// ---------------------------------------------------------------------------
const wss = new WebSocketServer({ server });
const clients = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);
  console.log(`[WS] Client connected (${clients.size} total)`);

  // Send current agent status on connect
  fetchAgentStatus().then(status => {
    ws.send(JSON.stringify({ type: 'agent_status', data: status }));
  });

  ws.on('message', async (raw) => {
    try {
      const msg = JSON.parse(raw);
      await handleMessage(ws, msg);
    } catch (err) {
      console.error('[WS] Message parse error:', err);
      ws.send(JSON.stringify({ type: 'error', data: { message: 'Invalid message format' } }));
    }
  });

  ws.on('close', () => {
    clients.delete(ws);
    console.log(`[WS] Client disconnected (${clients.size} total)`);
  });
});

// Broadcast to all connected clients
function broadcast(message) {
  const payload = JSON.stringify(message);
  for (const client of clients) {
    if (client.readyState === 1) { // OPEN
      client.send(payload);
    }
  }
}

// ---------------------------------------------------------------------------
//  Message Handler — Core Router
// ---------------------------------------------------------------------------
async function handleMessage(ws, msg) {
  const { type, data } = msg;

  switch (type) {
    case 'chat':
      await handleChat(ws, data);
      break;
    case 'tts':
      await handleTTS(ws, data);
      break;
    case 'agent_action':
      await handleAgentAction(ws, data);
      break;
    case 'memory_search':
      await handleMemorySearch(ws, data);
      break;
    case 'cortex_search':
      await handleCortexSearch(ws, data);
      break;
    default:
      ws.send(JSON.stringify({ type: 'error', data: { message: `Unknown type: ${type}` } }));
  }
}

// ---------------------------------------------------------------------------
//  Chat Router — @agent Detection
// ---------------------------------------------------------------------------
async function handleChat(ws, data) {
  const { message, ttsEnabled } = data;
  if (!message || !message.trim()) return;

  // Parse @agent mention
  const mentionMatch = message.match(/^@(\w+)\s+([\s\S]+)/);
  let targetAgent = null;
  let cleanMessage = message;

  if (mentionMatch) {
    const agentKey = mentionMatch[1].toLowerCase();
    // Map aliases
    const aliasMap = { agentzero: 'zero', 'agent-zero': 'zero', 'agent_zero': 'zero' };
    const resolvedKey = aliasMap[agentKey] || agentKey;
    
    if (AGENTS[resolvedKey]) {
      targetAgent = resolvedKey;
      cleanMessage = mentionMatch[2];
    }
  }

  // Send typing indicator
  ws.send(JSON.stringify({ 
    type: 'typing', 
    data: { agent: targetAgent || 'conductor' } 
  }));

  try {
    let response;
    if (targetAgent) {
      response = await routeToAgent(targetAgent, cleanMessage);
    } else {
      response = await queryConductor(cleanMessage);
    }

    const agentInfo = targetAgent ? AGENTS[targetAgent] : { 
      name: 'Conductor', icon: '⚡', color: '#00f0ff' 
    };

    const reply = {
      type: 'chat_response',
      data: {
        agent: targetAgent || 'conductor',
        agentName: agentInfo.name,
        agentIcon: agentInfo.icon,
        agentColor: agentInfo.color,
        message: response,
        timestamp: new Date().toISOString(),
      }
    };

    ws.send(JSON.stringify(reply));

    // TTS if enabled
    if (ttsEnabled && response) {
      speakText(response.substring(0, 500)); // limit TTS length
    }

    // Log to Cortex
    logToCortex('conductor', `User → ${agentInfo.name}: ${cleanMessage.substring(0, 100)}`);

  } catch (err) {
    console.error('[Chat] Error:', err.message);
    ws.send(JSON.stringify({
      type: 'chat_response',
      data: {
        agent: 'system',
        agentName: 'System',
        agentIcon: '⚠️',
        agentColor: '#f59e0b',
        message: `Fehler: ${err.message}`,
        timestamp: new Date().toISOString(),
      }
    }));
  }
}

// ---------------------------------------------------------------------------
//  Agent Routing
// ---------------------------------------------------------------------------
async function routeToAgent(agentKey, message) {
  const agent = AGENTS[agentKey];
  const systemPrompts = {
    hermes: 'Du bist Hermes — AI Gateway & Agent Runtime des Feenreichs. Du bist der Hauptagent.',
    paperclip: 'Du bist Paperclip — die Agent-Plattform mit Task-Management. Du hilfst bei Organisation.',
    openclaw: 'Du bist OpenClaw — autonomer lokaler Agent mit Telegram-Integration.',
    zero: 'Du bist Agent Zero — Docker-basierter Agent, vielseitig einsetzbar.',
    cortex: 'Du bist Cortex Hub — das zentrale Gedächtnis des Feenreichs.',
  };

  // Try to send via Cortex agent command endpoint first
  try {
    const resp = await fetchJSON(`${CORTEX_URL}/api/agents/command/${agentKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    if (resp && resp.response) return resp.response;
  } catch (e) {
    // Fall through to OpenRouter
  }

  // Fallback: use OpenRouter via Cortex with agent-specific system prompt
  return await queryOpenRouter(message, systemPrompts[agentKey] || `Du bist ${agent.name}.`);
}

async function queryConductor(message) {
  return await queryOpenRouter(message, CONDUCTOR_SYSTEM);
}

async function queryOpenRouter(prompt, systemPrompt) {
  const resp = await fetchJSON(`${CORTEX_URL}/api/openrouter/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt: prompt,
      system: systemPrompt,
      model: DEFAULT_MODEL,
    }),
  });

  if (resp && resp.success && resp.response) {
    return resp.response;
  }
  throw new Error(resp?.error || 'OpenRouter query failed');
}

// ---------------------------------------------------------------------------
//  Agent Status
// ---------------------------------------------------------------------------
async function fetchAgentStatus() {
  try {
    const resp = await fetchJSON(`${CORTEX_URL}/api/agents/status`);
    return resp?.agents || [];
  } catch (e) {
    console.error('[Status] Failed to fetch:', e.message);
    return [];
  }
}

// Periodic status broadcast
setInterval(async () => {
  const status = await fetchAgentStatus();
  broadcast({ type: 'agent_status', data: status });
}, 10000); // every 10 seconds

// ---------------------------------------------------------------------------
//  Agent Actions (Start/Stop/Restart)
// ---------------------------------------------------------------------------
async function handleAgentAction(ws, data) {
  const { action, agentId } = data;
  
  try {
    let endpoint;
    switch (action) {
      case 'start':
        endpoint = `${CORTEX_URL}/api/agentlauncher/start`;
        break;
      case 'stop':
        endpoint = `${CORTEX_URL}/api/agentlauncher/stop`;
        break;
      case 'restart':
        endpoint = `${CORTEX_URL}/api/agentlauncher/restart`;
        break;
      default:
        throw new Error(`Unknown action: ${action}`);
    }

    const resp = await fetchJSON(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId }),
    });

    ws.send(JSON.stringify({
      type: 'system_message',
      data: {
        message: `Agent ${agentId}: ${action} → ${resp?.status || 'sent'}`,
        timestamp: new Date().toISOString(),
      }
    }));

    // Refresh status after action
    setTimeout(async () => {
      const status = await fetchAgentStatus();
      broadcast({ type: 'agent_status', data: status });
    }, 2000);

  } catch (err) {
    ws.send(JSON.stringify({
      type: 'system_message',
      data: {
        message: `Agent ${agentId}: ${action} failed — ${err.message}`,
        timestamp: new Date().toISOString(),
      }
    }));
  }
}

// ---------------------------------------------------------------------------
//  Memory / Cortex Search
// ---------------------------------------------------------------------------
async function handleMemorySearch(ws, data) {
  const { query } = data;
  try {
    const resp = await fetchJSON(`${CORTEX_URL}/api/memory/search?q=${encodeURIComponent(query)}`);
    ws.send(JSON.stringify({ type: 'memory_results', data: resp }));
  } catch (err) {
    ws.send(JSON.stringify({ type: 'error', data: { message: err.message } }));
  }
}

async function handleCortexSearch(ws, data) {
  const { query } = data;
  try {
    const resp = await fetchJSON(`${CORTEX_URL}/api/memory/search?q=${encodeURIComponent(query)}`);
    ws.send(JSON.stringify({ type: 'cortex_results', data: resp }));
  } catch (err) {
    ws.send(JSON.stringify({ type: 'error', data: { message: err.message } }));
  }
}

// ---------------------------------------------------------------------------
//  Text-to-Speech (macOS `say`)
// ---------------------------------------------------------------------------
function speakText(text) {
  // Sanitize for shell
  const clean = text.replace(/["`$\\]/g, '').replace(/'/g, "\\'").substring(0, 500);
  exec(`say -v Anna "${clean}"`, (err) => {
    if (err) console.error('[TTS] Error:', err.message);
  });
}

async function handleTTS(ws, data) {
  const { text } = data;
  if (!text) return;
  speakText(text);
  ws.send(JSON.stringify({ 
    type: 'system_message', 
    data: { message: '🔊 Sprachausgabe gestartet', timestamp: new Date().toISOString() } 
  }));
}

// ---------------------------------------------------------------------------
//  Cortex Logging
// ---------------------------------------------------------------------------
async function logToCortex(agent, message) {
  try {
    await fetchJSON(`${CORTEX_URL}/api/memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: `[Conductor] ${message}`,
        type: 'event',
        source: 'conductor',
        tags: 'conductor,chat',
      }),
    });
  } catch (e) {
    // Silent fail for logging
  }
}

// ---------------------------------------------------------------------------
//  REST API Endpoints (for direct access)
// ---------------------------------------------------------------------------
app.get('/api/status', async (req, res) => {
  const status = await fetchAgentStatus();
  res.json({ agents: status, conductor: { port: PORT, uptime: process.uptime() } });
});

app.get('/api/cortex/stats', async (req, res) => {
  try {
    const stats = await fetchJSON(`${CORTEX_URL}/api/stats`);
    res.json(stats);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/tts', (req, res) => {
  const { text } = req.body;
  if (!text) return res.status(400).json({ error: 'text required' });
  speakText(text);
  res.json({ ok: true });
});

// ---------------------------------------------------------------------------
//  Agent Config CRUD — add/remove/list agents (persisted to agents.json)
// ---------------------------------------------------------------------------
app.get('/api/agents/config', (req, res) => {
  res.json(AGENTS);
});

app.post('/api/agents/config', (req, res) => {
  const { id, name, icon, port, color, desc } = req.body;
  if (!id || !name) return res.status(400).json({ error: 'id and name required' });
  AGENTS[id] = { name, icon: icon || '🤖', port: port || null, color: color || '#64748b', desc: desc || '' };
  saveAgents();
  broadcast({ type: 'agents_config_updated', data: AGENTS });
  res.json({ ok: true, agent: AGENTS[id] });
});

app.delete('/api/agents/config/:id', (req, res) => {
  const { id } = req.params;
  if (!AGENTS[id]) return res.status(404).json({ error: 'Agent not found' });
  delete AGENTS[id];
  saveAgents();
  broadcast({ type: 'agents_config_updated', data: AGENTS });
  res.json({ ok: true });
});

app.post('/api/agents/config/reload', (req, res) => {
  loadAgents();
  broadcast({ type: 'agents_config_updated', data: AGENTS });
  res.json({ ok: true, count: Object.keys(AGENTS).length });
});

// ---------------------------------------------------------------------------
//  Admin API — Process & Port Management
// ---------------------------------------------------------------------------

// Kill process by PID
app.post('/api/admin/kill/pid', (req, res) => {
  const { pid, signal } = req.body;
  if (!pid) return res.status(400).json({ error: 'pid required' });
  const sig = signal || 'TERM';
  exec(`kill -${sig} ${parseInt(pid)}`, (err, stdout, stderr) => {
    if (err) return res.json({ ok: false, error: stderr || err.message });
    res.json({ ok: true, message: `Sent ${sig} to PID ${pid}` });
  });
});

// Kill process by name
app.post('/api/admin/kill/name', (req, res) => {
  const { name, signal } = req.body;
  if (!name) return res.status(400).json({ error: 'name required' });
  const safeName = name.replace(/[^a-zA-Z0-9_\-\.]/g, '');
  const sig = signal || 'TERM';
  exec(`pkill -${sig} -f "${safeName}"`, (err, stdout, stderr) => {
    if (err && err.code === 1) return res.json({ ok: false, error: `No process matching "${safeName}"` });
    if (err) return res.json({ ok: false, error: stderr || err.message });
    res.json({ ok: true, message: `Sent ${sig} to processes matching "${safeName}"` });
  });
});

// Kill process on port (free port)
app.post('/api/admin/kill/port', (req, res) => {
  const { port } = req.body;
  if (!port) return res.status(400).json({ error: 'port required' });
  const p = parseInt(port);
  exec(`lsof -ti :${p}`, (err, stdout) => {
    if (err || !stdout.trim()) return res.json({ ok: false, error: `No process found on port ${p}` });
    const pids = stdout.trim().split('\n').join(' ');
    exec(`kill -9 ${pids}`, (err2) => {
      if (err2) return res.json({ ok: false, error: err2.message });
      res.json({ ok: true, message: `Killed PIDs [${pids}] on port ${p}` });
    });
  });
});

// Check what's on a port
app.get('/api/admin/port/:port', (req, res) => {
  const p = parseInt(req.params.port);
  exec(`lsof -i :${p} -P -n | head -5`, (err, stdout) => {
    if (err || !stdout.trim()) return res.json({ port: p, occupied: false, processes: [] });
    const lines = stdout.trim().split('\n');
    const header = lines[0];
    const processes = lines.slice(1).map(line => {
      const parts = line.split(/\s+/);
      return { command: parts[0], pid: parts[1], user: parts[2], type: parts[4], name: parts[8] };
    });
    res.json({ port: p, occupied: true, processes });
  });
});

// Connection test (ping an endpoint)
app.post('/api/admin/test', (req, res) => {
  const { url } = req.body;
  if (!url) return res.status(400).json({ error: 'url required' });
  const start = Date.now();
  exec(`curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 "${url}"`, (err, stdout) => {
    const ms = Date.now() - start;
    if (err) return res.json({ url, reachable: false, error: err.message, ms });
    const code = parseInt(stdout.trim());
    res.json({ url, reachable: code > 0 && code < 500, status: code, ms });
  });
});

// List running processes (filtered)
app.get('/api/admin/processes', (req, res) => {
  const filter = req.query.q || 'node|python|docker|hermes|paperclip|openclaw|agent|cortex';
  exec(`ps aux | grep -iE "${filter}" | grep -v grep | head -30`, (err, stdout) => {
    if (err) return res.json({ processes: [] });
    const processes = stdout.trim().split('\n').filter(Boolean).map(line => {
      const parts = line.split(/\s+/);
      return {
        user: parts[0], pid: parts[1], cpu: parts[2], mem: parts[3],
        command: parts.slice(10).join(' ').substring(0, 120),
      };
    });
    res.json({ processes });
  });
});

// List all listening ports
app.get('/api/admin/ports', (req, res) => {
  exec(`lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | tail -n +2 | sort -t: -k2 -n`, (err, stdout) => {
    if (err) return res.json({ ports: [] });
    const ports = stdout.trim().split('\n').filter(Boolean).map(line => {
      const parts = line.split(/\s+/);
      return { command: parts[0], pid: parts[1], user: parts[2], name: parts[8] };
    });
    res.json({ ports });
  });
});

// ---------------------------------------------------------------------------
//  Telegram Bot (optional — requires TELEGRAM_BOT_TOKEN)
// ---------------------------------------------------------------------------
if (process.env.TELEGRAM_BOT_TOKEN) {
  try {
    const { initTelegram } = require('./telegram');
    initTelegram(process.env.TELEGRAM_BOT_TOKEN, {
      routeToAgent,
      queryConductor,
      fetchAgentStatus,
      speakText,
      broadcast,
    });
    console.log('[Telegram] Bot initialized');
  } catch (err) {
    console.error('[Telegram] Failed to init:', err.message);
  }
} else {
  console.log('[Telegram] No BOT_TOKEN — Telegram disabled');
}

// ---------------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------------
async function fetchJSON(url, options = {}) {
  const resp = await fetch(url, {
    ...options,
    signal: AbortSignal.timeout(15000),
  });
  
  const text = await resp.text();
  try {
    return JSON.parse(text);
  } catch {
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${text.substring(0, 200)}`);
    return { raw: text };
  }
}

// ---------------------------------------------------------------------------
//  Start Server
// ---------------------------------------------------------------------------
server.listen(PORT, () => {
  console.log('');
  console.log('  ⚡ ═══════════════════════════════════════════ ⚡');
  console.log('  ║                                               ║');
  console.log('  ║     GNOM-HUB — Feenreich Command Hub   ║');
  console.log('  ║                                               ║');
  console.log(`  ║     🌐 http://localhost:${PORT}                  ║`);
  console.log(`  ║     🧠 Cortex: ${CORTEX_URL}            ║`);
  console.log(`  ║     🤖 Model:  ${DEFAULT_MODEL}        ║`);
  console.log('  ║                                               ║');
  console.log('  ⚡ ═══════════════════════════════════════════ ⚡');
  console.log('');
});
