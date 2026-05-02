// ============================================================================
//  LOCAL CONDUCTOR — Telegram Bot Module
//  Empfängt Nachrichten vom Handy und routet sie durch den Conductor
// ============================================================================

const TelegramBot = require('node-telegram-bot-api');

let bot = null;
let conductorAPI = null;

function initTelegram(token, api) {
  conductorAPI = api;
  bot = new TelegramBot(token, { polling: true });

  console.log('[Telegram] Bot starting with polling...');

  // /start command
  bot.onText(/\/start/, (msg) => {
    bot.sendMessage(msg.chat.id, 
      '⚡ *Local Conductor* verbunden!\n\n' +
      'Befehle:\n' +
      '• Nachricht senden → wird an Conductor AI geroutet\n' +
      '• `@hermes <text>` → direkt an Hermes\n' +
      '• `@paperclip <text>` → direkt an Paperclip\n' +
      '• `/status` → Agent-Status\n' +
      '• `/speak <text>` → Mac Sprachausgabe\n' +
      '• `/search <query>` → Cortex Memory durchsuchen',
      { parse_mode: 'Markdown' }
    );
  });

  // /status command
  bot.onText(/\/status/, async (msg) => {
    try {
      const agents = await conductorAPI.fetchAgentStatus();
      let text = '⚡ *Agent Status*\n\n';
      for (const agent of agents) {
        const statusIcon = agent.status === 'running' ? '🟢' : '🔴';
        const port = agent.port ? `:${agent.port}` : '';
        text += `${statusIcon} *${agent.agent_name}* ${port}\n`;
      }
      bot.sendMessage(msg.chat.id, text, { parse_mode: 'Markdown' });
    } catch (err) {
      bot.sendMessage(msg.chat.id, `❌ Status-Abfrage fehlgeschlagen: ${err.message}`);
    }
  });

  // /speak command — TTS on Mac
  bot.onText(/\/speak (.+)/, (msg, match) => {
    const text = match[1];
    conductorAPI.speakText(text);
    bot.sendMessage(msg.chat.id, `🔊 Spreche: "${text.substring(0, 100)}"`);
  });

  // /search command — Cortex memory search
  bot.onText(/\/search (.+)/, async (msg, match) => {
    const query = match[1];
    try {
      const resp = await fetch(`http://localhost:3002/api/memory/search?q=${encodeURIComponent(query)}`);
      const data = await resp.json();
      const results = data.results || [];
      
      if (results.length === 0) {
        bot.sendMessage(msg.chat.id, `🔍 Keine Ergebnisse für: "${query}"`);
        return;
      }

      let text = `🔍 *Cortex-Suche:* "${query}"\n\n`;
      for (const r of results.slice(0, 5)) {
        text += `• ${(r.content || '').substring(0, 150)}\n\n`;
      }
      bot.sendMessage(msg.chat.id, text, { parse_mode: 'Markdown' });
    } catch (err) {
      bot.sendMessage(msg.chat.id, `❌ Suche fehlgeschlagen: ${err.message}`);
    }
  });

  // General messages — route through Conductor
  bot.on('message', async (msg) => {
    // Skip commands
    if (msg.text && msg.text.startsWith('/')) return;
    if (!msg.text) return;

    const text = msg.text;
    
    // Check for @agent mention
    const mentionMatch = text.match(/^@(\w+)\s+([\s\S]+)/);
    
    try {
      let response;
      if (mentionMatch) {
        const agentKey = mentionMatch[1].toLowerCase();
        const message = mentionMatch[2];
        response = await conductorAPI.routeToAgent(agentKey, message);
      } else {
        response = await conductorAPI.queryConductor(text);
      }

      bot.sendMessage(msg.chat.id, response || 'Keine Antwort erhalten.');

      // Also broadcast to local WebSocket clients
      conductorAPI.broadcast({
        type: 'chat_response',
        data: {
          agent: 'telegram',
          agentName: 'Telegram',
          agentIcon: '📱',
          agentColor: '#2563eb',
          message: `[via Telegram] ${text}`,
          timestamp: new Date().toISOString(),
        }
      });

    } catch (err) {
      bot.sendMessage(msg.chat.id, `❌ Fehler: ${err.message}`);
    }
  });

  bot.on('polling_error', (err) => {
    console.error('[Telegram] Polling error:', err.message);
  });

  return bot;
}

module.exports = { initTelegram };
