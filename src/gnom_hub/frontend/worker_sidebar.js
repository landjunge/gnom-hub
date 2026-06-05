/* ═══════════════════════════════════════════
   GNOM-HUB — Worker Agents (Sidebar Panel)
   ═══════════════════════════════════════════ */

async function loadAgents() {
  const res = await api('GET', '/agents');
  const newAgents = Array.isArray(res) ? res : (res?.agents || []);
  
  // Check if any status changed
  let changed = newAgents.length !== agents.length;
  if (!changed) {
    for (let i = 0; i < newAgents.length; i++) {
      if (newAgents[i].status !== agents[i]?.status) { changed = true; break; }
    }
  }
  
  agents = newAgents;
  if (changed && typeof renderAgentList === 'function') renderAgentList();
  if (typeof updateStats === 'function') updateStats();
}

if (typeof _agentRefreshInterval === 'undefined') {
  window._agentRefreshInterval = setInterval(loadAgents, 10000);
}



// ── Agent Detail ──
async function selectAgent(id) {
  selectedId = id;
  const searchInput = document.getElementById('agent-search');
  renderAgentList(searchInput ? searchInput.value : '');
  const agent = agents.find(a => a.id === id);
  if (!agent) return;

  const on = agent.status === 'online';
  const isPaused = agent.status === 'paused';
  const resumeBtn = isPaused ? `<button onclick="resumeAgent('${agent.id}')" style="background:#ffa500; color:#000; border:none; border-radius:4px; font-weight:bold; cursor:pointer; padding:4px 8px; box-shadow:0 0 10px rgba(255,165,0,0.5);">▶ Resume</button>` : '';
  const port = agent.port;
  const openUiBtn = port ? `<button onclick="openAgentUI('${agent.name}','${port}')">🖥 Open UI</button>` : '';
  const nudgeBtn = on ? `<button onclick="doNudge('${agent.id}')">📢 Nudge</button>` : '';
  const ls = agent.last_seen ? new Date(agent.last_seen).toLocaleString() : '–';

  let statusDotClass = 'off';
  let statusLabel = 'Offline';
  if (on) {
    statusDotClass = 'on';
    statusLabel = 'Online';
  } else if (agent.status === 'busy') {
    statusDotClass = 'busy';
    statusLabel = 'Busy';
  } else if (isPaused) {
    statusDotClass = 'paused';
    statusLabel = 'Paused';
  }

  const meta = (window.getAgentMeta ? window.getAgentMeta(agent.name) : null) || { name: agent.name, desc: 'Schwarm-Mitglied' };
  const avatarUrl = window.getAgentAvatarUrl ? window.getAgentAvatarUrl(agent.name) : `/static/avatars/${agent.name.toLowerCase()}.png`;

  window.viewHistory.push('war-room');
  window.currentView = 'agent-detail';
  if (window.updateBackButtonState) window.updateBackButtonState();

  const target = document.getElementById('agent-detail-modal-body');
  const titleEl = document.getElementById('agent-detail-title');
  if (titleEl) titleEl.textContent = `${meta.name} - Details & Einstellungen`;

  const html = `
    <div class="panel" style="display:flex; gap:16px; align-items:center; border: 1px solid rgba(255,255,255,0.08); background: linear-gradient(145deg, rgba(20,25,40,0.8), rgba(10,15,30,0.95));">
      <img src="${avatarUrl}" alt="${meta.name}" style="width: 54px; height: 54px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.12); background: rgba(0,0,0,0.2); object-fit: cover;" onerror="this.src='/static/avatars/generalag.png'">
      <div style="flex-grow:1;">
        <h2 style="margin:0 0 6px 0; display: flex; align-items: center; justify-content: space-between;">
          <span>${meta.name}</span>
          <div class="actions">
            ${resumeBtn} ${openUiBtn} ${nudgeBtn}
            <button onclick="toggleStatus('${agent.id}','${agent.status}')">${on ? '⏹ Offline' : '▶ Online'}</button>
            <button class="btn-danger" onclick="deleteAgent('${agent.id}')">Delete</button>
          </div>
        </h2>
        <div class="status-row" style="margin:0;">
          <span class="dot ${statusDotClass}"></span><span class="label">${statusLabel}</span>
          ${port ? `<span class="badge port">:${port}</span>` : ''}
          <span class="label" style="margin-left: 10px;">Last seen: ${ls}</span>
        </div>
      </div>
    </div>
    
    <!-- OPTIMIZER PANEL -->
    <div class="panel" id="agent-optimizer-panel" style="border: 1px solid rgba(255,255,255,0.08); background: linear-gradient(145deg, rgba(20,25,40,0.8), rgba(10,15,30,0.95));">
      <h2 style="border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px; display: flex; align-items: center; justify-content: space-between;">
        <span>⚙️ Agent Inspector &amp; Live Optimizer</span>
        <span id="optimizer-dirty-badge" style="display:none; font-size:0.62rem; font-weight:600; color:#ffa500; background:rgba(255,165,0,0.12); border:1px solid rgba(255,165,0,0.35); border-radius:10px; padding:2px 8px; animation: pulse-badge 1.5s ease-in-out infinite;">● Nicht gespeichert</span>
      </h2>

      <!-- Agent Identity Block -->
      <div id="agent-identity-block" style="margin-bottom:14px;">
        <div style="font-size:0.62rem; font-weight:700; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Agent Identity</div>
        <div style="display:grid; grid-template-columns:85px 1fr 1fr 1fr; gap:8px;">
          <!-- Avatar Card -->
          <div id="identity-avatar" style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:8px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; text-align:center;">
            <img src="${avatarUrl}" alt="${meta.name}" style="width: 48px; height: 48px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.2); object-fit: cover;" onerror="this.src='/static/avatars/generalag.png'">
            <div style="font-size:0.58rem; font-weight:600; color:rgba(255,255,255,0.7); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; width:100%;">${meta.desc}</div>
          </div>
          <!-- LLM Card -->
          <div id="identity-llm" style="background:rgba(0,100,255,0.08); border:1px solid rgba(0,120,255,0.2); border-radius:8px; padding:10px 10px 8px; display:flex; flex-direction:column; gap:4px;">
            <div style="font-size:0.65rem; color:rgba(0,180,255,0.7); font-weight:700; letter-spacing:0.5px;">🧠 LLM</div>
            <div id="identity-llm-provider" style="font-size:0.75rem; color:#fff; font-weight:600;">–</div>
            <div id="identity-llm-model" style="font-size:0.62rem; color:rgba(255,255,255,0.45); word-break:break-all;">–</div>
            <select id="identity-llm-switch" onchange="quickSwitchLLM('${agent.id}', this.value)" style="margin-top:4px; font-size:0.62rem; background:rgba(0,0,0,0.4); color:#fff; border:1px solid rgba(0,150,255,0.3); border-radius:4px; padding:2px 4px; cursor:pointer; outline:none;">
              <option value="">– Wechseln –</option>
              <option value="deepseek|deepseek-chat">DeepSeek Chat</option>
              <option value="deepseek|deepseek-reasoner">DeepSeek Reasoner</option>
              <option value="openrouter|auto">OpenRouter (auto)</option>
              <option value="anthropic|claude-sonnet-4-5">Claude Sonnet</option>
              <option value="gemini|gemini-2.0-flash">Gemini Flash</option>
              <option value="lokal|llama3">Lokal (Ollama)</option>
            </select>
          </div>
          <!-- Tools Card -->
          <div id="identity-tools" style="background:rgba(57,255,20,0.05); border:1px solid rgba(57,255,20,0.15); border-radius:8px; padding:10px 10px 8px;">
            <div style="font-size:0.65rem; color:rgba(57,255,20,0.7); font-weight:700; letter-spacing:0.5px; margin-bottom:5px;">🔧 Tools</div>
            <div id="identity-tools-list" style="display:flex; flex-direction:column; gap:2px; font-size:0.62rem;"></div>
          </div>
          <!-- Soul Card -->
          <div id="identity-soul" style="background:rgba(176,38,255,0.07); border:1px solid rgba(176,38,255,0.2); border-radius:8px; padding:10px 10px 8px;">
            <div style="font-size:0.65rem; color:rgba(200,100,255,0.8); font-weight:700; letter-spacing:0.5px; margin-bottom:5px;">💡 Soul</div>
            <div id="identity-soul-count" style="font-size:1rem; font-weight:700; color:#fff; line-height:1;">–</div>
            <div style="font-size:0.58rem; color:rgba(255,255,255,0.35); margin-bottom:6px;">Fakten</div>
            <div id="identity-soul-facts" style="display:flex; flex-direction:column; gap:3px; font-size:0.6rem;"></div>
          </div>
        </div>
      </div>

      <!-- Config Summary -->
      <div id="optimizer-summary" style="font-size:0.68rem; color:rgba(255,255,255,0.45); background:rgba(0,0,0,0.2); border-radius:6px; padding:7px 12px; margin-bottom:14px; border:1px solid rgba(255,255,255,0.05); letter-spacing:0.2px; line-height:1.7;">Lade Konfiguration…</div>

      <div class="optimizer-grid" style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px;">
        <!-- Left Column: Sliders -->
        <div class="settings-column" style="display: flex; flex-direction: column; gap: 14px;">

          <div class="slider-group">
            <label style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px; font-weight: 500;">
              <span>Personality</span>
              <span id="label-personality" style="color: var(--accent); font-weight: bold;">-</span>
            </label>
            <input type="range" id="opt-personality" min="1" max="5" value="3" style="width: 100%; cursor: pointer;" oninput="updateOptSliderLabel('personality', this.value, true)">
            <div id="sub-personality" style="font-size:0.65rem; color:rgba(255,255,255,0.35); margin-top:3px; font-family:monospace;"></div>
          </div>

          <div class="slider-group">
            <label style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px; font-weight: 500;">
              <span>Response Style</span>
              <span id="label-response" style="color: var(--accent); font-weight: bold;">-</span>
            </label>
            <input type="range" id="opt-response" min="1" max="5" value="3" style="width: 100%; cursor: pointer;" oninput="updateOptSliderLabel('response', this.value, true)">
            <div id="sub-response" style="font-size:0.65rem; color:rgba(255,255,255,0.35); margin-top:3px; font-family:monospace;"></div>
          </div>

          <div class="slider-group">
            <label style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px; font-weight: 500;">
              <span>Memory Strength</span>
              <span id="label-memory" style="color: var(--accent); font-weight: bold;">-</span>
            </label>
            <input type="range" id="opt-memory" min="1" max="5" value="3" style="width: 100%; cursor: pointer;" oninput="updateOptSliderLabel('memory', this.value, true)">
            <div id="sub-memory" style="font-size:0.65rem; color:rgba(255,255,255,0.35); margin-top:3px; font-family:monospace;"></div>
          </div>

          <div class="slider-group">
            <label style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px; font-weight: 500;">
              <span>Creativity</span>
              <span id="label-creativity" style="color: var(--accent); font-weight: bold;">-</span>
            </label>
            <input type="range" id="opt-creativity" min="1" max="5" value="3" style="width: 100%; cursor: pointer;" oninput="updateOptSliderLabel('creativity', this.value, true)">
            <div id="sub-creativity" style="font-size:0.65rem; color:rgba(255,255,255,0.35); margin-top:3px; font-family:monospace;"></div>
          </div>

          <div class="slider-group">
            <label style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px; font-weight: 500;">
              <span>Risk Tolerance</span>
              <span id="label-risk" style="color: var(--accent); font-weight: bold;">-</span>
            </label>
            <input type="range" id="opt-risk" min="1" max="5" value="3" style="width: 100%; cursor: pointer;" oninput="updateOptSliderLabel('risk', this.value, true)">
            <div id="sub-risk" style="font-size:0.65rem; color:rgba(255,255,255,0.35); margin-top:3px; font-family:monospace;"></div>
          </div>

          <!-- Apply Button -->
          <button id="btn-apply-optimizer" onclick="saveAgentOptimizerSettings('${agent.id}')" style="margin-top:4px; width:100%; padding:9px 0; font-size:0.78rem; font-weight:700; color:#fff; background:linear-gradient(135deg,rgba(0,120,255,0.25),rgba(0,80,200,0.15)); border:1px solid rgba(0,150,255,0.5); border-radius:8px; cursor:pointer; transition:all 0.2s; letter-spacing:0.3px;" onmouseover="this.style.background='linear-gradient(135deg,rgba(0,150,255,0.4),rgba(0,100,220,0.3))'; this.style.borderColor='rgba(0,180,255,0.8)'; this.style.transform='translateY(-1px)';" onmouseout="this.style.background='linear-gradient(135deg,rgba(0,120,255,0.25),rgba(0,80,200,0.15))'; this.style.borderColor='rgba(0,150,255,0.5)'; this.style.transform='translateY(0)';" >💾 Einstellungen speichern</button>

          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button onclick="exportAgentConfig('${agent.id}')">📥 Export</button>
            <button onclick="document.getElementById('import-file-input').click()">📤 Import</button>
            <button onclick="saveActivePresetModal()">💾 Save Preset</button>
            <input type="file" id="import-file-input" style="display: none;" onchange="importAgentConfig('${agent.id}', this)">
          </div>
        </div>

        <!-- Right Column: Stats & Custom Prompt -->
        <div class="prompt-stats-column" style="display: flex; flex-direction: column; gap: 16px;">
          <div class="stats-box" style="background: rgba(0,0,0,0.2); padding: 12px 16px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.06); font-size: 0.8rem; line-height: 1.6;">
            <strong style="display: block; margin-bottom: 8px; color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Agent Statistics</strong>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px 12px;">
              <div>Calls: <span id="stat-calls" style="color: #fff; font-weight: bold;">0</span></div>
              <div>Errors: <span id="stat-errors" style="font-weight: bold;">0</span></div>
              <div>Latency: <span id="stat-latency" style="font-weight: bold;">0</span> ms <span id="stat-latency-icon" style="font-size:0.7rem;"></span></div>
              <div>Tokens: <span id="stat-tokens" style="color: #fff; font-weight: bold;">0</span></div>
            </div>
            <div id="stat-error-rate" style="margin-top:8px; font-size:0.72rem; padding:4px 8px; border-radius:4px; display:none;"></div>
            <div id="stat-custom-active" style="margin-top:6px; font-size:0.68rem; color:#ffa500; display:none;">✎ Custom Prompt aktiv</div>
          </div>

          <div style="display: flex; flex-direction: column; flex-grow: 1;">
            <label style="font-size: 0.8rem; margin-bottom: 6px; display: flex; justify-content: space-between; font-weight: 500;">
              <span>Rollen-Direktive (Base System Prompt)</span>
              <span style="opacity: 0.5; font-size: 0.7rem;">Definiert Kernverhalten und Regeln</span>
            </label>
            <textarea id="opt-sys-prompt" style="flex-grow: 1; min-height: 120px; width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.12); color: #fff; border-radius: 6px; padding: 10px; font-family: monospace; font-size: 0.75rem; resize: vertical; outline: none; transition: border-color 0.2s;" placeholder="Standard System Prompt..." oninput="_markOptimizerDirty()" onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='rgba(255,255,255,0.12)'"></textarea>
          </div>

          <div style="display: flex; flex-direction: column; flex-grow: 1; margin-top: 10px;">
            <label style="font-size: 0.8rem; margin-bottom: 6px; display: flex; justify-content: space-between; font-weight: 500;">
              <span>Custom System Prompt Suffix</span>
              <span style="opacity: 0.5; font-size: 0.7rem;">Wird an den Base Prompt angehängt</span>
            </label>
            <textarea id="opt-custom-prompt" style="flex-grow: 1; min-height: 110px; width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.12); color: #fff; border-radius: 6px; padding: 10px; font-family: monospace; font-size: 0.75rem; resize: vertical; outline: none; transition: border-color 0.2s;" placeholder="Ggf. benutzerdefinierten Prompt-Suffix eintragen..." oninput="_markOptimizerDirty()" onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='rgba(255,255,255,0.12)'"></textarea>
          </div>
        </div>
      </div>
    </div>
    
    <div class="panel">
      <h2>Memory <div class="actions">
        <button class="btn-danger" onclick="clearMemory('${agent.id}')">Clear all</button>
      </div></h2>
      <div class="add-mem">
        <textarea id="new-mem" placeholder="New memory entry…"></textarea>
        <button class="btn-primary" onclick="addMemory('${agent.id}')" style="align-self:flex-end">Save</button>
      </div>
      <div class="mem-search"><input placeholder="Search memories…" oninput="searchAgentMem('${agent.id}',this.value)"></div>
      <div id="mem-list"><div class="empty">Loading…</div></div>
    </div>
    <div id="agent-ui-frame"></div>`;

  if (target) {
    target.innerHTML = html;
    const modalBg = document.getElementById('modal-agent-detail');
    if (modalBg) {
      modalBg.classList.add('show');
    }
  } else {
    const content = document.getElementById('content');
    if (content) content.innerHTML = html;
  }

  loadAgentMemory(agent.id);
  loadAgentOptimizerData(agent.id);
  loadAgentProfile(agent.id);
}

