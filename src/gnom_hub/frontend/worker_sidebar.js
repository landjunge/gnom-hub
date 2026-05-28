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
      <div class="mem-content" id="mc-${m.id}">${m.content || ''}</div>
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
  el.innerHTML = `<textarea id="ed-${id}">${old}</textarea>
    <div style="margin-top:6px;display:flex;gap:6px;justify-content:flex-end">
      <button onclick="selectAgent(selectedId)">Abbrechen</button>
      <button class="btn-primary" onclick="saveMem('${id}')">Speichern</button>
    </div>`;
}

async function saveMem(id) {
  const c = document.getElementById('ed-' + id).value;
  await fetch(API + `/memory/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: c })
  });
  selectAgent(selectedId);
}

async function deleteMem(id) {
  await api('DELETE', `/memory/${id}`);
  selectAgent(selectedId);
  if (typeof updateStats === 'function') updateStats();
}

async function clearMemory(agentId) {
  if (!confirm('Clear all memories?')) return;
  await api('DELETE', `/agents/${agentId}/memory`);
  selectAgent(selectedId);
  if (typeof updateStats === 'function') updateStats();
}

// ── Agent Actions ──
async function toggleStatus(id, current) {
  const agent = agents.find(a => a.id === id);
  const curr = agent ? agent.status : current;
  const isOff = curr === 'offline' || curr === 'sleeping';
  const next = isOff ? 'online' : 'offline';
  await fetch(API + `/agents/${id}/status?status=${next}`, { method: 'PUT' });
  await loadAgents();
  if (selectedId === id) {
    selectAgent(id);
  }
}

async function resumeAgent(id) {
  await fetch(API + `/agents/${id}/status?status=busy`, { method: 'PUT' });
  await loadAgents();
  selectAgent(id);
}

async function deleteAgent(id) {
  if (!confirm('Delete agent and all memories?')) return;
  await api('DELETE', `/agents/${id}`);
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
