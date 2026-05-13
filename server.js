// ============================================================================
//  GNOM-HUB — Backend Server + Cortex v2
//  Zentrale Kommandozentrale des Agenten-Systems
//  Port 4200 | Express + WebSocket + Cortex v2 Engine
// ============================================================================

const express = require('express');
const http = require('http');
const { WebSocketServer } = require('ws');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

require('dotenv').config();

// ---------------------------------------------------------------------------
//  Cortex v2 — Integrated Engine
// ---------------------------------------------------------------------------
const cortex = require('./cortex');

// ---------------------------------------------------------------------------
//  Configuration
// ---------------------------------------------------------------------------
const PORT = process.env.CONDUCTOR_PORT || 4200;
const DEFAULT_MODEL = process.env.DEFAULT_MODEL || 'openai/gpt-4o-mini';
const AGENTS_FILE = path.join(__dirname, 'agents.json');

// OpenRouter config (used for LLM queries)
const OPENROUTER_KEY = process.env.OPENROUTER_API_KEY || '';
const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';

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
const CONDUCTOR_SYSTEM = `Du bist Gnom-Hub — die zentrale Kommandozentrale.
Du koordinierst alle Agenten (Hermes, Paperclip, OpenClaw, Agent Zero, Cortex) und hilfst dem User.
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
//  MCP Server (mounted after Cortex init in boot())
// ---------------------------------------------------------------------------
const { mountMCP } = require('./cortex/mcp-server');

// ---------------------------------------------------------------------------
//  WebSocket Server
// ---------------------------------------------------------------------------
const wss = new WebSocketServer({ server });
const clients = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);
  console.log(`[WS] Client connected (${clients.size} total)`);

  // Send current agent status on connect (with live port checks)
  (async () => {
    try {
      const agents = await fetchAgentStatus();
      ws.send(JSON.stringify({ type: 'agent_status', data: agents }));
    } catch (e) { /* cortex not ready yet */ }
  })();

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
    case 'cortex_search':
      await handleCortexSearch(ws, data);
      break;
    default:
      ws.send(JSON.stringify({ type: 'error', data: { message: `Unknown type: ${type}` } }));
  }
}

// ---------------------------------------------------------------------------
//  Chat Router — @agent Detection + Cortex Integration
// ---------------------------------------------------------------------------
async function handleChat(ws, data) {
  const { message, ttsEnabled } = data;
  if (!message || !message.trim()) return;

  // *** CORTEX v2: Observe user message (passive listener) ***
  const observePromise = cortex.observe(message, { role: 'user', agent: 'user', session: 'gnom-hub' });

  // *** CORTEX v2: Proactive recall (parallel) ***
  const recallPromise = cortex.recall(message);

  // Parse @agent mention
  const mentionMatch = message.match(/^@(\w+)\s+([\s\S]+)/);
  let targetAgent = null;
  let cleanMessage = message;

  if (mentionMatch) {
    const agentKey = mentionMatch[1].toLowerCase();
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

    // *** CORTEX v2: Observe agent response ***
    cortex.observe(response, {
      role: 'agent',
      agent: targetAgent || 'conductor',
      session: 'gnom-hub',
    });

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

    // *** CORTEX v2: Send proactive recall hints ***
    try {
      const recalls = await recallPromise;
      if (recalls.hasRecalls) {
        const formatted = cortex.recallHelpers.formatRecalls(recalls);
        if (formatted) {
          ws.send(JSON.stringify({
            type: 'cortex_recall',
            data: {
              agent: 'cortex',
              agentName: 'Cortex v2',
              agentIcon: '🧠',
              agentColor: '#06b6d4',
              message: formatted,
              timestamp: new Date().toISOString(),
            }
          }));
        }
      }
    } catch (recallErr) {
      // Silent fail for recall — non-critical
    }

    // TTS if enabled
    if (ttsEnabled && response) {
      speakText(response.substring(0, 500));
    }

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
//  Agent Routing — Multi-Strategy
// ---------------------------------------------------------------------------
async function routeToAgent(agentKey, message) {
  const agent = AGENTS[agentKey];
  const systemPrompts = {
    hermes: 'Du bist Hermes — AI Gateway & Agent Runtime. Du bist der Hauptagent.',
    paperclip: 'Du bist Paperclip — die Agent-Plattform mit Task-Management. Du hilfst bei Organisation.',
    openclaw: 'Du bist OpenClaw — autonomer lokaler Agent mit Telegram-Integration.',
    zero: 'Du bist Agent Zero — Docker-basierter Agent, vielseitig einsetzbar.',
    cortex: 'Du bist Cortex v2 — das intelligente zentrale Gedächtnis des Systems.',
  };

  // Strategy 1: Direct HTTP API (if agent has a port)
  if (agent?.port) {
    try {
      const resp = await fetchJSON(`http://localhost:${agent.port}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      if (resp?.response) return resp.response;
    } catch (e) { /* fall through */ }

    // Try OpenAI-compatible endpoint
    try {
      const resp = await fetchJSON(`http://localhost:${agent.port}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: message }],
          stream: false,
        }),
      });
      if (resp?.choices?.[0]?.message?.content) return resp.choices[0].message.content;
    } catch (e) { /* fall through */ }
  }

  // Strategy 2: Cortex message pipe (async delivery)
  cortex.pipe.send('gnom-hub', agentKey, message);

  // Strategy 3: OpenRouter with agent-specific persona
  return await queryOpenRouter(message, systemPrompts[agentKey] || `Du bist ${agent?.name || agentKey}.`);
}

async function queryConductor(message) {
  return await queryOpenRouter(message, CONDUCTOR_SYSTEM);
}

async function queryOpenRouter(prompt, systemPrompt) {
  if (!OPENROUTER_KEY) {
    return '⚠️ Kein OpenRouter API Key konfiguriert. Setze OPENROUTER_API_KEY in der Umgebung.';
  }

  const resp = await fetchJSON(OPENROUTER_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${OPENROUTER_KEY}`,
    },
    body: JSON.stringify({
      model: DEFAULT_MODEL,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: prompt },
      ],
    }),
  });

  if (resp?.choices?.[0]?.message?.content) {
    return resp.choices[0].message.content;
  }
  throw new Error(resp?.error?.message || 'OpenRouter query failed');
}