async function loadAgentMemory(agentId) {
  const el = document.getElementById('mem-list');
  if (!el) return;
  const mems = await api('GET', `/agents/${agentId}/memory`);
  renderMemories(el, mems);
}

async function searchAgentMem(agentId, q) {
  const el = document.getElementById('mem-list');
  if (!el) return;
  if (!q) return loadAgentMemory(agentId);
  const all = await api('GET', `/agents/${agentId}/memory`);
  const filtered = (all || []).filter(m => (m.content || '').toLowerCase().includes(q.toLowerCase()));
  renderMemories(el, filtered);
}

function renderMemories(el, mems) {
  if (!mems || !mems.length) { el.innerHTML = '<div class="empty">Keine Einträge.</div>'; return; }
  el.innerHTML = mems.map(m => {
    const d = m.timestamp ? new Date(m.timestamp).toLocaleString() : '';
    return `<div class="mem-item" id="mem-${m.id}">
      <div class="mem-head"><span>${d}</span><div>
        <button onclick="editMem('${m.id}')">✏</button>
        <button class="btn-danger" onclick="deleteMem('${m.id}')">✕</button>
      </div></div>
      <div class="mem-content" id="mc-${m.id}">${escapeHtml(m.content)}</div>
    </div>`;
  }).join('');
}

