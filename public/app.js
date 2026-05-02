// ============================================================================
//  LOCAL CONDUCTOR — Frontend Logic
// ============================================================================

(() => {
  'use strict';

  // ---- State ----
  let ws = null;
  let ttsEnabled = false;
  let agentStatusData = [];
  let autocompleteIndex = -1;
  let contextAgent = null;

  // Loaded dynamically from /api/agents/config — editable via agents.json
  let AGENTS_META = {
    conductor: { name: 'Conductor', icon: '⚡', color: '#00f0ff', desc: 'Kommandozentrale' },
  };

  async function loadAgentsConfig() {
    try {
      const resp = await fetch('/api/agents/config');
      const data = await resp.json();
      // Merge with conductor (always present)
      AGENTS_META = { ...data, conductor: { name: 'Conductor', icon: '⚡', color: '#00f0ff', desc: 'Kommandozentrale' } };
      console.log('[Config] Loaded', Object.keys(data).length, 'agents');
    } catch (err) {
      console.error('[Config] Failed to load agents:', err);
    }
  }

  // ---- DOM Elements ----
  const $chatMessages = document.getElementById('chatMessages');
  const $chatInput = document.getElementById('chatInput');
  const $btnSend = document.getElementById('btnSend');
  const $btnTTS = document.getElementById('btnTTS');
  const $ttsIcon = document.getElementById('ttsIcon');
  const $agentGrid = document.getElementById('agentGrid');
  const $cortexStatus = document.getElementById('cortexStatus');
  const $clock = document.getElementById('clock');
  const $autocomplete = document.getElementById('autocomplete');
  const $modalOverlay = document.getElementById('modalOverlay');
  const $modal = document.getElementById('modal');
  const $modalTitle = document.getElementById('modalTitle');
  const $modalBody = document.getElementById('modalBody');
  const $modalClose = document.getElementById('modalClose');
  const $contextMenu = document.getElementById('contextMenu');

  // ---- WebSocket Connection ----
  function connectWS() {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${protocol}://${location.host}`);

    ws.onopen = () => {
      setCortexStatus('online', 'Cortex: Online');
      addSystemMessage('WebSocket verbunden ✓');
    };

    ws.onclose = () => {
      setCortexStatus('offline', 'Cortex: Offline');
      setTimeout(connectWS, 3000);
    };

    ws.onerror = () => setCortexStatus('offline', 'Verbindungsfehler');

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleWSMessage(msg);
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };
  }

  function handleWSMessage(msg) {
    switch (msg.type) {
      case 'agent_status':
        updateAgentGrid(msg.data);
        break;
      case 'chat_response':
        removeTyping();
        addAgentMessage(msg.data);
        break;
      case 'typing':
        showTyping(msg.data.agent);
        break;
      case 'system_message':
        addSystemMessage(msg.data.message);
        break;
      case 'memory_results':
      case 'cortex_results':
        showMemoryResults(msg.data);
        break;
      case 'error':
        addSystemMessage(`❌ ${msg.data.message}`);
        break;
      case 'agents_config_updated':
        AGENTS_META = { ...msg.data, conductor: { name: 'Conductor', icon: '⚡', color: '#00f0ff', desc: 'Kommandozentrale' } };
        if (agentStatusData.length) updateAgentGrid(agentStatusData);
        addSystemMessage('Agenten-Konfiguration aktualisiert');
        break;
    }
  }

  // ---- Agent Status Grid ----
  function updateAgentGrid(agents) {
    agentStatusData = agents;
    $agentGrid.innerHTML = '';

    // Map status data to our agent meta
    const statusMap = {};
    for (const a of agents) {
      const key = guessAgentKey(a.agent_name);
      if (key) statusMap[key] = a;
    }

    const displayOrder = Object.keys(AGENTS_META).filter(k => k !== 'conductor');
    for (const key of displayOrder) {
      const meta = AGENTS_META[key];
      const status = statusMap[key];
      const isRunning = status?.status === 'running';
      const statusClass = isRunning ? 'running' : (status ? 'stopped' : 'unknown');

      const card = document.createElement('div');
      card.className = `agent-card ${isRunning ? '' : 'dimmed'}`;
      card.dataset.agent = key;
      card.innerHTML = `
        <span class="agent-icon">${meta.icon}</span>
        <div class="agent-info">
          <div class="agent-name">${meta.name}</div>
          <div class="agent-detail">
            <span class="agent-status-dot ${statusClass}"></span>
            ${isRunning ? 'Running' : 'Stopped'}
            ${status?.port ? ` · :${status.port}` : ''}
          </div>
        </div>
      `;

      card.addEventListener('click', () => insertMention(key));
      card.addEventListener('contextmenu', (e) => showContextMenu(e, key));
      $agentGrid.appendChild(card);
    }

    // Update stats
    const total = agents.length;
    const online = agents.filter(a => a.status === 'running').length;
    document.getElementById('statAgents').textContent = total;
    document.getElementById('statOnline').textContent = online;
  }

  function guessAgentKey(name) {
    const n = name.toLowerCase();
    if (n.includes('hermes')) return 'hermes';
    if (n.includes('paperclip')) return 'paperclip';
    if (n.includes('openclaw')) return 'openclaw';
    if (n.includes('agent zero') || n.includes('agentzero')) return 'zero';
    if (n.includes('cortex') && !n.includes('mcp')) return 'cortex';
    if (n.includes('launcher')) return 'launcher';
    if (n.includes('tandem')) return 'tandem';
    if (n.includes('gravid') || n.includes('antigravity')) return 'antigravity';
    return null;
  }

  // ---- Chat Messages ----
  function sendMessage() {
    const text = $chatInput.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

    addUserMessage(text);
    ws.send(JSON.stringify({ type: 'chat', data: { message: text, ttsEnabled } }));
    $chatInput.value = '';
    $chatInput.style.height = 'auto';
    hideAutocomplete();
  }

  function addUserMessage(text) {
    const el = document.createElement('div');
    el.className = 'message user';
    el.innerHTML = `
      <div class="message-bubble">
        <div class="message-meta">
          <span class="message-agent-name" style="color:var(--cyan)">Du</span>
          <span class="message-time">${timeStr()}</span>
        </div>
        ${escapeAndFormat(text)}
      </div>
      <div class="message-avatar" style="border-color:var(--cyan)">👤</div>
    `;
    $chatMessages.appendChild(el);
    scrollChat();
  }

  function addAgentMessage(data) {
    const meta = AGENTS_META[data.agent] || { name: data.agentName, icon: data.agentIcon, color: data.agentColor };
    const el = document.createElement('div');
    el.className = 'message agent';
    el.innerHTML = `
      <div class="message-avatar" style="border-color:${meta.color}">${meta.icon}</div>
      <div class="message-bubble">
        <div class="message-meta">
          <span class="message-agent-name" style="color:${meta.color}">${meta.name}</span>
          <span class="message-time">${timeStr()}</span>
        </div>
        ${escapeAndFormat(data.message)}
      </div>
    `;
    $chatMessages.appendChild(el);
    scrollChat();
  }

  function addSystemMessage(text) {
    const el = document.createElement('div');
    el.className = 'message system-message';
    el.innerHTML = `<div class="message-content"><span class="system-icon">⚡</span>${escapeHTML(text)}</div>`;
    $chatMessages.appendChild(el);
    scrollChat();
  }

  function showTyping(agent) {
    removeTyping();
    const meta = AGENTS_META[agent] || AGENTS_META.conductor;
    const el = document.createElement('div');
    el.className = 'typing-indicator';
    el.id = 'typingIndicator';
    el.innerHTML = `
      <div class="message-avatar" style="border-color:${meta.color};width:28px;height:28px;font-size:14px;border-radius:6px;display:flex;align-items:center;justify-content:center;background:var(--bg-card);border:1px solid var(--border);">${meta.icon}</div>
      <div class="typing-dots"><span></span><span></span><span></span></div>
      <span class="typing-label">${meta.name} denkt…</span>
    `;
    $chatMessages.appendChild(el);
    scrollChat();
  }

  function removeTyping() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
  }

  // ---- Autocomplete ----
  function checkAutocomplete(text) {
    const match = text.match(/@(\w*)$/);
    if (!match) { hideAutocomplete(); return; }

    const query = match[1].toLowerCase();
    const agents = Object.entries(AGENTS_META).filter(([k, v]) =>
      k !== 'conductor' && (k.includes(query) || v.name.toLowerCase().includes(query))
    );

    if (agents.length === 0) { hideAutocomplete(); return; }

    $autocomplete.innerHTML = '';
    agents.forEach(([key, meta]) => {
      const item = document.createElement('div');
      item.className = 'autocomplete-item';
      item.dataset.key = key;
      item.innerHTML = `
        <span class="autocomplete-item-icon">${meta.icon}</span>
        <div>
          <div class="autocomplete-item-name">${meta.name}</div>
          <div class="autocomplete-item-desc">${meta.desc}</div>
        </div>
      `;
      item.addEventListener('click', () => selectAutocomplete(key));
      $autocomplete.appendChild(item);
    });

    $autocomplete.style.display = 'block';
    autocompleteIndex = -1;
  }

  function selectAutocomplete(key) {
    const val = $chatInput.value;
    $chatInput.value = val.replace(/@\w*$/, `@${key} `);
    hideAutocomplete();
    $chatInput.focus();
  }

  function hideAutocomplete() {
    $autocomplete.style.display = 'none';
    autocompleteIndex = -1;
  }

  function insertMention(key) {
    $chatInput.value = `@${key} `;
    $chatInput.focus();
  }

  // ---- Context Menu ----
  function showContextMenu(e, agentKey) {
    e.preventDefault();
    contextAgent = agentKey;
    $contextMenu.style.display = 'block';
    $contextMenu.style.left = `${e.clientX}px`;
    $contextMenu.style.top = `${e.clientY}px`;
  }

  document.addEventListener('click', () => {
    $contextMenu.style.display = 'none';
  });

  $contextMenu.querySelectorAll('.ctx-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.action;
      if (!contextAgent) return;
      if (action === 'chat') {
        insertMention(contextAgent);
      } else if (action === 'remove') {
        removeAgent(contextAgent);
      } else if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'agent_action', data: { action, agentId: contextAgent } }));
        addSystemMessage(`${action} → ${contextAgent}…`);
      }
      $contextMenu.style.display = 'none';
    });
  });

  // ---- Modals ----
  function openModal(title, content) {
    $modalTitle.textContent = title;
    $modalBody.innerHTML = content;
    $modalOverlay.style.display = 'flex';
  }

  function closeModal() {
    $modalOverlay.style.display = 'none';
  }

  $modalClose.addEventListener('click', closeModal);
  $modalOverlay.addEventListener('click', (e) => {
    if (e.target === $modalOverlay) closeModal();
  });

  // Memory Search
  document.getElementById('btnMemorySearch').addEventListener('click', () => {
    openModal('🔍 CORTEX MEMORY SEARCH', `
      <input class="modal-input" id="memorySearchInput" placeholder="Suchbegriff…" autofocus>
      <div class="modal-results" id="memoryResults"></div>
    `);
    const input = document.getElementById('memorySearchInput');
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && input.value.trim()) {
        ws.send(JSON.stringify({ type: 'memory_search', data: { query: input.value.trim() } }));
      }
    });
  });

  function showMemoryResults(data) {
    const container = document.getElementById('memoryResults');
    if (!container) return;
    const results = data?.results || [];
    if (results.length === 0) {
      container.innerHTML = '<div class="modal-result-item"><div class="result-content">Keine Ergebnisse.</div></div>';
      return;
    }
    container.innerHTML = results.slice(0, 10).map(r => `
      <div class="modal-result-item">
        <div class="result-type">${r.type || 'memory'} · ${r.source || ''}</div>
        <div class="result-content">${escapeHTML(r.content || '')}</div>
      </div>
    `).join('');
  }

  // Speak
  document.getElementById('btnSpeak').addEventListener('click', () => {
    openModal('🔊 SPRACHAUSGABE', `
      <input class="modal-input" id="speakInput" placeholder="Text zum Vorlesen…" autofocus>
    `);
    document.getElementById('speakInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target.value.trim()) {
        ws.send(JSON.stringify({ type: 'tts', data: { text: e.target.value.trim() } }));
        closeModal();
      }
    });
  });

  // Cortex Stats
  document.getElementById('btnCortexStats').addEventListener('click', async () => {
    try {
      const resp = await fetch('/api/cortex/stats');
      const data = await resp.json();
      const stats = data.stats || data;
      const rows = Object.entries(stats).map(([k,v]) =>
        `<div class="modal-result-item" style="display:flex;justify-content:space-between;">
          <span class="result-type">${k}</span>
          <span class="result-content" style="font-family:var(--font-mono);color:var(--cyan);">${v}</span>
        </div>`
      ).join('');
      openModal('📊 CORTEX STATS', `<div class="modal-results">${rows}</div>`);
    } catch (err) {
      openModal('📊 CORTEX STATS', `<div class="modal-result-item">Fehler: ${err.message}</div>`);
    }
  });

  // Clear Chat
  document.getElementById('btnClearChat').addEventListener('click', () => {
    $chatMessages.innerHTML = '';
    addSystemMessage('Chat geleert.');
  });

  // Add Agent
  document.getElementById('btnAddAgent').addEventListener('click', () => {
    openModal('➕ AGENT HINZUFÜGEN', `
      <input class="modal-input" id="addAgentId" placeholder="ID (z.B. myagent)">
      <input class="modal-input" id="addAgentName" placeholder="Name (z.B. My Agent)">
      <input class="modal-input" id="addAgentIcon" placeholder="Icon (z.B. 🤖)" value="🤖">
      <input class="modal-input" id="addAgentPort" placeholder="Port (optional, z.B. 8080)">
      <input class="modal-input" id="addAgentColor" placeholder="Farbe (z.B. #10b981)" value="#64748b">
      <input class="modal-input" id="addAgentDesc" placeholder="Beschreibung">
      <button class="action-btn" id="addAgentSubmit" style="width:100%;margin-top:8px;justify-content:center;border-color:var(--cyan);color:var(--cyan);">
        <span>✓ Agent hinzufügen</span>
      </button>
      <div id="addAgentResult" style="margin-top:10px;"></div>
    `);
    document.getElementById('addAgentSubmit').addEventListener('click', async () => {
      const id = document.getElementById('addAgentId').value.trim().toLowerCase();
      const name = document.getElementById('addAgentName').value.trim();
      if (!id || !name) { document.getElementById('addAgentResult').textContent = '❌ ID und Name sind Pflicht'; return; }
      try {
        const resp = await fetch('/api/agents/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id, name,
            icon: document.getElementById('addAgentIcon').value.trim() || '🤖',
            port: parseInt(document.getElementById('addAgentPort').value) || null,
            color: document.getElementById('addAgentColor').value.trim() || '#64748b',
            desc: document.getElementById('addAgentDesc').value.trim(),
          }),
        });
        if (resp.ok) { closeModal(); addSystemMessage(`Agent "${name}" hinzugefügt`); }
        else { document.getElementById('addAgentResult').textContent = '❌ Fehler beim Speichern'; }
      } catch (err) { document.getElementById('addAgentResult').textContent = '❌ ' + err.message; }
    });
  });

  // Remove Agent (via context menu)
  async function removeAgent(agentId) {
    if (!confirm(`Agent "${agentId}" wirklich entfernen?`)) return;
    try {
      const resp = await fetch(`/api/agents/config/${agentId}`, { method: 'DELETE' });
      if (resp.ok) addSystemMessage(`Agent "${agentId}" entfernt`);
    } catch (err) { addSystemMessage(`❌ ${err.message}`); }
  }

  // ---- TTS Toggle ----
  $btnTTS.addEventListener('click', () => {
    ttsEnabled = !ttsEnabled;
    $ttsIcon.textContent = ttsEnabled ? '🔊' : '🔇';
    $btnTTS.classList.toggle('active', ttsEnabled);
    addSystemMessage(ttsEnabled ? '🔊 Sprachausgabe aktiviert' : '🔇 Sprachausgabe deaktiviert');
  });

  // ---- Input Handlers ----
  $chatInput.addEventListener('input', () => {
    $chatInput.style.height = 'auto';
    $chatInput.style.height = Math.min($chatInput.scrollHeight, 120) + 'px';
    checkAutocomplete($chatInput.value);
  });

  $chatInput.addEventListener('keydown', (e) => {
    if ($autocomplete.style.display !== 'none') {
      const items = $autocomplete.querySelectorAll('.autocomplete-item');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        autocompleteIndex = Math.min(autocompleteIndex + 1, items.length - 1);
        items.forEach((it, i) => it.classList.toggle('selected', i === autocompleteIndex));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        autocompleteIndex = Math.max(autocompleteIndex - 1, 0);
        items.forEach((it, i) => it.classList.toggle('selected', i === autocompleteIndex));
      } else if (e.key === 'Tab' || e.key === 'Enter') {
        if (autocompleteIndex >= 0 && items[autocompleteIndex]) {
          e.preventDefault();
          selectAutocomplete(items[autocompleteIndex].dataset.key);
          return;
        }
      } else if (e.key === 'Escape') {
        hideAutocomplete();
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  $btnSend.addEventListener('click', sendMessage);

  // Cmd+K shortcut for memory search
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      document.getElementById('btnMemorySearch').click();
    }
  });

  // ---- Cortex Status Indicator ----
  function setCortexStatus(state, text) {
    const dot = $cortexStatus.querySelector('.status-dot');
    dot.className = `status-dot ${state} pulse`;
    $cortexStatus.querySelector('.status-text').textContent = text;
  }

  // ---- Clock ----
  function updateClock() {
    $clock.textContent = new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  setInterval(updateClock, 1000);
  updateClock();

  // ---- Fetch Cortex Stats on load ----
  async function loadCortexStats() {
    try {
      const resp = await fetch('/api/cortex/stats');
      const data = await resp.json();
      const s = data.stats || data;
      document.getElementById('statMemory').textContent = s.memory || '-';
    } catch {}
  }

  // ---- Particles ----
  function createParticles() {
    const container = document.getElementById('particles');
    for (let i = 0; i < 30; i++) {
      const p = document.createElement('div');
      const size = Math.random() * 2 + 1;
      Object.assign(p.style, {
        position: 'absolute',
        width: size + 'px', height: size + 'px',
        borderRadius: '50%',
        background: Math.random() > 0.5 ? 'rgba(0,240,255,0.3)' : 'rgba(139,92,246,0.3)',
        left: Math.random() * 100 + '%',
        top: Math.random() * 100 + '%',
        animation: `particleFloat ${8 + Math.random() * 12}s ease-in-out infinite`,
        animationDelay: `-${Math.random() * 10}s`,
      });
      container.appendChild(p);
    }
    // Inject keyframes
    const style = document.createElement('style');
    style.textContent = `@keyframes particleFloat {
      0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.3; }
      25% { transform: translate(${r()}px, ${r()}px) scale(1.5); opacity: 0.6; }
      50% { transform: translate(${r()}px, ${r()}px) scale(0.8); opacity: 0.2; }
      75% { transform: translate(${r()}px, ${r()}px) scale(1.2); opacity: 0.5; }
    }`;
    document.head.appendChild(style);
    function r() { return (Math.random() - 0.5) * 80; }
  }

  // ---- Helpers ----
  function scrollChat() {
    requestAnimationFrame(() => {
      $chatMessages.scrollTop = $chatMessages.scrollHeight;
    });
  }

  function timeStr() {
    return new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  }

  function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAndFormat(text) {
    let html = escapeHTML(text);
    // Simple code blocks
    html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  // ---- Init ----
  createParticles();
  loadAgentsConfig().then(() => {
    connectWS();
    loadCortexStats();
  });

})();