// ---------------------------------------------------------------------------
//  Agent Status (now from Cortex v2)
// ---------------------------------------------------------------------------
// Check if a TCP port is actually listening
function checkPort(port, timeout = 1500) {
  return new Promise((resolve) => {
    if (!port) return resolve(false);
    const net = require('net');
    const socket = new net.Socket();
    socket.setTimeout(timeout);
    socket.once('connect', () => { socket.destroy(); resolve(true); });
    socket.once('timeout', () => { socket.destroy(); resolve(false); });
    socket.once('error', () => { socket.destroy(); resolve(false); });
    socket.connect(port, '127.0.0.1');
  });
}

async function fetchAgentStatus() {
  const agents = await cortex.agents.getAll();
  // Also check live port status for each agent
  const enriched = await Promise.all(agents.map(async (agent) => {
    const portAlive = await checkPort(agent.port);
    return {
      ...agent,
      status: portAlive ? 'running' : (agent.port ? 'stopped' : agent.status),
      portAlive,
    };
  }));
  return enriched;
}

// Periodic status broadcast
setInterval(async () => {
  const status = await fetchAgentStatus();
  broadcast({ type: 'agent_status', data: status });
}, 15000); // every 15 seconds

// ---------------------------------------------------------------------------
//  Agent Actions (Start/Stop/Restart)
// ---------------------------------------------------------------------------
async function handleAgentAction(ws, data) {
  const { action, agentId } = data;

  try {
    // For now, just update status in Cortex
    if (action === 'start') {
      cortex.agents.heartbeat(agentId, { status: 'busy', activity: 'starting' });
    } else if (action === 'stop') {
      cortex.agents.heartbeat(agentId, { status: 'offline', activity: 'stopped' });
    }

    ws.send(JSON.stringify({
      type: 'system_message',
      data: {
        message: `Agent ${agentId}: ${action} → sent`,
        timestamp: new Date().toISOString(),
      }
    }));

    // Refresh status
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
//  Cortex Search (now using Cortex v2 engine)
// ---------------------------------------------------------------------------
async function handleCortexSearch(ws, data) {
  const { query } = data;
  try {
    const results = await cortex.search(query);
    ws.send(JSON.stringify({ type: 'cortex_results', data: results }));
  } catch (err) {
    ws.send(JSON.stringify({ type: 'error', data: { message: err.message } }));
  }
}

// ---------------------------------------------------------------------------
//  Text-to-Speech (macOS `say`)
// ---------------------------------------------------------------------------
function speakText(text) {
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
//  REST API Endpoints
// ---------------------------------------------------------------------------

// -- Status --
app.get('/api/status', async (req, res) => {
  const agents = await fetchAgentStatus();
  res.json({ agents, conductor: { port: PORT, uptime: process.uptime() } });
});

// -- Cortex v2 REST API --
app.get('/api/cortex/stats', (req, res) => {
  res.json(cortex.stats());
});

app.get('/api/cortex/memories', async (req, res) => {
  const { q, type, limit, min_importance } = req.query;
  if (q) {
    const results = await cortex.search(q, {
      type,
      limit: parseInt(limit) || 10,
      minImportance: min_importance ? parseInt(min_importance) : undefined,
    });
    res.json(results);
  } else {
    const recent = cortex.memory.getRecent(parseInt(limit) || 20);
    res.json(recent);
  }
});

app.post('/api/cortex/memories', async (req, res) => {
  const { content, type, importance, source, tags } = req.body;
  if (!content) return res.status(400).json({ error: 'content required' });
  const result = await cortex.memory.create({
    content, type, importance, source,
    tags: typeof tags === 'string' ? tags.split(',').map(t => t.trim()) : tags || [],
  });
  res.json(result);
});

app.get('/api/cortex/memories/:id', (req, res) => {
  const mem = cortex.memory.get(req.params.id);
  if (!mem) return res.status(404).json({ error: 'Not found' });
  res.json(mem);
});

app.delete('/api/cortex/memories/:id', (req, res) => {
  const deleted = cortex.memory.delete(req.params.id);
  res.json({ ok: deleted });
});

app.get('/api/cortex/decisions', (req, res) => {
  const limit = parseInt(req.query.limit) || 10;
  res.json(cortex.decisions.get(limit));
});

app.post('/api/cortex/decisions', async (req, res) => {
  const { title, outcome, reasoning, tags } = req.body;
  if (!title || !outcome) return res.status(400).json({ error: 'title and outcome required' });
  const result = await cortex.decisions.create({
    title, outcome, reasoning,
    tags: typeof tags === 'string' ? tags.split(',').map(t => t.trim()) : tags || [],
  });
  res.json(result);
});

app.get('/api/cortex/agents', (req, res) => {
  res.json(cortex.agents.getAll());
});

app.post('/api/cortex/agents/register', (req, res) => {
  const { id, name, ...rest } = req.body;
  if (!id || !name) return res.status(400).json({ error: 'id and name required' });
  const result = cortex.agents.register({ id, name, ...rest });
  res.json(result);
});

app.post('/api/cortex/agents/:id/heartbeat', (req, res) => {
  const result = cortex.agents.heartbeat(req.params.id, req.body);
  res.json(result);
});

app.get('/api/cortex/tasks', (req, res) => {
  res.json(cortex.tasks.getActive());
});

app.post('/api/cortex/tasks', (req, res) => {
  const { title, description, priority, assignee } = req.body;
  if (!title) return res.status(400).json({ error: 'title required' });
  const result = cortex.tasks.create({ title, description, priority, assignee });
  res.json(result);
});

app.post('/api/cortex/recall', async (req, res) => {
  const { message } = req.body;
  if (!message) return res.status(400).json({ error: 'message required' });
  const recalls = await cortex.recall(message);
  res.json(recalls);
});

app.post('/api/cortex/pipe/send', (req, res) => {
  const { sender, recipient, content } = req.body;
  if (!sender || !recipient || !content) return res.status(400).json({ error: 'sender, recipient, content required' });
  const result = cortex.pipe.send(sender, recipient, content);
  res.json(result);
});

app.get('/api/cortex/pipe/:recipient', (req, res) => {
  const unreadOnly = req.query.unread !== 'false';
  const messages = cortex.pipe.read(req.params.recipient, unreadOnly);
  res.json(messages);
});

app.get('/api/cortex/cron', (req, res) => {
  res.json(cortex.cron.list());
});

app.post('/api/cortex/cron', (req, res) => {
  const { name, schedule, action } = req.body;
  if (!name || !schedule) return res.status(400).json({ error: 'name and schedule required' });
  const result = cortex.cron.create({ name, schedule, action: action || {} });
  res.json(result);
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
  const { id, name, icon, port, color, desc, webui_port, dir, start_cmd } = req.body;
  if (!id || !name) return res.status(400).json({ error: 'id and name required' });
  AGENTS[id] = { name, icon: icon || '🤖', port: port || null, webui_port: webui_port || null, dir: dir || '', start_cmd: start_cmd || '', color: color || '#64748b', desc: desc || '' };
  saveAgents();
  // Also register in Cortex v2
  cortex.agents.register({ id, name, icon: icon || '🤖', color: color || '#64748b', port, description: desc || '' });
  broadcast({ type: 'agents_config_updated', data: AGENTS });
  res.json({ ok: true, agent: AGENTS[id] });
});

app.delete('/api/agents/config/:id', (req, res) => {
  const { id } = req.params;
  if (!AGENTS[id]) return res.status(404).json({ error: 'Agent not found' });
  delete AGENTS[id];
  saveAgents();
  cortex.agents.remove(id);
  broadcast({ type: 'agents_config_updated', data: AGENTS });
  res.json({ ok: true });
});

app.post('/api/agents/config/reload', (req, res) => {
  loadAgents();
  cortex.agents.sync(AGENTS);
  broadcast({ type: 'agents_config_updated', data: AGENTS });
  res.json({ ok: true, count: Object.keys(AGENTS).length });
});

// ---------------------------------------------------------------------------
//  Agent Actions — Start/Stop/Restart via Admin Panel
// ---------------------------------------------------------------------------
app.post('/api/agents/action', async (req, res) => {
  const { action, agent_id } = req.body;
  if (!action || !agent_id) return res.status(400).json({ error: 'action and agent_id required' });

  const agent = AGENTS[agent_id];
  if (!agent) return res.status(404).json({ error: `Agent '${agent_id}' not found` });

  const { execSync } = require('child_process');
  const port = agent.port;

  try {
    if (action === 'stop') {
      if (port) {
        try {
          execSync(`lsof -ti:${port} | xargs kill -9 2>/dev/null`, { timeout: 5000 });
        } catch (_) { /* port may already be free */ }
        console.log(`[Admin] Stopped agent ${agent_id} (port ${port})`);
        res.json({ ok: true, message: `Agent ${agent.name} gestoppt (Port ${port})` });
      } else {
        res.json({ ok: true, message: `Agent ${agent.name}: kein Port konfiguriert, manuell stoppen` });
      }

    } else if (action === 'start' || action === 'restart') {
      // Kill first if restart
      if (action === 'restart' && port) {
        try { execSync(`lsof -ti:${port} | xargs kill -9 2>/dev/null`, { timeout: 5000 }); } catch (_) {}
        await new Promise(r => setTimeout(r, 1000));
      }

      // Agent-specific start commands
      const startCmds = {
        hermes:    'hermes --gateway',
        cortex:    `cd ${__dirname}/cortex && node index.js`,
        paperclip: 'echo "Paperclip needs manual start"',
        openclaw:  'openclaw',
        tandem:    'echo "Tandem needs manual start"',
        launcher:  'echo "Launcher needs manual start"',
        zero:      'echo "Agent Zero needs Docker"',
      };

      const cmd = agent.start_cmd || startCmds[agent_id];
      if (cmd && !cmd.includes('needs')) {
        const { spawn } = require('child_process');
        const spawnOpts = {
          shell: true,
          detached: true,
          stdio: 'ignore'
        };
        if (agent.dir) spawnOpts.cwd = agent.dir.replace(/^~/, process.env.HOME || '/Users/landjunge');
        
        const child = spawn(cmd, [], spawnOpts);
        child.unref();
        console.log(`[Admin] Started agent ${agent_id}: ${cmd}`);
        res.json({ ok: true, message: `Agent ${agent.name} wird gestartet…` });
      } else {
        res.json({ ok: true, message: `Agent ${agent.name}: manueller Start erforderlich` });
      }

    } else {
      res.status(400).json({ error: `Unknown action: ${action}` });
    }
  } catch (err) {
    console.error(`[Admin] Agent action failed:`, err.message);
    res.status(500).json({ error: err.message });
  }
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

// Kill process on port
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

// Check port
app.get('/api/admin/port/:port', (req, res) => {
  const p = parseInt(req.params.port);
  exec(`lsof -i :${p} -P -n | head -5`, (err, stdout) => {
    if (err || !stdout.trim()) return res.json({ port: p, occupied: false, processes: [] });
    const lines = stdout.trim().split('\n');
    const processes = lines.slice(1).map(line => {
      const parts = line.split(/\s+/);
      return { command: parts[0], pid: parts[1], user: parts[2], type: parts[4], name: parts[8] };
    });
    res.json({ port: p, occupied: true, processes });
  });
});

// Connection test
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

// List processes
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

// List listening ports
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
    signal: AbortSignal.timeout(60000),
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
//  Boot — async startup sequence
// ---------------------------------------------------------------------------
async function boot() {
  try {
    // 1. Initialize Cortex v2 (Redis + PostgreSQL)
    await cortex.init({
      openaiKey: OPENROUTER_KEY,
      agentsConfig: AGENTS,
      broadcast,
    });

    // 2. Mount MCP Server
    mountMCP(app);

    // 3. Start HTTP server
    const st = cortex.stats();
    server.listen(PORT, () => {
      console.log('');
      console.log('  ⚡ ════════════════════════════════════════════════ ⚡');
      console.log('  ║                                                    ║');
      console.log('  ║     GNOM-HUB + CORTEX v2 — Agent Engine           ║');
      console.log('  ║                                                    ║');
      console.log(`  ║     🌐 http://localhost:${PORT}                       ║`);
      console.log(`  ║     🐘 PostgreSQL: ${st.storage?.postgres || '?'}                        ║`);
      console.log(`  ║     🔴 Redis:      ${st.storage?.redis || '?'}                        ║`);
      console.log('  ║     📡 MCP Server: /mcp (Streamable HTTP)         ║');
      console.log('  ║                                                    ║');
      console.log('  ⚡ ════════════════════════════════════════════════ ⚡');
      console.log('');
    });
  } catch (err) {
    console.error('[BOOT] Fatal error:', err);
    process.exit(1);
  }
}

boot();