async function addMemory(agentId) {
  const ta = document.getElementById('new-mem');
  const c = ta.value.trim();
  if (!c) return;
  await api('POST', '/memory', { agent_id: agentId, content: c });
  ta.value = '';
  loadAgentMemory(agentId);
  if (typeof updateStats === 'function') updateStats();
}

function editMem(id) {
  const el = document.getElementById('mc-' + id);
  const old = el.innerText;
  el.textContent = '';
  const ta = document.createElement('textarea');
  ta.id = 'ed-' + id;
  ta.value = old;
  el.appendChild(ta);
  const btnDiv = document.createElement('div');
  btnDiv.style.cssText = 'margin-top:6px;display:flex;gap:6px;justify-content:flex-end';
  btnDiv.innerHTML = `<button onclick="selectAgent(selectedId)">Abbrechen</button><button class="btn-primary" onclick="saveMem('${id}')">Speichern</button>`;
  el.appendChild(btnDiv);
}

async function saveMem(id) {
  const c = document.getElementById('ed-' + id).value;
  await api('PUT', `/memory/${id}`, { content: c });
  selectAgent(selectedId);
}

async function deleteMem(id) {
  await api('DELETE', `/memory/${id}`);
  toast('Erinnerung gelöscht', 'info');
  selectAgent(selectedId);
  if (typeof updateStats === 'function') updateStats();
}

