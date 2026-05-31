/* ═══════════════════════════════════════════
   GNOM-HUB — Worker Agents (Sidebar Panel)
   ═══════════════════════════════════════════ */

async function loadAgents() {
  const res = await api('GET', '/agents');
  agents = Array.isArray(res) ? res : (res?.agents || []);
  if (typeof updateStats === 'function') updateStats();
  renderAgentList();
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

  document.getElementById('content').innerHTML = `
    <div class="panel">
      <h2>${agent.name} <div class="actions">
        ${resumeBtn} ${openUiBtn} ${nudgeBtn}
        <button onclick="toggleStatus('${agent.id}','${agent.status}')">${on ? '⏹ Offline' : '▶ Online'}</button>
        <button class="btn-danger" onclick="deleteAgent('${agent.id}')">Delete</button>
      </div></h2>
      <div class="status-row">
        <span class="dot ${statusDotClass}"></span><span class="label">${statusLabel}</span>
        ${port ? `<span class="badge port">:${port}</span>` : ''}
        <span class="label">Last seen: ${ls}</span>
      </div>
    </div>
    
    <!-- OPTIMIZER PANEL -->
    <div class="panel" id="agent-optimizer-panel" style="border: 1px solid rgba(255,255,255,0.08); background: linear-gradient(145deg, rgba(20,25,40,0.8), rgba(10,15,30,0.95));">
      <h2 style="border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px;">⚙️ Agent Inspector & Live Optimizer</h2>
      <div class="optimizer-grid" style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px; margin-top: 12px;">
        <!-- Left Column: Settings (Sliders) -->
        <div class="settings-column" style="display: flex; flex-direction: column; gap: 14px;">
          <div class="slider-group">
            <label style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 6px; font-weight: 500;">
              <span>Personality</span>
              <span id="label-personality" style="color: var(--accent); font-weight: bold;">-</span>
            </label>
            <input type="range" id="opt-personality" min="1" max="5" value="3" style="width: 100%; cursor: pointer;" oninput="updateOptSliderLabel('personality', this.value)">
          </div>
          
          <div class="slider-group">
            <label style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 6px; font-weight: 500;">
              <span>Response Style</span>
              <span id="label-response" style="color: var(--accent); font-weight: bold;">-</span>
            </label>
            <input type="range" id="opt-response" min="1" max="5" value="3" style="width: 100%; cursor: pointer;" oninput="updateOptSliderLabel('response', this.value)">
          </div>
          
          <div class="slider-group">
            <label style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 6px; font-weight: 500;">
              <span>Memory Strength</span>
              <span id="label-memory" style="color: var(--accent); font-weight: bold;">-</span>
            </label>
            <input type="range" id="opt-memory" min="1" max="5" value="3" style="width: 100%; cursor: pointer;" oninput="updateOptSliderLabel('memory', this.value)">
          </div>
          
          <div class="slider-group">
            <label style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 6px; font-weight: 500;">
              <span>Creativity</span>
              <span id="label-creativity" style="color: var(--accent); font-weight: bold;">-</span>
            </label>
            <input type="range" id="opt-creativity" min="1" max="5" value="3" style="width: 100%; cursor: pointer;" oninput="updateOptSliderLabel('creativity', this.value)">
          </div>
          
          <div class="slider-group">
            <label style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 6px; font-weight: 500;">
              <span>Risk Tolerance</span>
              <span id="label-risk" style="color: var(--accent); font-weight: bold;">-</span>
            </label>
            <input type="range" id="opt-risk" min="1" max="5" value="3" style="width: 100%; cursor: pointer;" oninput="updateOptSliderLabel('risk', this.value)">
          </div>

          <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px;">
            <button onclick="exportAgentConfig('${agent.id}')">📥 Export</button>
            <button onclick="document.getElementById('import-file-input').click()">📤 Import</button>
            <button onclick="saveActivePresetModal()">💾 Save Preset</button>
            <input type="file" id="import-file-input" style="display: none;" onchange="importAgentConfig('${agent.id}', this)">
          </div>
        </div>
        
        <!-- Right Column: Stats & Custom System Prompt -->
        <div class="prompt-stats-column" style="display: flex; flex-direction: column; gap: 16px;">
          <div class="stats-box" style="background: rgba(0, 0, 0, 0.2); padding: 12px 16px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.06); font-size: 0.8rem; line-height: 1.6;">
            <strong style="display: block; margin-bottom: 8px; color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Agent Statistics</strong>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px 12px;">
              <div>Calls: <span id="stat-calls" style="color: #fff; font-weight: bold;">0</span></div>
              <div>Errors: <span id="stat-errors" style="color: #ff4444; font-weight: bold;">0</span></div>
              <div>Latency: <span id="stat-latency" style="color: #fff; font-weight: bold;">0</span> ms</div>
              <div>Tokens: <span id="stat-tokens" style="color: #fff; font-weight: bold;">0</span></div>
            </div>
          </div>
          
          <div style="display: flex; flex-direction: column; flex-grow: 1;">
            <label style="font-size: 0.8rem; margin-bottom: 6px; display: flex; justify-content: space-between; font-weight: 500;">
              <span>Custom System Prompt Suffix</span>
              <span style="opacity: 0.5; font-size: 0.7rem;">Overrides base system prompt</span>
            </label>
            <textarea id="opt-custom-prompt" style="flex-grow: 1; min-height: 110px; width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.12); color: #fff; border-radius: 6px; padding: 10px; font-family: monospace; font-size: 0.75rem; resize: vertical; outline: none; transition: border-color 0.2s;" placeholder="Ggf. benutzerdefinierten Prompt-Suffix eintragen..." onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='rgba(255,255,255,0.12)'"></textarea>
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
  loadAgentMemory(agent.id);
  loadAgentOptimizerData(agent.id);
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
  if (typeof showWarRoom === 'function') showWarRoom();
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
function closeModal(id) { document.getElementById(id).classList.remove('show'); }
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
      document.getElementById('opt-response').value = settings.response_style ?? 3;
      document.getElementById('opt-memory').value = settings.memory_strength ?? 3;
      document.getElementById('opt-creativity').value = settings.creativity ?? 3;
      document.getElementById('opt-risk').value = settings.risk_tolerance ?? 3;
      document.getElementById('opt-custom-prompt').value = settings.custom_prompt ?? '';
      
      updateOptSliderLabel('personality', settings.personality ?? 3);
      updateOptSliderLabel('response', settings.response_style ?? 3);
      updateOptSliderLabel('memory', settings.memory_strength ?? 3);
      updateOptSliderLabel('creativity', settings.creativity ?? 3);
      updateOptSliderLabel('risk', settings.risk_tolerance ?? 3);
    }
    const stats = await api('GET', `/agents/${agentId}/stats`);
    if (stats) {
      document.getElementById('stat-calls').innerText = stats.total_calls ?? 0;
      document.getElementById('stat-errors').innerText = stats.errors ?? 0;
      document.getElementById('stat-latency').innerText = stats.avg_latency_ms ? Math.round(stats.avg_latency_ms) : 0;
      document.getElementById('stat-tokens').innerText = stats.total_tokens ?? 0;
    }
  } catch (err) {
    console.error('Error loading optimizer data:', err);
  }
}

function updateOptSliderLabel(type, val) {
  const v = parseInt(val);
  let txt = '';
  if (type === 'personality') {
    const map = { 1: 'Formal (1)', 2: 'Eher formal (2)', 3: 'Ausgeglichen (3)', 4: 'Locker (4)', 5: 'Sehr locker (5)' };
    txt = map[v] || v;
  } else if (type === 'response') {
    const map = { 1: 'Sehr knapp (1)', 2: 'Knapp (2)', 3: 'Ausgeglichen (3)', 4: 'Ausführlich (4)', 5: 'Sehr ausführlich (5)' };
    txt = map[v] || v;
  } else if (type === 'memory') {
    const map = { 1: 'Minimal (top_k: 2)', 2: 'Gering (top_k: 4)', 3: 'Standard (top_k: 8)', 4: 'Stark (top_k: 12)', 5: 'Maximum (top_k: 16)' };
    txt = map[v] || v;
  } else if (type === 'creativity') {
    const map = { 1: 'Konservativ (temp: 0.1)', 2: 'Fokussiert (temp: 0.4)', 3: 'Ausgeglichen (temp: 0.7)', 4: 'Kreativ (temp: 0.9)', 5: 'Wild (temp: 1.2)' };
    txt = map[v] || v;
  } else if (type === 'risk') {
    const map = { 1: 'Sehr vorsichtig (1)', 2: 'Vorsichtig (2)', 3: 'Ausgeglichen (3)', 4: 'Mutig (4)', 5: 'Sehr mutig (5)' };
    txt = map[v] || v;
  }
  const el = document.getElementById('label-' + type);
  if (el) el.innerText = txt;
}

async function saveAgentOptimizerSettings(agentId) {
  const personality = parseInt(document.getElementById('opt-personality').value);
  const response_style = parseInt(document.getElementById('opt-response').value);
  const memory_strength = parseInt(document.getElementById('opt-memory').value);
  const creativity = parseInt(document.getElementById('opt-creativity').value);
  const risk_tolerance = parseInt(document.getElementById('opt-risk').value);
  const custom_prompt = document.getElementById('opt-custom-prompt').value;
  try {
    const res = await api('PUT', `/agents/${agentId}/settings`, { personality, response_style, memory_strength, creativity, risk_tolerance, custom_prompt });
    if (res !== null) {
      toast('Einstellungen erfolgreich gespeichert!', 'success');
      loadAgentOptimizerData(agentId);
    } else {
      toast('Fehler beim Speichern der Einstellungen.', 'error');
    }
  } catch (err) {
    toast('Fehler beim Speichern: ' + err.message, 'error');
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
