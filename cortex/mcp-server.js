// ============================================================================
//  Cortex v2 — MCP Server
//  Model Context Protocol server for agent auto-registration & tool access.
//  Exposes Cortex as a set of MCP tools and resources.
//  Transport: Streamable HTTP on /mcp endpoint
// ============================================================================

const { McpServer } = require('@modelcontextprotocol/sdk/server/mcp.js');
const { StreamableHTTPServerTransport } = require('@modelcontextprotocol/sdk/server/streamableHttp.js');
const { z } = require('zod');
const cortex = require('./index');

let mcpServer = null;

/**
 * Create and configure the MCP server with all Cortex tools and resources.
 * @returns {McpServer}
 */
function createMCPServer() {
  mcpServer = new McpServer({
    name: 'cortex-v2',
    version: '2.0.0',
  });

  // =========================================================================
  //  TOOLS
  // =========================================================================

  // -- cortex_remember --
  mcpServer.tool(
    'cortex_remember',
    'Speichere eine Erinnerung im Cortex-Langzeitgedächtnis.',
    {
      content: z.string().describe('Der Inhalt der Erinnerung'),
      type: z.enum(['fact', 'decision', 'event', 'insight', 'task_result']).default('fact').describe('Typ der Erinnerung'),
      importance: z.number().min(1).max(10).default(5).describe('Wichtigkeit 1-10'),
      tags: z.string().default('').describe('Komma-getrennte Tags'),
      source: z.string().default('mcp').describe('Quelle der Erinnerung'),
    },
    async ({ content, type, importance, tags, source }) => {
      const result = await cortex.memory.create({
        content,
        type,
        importance,
        source,
        tags: tags ? tags.split(',').map(t => t.trim()) : [],
      });
      return {
        content: [{ type: 'text', text: JSON.stringify(result) }],
      };
    }
  );

  // -- cortex_search --
  mcpServer.tool(
    'cortex_search',
    'Durchsuche das Cortex-Gedächtnis semantisch.',
    {
      query: z.string().describe('Suchanfrage'),
      limit: z.number().default(10).describe('Max. Ergebnisse'),
      type: z.string().optional().describe('Filter nach Typ'),
      min_importance: z.number().optional().describe('Min. Wichtigkeit'),
    },
    async ({ query, limit, type, min_importance }) => {
      const results = await cortex.search(query, {
        limit,
        type,
        minImportance: min_importance,
      });
      return {
        content: [{ type: 'text', text: JSON.stringify(results, null, 2) }],
      };
    }
  );

  // -- cortex_recall --
  mcpServer.tool(
    'cortex_recall',
    'Proaktiver Recall — finde relevante Erinnerungen, Entscheidungen und offene Tasks.',
    {
      message: z.string().describe('Nachricht/Kontext für den Recall'),
    },
    async ({ message }) => {
      const recalls = await cortex.recall(message);
      const formatted = cortex.recallHelpers.formatRecalls(recalls);
      return {
        content: [{
          type: 'text',
          text: formatted || 'Keine relevanten Erinnerungen gefunden.',
        }],
      };
    }
  );

  // -- cortex_decide --
  mcpServer.tool(
    'cortex_decide',
    'Logge eine explizite Entscheidung.',
    {
      title: z.string().describe('Titel der Entscheidung'),
      outcome: z.string().describe('Was wurde entschieden?'),
      reasoning: z.string().default('').describe('Begründung'),
      tags: z.string().default('').describe('Komma-getrennte Tags'),
    },
    async ({ title, outcome, reasoning, tags }) => {
      const result = await cortex.decisions.create({
        title,
        outcome,
        reasoning,
        tags: tags ? tags.split(',').map(t => t.trim()) : [],
      });
      return {
        content: [{ type: 'text', text: JSON.stringify(result) }],
      };
    }
  );

  // -- cortex_agent_register --
  mcpServer.tool(
    'cortex_agent_register',
    'Registriere einen neuen Agenten im Cortex.',
    {
      id: z.string().describe('Eindeutige Agent-ID'),
      name: z.string().describe('Display-Name'),
      type: z.string().default('agent').describe('agent | mcp_client | service'),
      icon: z.string().default('🤖').describe('Icon/Emoji'),
      color: z.string().default('#64748b').describe('Farbe (Hex)'),
      description: z.string().default('').describe('Beschreibung'),
      port: z.number().optional().describe('Port des Agenten'),
    },
    async ({ id, name, type, icon, color, description, port }) => {
      const result = await cortex.agents.register({ id, name, type, icon, color, description, port });
      return {
        content: [{ type: 'text', text: JSON.stringify(result) }],
      };
    }
  );

  // -- cortex_agent_heartbeat --
  mcpServer.tool(
    'cortex_agent_heartbeat',
    'Sende einen Heartbeat (Status-Update) für einen Agenten.',
    {
      agent_id: z.string().describe('Agent-ID'),
      status: z.enum(['idle', 'busy', 'offline', 'error']).default('idle'),
      activity: z.string().default('').describe('Aktuelle Aktivität'),
    },
    async ({ agent_id, status, activity }) => {
      const result = await cortex.agents.heartbeat(agent_id, { status, activity });
      return {
        content: [{ type: 'text', text: JSON.stringify(result) }],
      };
    }
  );

  // -- cortex_task_create --
  mcpServer.tool(
    'cortex_task_create',
    'Erstelle einen neuen Task.',
    {
      title: z.string().describe('Titel des Tasks'),
      description: z.string().default('').describe('Beschreibung'),
      priority: z.number().min(1).max(10).default(5).describe('Priorität 1-10'),
      assignee: z.string().default('').describe('Zugewiesen an (Agent-ID)'),
    },
    async ({ title, description, priority, assignee }) => {
      const result = await cortex.tasks.create({ title, description, priority, assignee });
      return {
        content: [{ type: 'text', text: JSON.stringify(result) }],
      };
    }
  );

  // -- cortex_task_update --
  mcpServer.tool(
    'cortex_task_update',
    'Aktualisiere einen Task.',
    {
      id: z.string().describe('Task-ID'),
      status: z.enum(['open', 'in_progress', 'done', 'cancelled']).optional(),
      title: z.string().optional(),
    },
    async ({ id, status, title }) => {
      const updates = {};
      if (status) updates.status = status;
      if (title) updates.title = title;
      const result = await cortex.tasks.update(id, updates);
      return {
        content: [{ type: 'text', text: result ? JSON.stringify(result) : 'Task not found' }],
      };
    }
  );

  // -- cortex_pipe_send --
  mcpServer.tool(
    'cortex_pipe_send',
    'Sende eine Nachricht an einen anderen Agenten.',
    {
      sender: z.string().describe('Sender Agent-ID'),
      recipient: z.string().describe('Empfänger Agent-ID'),
      content: z.string().describe('Nachrichteninhalt'),
    },
    async ({ sender, recipient, content }) => {
      const result = await cortex.pipe.send(sender, recipient, content);
      return {
        content: [{ type: 'text', text: JSON.stringify(result) }],
      };
    }
  );

  // -- cortex_pipe_read --
  mcpServer.tool(
    'cortex_pipe_read',
    'Lese Nachrichten für einen Agenten.',
    {
      recipient: z.string().describe('Agent-ID'),
      unread_only: z.boolean().default(true),
    },
    async ({ recipient, unread_only }) => {
      const messages = await cortex.pipe.read(recipient, unread_only);
      return {
        content: [{ type: 'text', text: JSON.stringify(messages, null, 2) }],
      };
    }
  );

  // -- cortex_cron_add --
  mcpServer.tool(
    'cortex_cron_add',
    'Füge einen Cronjob hinzu.',
    {
      name: z.string().describe('Name des Jobs'),
      schedule: z.string().describe('Cron-Expression (z.B. "0 * * * *")'),
      action: z.string().describe('JSON-Action: { "type": "...", "target": "...", "payload": "..." }'),
    },
    async ({ name, schedule, action }) => {
      let parsedAction;
      try {
        parsedAction = JSON.parse(action);
      } catch {
        parsedAction = { type: 'custom', payload: action };
      }
      const result = await cortex.cron.create({ name, schedule, action: parsedAction });
      return {
        content: [{ type: 'text', text: JSON.stringify(result) }],
      };
    }
  );

  // -- cortex_stats --
  mcpServer.tool(
    'cortex_stats',
    'Zeige Cortex-Statistiken.',
    {},
    async () => {
      const s = cortex.stats();
      return {
        content: [{ type: 'text', text: JSON.stringify(s, null, 2) }],
      };
    }
  );

  // =========================================================================
  //  RESOURCES
  // =========================================================================

  mcpServer.resource(
    'memory-recent',
    'memory://recent',
    { description: 'Letzte 20 Memories', mimeType: 'application/json' },
    async () => {
      const recent = await cortex.memory.getRecent(20);
      return { contents: [{ uri: 'memory://recent', text: JSON.stringify(recent, null, 2), mimeType: 'application/json' }] };
    }
  );

  mcpServer.resource(
    'memory-decisions',
    'memory://decisions',
    { description: 'Letzte 10 Entscheidungen', mimeType: 'application/json' },
    async () => {
      const decs = await cortex.decisions.get(10);
      return { contents: [{ uri: 'memory://decisions', text: JSON.stringify(decs, null, 2), mimeType: 'application/json' }] };
    }
  );

  mcpServer.resource(
    'memory-agents',
    'memory://agents',
    { description: 'Alle registrierten Agenten + Status', mimeType: 'application/json' },
    async () => {
      const agents = await cortex.agents.getAll();
      return { contents: [{ uri: 'memory://agents', text: JSON.stringify(agents, null, 2), mimeType: 'application/json' }] };
    }
  );

  mcpServer.resource(
    'memory-tasks',
    'memory://tasks/active',
    { description: 'Alle aktiven Tasks', mimeType: 'application/json' },
    async () => {
      const tasks = await cortex.tasks.getActive();
      return { contents: [{ uri: 'memory://tasks/active', text: JSON.stringify(tasks, null, 2), mimeType: 'application/json' }] };
    }
  );

  mcpServer.resource(
    'memory-stats',
    'memory://stats',
    { description: 'Cortex-Statistiken', mimeType: 'application/json' },
    async () => {
      const s = cortex.stats();
      return { contents: [{ uri: 'memory://stats', text: JSON.stringify(s, null, 2), mimeType: 'application/json' }] };
    }
  );

  return mcpServer;
}

/**
 * Mount MCP Streamable HTTP transport on an Express app.
 * @param {import('express').Express} app
 */
function mountMCP(app) {
  if (!mcpServer) {
    createMCPServer();
  }

  // Streamable HTTP transport on /mcp
  app.post('/mcp', async (req, res) => {
    try {
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined, // stateless
      });
      res.on('close', () => transport.close());
      await mcpServer.connect(transport);
      await transport.handleRequest(req, res, req.body);
    } catch (err) {
      console.error('[Cortex/MCP] Error:', err.message);
      if (!res.headersSent) {
        res.status(500).json({ error: err.message });
      }
    }
  });

  // Handle GET for SSE (optional, for clients that prefer SSE)
  app.get('/mcp', async (req, res) => {
    res.writeHead(405, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Use POST for MCP requests (Streamable HTTP transport)' }));
  });

  // Handle DELETE for session termination
  app.delete('/mcp', async (req, res) => {
    res.writeHead(405, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Session termination not supported in stateless mode' }));
  });

  console.log('[Cortex/MCP] MCP Server mounted on /mcp (Streamable HTTP)');
}

module.exports = { createMCPServer, mountMCP, getMCPServer: () => mcpServer };