async function clearMemory(agentId) {
  if (!confirm('Clear all memories?')) return;
  await api('DELETE', `/agents/${agentId}/memory`);
  toast('Alle Erinnerungen gelöscht', 'warning');
  selectAgent(selectedId);
  if (typeof updateStats === 'function') updateStats();
}

// ── Agent Actions ──
async function toggleStatus(id, current) {
  const agent = agents.find(a => a.id === id);
  const curr = agent ? agent.status : current;
  const isOff = curr === 'offline' || curr === 'sleeping';
  const next = isOff ? 'online' : 'offline';
  await api('PUT', `/agents/${id}/status?status=${next}`);
  const agentName = agent ? agent.name : id;
  toast(`${agentName} ist jetzt ${next === 'online' ? 'Online 🟢' : 'Offline 🔴'}`, 'info');
  await loadAgents();
  if (selectedId === id) {
    selectAgent(id);
  }
}

async function resumeAgent(id) {
  await api('PUT', `/agents/${id}/status?status=busy`);
  const agent = agents.find(a => a.id === id);
  const agentName = agent ? agent.name : id;
  toast(`${agentName} arbeitet wieder (Busy) 🟡`, 'info');
  await loadAgents();
  selectAgent(id);
}

async function deleteAgent(id) {
  if (!confirm('Delete agent and all memories?')) return;
  const agent = agents.find(a => a.id === id);
  const agentName = agent ? agent.name : id;
  await api('DELETE', `/agents/${id}`);
  toast(`${agentName} wurde gelöscht ❌`, 'warning');
  selectedId = null;
  closeModal('modal-agent-detail');
  await loadAgents();
}

