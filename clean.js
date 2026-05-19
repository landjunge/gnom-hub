    /* ═══════════════════════════════════════════
       GNOM-HUB — Core Logic
       ═══════════════════════════════════════════ */

    // ── Toast ──
    function toast(msg, type = 'info') {
      const c = document.getElementById('toasts');
      const t = document.createElement('div');
      t.className = `toast ${type}`;
      t.textContent = msg;
      c.appendChild(t);
      setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(() => t.remove(), 300); }, 10500);
    }

    // ── NUKE (G-Button Long Press) ──
    let _nukeTimer = null;
    let _nukeArmed = false;
    function nukeStart(e) {
      e.stopPropagation();
      const btn = document.getElementById('nuke-btn');
      btn.classList.add('nuke-charging');
      _nukeArmed = false;
      _nukeTimer = setTimeout(() => {
        _nukeArmed = true;
        btn.classList.remove('nuke-charging');
        btn.classList.add('nuke-fired');
        nukeHub();
      }, 2000);
    }
    function nukeCancel() {
      if (_nukeTimer) { clearTimeout(_nukeTimer); _nukeTimer = null; }
      if (!_nukeArmed) {
        const btn = document.getElementById('nuke-btn');
        btn.classList.remove('nuke-charging');
      }
    }
    async function nukeHub() {
      const btn = document.getElementById('nuke-btn');
      
      const overlay = document.createElement('div');
      overlay.style.cssText = "position:fixed;top:0;left:0;width:100vw;height:100vh;background:radial-gradient(circle, rgba(40,0,0,0.95) 0%, rgba(10,0,0,1) 100%);z-index:99999;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#ff3333;font-family:monospace;text-align:center;text-transform:uppercase;";
      overlay.innerHTML = `<h1 style="font-size:4rem;text-shadow:0 0 20px #ff0000;margin:0;">☢️ SYSTEM PURGE</h1><h2 style="font-size:2rem;margin-top:10px;color:#ffaaaa;" id="nuke-status">Server wird beendet...</h2>`;
      document.body.appendChild(overlay);

      try {
        await fetch((API || '/api').replace('/api', '') + '/api/admin/nuke', { method: 'POST' });
      } catch(e) { /* Hub stirbt, das ist gewollt */ }
      
      btn.textContent = '✕';
      btn.classList.remove('nuke-fired');
      btn.classList.add('nuke-offline');
      
      let sec = 0;
      const statusEl = document.getElementById('nuke-status');
      
      // Auto-Reconnect Loop
      const reconnect = setInterval(async () => {
        sec += 2;
        if (statusEl) statusEl.textContent = `Warte auf Neustart... ${sec}s`;
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 1000);
          const r = await fetch((API || '/api').replace('/api', '') + '/api/health', { signal: controller.signal });
          clearTimeout(timeoutId);
          if (r.ok) {
            clearInterval(reconnect);
            if (statusEl) {
                statusEl.style.color = '#39ff14';
                statusEl.textContent = '🟢 VERBINDUNG WIEDERHERGESTELLT';
            }
            btn.textContent = 'G';
            btn.classList.remove('nuke-offline');
            btn.classList.add('nuke-ready');
            _nukeArmed = false;
            setTimeout(() => { btn.classList.remove('nuke-ready'); location.reload(); }, 1200);
          }
        } catch(e) { /* noch tot */ }
        if (sec > 60) {
          clearInterval(reconnect);
          if (statusEl) statusEl.textContent = '⚠️ Timeout. Bitte Server manuell starten: python3 -m gnom_hub';
          _nukeArmed = false;
        }
      }, 2000);
    }

    // ── API Discovery ──
    let API = '';
    let agents = [];
    let selectedId = null;

    async function discoverPort() {
      if (location.protocol !== 'file:') { API = location.origin + '/api'; return; }
      for (const p of [3003, 3002, 3001, 3000]) {
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 2000);
          const r = await fetch(`http://127.0.0.1:${p}/api/stats`, { signal: controller.signal });
          clearTimeout(timeoutId);
          if (r.ok) { API = `http://127.0.0.1:${p}/api`; return; }
        } catch (e) { }
      }
    }

    async function api(method, path, body) {
      try {
        const opts = { method, headers: { 'Content-Type': 'application/json' } };
        if (body) opts.body = JSON.stringify(body);
        const r = await fetch(API + path, opts);
        if (!r.ok) throw new Error(r.status);
        const text = await r.text();
        return text ? JSON.parse(text) : null;
      } catch (e) { console.error('API:', path, e); return null; }
    }

    // ── Colors ──
    const P_COLORS = ['#00E5FF', '#B026FF', '#FF007F', '#39FF14', '#FF3366', '#8A2BE2', '#0066FF', '#00FF9D', '#FF9900', '#FFD700', '#FF1493', '#00FA9A', '#1E90FF', '#FF4500', '#00FFFF'];
    const KNOWN_COLORS = {
      'generalag': '#00FFFF',    // Cyan
      'summarizerag': '#FF00FF', // Magenta
      'cronjobag': '#FFA500',    // Orange
      'backupag': '#00FF00',     // Lime Green
      'skillsag': '#FFFF00',     // Yellow
      'soulag': '#FF0000',       // Red
      'watchdogag': '#FF69B4',   // Hot Pink
      'tinyag': '#FFFFFF',       // White
      'testag1': '#0000FF',      // Pure Blue
      'testag2': '#800080',      // Deep Purple
      'testag3': '#008080',      // Teal
      'hermes-agent': '#8B4513', // Brown
      'writerag': '#00FF00',     // Grün
      'coderag': '#FF0000',      // Rot
      'researcherag': '#FFFF00', // Gelb
      'editorag': '#0088FF',           // Blau
      'web_crawlerag': '#FF8800',      // Orange
      'data_crawlerag': '#FF8800',     // Orange
      'smart_crawlerag': '#FF8800'     // Orange
    };
    function agentColor(name) {
      if (!name) return '#00E5FF';
      const n = name.toLowerCase();
      if (KNOWN_COLORS[n]) return KNOWN_COLORS[n];
      let h = 5381; for (let i = 0; i < name.length; i++) h = ((h << 5) + h) + name.charCodeAt(i);
      return P_COLORS[Math.abs(h) % P_COLORS.length];
    }
    function groupColor(g) {
      if (!g) return null;
      let h = 5381; for (let i = 0; i < g.length; i++) h = ((h << 5) + h) + g.charCodeAt(i);
      return P_COLORS[Math.abs(h) % P_COLORS.length];
    }

    // ── Agents ──
    async function loadAgents() {
      const res = await api('GET', '/agents');
      agents = Array.isArray(res) ? res : (res?.agents || []);
      updateStats();
      renderAgentList();
    }

    function renderAgentList(filter = '') {
      const el = document.getElementById('agent-list');
      const lampsEl = document.getElementById('status-lamps');
      const f = filter.toLowerCase();

      let filtered = f ? agents.filter(a => a.name.toLowerCase().includes(f)) : agents;
      filtered = filtered.filter(a => !a.name.toLowerCase().includes('hermes'));

      const coreNames = ['writerag', 'coderag', 'researcherag', 'editorag', 'web_crawlerag', 'data_crawlerag', 'smart_crawlerag'];
      const coreAgents = filtered.filter(a => coreNames.includes(a.name.toLowerCase()) && a.status !== 'sleeping');
      const internalAgents = filtered.filter(a => !coreNames.includes(a.name.toLowerCase()));

      // Render Core Agents to Sidebar
      if (!coreAgents.length) {
        el.innerHTML = '<div class="empty">Keine Agenten.</div>';
      } else {
        const renderCard = (a) => {
          const on = a.status === 'online';
          const role = a.role && a.role !== 'normal' ? a.role : '';
          const roleIcon = role === 'general' ? ' 👑' : role === 'summarizer' ? ' 📋' : '';
          const c = agentColor(a.name);
          return `<div class="agent-card ${a.id === selectedId ? 'active' : ''}" id="card-${a.id}" onclick="selectAgent('${a.id}')" style="border-left-color:${c};">
        <h3><span class="dot ${on ? 'on' : 'off'}" style="${on ? 'background:' + c + ';box-shadow:0 0 6px ' + c : ''}"></span><span>${a.name}</span>${roleIcon}</h3>
        <div class="desc">${a.description || '–'}</div>
        <div class="meta">${a.port ? `<span class="badge port">:${a.port}</span>` : ''}${role ? `<span class="badge role ${role}">${role}</span>` : ''}</div>
      </div>`;
        };
        el.innerHTML = coreAgents.map(renderCard).join('');
      }


    }

    function filterAgents(q) { renderAgentList(q); }

    // ── Agent Detail ──
    async function selectAgent(id) {
      selectedId = id;
      renderAgentList(document.getElementById('agent-search').value);
      const agent = agents.find(a => a.id === id);
      if (!agent) return;

      const on = agent.status === 'online';
      const port = agent.port;
      const openUiBtn = port ? `<button onclick="openAgentUI('${agent.name}','${port}')">🖥 Open UI</button>` : '';
      const nudgeBtn = on ? `<button onclick="doNudge('${agent.id}')">📢 Nudge</button>` : '';
      const ls = agent.last_seen ? new Date(agent.last_seen).toLocaleString() : '–';

      document.getElementById('content').innerHTML = `
    <div class="panel">
      <h2>${agent.name} <div class="actions">
        ${openUiBtn} ${nudgeBtn}
        <button onclick="toggleStatus('${agent.id}','${agent.status}')">${on ? '⏹ Offline' : '▶ Online'}</button>
        <button class="btn-danger" onclick="deleteAgent('${agent.id}')">Löschen</button>
      </div></h2>
      <div class="status-row">
        <span class="dot ${on ? 'on' : 'off'}"></span><span class="label">${on ? 'Online' : 'Offline'}</span>
        ${port ? `<span class="badge port">:${port}</span>` : ''}
        <span class="label">Last seen: ${ls}</span>
      </div>
    </div>
    <div class="panel">
      <h2>Memory <div class="actions">
        <button class="btn-danger" onclick="clearMemory('${agent.id}')">Alle löschen</button>
      </div></h2>
      <div class="add-mem">
        <textarea id="new-mem" placeholder="Neuen Memory-Eintrag…"></textarea>
        <button class="btn-primary" onclick="addMemory('${agent.id}')" style="align-self:flex-end">Speichern</button>
      </div>
      <div class="mem-search"><input placeholder="Memories durchsuchen…" oninput="searchAgentMem('${agent.id}',this.value)"></div>
      <div id="mem-list"><div class="empty">Lade…</div></div>
    </div>
    <div id="agent-ui-frame"></div>`;
      loadAgentMemory(agent.id);
    }

    async function loadAgentMemory(agentId) {
      const el = document.getElementById('mem-list');
      const mems = await api('GET', `/agents/${agentId}/memory`);
      renderMemories(el, mems);
    }

    async function searchAgentMem(agentId, q) {
      const el = document.getElementById('mem-list');
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
      updateStats();
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
      await fetch(API + `/memory/${id}?content=${encodeURIComponent(c)}`, { method: 'PUT' });
      selectAgent(selectedId);
    }

    async function deleteMem(id) {
      await api('DELETE', `/memory/${id}`);
      selectAgent(selectedId);
      updateStats();
    }

    async function clearMemory(agentId) {
      if (!confirm('Alle Memories löschen?')) return;
      await api('DELETE', `/agents/${agentId}/memory`);
      selectAgent(selectedId);
      updateStats();
    }

    // ── Agent Actions ──
    async function toggleStatus(id, current) {
      const next = current === 'online' ? 'offline' : 'online';
      await fetch(API + `/agents/${id}/status?status=${next}`, { method: 'PUT' });
      await loadAgents();
      selectAgent(id);
    }

    async function deleteAgent(id) {
      if (!confirm('Agent und alle Memories löschen?')) return;
      await api('DELETE', `/agents/${id}`);
      selectedId = null;
      showWarRoom();
      await loadAgents();
    }

    function openAgentUI(name, port) {
      const frame = document.getElementById('agent-ui-frame');
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
      if (!n || !p) { alert('Name and Port are required.'); return; }
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

    // ── Stats ──
    async function updateStats() {
      const s = await api('GET', '/stats');
      if (s) {
        const sysNames = ['watchdogag', 'skillsag', 'backupag', 'cronjobag', 'soulag', 'summarizerag', 'generalag', 'securityag'];
        const totalA = s.agents ?? agents.length;
        const sysA = s.sys_agents ?? agents.filter(a => sysNames.includes((a.name || '').toLowerCase())).length;
        const workA = s.work_agents ?? (totalA - sysA);
        document.getElementById('s-agents').textContent = `${totalA} (Sys: ${sysA} | Work: ${workA})`;
        document.getElementById('s-memory').textContent = s.memory ?? 0;
        if (document.getElementById('s-tokens')) {
          const tFree = s.tokens_free ?? 0;
          const tPay = s.tokens_pay ?? 0;
          document.getElementById('s-tokens').textContent = `Free: ${tFree} | Pay: ${tPay}`;
          if (document.getElementById('layer-tfree')) document.getElementById('layer-tfree').textContent = (tFree / 1000).toFixed(1) + 'K';
          if (document.getElementById('layer-tpay')) document.getElementById('layer-tpay').textContent = (tPay / 1000).toFixed(1) + 'K';
        }
      }
    }

    // ═══ WAR ROOM (FIX: always renders complete chat with autocomplete) ═══
    function buildWarRoomHTML() {
      const ttsChecked = document.getElementById('tts-enabled')?.checked ?? false;
      return `<div class="panel" id="war-room">
    <h2 style="display:flex; align-items:center;">War Room <span id="project-indicator" style="font-size:0.75rem; color:var(--text-muted); background:rgba(255,255,255,0.05); padding:3px 8px; border-radius:12px; margin-left:10px; border:1px solid rgba(255,255,255,0.1);">MAIN HUB</span>
      <button id="project-help-btn" onclick="const e=document.getElementById('project-explanation'); e.style.display = e.style.display==='none' ? 'block' : 'none';" style="display:none; margin-left:8px; padding:3px 8px; font-size:0.7rem; border-radius:12px; border:1px solid var(--green); background:rgba(57,255,20,0.1); color:var(--green); cursor:pointer;">ℹ️ Info</button>
    </h2>
    <div id="project-explanation" style="display:none; font-size:0.8rem; color:#fff; background:rgba(61,220,132,0.1); border-left:3px solid var(--green); padding:10px 14px; margin-bottom:12px; border-radius:4px; line-height:1.5;"></div>
    <div id="chat-display"></div>
    <div class="chat-bar">
      <div class="chat-input-wrap">
        <div class="ac-dropdown" id="ac-dropdown"></div>
        <textarea id="chat-input" placeholder="@bs @research @idea …" oninput="onChatInput(this)" onkeydown="onChatKey(event)"></textarea>
      </div>
      <div style="display:flex; flex-direction:column; gap:8px; height: 92px; min-width: 85px;">
        <input type="checkbox" id="tts-enabled" style="display:none;" ${ttsChecked ? 'checked' : ''}>
        <button id="mic-btn" class="btn-mic" style="flex:1; width:100%; padding:0;" onclick="toggleSTT()" title="Voice Input">Rec</button>
        <button class="btn-primary" style="flex:1; width:100%; padding:0;" onclick="sendChat()">Send</button>
      </div>
    </div>
    <div class="chat-hints">
      <span data-tooltip="Brainstorm: Aktiviere den Schwarm für komplexe Ideen.">@bs</span>
      <span data-tooltip="Research: Starte einen autonomen Recherche-Job.">@research</span>
      <span data-tooltip="Job Task: Verteile Hintergrundaufgaben an Agenten.">@job</span>
      <span data-tooltip="Idea: Notiere einen Gedanken in der System-Memory.">@idea</span>
      <span data-tooltip="Skill: Injiziere einem Agenten eine neue Fähigkeit.">@skill</span>
      <span data-tooltip="Free: Löse aktive Jobs von einem Agenten.">@free</span>
      <span data-tooltip="Projekt wechseln: (z.B. @@projekt netzwerkpunkt)">@@projekt</span>
      <span data-tooltip="Löschen: (@@clear chat, @@clear @projekt, @@clear all agents)">@@clear</span>
      <span data-tooltip="Status: System- und Agenten-Status abrufen.">@@status</span>
      <span data-tooltip="Provider wechseln: (z.B. @@provider ollama llama3)">@@provider</span>
      <span data-tooltip="Git: Git Befehle ausführen (z.B. @@git status)">@@git</span>
      <span data-tooltip="Rollback: Mache Änderungen rückgängig (Swarm-Checkpoint)">@@rollback</span>
      <span data-tooltip="Checkpoint: Aktuellen Memory-Status erzwingen">@@checkpoint</span>
      <span data-tooltip="Summarize: Generiere eine kurze Zusammenfassung">@@summary</span>
      <span data-tooltip="Desktop: Kontrolliere das OS via PyAutoGUI.">@@desktop</span>
      <span data-tooltip="Vision: Bildschirm analysieren.">@@vision</span>
      <span data-tooltip="Kaffeepause: (Animation)">/coffee</span>
      <span data-tooltip="UFO Event: (Animation)">/ufo</span>
      <span data-tooltip="Ghost: (Animation)">/ghost</span>
    </div>
  </div>`;
    }

    // ── Workspace ──
    async function showWorkspace() {
      selectedId = null;
      document.getElementById('content').innerHTML = `
    <div class="panel" id="workspace-panel">
      <h2>Workspace <div class="actions"><button class="btn-primary" onclick="loadWorkspace()">Refresh</button></div></h2>
      <div id="workspace-list"><div class="empty">Lade Dateien...</div></div>
    </div>
  `;
      await loadWorkspace();
    }

    async function loadWorkspace() {
      const list = document.getElementById('workspace-list');
      if (!list) return;
      const files = await api('GET', '/workspace');
      const projRes = await api('GET', '/project');
      const projName = projRes && projRes.project ? projRes.project : 'default';

      const panelTitle = document.querySelector('#workspace-panel h2');
      if (panelTitle) {
        panelTitle.innerHTML = `📁 gnom_workspace / <span style="color:var(--green)">${projName}</span> <div class="actions"><button class="btn-primary" onclick="loadWorkspace()">Refresh</button></div>`;
      }

      if (!files || files.error) {
        list.innerHTML = '<div class="empty">Fehler beim Laden des Workspaces.</div>';
        return;
      }
      if (files.length === 0) {
        list.innerHTML = '<div class="empty">Dieser Projekt-Ordner ist leer.</div>';
        return;
      }
      let html = '';
      files.forEach(f => {
        const date = new Date(f.mtime * 1000).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const ext = f.name.split('.').pop().toLowerCase();
        const isWeb = ['html', 'htm', 'css', 'js', 'svg'].includes(ext);
        const isPy = ext === 'py';
        let actionBtn = '';
        if (isWeb) {
          actionBtn = `<button class="btn-primary" onclick="event.stopPropagation(); openWorkspaceFile('${f.name}')" title="Im Browser öffnen">🌐 Open</button>`;
        } else if (isPy) {
          actionBtn = `<button class="btn-primary" onclick="event.stopPropagation(); runWorkspaceFile('${f.name}')" title="Python ausführen">▶ Run</button>`;
        }
        html += `<div class="mem-item" style="display:flex; justify-content:space-between; align-items:center;">
          <div style="cursor:pointer; flex:1;" onclick="readWorkspaceFile('${f.name}')">
            <strong style="color:#0096ff">${f.name}</strong> 
            <span style="font-size:0.8em;color:var(--text-dim);margin-left:10px;">${f.size} Bytes</span>
          </div>
          <div style="display:flex; align-items:center; gap:10px;">
            <span style="font-size:0.75rem; color:var(--text-muted);">${date}</span>
            ${actionBtn}
          </div>
      </div>`;
      });
      list.innerHTML = html;
    }

    function openWorkspaceFile(name) {
      window.open(`/api/workspace/${name}/serve`, '_blank');
    }

    async function runWorkspaceFile(name) {
      toast('Starte ' + name + '...', 'info');
      const res = await api('POST', `/workspace/${name}/run`);
      if (!res) { toast('Ausführung fehlgeschlagen', 'error'); return; }
      const modal = document.createElement('div');
      modal.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:9999;display:flex;align-items:center;justify-content:center;";
      const hasErr = res.stderr && res.stderr.trim();
      const statusColor = res.code === 0 ? 'var(--green)' : '#ff4444';
      modal.innerHTML = `
      <div class="panel" style="width:70%; max-height:80%; display:flex; flex-direction:column;">
        <h2>▶ ${name} <span style="color:${statusColor};font-size:0.8em;">Exit: ${res.code}</span> <button onclick="this.parentElement.parentElement.parentElement.remove()" style="float:right">X</button></h2>
        <pre style="flex-grow:1; overflow:auto; background:var(--bg-input); color:var(--text); border:1px solid var(--border); border-radius:var(--radius); padding:10px; font-family:monospace; white-space:pre-wrap; max-height:60vh;">${res.stdout || '(keine Ausgabe)'}</pre>
        ${hasErr ? `<pre style="margin-top:8px; background:#1a0000; color:#ff6666; border:1px solid #ff4444; border-radius:var(--radius); padding:10px; font-family:monospace; white-space:pre-wrap; max-height:20vh; overflow:auto;">STDERR:\n${res.stderr}</pre>` : ''}
      </div>
    `;
      document.body.appendChild(modal);
    }

    async function readWorkspaceFile(name) {
      const res = await api('GET', `/workspace/${name}`);
      if (res && res.content !== undefined) {
        const modal = document.createElement('div');
        modal.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:9999;display:flex;align-items:center;justify-content:center;";
        modal.innerHTML = `
         <div class="panel" style="width:80%; height:80%; display:flex; flex-direction:column;">
           <h2>${name} <button onclick="this.parentElement.parentElement.parentElement.remove()" style="float:right">X</button></h2>
           <textarea readonly style="flex-grow:1; background:var(--bg-input); color:var(--text); border:1px solid var(--border); border-radius:var(--radius); padding:10px; font-family:monospace; resize:none;">${res.content}</textarea>
         </div>
       `;
        document.body.appendChild(modal);
      } else {
        toast("Fehler beim Lesen der Datei", "error");
      }
    }

    async function updateProjectIndicator() {
      const res = await api('GET', '/project');
      const p = res && res.project ? res.project : 'default';
      const ind = document.getElementById('project-indicator');
      const expl = document.getElementById('project-explanation');
      const helpBtn = document.getElementById('project-help-btn');
      if (ind) {
        if (p === 'default') {
          ind.textContent = 'MAIN HUB';
          ind.style.color = 'var(--text-muted)';
          ind.style.borderColor = 'rgba(255,255,255,0.1)';
          ind.style.background = 'rgba(255,255,255,0.05)';
          if (helpBtn) helpBtn.style.display = 'none';
          if (expl) expl.style.display = 'none';
        } else {
          ind.textContent = p.toUpperCase();
          ind.style.color = 'var(--green)';
          ind.style.borderColor = 'rgba(57,255,20,0.3)';
          ind.style.background = 'rgba(57,255,20,0.05)';
          if (helpBtn) helpBtn.style.display = 'inline-block';
        }
      }
      if (expl && p !== 'default') {
        expl.innerHTML = `🛡️ <strong>Projekt-Modus aktiv: ${p}</strong><br>Du bist im Projekt <b>${p}</b>. Die Kommunikation, alle Dateien und Agenten-Gedanken werden exklusiv für dieses Projekt gespeichert. Wenn du in 10 Jahren weiter machen willst, findest du alles exakt so wieder. <i>(Tippe <code>@projekt default</code> um das Projekt zu verlassen)</i>`;
      }
    }

    function showWarRoom() {
      selectedId = null;
      renderAgentList(document.getElementById('agent-search').value);
      document.getElementById('content').innerHTML = buildWarRoomHTML();
      updateProjectIndicator();
      refreshChat();
    }

    // ── Autocomplete ──
    const BUILTIN_CMDS = ['bs', 'research', 'job', 'idea', 'summary', 'status', 'clear', 'skill', 'free', 'provider', 'git', 'rollback', 'checkpoint', 'projekt', 'evolve', 'tts'];
    let acIdx = -1;

    function onChatInput(ta) {
      const dd = document.getElementById('ac-dropdown');
      if (!dd) return;
      const val = ta.value, m = val.match(/@(\w*)$/);
      if (!m) { dd.classList.remove('show'); return; }
      const q = m[1].toLowerCase();
      const agentNames = agents.map(a => a.name);
      const all = [...BUILTIN_CMDS, ...agentNames].filter(n => n.toLowerCase().startsWith(q));
      if (!all.length || (all.length === 1 && all[0].toLowerCase() === q)) { dd.classList.remove('show'); return; }
      acIdx = -1;
      dd.innerHTML = all.map(n => `<div class="ac-item" onmousedown="pickAc('${n}')">${BUILTIN_CMDS.includes(n) ? '@' + n : '@ ' + n}</div>`).join('');
      dd.classList.add('show');
    }

    function pickAc(name) {
      const ta = document.getElementById('chat-input');
      ta.value = ta.value.replace(/@\w*$/, '@' + name + ' ');
      document.getElementById('ac-dropdown').classList.remove('show');
      ta.focus();
    }

    function onChatKey(e) {
      const dd = document.getElementById('ac-dropdown');
      if (!dd) return;
      const items = dd.querySelectorAll('.ac-item');
      if (dd.classList.contains('show') && items.length) {
        if (e.key === 'ArrowDown') { e.preventDefault(); acIdx = Math.min(acIdx + 1, items.length - 1); items.forEach((el, i) => el.classList.toggle('active', i === acIdx)); return; }
        if (e.key === 'ArrowUp') { e.preventDefault(); acIdx = Math.max(acIdx - 1, 0); items.forEach((el, i) => el.classList.toggle('active', i === acIdx)); return; }
        if (e.key === 'Tab') { e.preventDefault(); pickAc(items[acIdx >= 0 ? acIdx : 0]?.textContent.replace(/^@\s?/, '') || ''); return; }
        if (e.key === 'Enter' && acIdx >= 0) { e.preventDefault(); pickAc(items[acIdx]?.textContent.replace(/^@\s?/, '') || ''); return; }
        if (e.key === 'Escape') { dd.classList.remove('show'); return; }
      }
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
    }

    // ── Chat ──
    async function sendChat() {
      const ta = document.getElementById('chat-input');
      if (!ta) return;
      const msg = ta.value.trim();
      if (!msg) return;
      ta.value = '';

      // Easter Egg Cheat Codes & UI Commands
      const m = msg.toLowerCase();
      if (m === '@tts on') { const cb = document.getElementById('tts-enabled'); if (cb) cb.checked = true; ta.value = ''; toast('🗣️ TTS Aktiviert', 'success'); return; }
      if (m === '@tts off') { const cb = document.getElementById('tts-enabled'); if (cb) cb.checked = false; stopTTS(); ta.value = ''; toast('🔇 TTS Deaktiviert', 'info'); return; }
      if (m === '@tts') { const cb = document.getElementById('tts-enabled'); if (cb) { cb.checked = !cb.checked; if (!cb.checked) stopTTS(); toast(cb.checked ? '🗣️ TTS Aktiviert' : '🔇 TTS Deaktiviert', cb.checked ? 'success' : 'info'); } ta.value = ''; return; }
      if (m === '/ufo') { if (window.showUfoAttack) window.showUfoAttack(); return; }
      if (m === '/ghost') { if (window.showGhost) window.showGhost(); return; }
      if (m === '/coffee') { if (window.showCoffeeBreak) window.showCoffeeBreak(); return; }
      if (m.startsWith('@showbox speed ')) {
        const speedVal = parseFloat(m.substring(12).trim());
        if (!isNaN(speedVal) && speedVal > 0) {
          window.showboxSpeed = speedVal * 1000;
          if (window.activeShowboxIndex >= 0 && window.showboxActive) {
            const idx = window.activeShowboxIndex;
            window.closeShowbox();
            setTimeout(() => window.triggerShowbox(idx), 100);
          }
          toast(`Show Speed: ${speedVal}s`, 'success');
        } else {
          toast('Ungültiger Speed-Wert!', 'error');
        }
        ta.value = '';
        return;
      }

      if (m.startsWith('@showbox ')) {
        const showName = m.substring(6).trim();
        if (window.activeShowboxIndex >= 0) {
          const s = document.createElement('script');
          s.src = showName + '.js';
          s.onload = () => {
            if (window.loadedShowbox) {
              const idx = window.activeShowboxIndex;
              window.showboxes[idx] = window.loadedShowbox;
              window.closeShowbox();
              setTimeout(() => window.triggerShowbox(idx), 100);
            }
          };
          document.head.appendChild(s);
          toast(`Lade neue Show: ${showName}`, 'success');
        } else {
          toast('Bitte zuerst einen Button/eine Show aktivieren!', 'error');
        }
        ta.value = '';
        return;
      }

      document.getElementById('ac-dropdown')?.classList.remove('show');
      const res = await api('POST', '/chat', { content: msg });
      if (res) {
        if (res.status === 'role_set') toast(`👑 ${res.agent} → ${res.role}`, 'success');
        else if (res.status === 'idea_saved') toast('💡 Idea saved', 'success');
        else if (res.status === 'job_created') toast(`📋 Job → ${res.general}: ${res.task?.substring(0, 60)}`, 'success');
        else if (res.msg) toast(`⚠️ ${res.msg}`, 'error');
        else if (res.status === 'cleared') toast('🗑 Chat cleared', 'success');
        else if (res.status === 'agents') toast(`📊 ${res.agents.map(a => a.name + '(' + a.role + ')').join(', ')}`, 'info');
        else { const target = res.target ? `→ ${res.target}` : `→ ${(res.asked || []).join(', ') || 'nobody'}`; toast(`${res.mode === 'brainstorm' ? '🧠' : res.mode === 'research' ? '🔍' : '💬'} ${target}`, 'success'); }
        refreshChat(); loadAgents();
      } else { toast('Hub unreachable', 'error'); }
    }

    function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

    async function refreshChat() {
      const el = document.getElementById('chat-display');
      if (!el) return;
      const msgs = await api('GET', '/chat?limit=20');

      // Prevent DOM rebuild if messages haven't changed
      const dataStr = JSON.stringify(msgs || []);
      if (window._lastChatData === dataStr) return;
      window._lastChatData = dataStr;

      const st = el.scrollTop;
      const wasAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;

      if (!msgs || !msgs.length) { el.innerHTML = '<div class="empty">No messages yet.</div>'; return; }
      const sorted = msgs.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));
      window._processedShowboxes = window._processedShowboxes || new Set();

      el.innerHTML = sorted.map(m => {
        const isUser = m.metadata?.sender === 'user';
        const name = isUser ? 'You' : (m.metadata?.sender || 'System');
        const time = m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : '';
        const c = isUser ? 'var(--primary)' : agentColor(name);
        const nameColor = isUser ? 'var(--primary)' : (name.toLowerCase().startsWith('testag') ? '#0066FF' : 'inherit');
        const mid = m.id || Math.random().toString(36).slice(2);
        
        let rawContent = m.content || "";
        let showBoxFound = false;
        let showData = null;
        const showboxMatch = rawContent.match(/<SHOWBOX(?::(\d+))?>([\s\S]*?)<\/SHOWBOX>/);
        
        if (showboxMatch) {
           showBoxFound = true;
           rawContent = rawContent.replace(showboxMatch[0], '').trim();
           if (!window._processedShowboxes.has(mid)) {
               window._processedShowboxes.add(mid);
               try { 
                 showData = JSON.parse(showboxMatch[2]); 
                 if (showboxMatch[1] !== undefined) {
                     showData._targetIdx = parseInt(showboxMatch[1], 10) - 1; // 1-based to 0-based
                 }
               } 
               catch(e) { console.error("SHOWBOX parse error", e); }
           }
        }
        
        let safe = esc(rawContent);
        if (showBoxFound) {
           const targetText = (showData && showData._targetIdx !== undefined) ? ` Button ${showData._targetIdx + 1}` : '';
           safe += `<div style="color:var(--cyan);font-size:0.8em;margin-top:8px;">[ 🎬 Showbox Triggered${targetText} ]</div>`;
        }
        
        if (showData && Array.isArray(showData) && showData.length > 0) {
           setTimeout(() => {
               let targetIdx = window.activeShowboxIndex >= 0 ? window.activeShowboxIndex : 0;
               if (showData._targetIdx !== undefined && showData._targetIdx >= 0 && showData._targetIdx < window.showboxes.length) {
                   targetIdx = showData._targetIdx;
               }
               window.showboxes[targetIdx] = showData;
               if (window.closeShowbox) window.closeShowbox();
               setTimeout(() => { if (window.triggerShowbox) window.triggerShowbox(targetIdx); }, 100);
           }, 300);
        }

        safe = safe.replace(/\[SOUL:\s*([\s\S]*?)\]/g, '<div style="font-size:0.6rem; color:var(--bg-surface); opacity:0.5; margin-top:4px;">[SOUL: $1]</div>');
        safe = safe.replace(/\n/g, '<br>');
        return `<div class="chat-msg ${isUser ? 'user' : 'agent'}" style="border-left-color:${c};">
      <div class="chat-meta"><span class="agent-name" style="color:${nameColor}">${esc(name)}</span><span><button class="copy-btn" onclick="copyMsg('${mid}')" title="Copy">📋</button><button class="copy-btn del-btn" onclick="deleteChatMsg('${mid}')" title="Delete">🗑</button>${time}</span></div>
      <div class="mem-content" id="msg-${mid}">${safe}</div></div>`;
      }).join('');

      if (wasAtBottom || !window._chatInitialized) {
        el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
        window._chatInitialized = true;
      } else {
        el.scrollTop = st;
      }

      // TTS
      if (!window._spokenIds) window._spokenIds = new Set();
      sorted.filter(m => m.metadata?.sender !== 'user' && !window._spokenIds.has(m.id)).forEach(m => {
        window._spokenIds.add(m.id);
        speak(`${m.metadata?.sender || 'System'} sagt: ${m.content}`);
      });
    }

    function copyMsg(id) {
      const el = document.getElementById('msg-' + id);
      if (!el) return;
      navigator.clipboard.writeText(el.innerText).then(() => {
        const btn = el.parentElement.querySelector('.copy-btn');
        if (btn) { btn.textContent = '✅'; setTimeout(() => btn.textContent = '📋', 1200); }
      });
    }

    // ── TTS Queue ──
    const _ttsQ = []; let _ttsBusy = false;
    function stopTTS() {
      speechSynthesis.cancel();
      _ttsQ.length = 0;
      _ttsBusy = false;
      const btn = document.getElementById('stop-tts-btn');
      if (btn) btn.style.display = 'none';
    }

    async function deleteChatMsg(id) {
      await api('DELETE', `/memory/${id}`);
      stopTTS();
      window._lastChatData = null; // force re-render
      refreshChat();
    }

    async function speak(text, agentId = '') {
      if (!document.getElementById('tts-enabled')?.checked) return;
      _ttsQ.push({ text, agentId });
      if (_ttsBusy) return;
      _ttsBusy = true;
      const stopBtn = document.getElementById('stop-tts-btn');
      if (stopBtn) stopBtn.style.display = 'block';

      while (_ttsQ.length) {
        const { text: t, agentId: a } = _ttsQ.shift();
        speechSynthesis.cancel();
        try {
          const r = await fetch(`${API}/audio/tts`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: t, agent_id: a }) });
          if (r.ok && r.headers.get('content-type')?.includes('audio')) {
            const audio = new Audio(URL.createObjectURL(await r.blob()));
            await new Promise(ok => { audio.onended = ok; audio.onerror = ok; audio.play(); }); continue;
          }
        } catch { }
        const u = new SpeechSynthesisUtterance(t); u.lang = 'de-DE'; u.rate = 1.0;
        await new Promise(ok => { u.onend = ok; u.onerror = ok; speechSynthesis.speak(u); });
      }
      _ttsBusy = false;
      if (stopBtn) stopBtn.style.display = 'none';
    }

    // ── STT ──
    let recognition;
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SR();
      recognition.continuous = true; recognition.lang = 'de-DE';
      recognition.onresult = (e) => {
        let text = '';
        for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript + ' ';
        const inp = document.getElementById('chat-input');
        if (inp) inp.value = text.trim();
      };
      recognition.onerror = () => { const b = document.getElementById('mic-btn'); if (b) { b.classList.remove('active'); b.innerText = 'Rec'; } };
      recognition.onend = () => { const b = document.getElementById('mic-btn'); if (b) { b.classList.remove('active'); b.innerText = 'Rec'; } };
    }
    function toggleSTT() {
      const btn = document.getElementById('mic-btn');
      if (!recognition) { toast('Browser does not support voice input', 'error'); return; }
      if (btn.classList.contains('active')) {
        recognition.stop();
        btn.classList.remove('active');
        btn.innerText = 'Rec';
      } else {
        recognition.start();
        btn.classList.add('active');
        btn.innerText = 'Stop';
      }
    }

    // ── Status Lamps ──
    let _lastInternals = '';
    function updateLamps(hubAgents) {
      const el = document.getElementById('status-lamps');
      if (!hubAgents) return;

      // Alle 8 System-Agenten als Lämpchen anzeigen
      const sysNames = ['watchdogag', 'skillsag', 'backupag', 'cronjobag', 'soulag', 'summarizerag', 'generalag', 'securityag'];
      const hiddenSys = [
        { name: 'WatchdogAG', status: 'online' },
        { name: 'SkillsAG', status: 'online' },
        { name: 'BackupAG', status: 'online' },
        { name: 'CronjobAG', status: 'online' },
        { name: 'SoulAG', status: 'online' },
        { name: 'SecurityAG', status: 'online' }
      ];

      // Kombiniere die DB-System-Agenten und die unsichtbaren System-Agenten
      let displayAgents = [...hiddenSys.filter(h => !hubAgents.some(a => a.name === h.name)), ...hubAgents];
      // Filtere strikt nur die System-Agenten (keine Work-Agenten wie Lian, Elara, Kira!)
      displayAgents = displayAgents.filter(a => sysNames.includes((a.name || '').toLowerCase()));

      const names = displayAgents.map(a => a.name).join(',');

      if (_lastInternals !== names) {
        el.innerHTML = displayAgents.map((a, i) => {
          const dur = (2.5 + Math.random() * 2.0).toFixed(2);   // 2.5s – 4.5s
          const dly = (-(Math.random() * 6.0)).toFixed(2);       // -0 … -6s offset
          const col = agentColor(a.name);
          return `<div class="lamp" data-ag="${a.name}" title="${a.name}" style="color:${col};background:${col};--dur:${dur}s;--delay:${dly}s"></div>`;
        }).join('');
        _lastInternals = names;
      }

      el.querySelectorAll('.lamp').forEach(l => {
        const key = l.dataset.ag;
        const agent = displayAgents.find(a => a.name === key);
        const st = agent?.status || 'offline';
        l.className = st === 'busy' ? 'lamp busy' : st === 'online' ? 'lamp on' : 'lamp';
      });
    }

    // ── Coffee & UFO Reminders ──
    function checkTimers() {
      const now = Date.now();

      // Coffee & UFO disabled per user request

      // Ghost (6 hours and 6 minutes)
      const lastGhost = localStorage.getItem('last_ghost_time');
      if (!lastGhost) {
        localStorage.setItem('last_ghost_time', now);
      } else if (now - parseInt(lastGhost) > ((6 * 60 * 60) + (6 * 60)) * 1000) {
        localStorage.setItem('last_ghost_time', now);
        const ghostOverlay = document.getElementById('ghost-overlay');
        if (ghostOverlay) {
          // Clone and re-append to restart the CSS animation
          const newGhost = ghostOverlay.cloneNode(true);
          ghostOverlay.parentNode.replaceChild(newGhost, ghostOverlay);
          newGhost.style.display = 'flex';
          setTimeout(() => { newGhost.style.display = 'none'; }, 120000); // 120s animation
        }
      }
    }
    setInterval(checkTimers, 60000); // Check every minute
    window.coffeeTimer = null;
    window.coffeeFleeCount = 0;
    window.showCoffeeBreak = () => {
      const el = document.getElementById('coffee-overlay');
      el.style.transition = 'none';
      el.style.bottom = '30px';
      el.style.right = '30px';
      el.style.top = 'auto';
      el.style.left = 'auto';
      el.style.display = 'block';
      window.coffeeFleeCount = 0;
      speak("Take it easy. Drink coffee.");
      clearTimeout(window.coffeeTimer);
      window.coffeeTimer = setTimeout(() => { el.style.display = 'none'; }, 20000);
    };

    window.fleeCoffee = () => {
      window.coffeeFleeCount++;
      const el = document.getElementById('coffee-overlay');
      if (window.coffeeFleeCount >= 3) {
        el.style.display = 'none';
        clearTimeout(window.coffeeTimer);
        return;
      }
      el.style.transition = 'all 0.15s cubic-bezier(0.25, 1, 0.5, 1)';
      const maxX = Math.max(10, window.innerWidth - el.offsetWidth - 20);
      const maxY = Math.max(10, window.innerHeight - el.offsetHeight - 20);
      const rx = Math.max(10, Math.floor(Math.random() * maxX));
      const ry = Math.max(10, Math.floor(Math.random() * maxY));
      el.style.bottom = 'auto';
      el.style.right = 'auto';
      el.style.left = rx + 'px';
      el.style.top = ry + 'px';
    };
    window.showUfoAttack = () => {
      const o = document.getElementById('ufo-overlay');
      o.style.display = 'flex';
      setTimeout(() => { o.style.display = 'none'; }, 600000);
    };
    window.showGhost = () => {
      const o = document.getElementById('ghost-overlay');
      const newGhost = o.cloneNode(true);
      o.parentNode.replaceChild(newGhost, o);
      newGhost.style.display = 'flex';
      setTimeout(() => { newGhost.style.display = 'none'; }, 120000);
    };

    // ── Init ──
    (async () => {
      try {
        checkTimers();
        await discoverPort();
        if (!API) {
          document.getElementById('content').innerHTML = '<div class="empty" style="padding:80px 20px"><h2 style="color:var(--error);margin-bottom:10px">Hub unreachable (No API)</h2><p>Server nicht gefunden. Öffne http://127.0.0.1:3002/ im Browser.</p></div>';
          return;
        }
        await loadAgents();
        updateLamps(agents);
        showWarRoom();
        setInterval(async () => {

        const res = await api('GET', '/agents');
        agents = Array.isArray(res) ? res : (res?.agents || []);
        renderAgentList(document.getElementById('agent-search').value);
        updateStats();
        updateLamps(agents);
      }, 15000);
      setInterval(refreshChat, 5000);
      } catch (err) {
        document.getElementById('content').innerHTML = `<div class="empty" style="padding:80px 20px"><h2 style="color:red">UI Error</h2><p>${err.message}</p></div>`;
      }

      // Layer Animation
      let currentLayer = 0;
      const totalLayers = 10;
      window.showboxActive = false;
      let showboxInterval = null;
      let showboxTimeout = null;
      window.activeShowboxIndex = -1;
      window.showboxSpeed = window.showboxSpeed || 3000;

      // Die Themen werden jetzt über die externe Datei "themes.js" geladen.

      window.triggerShowbox = (showboxIndex) => {
        if (window.showboxActive && window.activeShowboxIndex === showboxIndex) {
          window.closeShowbox();
          return;
        }
        if(showboxInterval) clearInterval(showboxInterval);
        if(showboxTimeout) clearTimeout(showboxTimeout);
        
        window.activeShowboxIndex = showboxIndex;
        if (!window.showboxes) window.showboxes = [["<span style='color:red;'>Keine themes.js gefunden!</span>"]];
        const showboxSteps = window.showboxes[showboxIndex] || window.showboxes[0];
        
        window.showboxActive = true;
        let step = 0;
        
        for(let i=0; i<totalLayers; i++) {
          const l = document.getElementById(`layer-${i}`);
          if(l) l.classList.remove('active');
        }
        
        const tutLayer = document.getElementById('layer-showbox');
        const tutText = document.getElementById('showbox-text');
        
        const updateText = () => {
          tutText.innerHTML = showboxSteps[step];
          let size = 80; // Start large
          tutText.style.fontSize = size + 'px';
          // Auto-scale to fit perfectly within the parent (accounting for 3px padding on edges)
          while((tutText.scrollHeight > tutLayer.clientHeight - 6 || tutText.scrollWidth > tutLayer.clientWidth - 6) && size > 8) {
            size--;
            tutText.style.fontSize = size + 'px';
          }
          tutText.style.opacity = 1;
        };

        tutText.style.opacity = 0;
        showboxTimeout = setTimeout(updateText, 100);
        tutLayer.classList.add('active');

        showboxInterval = setInterval(() => {
          step++;
          if (step >= showboxSteps.length) {
            window.closeShowbox();
            return;
          }
          tutText.style.opacity = 0;
          showboxTimeout = setTimeout(updateText, 300);
        }, window.showboxSpeed); // Zeigt jedes Bild/Info für X Sekunden
      };

      window.closeShowbox = () => {
        if(showboxInterval) {
          clearInterval(showboxInterval);
          showboxInterval = null;
        }
        if(showboxTimeout) {
          clearTimeout(showboxTimeout);
          showboxTimeout = null;
        }
        window.activeShowboxIndex = -1;
        window.showboxActive = false;
        const tutLayer = document.getElementById('layer-showbox');
        if(tutLayer) tutLayer.classList.remove('active');
        const curr = document.getElementById(`layer-${currentLayer}`);
        if(curr) curr.classList.add('active');
      };

      setInterval(() => {
        if (window.showboxActive) return;
        const oldL = document.getElementById(`layer-${currentLayer}`);
        if(oldL) oldL.classList.remove('active');
        currentLayer = (currentLayer + 1) % totalLayers;
        const newL = document.getElementById(`layer-${currentLayer}`);
        if(newL) newL.classList.add('active');
      }, 5000);
    })();

    // ── LLM Config ──
    async function showLLMConfig() {
      selectedId = null;
      document.getElementById('content').innerHTML = `
        <div class="panel" id="llm-panel">
          <h2>LLM Konfiguration</h2>
          <div style="display:flex; gap: 20px; flex-wrap: wrap;">
            <div style="flex:1; min-width: 250px; background:var(--bg-card); padding:15px; border-radius:var(--radius); border:1px solid rgba(255,255,255,0.1);">
              <h3 style="margin-bottom:5px;">API Keys</h3>
              <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:5px;">Ein Key pro Zeile</p>
              <textarea id="llm-keys-input" rows="3" style="width:100%; margin-bottom:10px; background:var(--bg); border:1px solid rgba(255,255,255,0.2); color:white; padding:8px; border-radius:4px; font-size:0.85rem;" placeholder="sk-..."></textarea>
              <button class="btn-primary" onclick="saveAndTestKeys()" style="width:100%; font-size:0.85rem; padding:6px;">Speichern & Testen</button>
              <div id="llm-keys-status" style="margin-top:10px; font-size:0.85rem; max-height:100px; overflow-y:auto;"></div>
            </div>
            <div style="flex:2; min-width: 400px; background:var(--bg-card); padding:20px; border-radius:var(--radius); border:1px solid rgba(255,255,255,0.1);">
              <h3>Agenten Zuweisung</h3>
              <div id="llm-agents-list" style="margin-bottom:20px; max-height:400px; overflow-y:auto; padding-right:10px;">Lade Agenten...</div>
              <div style="display:flex; gap:10px;">
                <button class="btn-primary" onclick="saveAgentLLMs()">Agenten-Settings Speichern</button>
                <button class="btn-primary" onclick="api('POST', '/restart')" style="background:#cc3333;">Server Neustart</button>
              </div>
            </div>
          </div>
        </div>
      `;
      loadLLMConfig();
    }

    let globalKeys = [];
    async function loadLLMConfig() {
      const keysRes = await api('GET', '/llm/keys');
      if (keysRes) {
        globalKeys = Object.keys(keysRes).length > 0 ? Object.values(keysRes) : [];
        if (globalKeys.length > 0 && globalKeys[0].key) {
           document.getElementById('llm-keys-input').value = globalKeys.map(k => k.key).join('\n');
           renderKeyStatus(globalKeys);
        }
      }

      const agentsRes = await api('GET', '/agents');
      const llmAgentsRes = await api('GET', '/llm/agents');
      
      let html = '';
      const providers = ['deepseek', 'openrouter', 'lokal'];
      const models = {
        'deepseek': ['deepseek-chat', 'deepseek-reasoner'],
        'openrouter': ['deepseek/deepseek-v4-flash:free', 'openai/gpt-oss-120b:free', 'minimax/minimax-m2.5:free', 'nvidia/nemotron-nano-9b-v2:free', 'openai/gpt-oss-20b:free', 'anthropic/claude-3-opus', 'anthropic/claude-3.5-sonnet'],
        'lokal': ['llama3', 'mistral', 'qwen2']
      };

      if (agentsRes && Array.isArray(agentsRes)) {
        agentsRes.forEach(a => {
           let safeAgentsRes = llmAgentsRes || {};
           let conf = safeAgentsRes[(a.name || '').toLowerCase()] || {};
           let pSel = conf.provider || 'deepseek';
           let mSel = conf.model || 'deepseek-chat';
           
           html += `<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px; padding:8px; background:rgba(255,255,255,0.05); border-radius:8px; font-size:0.9rem;">
             <div style="width:120px; font-weight:bold; overflow:hidden; text-overflow:ellipsis;">${a.name}</div>
             <select id="prov-${a.name}" onchange="updateModels('${a.name}')" style="background:var(--bg); color:white; border:1px solid rgba(255,255,255,0.2); padding:4px; border-radius:4px; width:120px;">
               ${providers.map(p => `<option value="${p}" ${p === pSel ? 'selected':''}>${p}</option>`).join('')}
             </select>
             <select id="mod-${a.name}" style="background:var(--bg); color:white; border:1px solid rgba(255,255,255,0.2); padding:4px; border-radius:4px; flex:1; min-width:150px;">
               ${(models[pSel]||[]).map(m => `<option value="${m}" ${m === mSel ? 'selected':''}>${m}</option>`).join('')}
             </select>
             <button class="btn-primary" onclick="testAgentLLM('${a.name}')" style="padding:4px 10px; font-size:0.8rem;">Test</button>
             <div id="lamp-${a.name}" style="width:12px; height:12px; border-radius:50%; background:gray; box-shadow:0 0 5px rgba(0,0,0,0.5);"></div>
           </div>`;
        });
      }
      document.getElementById('llm-agents-list').innerHTML = html;
      window.llmModelsMap = models;
    }

    window.updateModels = function(aName) {
      const p = document.getElementById(`prov-${aName}`).value;
      const modSelect = document.getElementById(`mod-${aName}`);
      const mods = window.llmModelsMap[p] || [];
      modSelect.innerHTML = mods.map(m => `<option value="${m}">${m}</option>`).join('');
    };

    async function saveAndTestKeys() {
      const input = document.getElementById('llm-keys-input').value;
      const rawKeys = input.split('\n').map(k => k.trim()).filter(k => k);
      
      document.getElementById('llm-keys-status').innerHTML = 'Teste Keys...';
      
      let testedKeys = [];
      let nextId = Date.now();
      
      for(let k of rawKeys) {
        let prov = 'deepseek';
        if (k.startsWith('sk-or-')) prov = 'openrouter';
        
        let res = await api('POST', '/llm/test', { key: k, provider: prov });
        testedKeys.push({
          id: 'k_' + (nextId++),
          key: k,
          provider: prov,
          valid: res && res.valid,
          info: res ? res.info : 'Error'
        });
      }
      
      let toSave = {};
      testedKeys.forEach(k => toSave[k.id] = k);
      await api('POST', '/llm/keys', toSave);
      
      globalKeys = testedKeys;
      renderKeyStatus(testedKeys);
      loadLLMConfig();
    }

    function renderKeyStatus(keys) {
      let h = '';
      keys.forEach((k, idx) => {
        let c = k.valid ? 'var(--green)' : '#ff3333';
        h += `<div style="color:${c}; margin-bottom:5px;">${k.valid ? '✅' : '❌'} Key ${idx+1} (${k.provider}) ${k.info !== 'OK' ? '('+k.info.substring(0,20)+')' : ''}</div>`;
      });
      document.getElementById('llm-keys-status').innerHTML = h;
    }

    async function saveAgentLLMs() {
      const agentsRes = await api('GET', '/agents');
      let config = {};
      if (agentsRes && Array.isArray(agentsRes)) {
        agentsRes.forEach(a => {
          let p = document.getElementById(`prov-${a.name}`);
          let m = document.getElementById(`mod-${a.name}`);
          if(p && m) {
            config[a.name.toLowerCase()] = {
              provider: p.value,
              model: m.value
            };
          }
        });
      }
      await api('POST', '/llm/agents', config);
      alert('Agenten-Settings gespeichert!');
    }

    async function testAgentLLM(aName) {
      const p = document.getElementById(`prov-${aName}`).value;
      const m = document.getElementById(`mod-${aName}`).value;
      const lamp = document.getElementById(`lamp-${aName}`);
      
      lamp.style.background = 'yellow';
      lamp.style.boxShadow = '0 0 8px yellow';
      
      let res = await api('POST', '/llm/test_agent', { agent: aName, provider: p, model: m });
      if (res && res.valid) {
        lamp.style.background = '#39ff14';
        lamp.style.boxShadow = '0 0 10px #39ff14';
      } else {
        lamp.style.background = '#ff3333';
        lamp.style.boxShadow = '0 0 10px #ff3333';
        if (res && res.info) alert(`Fehler bei ${aName}: ` + res.info);
      }
    }