function openAgentUI(name, port) {
  const frame = document.getElementById('agent-ui-frame');
  if (!frame) return;
  if (frame.innerHTML) { frame.innerHTML = ''; return; }
  frame.innerHTML = `<div class="panel"><h2>🖥 ${name} <div class="actions"><button onclick="document.getElementById('agent-ui-frame').innerHTML=''">Schließen</button>
    <button onclick="window.open('http://127.0.0.1:${port}','_blank')">↗ Tab</button></div></h2>
    <iframe src="http://127.0.0.1:${port}"></iframe></div>`;
}

// ── Register ──
function openAddAgent() { document.getElementById('modal-add').classList.add('show'); }
function closeModal(id) {
  document.getElementById(id).classList.remove('show');
  if (id === 'modal-agent-detail') {
    selectedId = null;
    const searchInput = document.getElementById('agent-search');
    if (typeof renderAgentList === 'function') {
      renderAgentList(searchInput ? searchInput.value : '');
    }
  }
}
async function doRegister() {
  const n = document.getElementById('add-name').value.trim();
  const p = parseInt(document.getElementById('add-port').value) || 0;
  const d = document.getElementById('add-desc').value.trim();
  if (!n || !p) { toast('Name and Port are required.', 'error'); return; }
  await api('POST', '/agents/register', { name: n, port: p, description: d });
  document.getElementById('add-name').value = '';
  document.getElementById('add-port').value = '';
  document.getElementById('add-desc').value = '';
  closeModal('modal-add');
  await loadAgents();
}

// ── Nudge ──
async function doNudge(id) {
  const card = document.getElementById('card-' + id);
  if (card) { card.classList.add('nudge-active'); setTimeout(() => card.classList.remove('nudge-active'), 800); }
  await api('POST', `/agents/${id}/nudge`);
}

// ── Agent Inspector & Live Optimizer Helpers ──
async function loadAgentOptimizerData(agentId) {
  try {
    const settings = await api('GET', `/agents/${agentId}/settings`);
    if (settings) {
      document.getElementById('opt-personality').value = settings.personality ?? 3;
      document.getElementById('opt-response').value    = settings.response_style ?? 3;
      document.getElementById('opt-memory').value      = settings.memory_strength ?? 3;
      document.getElementById('opt-creativity').value  = settings.creativity ?? 3;
      document.getElementById('opt-risk').value        = settings.risk_tolerance ?? 3;
      document.getElementById('opt-sys-prompt').value = settings.sys_prompt ?? '';
      document.getElementById('opt-custom-prompt').value = settings.custom_prompt ?? '';

      // Alle Labels + Subtexte sofort rendern (kein Dirty-Badge)
      ['personality', 'response', 'memory', 'creativity', 'risk'].forEach(t => {
        const keyMap = { personality: 'personality', response: 'response_style', memory: 'memory_strength', creativity: 'creativity', risk: 'risk_tolerance' };
        updateOptSliderLabel(t, settings[keyMap[t]] ?? 3, false);
      });
      _clearOptimizerDirty();

      // Custom Prompt Badge
      const cpBadge = document.getElementById('stat-custom-active');
      if (cpBadge) cpBadge.style.display = (settings.custom_prompt || '').trim() ? 'block' : 'none';
    }

    const stats = await api('GET', `/agents/${agentId}/stats`);
    if (stats) {
      const calls  = stats.total_calls ?? 0;
      const errors = stats.errors ?? 0;
      const latMs  = stats.avg_latency_ms ? Math.round(stats.avg_latency_ms) : 0;

      document.getElementById('stat-calls').innerText  = calls;
      document.getElementById('stat-tokens').innerText = stats.total_tokens ?? 0;

      // Errors mit Ampelfarbe
      const errEl = document.getElementById('stat-errors');
      if (errEl) { errEl.innerText = errors; errEl.style.color = errors === 0 ? '#39ff14' : errors < 5 ? '#ffa500' : '#ff4444'; }

      // Latency mit Icon
      const latEl   = document.getElementById('stat-latency');
      const latIcon = document.getElementById('stat-latency-icon');
      if (latEl)   { latEl.innerText = latMs; latEl.style.color = latMs < 500 ? '#39ff14' : latMs < 2000 ? '#ffa500' : '#ff4444'; }
      if (latIcon) latIcon.textContent = latMs < 500 ? '🟢' : latMs < 2000 ? '🟡' : '🔴';

      // Fehlerrate
      const rateEl = document.getElementById('stat-error-rate');
      if (rateEl && calls > 0) {
        const rate = ((errors / calls) * 100).toFixed(1);
        const col  = rate < 5 ? '#39ff14' : rate < 15 ? '#ffa500' : '#ff4444';
        const bg   = rate < 5 ? 'rgba(57,255,20,0.08)' : rate < 15 ? 'rgba(255,165,0,0.1)' : 'rgba(255,68,68,0.1)';
        rateEl.style.display = 'block';
        rateEl.style.color = col;
        rateEl.style.background = bg;
        rateEl.style.border = `1px solid ${col}33`;
        rateEl.textContent = `Fehlerrate: ${rate}%  (${errors} von ${calls} Calls)`;
      } else if (rateEl) {
        rateEl.style.display = 'none';
      }
    }
  } catch (err) {
    console.error('Error loading optimizer data:', err);
  }
}

// ── Slider label maps ──
const _SLIDER_MAPS = {
  personality: {
    labels: { 1: 'Formal', 2: 'Eher formal', 3: 'Ausgeglichen', 4: 'Locker', 5: 'Sehr locker' },
    subs:   { 1: '→ Tone: sehr formell, sachlich', 2: '→ Tone: formell', 3: '→ Tone: neutral', 4: '→ Tone: locker, freundlich', 5: '→ Tone: sehr locker, umgangssprachlich' }
  },
  response: {
    labels: { 1: 'Sehr knapp', 2: 'Knapp', 3: 'Ausgeglichen', 4: 'Ausführlich', 5: 'Sehr ausführlich' },
    subs:   { 1: '→ max_tokens: sehr niedrig, 1-2 Sätze', 2: '→ max_tokens: niedrig, kurze Absätze', 3: '→ max_tokens: mittel, Standard', 4: '→ max_tokens: hoch, strukturierte Antwort', 5: '→ max_tokens: sehr hoch, detailliert' }
  },
  memory: {
    labels: { 1: 'Minimal', 2: 'Gering', 3: 'Standard', 4: 'Stark', 5: 'Maximum' },
    subs:   { 1: '→ top_k: 2  (kaum Kontext)', 2: '→ top_k: 4', 3: '→ top_k: 8  (Standard)', 4: '→ top_k: 12', 5: '→ top_k: 16 (maximaler Kontext)' }
  },
  creativity: {
    labels: { 1: 'Konservativ', 2: 'Fokussiert', 3: 'Ausgeglichen', 4: 'Kreativ', 5: 'Wild' },
    subs:   { 1: '→ temperature: 0.1 (deterministisch)', 2: '→ temperature: 0.4', 3: '→ temperature: 0.7 (Standard)', 4: '→ temperature: 0.9', 5: '→ temperature: 1.2 (sehr zufällig)' }
  },
  risk: {
    labels: { 1: 'Sehr vorsichtig', 2: 'Vorsichtig', 3: 'Ausgeglichen', 4: 'Mutig', 5: 'Sehr mutig' },
    subs:   { 1: '→ Entscheidungen: immer eskalieren', 2: '→ Entscheidungen: vorsichtig prüfen', 3: '→ Entscheidungen: standard', 4: '→ Entscheidungen: eigenständig handeln', 5: '→ Entscheidungen: maximale Eigenverantwortung' }
  }
};

function _markOptimizerDirty() {
  const badge = document.getElementById('optimizer-dirty-badge');
  if (badge) badge.style.display = 'inline-block';
}

function _clearOptimizerDirty() {
  const badge = document.getElementById('optimizer-dirty-badge');
  if (badge) badge.style.display = 'none';
}

function _buildOptimizerSummary() {
  const p  = parseInt(document.getElementById('opt-personality')?.value || 3);
  const rs = parseInt(document.getElementById('opt-response')?.value    || 3);
  const m  = parseInt(document.getElementById('opt-memory')?.value      || 3);
  const cr = parseInt(document.getElementById('opt-creativity')?.value  || 3);
  const rk = parseInt(document.getElementById('opt-risk')?.value        || 3);
  const top_k_map  = { 1:2, 2:4, 3:8, 4:12, 5:16 };
  const temp_map   = { 1:'0.1', 2:'0.4', 3:'0.7', 4:'0.9', 5:'1.2' };
  const parts = [
    `Pers.: ${_SLIDER_MAPS.personality.labels[p] || p}`,
    `Style: ${_SLIDER_MAPS.response.labels[rs] || rs}`,
    `Memory: top_k=${top_k_map[m] || 8}`,
    `Temp: ${temp_map[cr] || '0.7'}`,
    `Risiko: ${_SLIDER_MAPS.risk.labels[rk] || rk}`
  ];
  const el = document.getElementById('optimizer-summary');
  if (el) el.textContent = parts.join('  ·  ');
}

function updateOptSliderLabel(type, val, markDirty = false) {
  const v = parseInt(val);
  const map = _SLIDER_MAPS[type];
  if (!map) return;
  const labelEl = document.getElementById('label-' + type);
  const subEl   = document.getElementById('sub-'   + type);
  if (labelEl) labelEl.innerText = `${map.labels[v] || v} (${v})`;
  if (subEl)   subEl.innerText   = map.subs[v]   || '';
  _buildOptimizerSummary();
  if (markDirty) _markOptimizerDirty();
}

async function saveAgentOptimizerSettings(agentId) {
  const personality     = parseInt(document.getElementById('opt-personality').value);
  const response_style  = parseInt(document.getElementById('opt-response').value);
  const memory_strength = parseInt(document.getElementById('opt-memory').value);
  const creativity      = parseInt(document.getElementById('opt-creativity').value);
  const risk_tolerance  = parseInt(document.getElementById('opt-risk').value);
  const custom_prompt   = document.getElementById('opt-custom-prompt').value;
  const sys_prompt      = document.getElementById('opt-sys-prompt').value;

  // Button-Feedback
  const btn = document.getElementById('btn-apply-optimizer');
  if (btn) { btn.textContent = '⏳ Speichere…'; btn.disabled = true; }

  try {
    const res = await api('PUT', `/agents/${agentId}/settings`, { personality, response_style, memory_strength, creativity, risk_tolerance, custom_prompt, sys_prompt });
    if (res !== null) {
      toast('Einstellungen erfolgreich gespeichert!', 'success');
      _clearOptimizerDirty();
      _buildOptimizerSummary();
      // Custom Prompt Badge aktualisieren
      const cpBadge = document.getElementById('stat-custom-active');
      if (cpBadge) cpBadge.style.display = custom_prompt.trim() ? 'block' : 'none';
      if (btn) { btn.textContent = '✓ Gespeichert'; setTimeout(() => { if (btn) btn.textContent = '💾 Einstellungen speichern'; btn.disabled = false; }, 1500); }
    } else {
      toast('Fehler beim Speichern der Einstellungen.', 'error');
      if (btn) { btn.textContent = '💾 Einstellungen speichern'; btn.disabled = false; }
    }
  } catch (err) {
    toast('Fehler beim Speichern: ' + err.message, 'error');
    if (btn) { btn.textContent = '💾 Einstellungen speichern'; btn.disabled = false; }
  }
}

async function exportAgentConfig(agentId) {
  try {
    const res = await api('GET', `/agents/${agentId}/export`);
    if (res) {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(res, null, 2));
      const dlAnchorElem = document.createElement('a');
      dlAnchorElem.setAttribute("href",     dataStr     );
      dlAnchorElem.setAttribute("download", `${res.agent?.name || 'agent'}_config.json`);
      dlAnchorElem.click();
      toast('Konfiguration exportiert!', 'success');
    }
  } catch (err) {
    toast('Export fehlgeschlagen: ' + err.message, 'error');
  }
}

async function importAgentConfig(agentId, input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async function(e) {
    try {
      const data = JSON.parse(e.target.result);
      const res = await api('POST', `/agents/${agentId}/import`, {
        settings: data.settings,
        soul_facts: data.soul_facts,
        prompt_versions: data.prompt_versions
      });
      if (res !== null) {
        toast('Konfiguration erfolgreich importiert!', 'success');
        loadAgentOptimizerData(agentId);
        loadAgentMemory(agentId);
      } else {
        toast('Fehler beim Importieren der Konfiguration.', 'error');
      }
    } catch (err) {
      toast('Ungültige JSON-Datei: ' + err.message, 'error');
    }
  };
  reader.readAsText(file);
  input.value = '';
}

function saveActivePresetModal() {
  document.getElementById('modal-save-preset').classList.add('show');
}

async function doSavePreset() {
  const name = document.getElementById('preset-name').value.trim();
  const description = document.getElementById('preset-desc').value.trim();
  if (!name || !description) { toast('Name und Beschreibung sind erforderlich.', 'error'); return; }
  try {
    const res = await api('POST', '/presets/save', { name, description });
    if (res !== null) {
      toast('Preset erfolgreich gespeichert!', 'success');
      closeModal('modal-save-preset');
      document.getElementById('preset-name').value = '';
      document.getElementById('preset-desc').value = '';
      if (typeof loadActivePreset === 'function') {
        await loadActivePreset();
      }
    } else {
      toast('Fehler beim Speichern des Presets.', 'error');
    }
  } catch (err) {
    toast('Fehler beim Speichern: ' + err.message, 'error');
  }
}

// ── Agent Profile (Identity Block) ──
const _ALL_TOOLS = [
  { key: 'read_file',       label: 'read',    icon: '📄' },
  { key: 'write_file',      label: 'write',   icon: '✏️' },
  { key: 'run_command',     label: 'run',     icon: '⚡' },
  { key: 'browser',         label: 'browser', icon: '🌐' },
  { key: 'generate_image',  label: 'image',   icon: '🎨' },
  { key: 'war_room_chat',   label: '@job',    icon: '💬' },
  { key: 'crawl_url',       label: 'crawl',   icon: '🕷️' },
  { key: 'evolve',          label: 'evolve',  icon: '🧬' },
];

async function loadAgentProfile(agentId) {
  try {
    const profile = await api('GET', `/agents/${agentId}/profile`);
    if (profile) renderIdentitySection(profile, agentId);
  } catch (err) {
    console.warn('Could not load agent profile:', err);
  }
}

function renderIdentitySection(profile, agentId) {
  // — LLM Card —
  const provEl = document.getElementById('identity-llm-provider');
  const modEl  = document.getElementById('identity-llm-model');
  const sw     = document.getElementById('identity-llm-switch');
  if (provEl) provEl.textContent = profile.llm_provider || '–';
  if (modEl)  modEl.textContent  = profile.llm_model    || '–';
  // Pre-select matching option in dropdown
  if (sw) {
    const target = `${profile.llm_provider}|${profile.llm_model}`;
    for (const opt of sw.options) {
      if (opt.value === target) { opt.selected = true; break; }
    }
  }

  // — Tools Card —
  const toolsEl = document.getElementById('identity-tools-list');
  if (toolsEl) {
    toolsEl.innerHTML = _ALL_TOOLS.map(t => {
      const has = (profile.tools || []).includes(t.key);
      return `<span style="color:${has ? '#39ff14' : 'rgba(255,255,255,0.18)'}; display:flex; gap:4px; align-items:center;" title="${t.key}">${has ? '✅' : '❌'} ${t.icon} ${t.label}</span>`;
    }).join('');
  }

  // — Soul Card —
  const cntEl   = document.getElementById('identity-soul-count');
  const factsEl = document.getElementById('identity-soul-facts');
  if (cntEl) cntEl.textContent = profile.soul_fact_count ?? '0';
  if (factsEl) {
    const facts = profile.top_soul_facts || [];
    if (!facts.length) {
      factsEl.innerHTML = '<span style="color:rgba(255,255,255,0.25);">keine Fakten</span>';
    } else {
      factsEl.innerHTML = facts.map(f => {
        const pCol = f.priority === 'high' ? '#ff9900' : f.priority === 'low' ? '#888' : '#aaa';
        const short = (f.value || '').substring(0, 42) + ((f.value || '').length > 42 ? '…' : '');
        return `<div style="border-left:2px solid ${pCol}; padding-left:4px; color:rgba(255,255,255,0.6);" title="${escapeHtml(f.value)}"><span style="color:${pCol}; font-weight:600;">${escapeHtml(f.key)}</span>: ${escapeHtml(short)}</div>`;
      }).join('');
    }
  }
}

async function quickSwitchLLM(agentId, providerModel) {
  if (!providerModel) return;
  const [provider, model] = providerModel.split('|');
  const agent = agents.find(a => a.id === agentId);
  if (!agent) return;
  try {
    // Read current llm_agents map, patch this agent, write back
    const current = await api('GET', '/llm/agents') || {};
    const key = agent.name.toLowerCase();
    current[key] = { ...(current[key] || {}), provider, model };
    const res = await api('POST', '/llm/agents', current);
    if (res && res.status === 'ok') {
      toast(`${agent.name} → ${provider} / ${model}`, 'success');
      // Update display immediately
      const provEl = document.getElementById('identity-llm-provider');
      const modEl  = document.getElementById('identity-llm-model');
      if (provEl) provEl.textContent = provider;
      if (modEl)  modEl.textContent  = model;
    } else {
      toast('LLM-Wechsel fehlgeschlagen', 'error');
    }
  } catch (err) {
    toast('Fehler beim LLM-Wechsel: ' + err.message, 'error');
  }
  // Reset dropdown to placeholder so re-selection is always possible
  const sw = document.getElementById('identity-llm-switch');
  if (sw) sw.value = '';
}
