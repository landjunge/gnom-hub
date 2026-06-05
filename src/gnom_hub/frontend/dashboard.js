/* ═══════════════════════════════════════════
   GNOM-HUB — Bento Dashboard & LLM Config
   ═══════════════════════════════════════════ */

var dashboardInterval = null;
var globalKeys = [];
window.showKeysFull = false;

function stopDashboardPolling() {
  if (dashboardInterval) {
    clearInterval(dashboardInterval);
    dashboardInterval = null;
  }
}

function runDashboardPolling() {
  if (!document.getElementById('dashboard-panel')) {
    stopDashboardPolling();
    return;
  }
  loadDashboardData();
}

async function showDashboard() {
  if (typeof trackView === 'function') trackView('dashboard');
  selectedId = null;
  document.getElementById('content').innerHTML = `
    <div class="panel" id="dashboard-panel">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px;">
        <h2 style="margin:0; font-size:0.95rem; font-weight:600; border:none; letter-spacing:0.5px;">Agent Health Dashboard</h2>
      </div>
      <div id="swarm-status-banner" style="display:none; margin-top:15px; padding:15px; background:rgba(0,229,255,0.04); border:1px solid rgba(0,229,255,0.2); border-radius:var(--radius); box-shadow:0 0 20px rgba(0,229,255,0.05); backdrop-filter:blur(10px);">
        <div style="font-weight:bold; color:var(--accent); font-size:1.05rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px; display:flex; align-items:center; gap:8px;">
          <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:var(--accent); animation: pulse-glow 1.5s infinite;"></span>
          Swarm Intelligence & Team Workflows
        </div>
        <div id="swarm-workflow-text" style="font-size:0.95rem; color:#fff; font-weight:500; margin-bottom:6px;">None</div>
        <div id="swarm-comms-text" style="font-size:0.85rem; color:var(--text-dim); line-height:1.4;"></div>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-top: 15px;" id="dashboard-grid">
        <div class="empty">Metriken werden geladen...</div>
      </div>
      <h2 style="margin-top: 24px; display:flex; align-items:center; gap:8px; font-size:0.95rem; font-weight:600;">
        <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#a855f7;"></span>
        Agent Evolution & Self-Improvement Log
      </h2>
      <div id="evolution-log-section" style="margin-top: 10px; display: flex; flex-direction: column; gap: 10px; max-height: 250px; overflow-y: auto; padding-right: 5px;">
        <div class="empty" style="color:var(--text-dim); font-style:italic;">Keine Evolutions-Logs vorhanden.</div>
      </div>
      <h2 style="margin-top: 24px; display:flex; align-items:center; gap:8px; font-size:0.95rem; font-weight:600;">
        <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#10b981;"></span>
        Submit Swarm Job Feedback
      </h2>
      <div id="feedback-section" style="margin-top: 10px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255,255,255,0.05); padding: 12px; border-radius: var(--radius); display: flex; flex-direction: column; gap: 8px;">
        <div style="display:flex; gap:8px;">
          <button class="btn-primary" onclick="submitFeedback('up')" style="flex:1; background:rgba(16, 185, 129, 0.1); border:1px solid #10b981; color:rgba(255,255,255,0.85); padding:6px 0; border-radius:var(--radius-sm); font-size:0.85rem; cursor:pointer; transition:var(--transition); font-weight:500;">👍 Daumen hoch</button>
          <button class="btn-primary" onclick="submitFeedback('down')" style="flex:1; background:rgba(239, 68, 68, 0.1); border:1px solid #ef4444; color:rgba(255,255,255,0.85); padding:6px 0; border-radius:var(--radius-sm); font-size:0.85rem; cursor:pointer; transition:var(--transition); font-weight:500;">👎 Daumen runter</button>
        </div>
        <div style="display:flex; gap:10px; align-items:stretch;">
          <input type="text" id="feedback-comment" placeholder="Kommentar hinzufügen..." style="flex:1; background:var(--bg-input); border:1px solid var(--glass-border); border-radius:var(--radius-sm); color:var(--text); padding:8px 12px; font-size:0.9rem; outline:none;">
          <button class="btn-primary" onclick="submitFeedbackComment()" style="padding:0 20px;">Senden</button>
        </div>
        <div id="feedback-status" style="font-size:0.8rem; color:var(--green); display:none;">Feedback gesendet!</div>
      </div>
    </div>
  `;
  await loadDashboardData();
  stopDashboardPolling();
  dashboardInterval = setInterval(runDashboardPolling, 3000);
}

window.submitFeedback = async function(vote) {
  const comment = document.getElementById('feedback-comment')?.value || '';
  const res = await api('POST', '/feedback', { vote, comment });
  if (res && res.status === 'ok') {
    const s = document.getElementById('feedback-status');
    if (s) { s.style.display = 'block'; s.textContent = 'Feedback gesendet!'; setTimeout(() => s.style.display = 'none', 3000); }
  }
};

window.submitFeedbackComment = async function() {
  const el = document.getElementById('feedback-comment');
  const comment = el ? el.value : '';
  if (!comment.trim()) return;
  const res = await api('POST', '/feedback', { vote: 'comment', comment });
  if (res && res.status === 'ok') {
    if (el) el.value = '';
    const s = document.getElementById('feedback-status');
    if (s) { s.style.display = 'block'; s.textContent = 'Kommentar gesendet!'; setTimeout(() => s.style.display = 'none', 3000); }
  }
};

async function loadDashboardData() {
  const metrics = await api('GET', '/metrics');
  const grid = document.getElementById('dashboard-grid');
  if (!grid) return;
  
  const banner = document.getElementById('swarm-status-banner');
  const activeWorkers = [];
  if (metrics) {
    const wf = metrics._active_workflow;
    const comms = metrics._swarm_comms || [];
    if (wf) {
      const matches = wf.match(/\b\w+AG\b/gi);
      if (matches) matches.forEach(m => activeWorkers.push(m.toLowerCase()));
    }
    comms.forEach(c => {
      if (c.from) activeWorkers.push(c.from.toLowerCase());
      if (c.to) activeWorkers.push(c.to.toLowerCase());
    });
    if (banner) {
      if (wf || comms.length > 0) {
        banner.style.display = 'block';
        const wfText = document.getElementById('swarm-workflow-text');
        const commsText = document.getElementById('swarm-comms-text');
        if (wfText) wfText.textContent = wf || 'Team-Workflow: Diskussions-Schwarm aktiv';
        if (commsText) {
          commsText.innerHTML = comms.map(c => `
            <div style="display:flex; align-items:center; gap:8px; margin-top:4px; font-size: 0.85rem;">
              <span style="color:var(--accent); font-weight:600;">${escapeHtml(c.from)}</span>
              <span style="color:rgba(255,255,255,0.6);">💬 fragt/antwortet</span>
              <span style="color:var(--accent); font-weight:600;">${escapeHtml(c.to)}</span>
            </div>
          `).join('') || '<div style="color:rgba(255,255,255,0.4)">Interne Diskussion läuft...</div>';
        }
      } else {
        banner.style.display = 'none';
      }
    }
  }

  if (!metrics || Object.keys(metrics).length === 0) {
    grid.innerHTML = '<div class="empty">Keine Metriken verfügbar.</div>';
    return;
  }
  const names = ['soulag', 'generalag', 'watchdogag', 'securityag', 'coderag', 'researcherag', 'writerag', 'editorag'];
  grid.innerHTML = names.map(n => {
    const m = metrics[n] || { total: 0, failed: 0, avg_time_ms: 0, last_seen: 0, success_rate: 1.0, status: 'offline' };
    const isActive = activeWorkers.includes(n);
    let color = '#ef4444';
    let statusLabel = 'OFFLINE / DEAD';
    if (m.status === 'online') {
      if (m.success_rate >= 0.8) {
        color = '#10b981';
        statusLabel = 'ALIVE (ONLINE)';
      } else {
        color = '#f59e0b';
        statusLabel = 'WARNING (HIGH ERRORS)';
      }
    } else if (m.total > 0 && ((Date.now() / 1000) - m.last_seen < 120)) {
      color = '#f59e0b';
      statusLabel = 'WARNING (HEARTBEAT)';
    }
    const successPercent = (m.success_rate * 100).toFixed(0);
    const lastSeenStr = m.last_seen > 0 ? new Date(m.last_seen * 1000).toLocaleTimeString() : 'nie';
    const agentColorHex = agentColor(n);
    return `
      <div class="agent-health-card" style="background: rgba(255, 255, 255, 0.02); backdrop-filter: blur(8px); border: ${isActive ? '1px solid var(--accent)' : '1px solid rgba(255, 255, 255, 0.05)'}; border-radius: 12px; padding: 15px; display: flex; flex-direction: column; gap: 10px; border-top: 3px solid ${agentColorHex}; transition: all 0.3s ease; ${isActive ? 'box-shadow: 0 4px 12px rgba(0, 229, 255, 0.05);' : ''}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h3 style="margin: 0; font-size: 1.05rem; color: #fff; text-transform: capitalize; display: flex; align-items: center; gap: 6px; font-weight: 600;">
            ${n.replace('ag', 'AG')}
            ${isActive ? `<span style="font-size:0.65rem; background:rgba(0,229,255,0.15); color:var(--accent); border:1px solid rgba(0,229,255,0.3); border-radius:4px; padding:1px 4px; font-weight:bold;">TEAM</span>` : ''}
          </h3>
          <div style="display: flex; align-items: center; gap: 4px; font-size: 0.72rem; font-weight: 500; color: ${color};">
            <span style="width: 8px; height: 8px; border-radius: 50%; background: ${color}; display: inline-block;"></span>
            <span>${statusLabel}</span>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; color: rgba(255, 255, 255, 0.7);">
          <div>Requests: <strong style="color: #fff;">${m.total}</strong></div>
          <div>Errors: <strong style="color: #fff;">${m.failed}</strong></div>
          <div>Avg. Latenz: <strong style="color: #fff;">${m.avg_time_ms.toFixed(0)} ms</strong></div>
          <div>Erfolg: <strong style="color: #fff;">${successPercent}%</strong></div>
        </div>
        <div style="font-size: 0.75rem; color: rgba(255,255,255,0.4); border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px; margin-top: 5px;">
          Letzter Kontakt: ${lastSeenStr}
        </div>
      </div>
    `;
  }).join('');

  const evLog = document.getElementById('evolution-log-section');
  if (evLog && metrics && metrics._evolution_log) {
    if (metrics._evolution_log.length === 0) {
      evLog.innerHTML = `<div class="empty" style="color:var(--text-dim); font-style:italic;">Keine Evolutions-Logs vorhanden.</div>`;
    } else {
      evLog.innerHTML = metrics._evolution_log.map(el => {
        const agentName = el.key.split('_')[1] || 'Agent';
        const timestamp = new Date(el.timestamp).toLocaleString();
        return `
          <div class="mem-item" style="border-left: 3px solid #a855f7; background: rgba(168, 85, 247, 0.03); padding: 12px 16px; border-radius: 4px 8px 8px 4px; display: flex; flex-direction: column; gap: 4px; transition: var(--transition);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <strong style="color: #c084fc; text-transform: uppercase; font-size: 0.85rem;">Evolution: ${agentName}</strong>
              <span style="font-size: 0.75rem; color: var(--text-dim);">${timestamp}</span>
            </div>
            <div style="font-size: 0.9rem; color: #fff; line-height: 1.4;">${escapeHtml(el.value)}</div>
          </div>
        `;
      }).join('');
    }
  }
}

async function showLLMConfig() {
  if (typeof trackView === 'function') trackView('llm');
  selectedId = null;
  document.getElementById('content').innerHTML = `
    <div class="panel" id="llm-panel" style="height:calc(100vh - 91px); box-sizing:border-box; display:flex; flex-direction:column; padding:15px 20px; background:rgba(10, 15, 30, 0.4); border:1px solid var(--glass-border); margin-bottom:0; overflow:hidden;">
      
      <!-- Main LLM Container -->
      <div class="llm-container" id="settings-tab-global-content" style="flex:1; min-height:0; display:grid; grid-template-columns:1fr 1.5fr; gap:20px; overflow:hidden;">
        <!-- Left Column: Settings Modules -->
        <div style="display:flex; flex-direction:column; gap:15px; overflow-y:auto; padding-right:5px; height:100%; scrollbar-width:thin;">
          <!-- Module 1: API Keys -->
          <div class="llm-card" style="flex-shrink:0;">
            <div class="llm-card-header">
              <h3 class="llm-card-title">🔑 API Keys & Authentication</h3>
              <label style="display:flex; align-items:center; gap:5px; font-size:0.75rem; color:var(--text-dim); cursor:pointer;" data-help="Zeigt oder verbirgt die API-Schlüssel im Eingabefeld." data-help-title="Schlüssel anzeigen">
                <input type="checkbox" id="toggle-show-keys" onchange="toggleKeysVisibility(this.checked)" class="llm-toggle-input">
                <span>Anzeigen</span>
              </label>
            </div>
            <span class="llm-card-description">Füge deine API-Schlüssel ein (ein Schlüssel pro Zeile, z.B. <code>OPENAI_API_KEY=sk-...</code>).</span>
            <textarea id="llm-keys-input" rows="2" class="llm-input-area" placeholder="Einfügen per Cmd+V oder manuell eingeben..." data-help="Trage hier deine Provider-Schlüssel ein (z.B. OPENROUTER_API_KEY=sk-... oder OLLAMA_BASE_URL=...). Ein Eintrag pro Zeile." data-help-title="API-Keys Textfeld"></textarea>
            <div class="llm-btn-group">
              <button class="btn-primary" id="save-keys-btn" onclick="saveAndTestKeys()" style="flex:1;" data-help="Speichert deine eingetragenen Schlüssel und testet direkt die Verbindung zu den Providern." data-help-title="Schlüssel verifizieren">Verifizieren & Speichern</button>
            </div>
            <div id="llm-keys-status" style="font-size:0.78rem; max-height:85px; overflow-y:auto; display:flex; flex-direction:column; gap:4px; padding:6px; border-radius:8px; background:rgba(0,0,0,0.18); scrollbar-width:thin;"></div>
          </div>
          
          <!-- Module 3: Global Options -->
          <div class="llm-card" style="flex-shrink:0;">
            <div class="llm-card-header">
              <h3 class="llm-card-title">⚙️ Globale Optionen</h3>
            </div>
            <div style="display:flex; flex-direction:column; gap:10px;">
              <div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">
                <span style="font-size:0.8rem; color:var(--text-dim);">Systemsprache</span>
                <div style="display:flex; gap:6px; width:120px;">
                  <button class="btn-primary" id="lang-btn-de" onclick="setSystemLanguage('de')" style="flex:1;" data-help="Stellt die Sprache des Hubs und der Agenten-Prompts auf Deutsch." data-help-title="Sprache: DE">DE</button>
                  <button class="btn-primary" id="lang-btn-en" onclick="setSystemLanguage('en')" style="flex:1;" data-help="Stellt die Sprache des Hubs und der Agenten-Prompts auf Englisch." data-help-title="Sprache: EN">EN</button>
                </div>
              </div>
              <div class="llm-toggle-row" data-help="Gibt erstellte Webseiten direkt per FTP auf deinem Webspace live frei." data-help-title="Auto-Deploy">
                <label for="auto-deploy-checkbox" class="llm-toggle-label">
                  <span>🌐 Auto-Deploy Webseiten</span>
                </label>
                <input type="checkbox" id="auto-deploy-checkbox" onchange="toggleFtpAutoDeploy(this.checked)" class="llm-toggle-input">
              </div>
              <div class="llm-toggle-row" data-help="Führt Playwright-Webrecherche-Befehle in einer isolierten Docker-Sandbox aus." data-help-title="Docker-Playwright">
                <label for="browser-docker-checkbox" class="llm-toggle-label">
                  <span>🐳 Browser in Docker ausführen</span>
                </label>
                <input type="checkbox" id="browser-docker-checkbox" onchange="toggleBrowserDocker(this.checked)" class="llm-toggle-input">
              </div>
            </div>
          </div>
          
          <!-- Module 4: System Information -->
          <div class="llm-card" style="flex-shrink:0;">
            <div class="llm-card-header">
              <h3 class="llm-card-title">📊 Systemumgebung</h3>
            </div>
            <div id="system-info-panel" class="llm-system-info" data-help="Echtzeit-Metriken deiner lokalen CPU-, RAM- und Thread-Auslastung." data-help-title="Systemumgebung">
              Lade System-Informationen...
            </div>
          </div>
        </div>
        
        <!-- Right Column: Agent LLM Routing -->
        <div class="llm-card" style="height:100%; display:flex; flex-direction:column; overflow:hidden;">
          <div class="llm-card-header" style="flex-shrink:0;">
            <h3 class="llm-card-title">⚡ Agenten-Routing & LLM-Zuweisung</h3>
            <div style="display:flex; gap:6px; align-items:center;">
              <button class="btn-primary" onclick="autoRouteAllAgents()" data-help="Verteilt alle Agenten basierend auf verfügbaren APIs automatisch und kosteneffizient auf die besten LLM-Modelle." data-help-title="Auto-Route ausführen">⚡ Auto-Route</button>
              <button class="btn-primary" onclick="setAllToProvider('lokal')" title="Alle auf lokale Ollama-Modelle setzen">🏠 Alle Lokal</button>
              <button class="btn-primary" onclick="setAllToProvider('openrouter')" title="Alle auf OpenRouter Free Modelle setzen">🌍 Alle OpenRouter</button>
            </div>
          </div>
          
          <div id="routing-progress-banner" style="display:none; align-items:center; justify-content:space-between; padding:10px 14px; background:rgba(0,229,255,0.08); border:1px solid rgba(0,229,255,0.22); border-radius:10px; font-size:0.8rem; margin-bottom:10px; flex-shrink:0;">
            <div style="display:flex; align-items:center; gap:10px;">
              <div id="routing-banner-spinner" style="width:14px; height:14px; border:2px solid rgba(0,229,255,0.3); border-top-color:#00e5ff; border-radius:50%; animation:spin 1s linear infinite;"></div>
              <span id="routing-progress-text" style="color:white; font-weight:500;">Auto-routing läuft...</span>
            </div>
            <div id="routing-progress-percentage" style="color:#00e5ff; font-family:monospace; font-weight:bold;">0%</div>
          </div>
          
          <div id="llm-agents-list" style="flex:1; overflow-y:auto; padding-right:5px; scrollbar-width:thin;" data-help="Klicke auf den Namen eines Agenten, um sein Verhalten, seine Personality und sein Gedächtnis anzupassen." data-help-title="LLM-Zuweisung">
            Lade Agenten-Zuweisungen...
          </div>
          
          <div style="padding: 10px 0 0 0; display: flex; justify-content: flex-end; border-top: 1px solid rgba(255,255,255,0.08); flex-shrink: 0;">
            <button class="btn-primary" id="save-agents-btn-bottom" onclick="saveAgentLLMs()" style="width: 100%; justify-content: center; display: flex; align-items: center; gap: 6px;">
              💾 Routing Speichern
            </button>
          </div>
          
          <div id="routing-insights-panel" style="margin-top:10px; display:none; flex-shrink:0;"></div>
        </div>
      </div>

      <!-- Agent Behavior Modal Overlay -->
      <div id="agent-behavior-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.65); backdrop-filter:blur(6px); z-index:1000; align-items:center; justify-content:center;">
        <div class="llm-card" style="width:750px; max-width:90%; height:550px; display:flex; flex-direction:column; overflow:hidden; background:rgba(15,22,40,0.95); border:1px solid var(--glass-border); border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,0.5); padding:20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:10px; margin-bottom:15px; flex-shrink:0;">
            <div style="display:flex; align-items:center; gap:12px;">
              <img id="modal-agent-avatar" style="width:45px; height:45px; border-radius:50%; border:2px solid var(--primary); object-fit:cover;">
              <div>
                <h3 id="modal-agent-name" style="margin:0; font-size:1.1rem; color:#fff; font-weight:600;">Agent Name</h3>
                <span id="modal-agent-role" style="font-size:0.75rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:0.5px;">Rolle</span>
              </div>
            </div>
            <button onclick="closeAgentBehaviorModal()" class="btn-primary" style="padding:4px 10px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.15); cursor:pointer;">&times; Schließen</button>
          </div>
          
          <div style="flex:1; display:grid; grid-template-columns:1fr 1.2fr; gap:20px; overflow:hidden; min-height:0;">
            <!-- Left Column: Sliders and System Prompt -->
            <div style="overflow-y:auto; padding-right:5px; display:flex; flex-direction:column; gap:14px; scrollbar-width:thin;">
              <div class="slider-group">
                <label style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px; font-weight:500;">
                  <span>Personality</span>
                  <span id="modal-label-personality" style="color:var(--cyan); font-weight:bold;">-</span>
                </label>
                <input type="range" id="modal-opt-personality" min="1" max="5" value="3" oninput="updateModalSliderLabel('personality', this.value)" style="cursor:pointer; width:100%;">
              </div>
              <div class="slider-group">
                <label style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px; font-weight:500;">
                  <span>Response Style</span>
                  <span id="modal-label-response" style="color:var(--cyan); font-weight:bold;">-</span>
                </label>
                <input type="range" id="modal-opt-response" min="1" max="5" value="3" oninput="updateModalSliderLabel('response', this.value)" style="cursor:pointer; width:100%;">
              </div>
              <div class="slider-group">
                <label style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px; font-weight:500;">
                  <span>Memory Strength</span>
                  <span id="modal-label-memory" style="color:var(--cyan); font-weight:bold;">-</span>
                </label>
                <input type="range" id="modal-opt-memory" min="1" max="5" value="3" oninput="updateModalSliderLabel('memory', this.value)" style="cursor:pointer; width:100%;">
              </div>
              <div class="slider-group">
                <label style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px; font-weight:500;">
                  <span>Creativity</span>
                  <span id="modal-label-creativity" style="color:var(--cyan); font-weight:bold;">-</span>
                </label>
                <input type="range" id="modal-opt-creativity" min="1" max="5" value="3" oninput="updateModalSliderLabel('creativity', this.value)" style="cursor:pointer; width:100%;">
              </div>
              <div class="slider-group">
                <label style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px; font-weight:500;">
                  <span>Risk Tolerance</span>
                  <span id="modal-label-risk" style="color:var(--cyan); font-weight:bold;">-</span>
                </label>
                <input type="range" id="modal-opt-risk" min="1" max="5" value="3" oninput="updateModalSliderLabel('risk', this.value)" style="cursor:pointer; width:100%;">
              </div>
              <div style="display:flex; flex-direction:column; gap:4px; margin-top:4px;">
                <label style="font-size:0.8rem; font-weight:500; display:flex; justify-content:space-between;">
                  <span>Custom System Prompt Suffix</span>
                </label>
                <textarea id="modal-opt-custom-prompt" style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.12); color:#fff; border-radius:6px; padding:6px; font-family:monospace; font-size:0.75rem; resize:vertical; outline:none; min-height:80px;" placeholder="Prompt-Erweiterung eingeben..."></textarea>
              </div>
              <div style="display:flex; gap:8px; margin-top:4px;">
                <button class="btn-primary" style="flex:1;" id="modal-save-behavior-btn">Speichern</button>
              </div>
            </div>
            
            <!-- Right Column: Memories & Soul Facts -->
            <div style="display:flex; flex-direction:column; overflow:hidden; height:100%;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-shrink:0;">
                <h4 style="margin:0; font-size:0.85rem; color:#fff; font-weight:600;">🧠 Gedächtnis & Soul Facts</h4>
                <button class="btn-danger" id="modal-clear-memories-btn" style="font-size:0.7rem; padding:2px 6px;">Alle löschen</button>
              </div>
              <div style="display:flex; flex-direction:column; gap:6px; flex-shrink:0; border-bottom:1px solid rgba(255,255,255,0.04); padding-bottom:8px;">
                <textarea id="modal-new-mem" style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.12); color:#fff; border-radius:6px; padding:6px; font-size:0.75rem; resize:none; min-height:40px; outline:none;" placeholder="Neuen Eintrag für Langzeitgedächtnis hinzufügen..."></textarea>
                <button class="btn-primary" style="align-self:flex-end; font-size:0.75rem; padding:2px 8px;" id="modal-add-mem-btn">Hinzufügen</button>
              </div>
              <div style="padding:6px 0; flex-shrink:0;">
                <input id="modal-search-mem" style="width:100%; padding:4px 8px; background:rgba(0,0,0,0.25); border:1px solid rgba(255,255,255,0.08); border-radius:6px; color:#fff; font-size:0.75rem; outline:none;" placeholder="Suchen in Erinnerungen...">
              </div>
              <div id="modal-mem-list" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:6px; scrollbar-width:thin;">
                <div class="empty">Keine Erinnerungen geladen.</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
  loadLLMConfig();
}

async function showHelpPage() {
  if (typeof trackView === 'function') trackView('help');
  selectedId = null;
  document.getElementById('content').innerHTML = `
    <div class="panel" id="help-panel" style="display:flex; flex-direction:column; gap:12px; height:100%; box-sizing:border-box; padding:12px 15px;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px;">
        <h2 style="margin:0; font-size:0.95rem; font-weight:600; border:none; letter-spacing:0.5px;">Help Center</h2>
      </div>
      <iframe src="/static/help.html" style="width: 100%; flex-grow:1; border: 1px solid var(--glass-border); border-radius: var(--radius); background: rgba(10, 12, 20, 0.5); min-height: 60vh;"></iframe>
    </div>
  `;
}

async function setSystemLanguage(lang) {
  try {
    await api('POST', '/admin/language', { language: lang });
    document.getElementById('lang-btn-de').style.borderColor = lang === 'de' ? 'var(--primary)' : '';
    document.getElementById('lang-btn-de').style.background = lang === 'de' ? 'rgba(0,150,255,0.2)' : '';
    document.getElementById('lang-btn-en').style.borderColor = lang === 'en' ? 'var(--primary)' : '';
    document.getElementById('lang-btn-en').style.background = lang === 'en' ? 'rgba(0,150,255,0.2)' : '';
  } catch (e) {
    console.error("Failed to set language", e);
  }
}

async function loadLanguageState() {
  try {
    const langRes = await api('GET', '/admin/language');
    const lang = langRes?.language || 'en';
    document.getElementById('lang-btn-de').style.borderColor = lang === 'de' ? 'var(--primary)' : '';
    document.getElementById('lang-btn-de').style.background = lang === 'de' ? 'rgba(0,150,255,0.2)' : '';
    document.getElementById('lang-btn-en').style.borderColor = lang === 'en' ? 'var(--primary)' : '';
    document.getElementById('lang-btn-en').style.background = lang === 'en' ? 'rgba(0,150,255,0.2)' : '';
  } catch (e) {
    console.error("Language loading error", e);
  }
}

async function toggleFtpAutoDeploy(val) {
  try {
    await api('POST', '/admin/autodeploy', { auto_deploy: val });
  } catch (e) {
    console.error("Failed to toggle FTP auto-deploy", e);
  }
}

async function loadFtpAutoDeployState() {
  try {
    const res = await api('GET', '/admin/autodeploy');
    const active = res?.auto_deploy || false;
    const cb = document.getElementById('auto-deploy-checkbox');
    if (cb) cb.checked = active;
  } catch (e) {
    console.error("FTP auto-deploy load error", e);
  }
}

async function toggleBrowserDocker(val) {
  try {
    await api('POST', '/admin/browser_docker', { use_docker: val });
  } catch (e) {
    console.error("Failed to toggle Browser Docker", e);
  }
}

async function loadBrowserDockerState() {
  try {
    const res = await api('GET', '/admin/browser_docker');
    const active = res?.use_docker !== false;
    const cb = document.getElementById('browser-docker-checkbox');
    if (cb) cb.checked = active;
  } catch (e) {
    console.error("Browser Docker state load error", e);
  }
}

async function loadSystemInfoState() {
  try {
    const sysInfo = await api('GET', '/system/info');
    if (sysInfo) {
      let warnHtml = '';
      if (sysInfo.is_intel) {
        warnHtml = `
          <div style="margin-top:10px; padding:10px; background:rgba(255,170,0,0.15); border:1px solid #ffaa00; border-radius:6px; color:#ffaa00; font-size:0.8rem; line-height:1.3;">
            ⚠️ <strong>Intel CPU detected (${sysInfo.cpu})</strong><br>
            Local models > 4B parameters run slowly here. We recommend using <strong>Gemma 2:2b</strong> or <strong>Llama 3.2</strong>.
          </div>
        `;
      }
      document.getElementById('system-info-panel').innerHTML = `
        <strong>💻 System Info:</strong><br>
        • CPU: ${sysInfo.cpu}<br>
        • RAM: ${sysInfo.ram}<br>
        ${warnHtml}
      `;
    }
  } catch (e) {
    console.error("System info error", e);
    document.getElementById('system-info-panel').innerHTML = "System Info not available.";
  }
}

function getProviderDisplayName(p) {
  const labels = {
    'auto': 'Auto-Routing',
    'deepseek': 'DeepSeek',
    'openrouter': 'OpenRouter',
    'openai': 'OpenAI',
    'anthropic': 'Anthropic',
    'gemini': 'Gemini',
    'mistral': 'Mistral',
    'lokal': 'Local (Ollama)',
    'elevenlabs': 'ElevenLabs (TTS)',
    'brave': 'Brave (Web Search)'
  };
  return labels[p] || p;
}

function getModelDisplayName(p, m) {
  if (p === 'openrouter') {
    const labels = {
      'baidu/cobuddy:free': 'Baidu CoBuddy (Free)',
      'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free': 'Nvidia Nemotron Omni Reasoning (Free)',
      'poolside/laguna-xs.2:free': 'Poolside Laguna XS (Free)',
      'poolside/laguna-m.1:free': 'Poolside Laguna M (Free)',
      'deepseek/deepseek-v4-flash:free': 'DeepSeek Flash (Free)',
      'google/gemma-2-9b-it': 'Gemma 2 9B IT',
      'meta-llama/llama-3.1-8b-instruct': 'Llama 3.1 8B',
      'mistralai/mistral-7b-instruct': 'Mistral 7B',
      'qwen/qwen2.5-7b-instruct': 'Qwen 2.5 7B',
      'deepseek/deepseek-chat': 'DeepSeek Chat',
      'llama3.2': 'Llama 3.2',
      'liquid/lfm-2.5-1.2b-thinking:free': 'Liquid LFM 2.5 1.2B Thinking (Free)',
      'liquid/lfm-2.5-1.2b-instruct:free': 'Liquid LFM 2.5 1.2B Instruct (Free)',
      'nvidia/nemotron-3-nano-30b-a3b:free': 'Nvidia Nemotron 3 Nano (Free)',
      'nvidia/nemotron-nano-9b-v2:free': 'Nvidia Nemotron Nano 9B v2 (Free)',
      'openai/gpt-oss-120b:free': 'OpenAI GPT OSS 120B (Free)',
      'openai/gpt-oss-20b:free': 'OpenAI GPT OSS 20B (Free)',
      'arcee-ai/trinity-large-thinking:free': 'Arcee Trinity Large Thinking (Free)',
      'z-ai/glm-4.5-air:free': 'GLM 4.5 Air (Free)',
      'nvidia/nemotron-3-super-120b-a12b:free': 'Nvidia Nemotron 3 Super (Free)',
      'nvidia/nemotron-nano-12b-v2-vl:free': 'Nvidia Nemotron Nano 12B Vision (Free)',
      'google/gemma-4-26b-a4b-it:free': 'Gemma 4 26B (Free)',
      'google/gemma-4-31b-it:free': 'Gemma 4 31B (Free)',
      'minimax/minimax-m2.5:free': 'MiniMax M2.5 (Free)',
      'qwen/qwen3-next-80b-a3b-instruct:free': 'Qwen 3 Next 80B (Free)',
      'cognitivecomputations/dolphin-mistral-24b-venice-edition:free': 'Dolphin Mistral 24B Venice (Free)',
      'meta-llama/llama-3.2-3b-instruct:free': 'Llama 3.2 3B (Free)',
      'nousresearch/hermes-3-llama-3.1-405b:free': 'Hermes 3 Llama 3.1 405B (Free)'
    };
    return labels[m] || m;
  }
  return m;
}

function getAgentCapsFromList(capsList) {
  const capConfig = [
    { name: 'text', color: '#39ff14', label: 'Text' },
    { name: 'vision', color: '#00e5ff', label: 'Vision' },
    { name: 'image', color: '#ff007f', label: 'Image' },
    { name: 'audio', color: '#ffa500', label: 'Audio' },
    { name: 'tools', color: '#b026ff', label: 'Tools' }
  ];
  if (!capsList || !capsList.length) return '';
  return capConfig.filter(c => capsList.includes(c.name)).map(c => {
    return `<span style="display:inline-flex; align-items:center; gap:3px; margin-right:4px; font-size:0.68rem; color:rgba(255,255,255,0.85); font-weight:500; padding:1px 4px; border-radius:3px; background:rgba(0,0,0,0.15); border:1px solid ${c.color}22;">
      <span style="width:6px; height:6px; border-radius:50%; background:${c.color}; box-shadow:0 0 3px ${c.color}; display:inline-block; flex-shrink:0;"></span>
      <span>${c.label}</span>
    </span>`;
  }).join('');
}

function getAgentCapsHtml(pSel, mSel) {
  const capConfig = [
    { name: 'text', color: '#39ff14', label: 'Text' },
    { name: 'vision', color: '#00e5ff', label: 'Vision' },
    { name: 'image', color: '#ff007f', label: 'Image' },
    { name: 'audio', color: '#ffa500', label: 'Audio' },
    { name: 'tools', color: '#b026ff', label: 'Tools' }
  ];
  let activeCaps = [];
  if (pSel === 'lokal') {
    activeCaps = ['text', 'vision', 'tools'];
  } else {
    (globalKeys || []).forEach(k => {
      if (k.provider === pSel && k.valid) {
        if (k.caps && Array.isArray(k.caps)) {
          k.caps.forEach(c => {
            if (!activeCaps.includes(c)) activeCaps.push(c);
          });
        }
      }
    });
  }
  return capConfig.filter(c => activeCaps.includes(c.name)).map(c => {
    return `<span style="display:inline-flex; align-items:center; gap:3px; margin-right:4px; font-size:0.68rem; color:rgba(255,255,255,0.85); font-weight:500; padding:1px 4px; border-radius:3px; background:rgba(0,0,0,0.15); border:1px solid ${c.color}22;">
      <span style="width:6px; height:6px; border-radius:50%; background:${c.color}; box-shadow:0 0 3px ${c.color}; display:inline-block; flex-shrink:0;"></span>
      <span>${c.label}</span>
    </span>`;
  }).join('');
}

function loadLLMAgentsListState(agentsRes, llmAgentsRes, models, providers) {
  let html = '';
  if (agentsRes && Array.isArray(agentsRes)) {
    agentsRes.forEach(a => {
      let safeAgentsRes = llmAgentsRes || {};
      let conf = safeAgentsRes[(a.name || '').toLowerCase()] || {};
      let pSel = conf.provider || 'deepseek';
      let mSel = conf.model || 'deepseek-chat';
      
      if (models[pSel] && !models[pSel].includes(mSel)) {
        models[pSel].push(mSel);
      }

      let lampBg = 'gray';
      let lampShadow = 'rgba(0,0,0,0.5)';
      let lampTitle = 'Nicht getestet';
      let capsHtml = '';
      if (window.testedAgentStatus && window.testedAgentStatus[a.name]) {
        const st = window.testedAgentStatus[a.name];
        if (st.provider === pSel && st.model === mSel) {
          lampBg = st.valid ? '#39ff14' : '#ff3333';
          lampShadow = st.valid ? '#39ff14' : '#ff3333';
          lampTitle = st.info || '';
          capsHtml = st.valid ? getAgentCapsFromList(st.caps) : '';
        } else {
          delete window.testedAgentStatus[a.name];
        }
      }
      
      html += `<div style="display:flex; align-items:center; gap:6px; margin-bottom:4px; padding:4px 8px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); border-radius:6px; font-size:0.8rem;">
        <div style="width:100px; font-weight:bold; overflow:hidden; text-overflow:ellipsis; cursor:pointer; text-decoration:underline;" onclick="openAgentBehaviorModal('${a.name}')" title="Klicke hier, um Verhalten und Gedächtnis von ${a.name} anzupassen">${a.name}</div>
        <select id="prov-${a.name}" onchange="updateModels('${a.name}')" style="background:var(--bg); color:white; border:1px solid rgba(255,255,255,0.15); padding:2px 4px; border-radius:4px; width:100px; font-size:0.75rem;">
          ${providers.map(p => `<option value="${p}" ${p === pSel ? 'selected':''}>${getProviderDisplayName(p)}</option>`).join('')}
        </select>
        <select id="mod-${a.name}" data-db-model="${mSel}" onchange="updateAgentCaps('${a.name}')" style="background:var(--bg); color:white; border:1px solid rgba(255,255,255,0.15); padding:2px 4px; border-radius:4px; width:130px; flex-shrink:0; font-size:0.75rem;">
          ${(models[pSel]||[]).map(m => `<option value="${m}" ${m === mSel ? 'selected':''}>${getModelDisplayName(pSel, m)}</option>`).join('')}
        </select>
        <button class="btn-primary" onclick="testAgentLLM('${a.name}')" style="padding:2px 6px; font-size:0.72rem; flex-shrink:0; display:flex; align-items:center; gap:4px;">
          <span id="lamp-${a.name}" style="width:8px; height:8px; border-radius:50%; background:${lampBg}; display:inline-block; box-shadow:0 0 3px ${lampShadow}; flex-shrink:0;" title="${lampTitle}"></span>
          <span>Test</span>
        </button>
        <div id="caps-agent-${a.name}" style="display:flex; gap:3px; align-items:center; flex-shrink:0; margin-left:4px;">
          ${(window.testedAgentStatus && window.testedAgentStatus[a.name] && window.testedAgentStatus[a.name].caps) ? getAgentCapsFromList(window.testedAgentStatus[a.name].caps) : ''}
        </div>
      </div>`;
    });
  }
  document.getElementById('llm-agents-list').innerHTML = html;
  window.llmAgentsListGlobal = agentsRes;
}

async function loadLLMConfig() {
  try {
    window.testedAgentStatus = JSON.parse(localStorage.getItem('gnom_tested_agent_status') || '{}');
  } catch (e) {
    window.testedAgentStatus = {};
  }
  let keysRes, agentsRes, llmAgentsRes;
  try {
    const results = await Promise.all([
      loadLanguageState(),
      loadSystemInfoState(),
      loadFtpAutoDeployState(),
      loadBrowserDockerState(),
      loadActivePreset(),
      api('GET', '/llm/keys'),
      api('GET', '/agents'),
      api('GET', '/llm/agents')
    ]);
    keysRes = results[5];
    agentsRes = results[6];
    llmAgentsRes = results[7];
    if (keysRes) {
      globalKeys = Object.keys(keysRes).length > 0 ? Object.values(keysRes) : [];
      renderKeyStatus(globalKeys);
      if (globalKeys.length > 0) {
        document.getElementById('llm-keys-input').value = globalKeys.map(k => {
          if (!k.key) return '';
          const keyName = k.label ? k.label + "=" : (k.provider ? k.provider.toUpperCase() + "_API_KEY=" : "");
          const displayKey = window.showKeysFull ? k.key : maskKey(k.key);
          return keyName + displayKey;
        }).filter(k => k).join('\n');
      }
    }
  } catch (e) {
    console.error("Failed to load initial config in parallel", e);
  }
  
  const providers = ['deepseek', 'openrouter', 'openai', 'anthropic', 'gemini', 'mistral', 'lokal'];
  let models = {
    'deepseek': ['deepseek-chat', 'deepseek-reasoner'],
    'openrouter': ['nousresearch/hermes-3-llama-3.1-405b:free', 'qwen/qwen3-coder:free', 'meta-llama/llama-3.3-70b-instruct:free'],
    'openai': ['gpt-4o', 'gpt-4o-mini', 'o1-mini', 'o1-preview'],
    'anthropic': ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
    'gemini': ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash-exp'],
    'mistral': ['mistral-large-latest', 'pixtral-large-latest', 'codestral-latest'],
    'lokal': ['llama3', 'mistral', 'qwen2', 'phi3', 'gemma2']
  };

  loadLLMAgentsListState(agentsRes, llmAgentsRes, models, providers);
  window.llmModelsMap = models;

  api('GET', '/llm/available_models').then(availableModels => {
    if (availableModels) {
      models = { ...models, ...availableModels };
      window.llmModelsMap = models;
      if (agentsRes && Array.isArray(agentsRes)) {
        agentsRes.forEach(a => {
          const provSel = document.getElementById(`prov-${a.name}`);
          const modSelect = document.getElementById(`mod-${a.name}`);
          if (provSel && modSelect) {
            const currentProv = provSel.value;
            const currentMod = modSelect.value;
            const dbMod = modSelect.getAttribute('data-db-model') || currentMod;
            const mods = models[currentProv] || [];
            if (dbMod && !mods.includes(dbMod)) {
              mods.push(dbMod);
            }
            if (currentMod && !mods.includes(currentMod)) {
              mods.push(currentMod);
            }
            modSelect.innerHTML = mods.map(m => `<option value="${m}">${getModelDisplayName(currentProv, m)}</option>`).join('');
            if (mods.includes(dbMod)) {
              modSelect.value = dbMod;
            } else if (mods.includes(currentMod)) {
              modSelect.value = currentMod;
            } else if (mods.length > 0) {
              modSelect.value = mods[0];
            }

            const lamp = document.getElementById(`lamp-${a.name}`);
            const capsDiv = document.getElementById(`caps-agent-${a.name}`);
            const pVal = provSel.value;
            const mVal = modSelect.value;
            
            if (window.testedAgentStatus && window.testedAgentStatus[a.name] && 
                window.testedAgentStatus[a.name].provider === pVal && 
                window.testedAgentStatus[a.name].model === mVal) {
              const st = window.testedAgentStatus[a.name];
              if (lamp) {
                lamp.style.background = st.valid ? '#39ff14' : '#ff3333';
                lamp.style.boxShadow = st.valid ? '0 0 10px #39ff14' : '0 0 10px #ff3333';
                lamp.title = st.info || '';
              }
              if (capsDiv) capsDiv.innerHTML = getAgentCapsFromList(st.caps);
            } else {
              if (lamp) {
                lamp.style.background = 'gray';
                lamp.style.boxShadow = '0 0 3px rgba(0,0,0,0.5)';
                lamp.title = 'Nicht getestet';
              }
              if (capsDiv) capsDiv.innerHTML = '';
              if (window.testedAgentStatus) delete window.testedAgentStatus[a.name];
            }
          }
        });
        if (window.testedAgentStatus) {
          localStorage.setItem('gnom_tested_agent_status', JSON.stringify(window.testedAgentStatus));
        }
      }
    }
  }).catch(e => {
    console.error("Failed to load available models asynchronously", e);
  }).finally(() => {
    if (window.loadRoutingInsights) window.loadRoutingInsights();
  });
}

window.updateAgentCaps = async function(aName) {
  if (window.testedAgentStatus) {
    delete window.testedAgentStatus[aName];
    localStorage.setItem('gnom_tested_agent_status', JSON.stringify(window.testedAgentStatus));
  }
  const lamp = document.getElementById(`lamp-${aName}`);
  if (lamp) {
    lamp.style.background = 'gray';
    lamp.style.boxShadow = '0 0 3px rgba(0,0,0,0.5)';
    lamp.title = 'Nicht getestet';
  }
  const capsContainer = document.getElementById(`caps-agent-${aName}`);
  if (capsContainer) capsContainer.innerHTML = '';
  await saveAgentLLMs();
};

window.updateModels = function(aName) {
  const p = document.getElementById(`prov-${aName}`).value;
  const modSelect = document.getElementById(`mod-${aName}`);
  const mods = window.llmModelsMap[p] || [];
  modSelect.innerHTML = mods.map(m => `<option value="${m}">${getModelDisplayName(p, m)}</option>`).join('');
  window.updateAgentCaps(aName);
};

function maskKey(key) {
  if (!key) return '';
  if (key.length <= 12) return '••••••••';
  const prefix = key.substring(0, 8);
  const suffix = key.substring(key.length - 4);
  return `${prefix}••••••••••••${suffix}`;
}

window.toggleKeysVisibility = function(show) {
  window.showKeysFull = show;
  if (globalKeys.length > 0) {
    document.getElementById('llm-keys-input').value = globalKeys.map(k => {
      if (!k.key) return '';
      const keyName = k.label ? k.label + "=" : (k.provider ? k.provider.toUpperCase() + "_API_KEY=" : "");
      const displayKey = window.showKeysFull ? k.key : maskKey(k.key);
      return keyName + displayKey;
    }).filter(k => k).join('\n');
  }
  renderKeyStatus(globalKeys);
};

function cleanKey(line) {
  let raw = line.trim();
  if (raw.startsWith("export ")) raw = raw.substring(7).trim();
  if (raw.includes("=")) {
    raw = raw.split("=")[1].trim();
  } else if (raw.includes(":")) {
    raw = raw.split(":")[1].trim();
  }
  raw = raw.replace(/^['"]|['"]$/g, '').trim();
  raw = raw.replace(/^[-*+•]\s*/, '').trim();
  raw = raw.replace(/\s*(#|\/\/).*$/, '').trim();
  raw = raw.replace(/\s*\(.*?\)\s*$/, '').trim();
  return raw;
}

function detectProvider(line, cleanedKey) {
  const upper = line.toUpperCase();
  if (upper.includes("OPENROUTER")) return "openrouter";
  if (upper.includes("DEEPSEEK")) return "deepseek";
  if (upper.includes("ANTHROPIC") || upper.includes("CLAUDE")) return "anthropic";
  if (upper.includes("GEMINI") || upper.includes("GOOGLE")) return "gemini";
  if (upper.includes("OPENAI")) return "openai";
  if (upper.includes("MISTRAL")) return "mistral";
  if (upper.includes("ELEVEN") || upper.includes("11LABS")) return "elevenlabs";
  if (upper.includes("BRAVE")) return "brave";
  
  if (cleanedKey.startsWith("sk-or-")) return "openrouter";
  if (cleanedKey.startsWith("sk-ant-")) return "anthropic";
  if (cleanedKey.startsWith("AIzaSy")) return "gemini";
  if (cleanedKey.startsWith("BS-")) return "brave";
  if (/^[0-9a-fA-F]{32}$/.test(cleanedKey)) return "elevenlabs";
  return null;
}

async function saveKeysOnly() {
  const btn = document.getElementById('save-keys-btn');
  const origText = btn ? btn.innerText : 'Speichern';
  const origBg = btn ? btn.style.background : '';
  const origColor = btn ? btn.style.color : '';

  const input = document.getElementById('llm-keys-input').value;
  const rawLines = input.split('\n').map(k => k.trim()).filter(k => k);
  
  document.getElementById('llm-keys-status').innerHTML = 'Speichere Keys...';
  
  let testedKeys = [];
  let nextId = Date.now();
  
  for(let line of rawLines) {
    let isMasked = line.includes('•') || line.includes('*') || line.includes('...');
    let k = cleanKey(line);
    if (!k) continue;
    
    let label = '';
    if (line.includes('=')) {
      label = line.split('=')[0].trim();
      label = label.replace(/^#\s*UNGÜLTIG:\s*/i, '').replace(/^#\s*/, '').trim();
    }
    
    let existing = null;
    if (isMasked) {
      existing = globalKeys.find(gk => maskKey(gk.key) === k);
    } else {
      existing = globalKeys.find(gk => gk.key === k);
    }
    
    if (existing) {
      if (label && (!existing.label || existing.label !== label)) {
        existing.label = label;
      }
      existing.valid = true;
      existing.info = 'Gespeichert';
      if (!existing.caps || existing.caps.length === 0) {
        existing.caps = ['text', 'vision', 'image', 'audio', 'web', 'tools'];
      }
      testedKeys.push(existing);
    } else {
      let p = detectProvider(line, k) || 'unknown';
      testedKeys.push({
        id: 'k_' + (nextId++),
        key: k,
        provider: p,
        valid: true,
        info: 'Gespeichert (Nicht getestet)',
        caps: ['text', 'vision', 'image', 'audio', 'web', 'tools'],
        label: label || (p ? p.toUpperCase() + '_API_KEY' : 'API_KEY')
      });
    }
  }
  
  let toSave = {};
  testedKeys.forEach(k => toSave[k.id] = k);
  const res = await api('POST', '/llm/keys', toSave);
  
  if (res && res.status === 'ok') {
    globalKeys = testedKeys;
    renderKeyStatus(testedKeys);
    
    if (btn) {
      btn.innerText = 'Gespeichert! ✓';
      btn.style.background = '#39ff14';
      btn.style.borderColor = '#39ff14';
      btn.style.color = '#000';
    }
    toast('LLM Konfiguration gespeichert!', 'success');
  } else {
    if (btn) {
      btn.innerText = 'Fehler!';
      btn.style.background = '#ff3333';
      btn.style.borderColor = '#ff3333';
      btn.style.color = '#fff';
    }
    toast('Fehler beim Speichern der LLM Konfiguration.', 'error');
  }
  
  setTimeout(() => {
    if (btn) {
      btn.innerText = origText;
      btn.style.background = origBg;
      btn.style.borderColor = origBg;
      btn.style.color = origColor;
    }
  }, 1500);
}

async function saveAndTestKeys() {
  try {
    const input = document.getElementById('llm-keys-input').value;
    const rawLines = input.split('\n').map(k => k.trim()).filter(k => k);
    
    document.getElementById('llm-keys-status').innerHTML = 'Testing & assigning keys...';
  
  let testedKeys = [];
  let nextId = Date.now();
  
  for(let line of rawLines) {
    let isMasked = line.includes('•') || line.includes('*') || line.includes('...');
    let k = cleanKey(line);
    if (!k) continue;
    
    let label = '';
    if (line.includes('=')) {
      label = line.split('=')[0].trim();
      label = label.replace(/^#\s*UNGÜLTIG:\s*/i, '').replace(/^#\s*/, '').trim();
    }
    
    let existing = null;
    if (isMasked) {
      existing = globalKeys.find(gk => maskKey(gk.key) === k);
    } else {
      existing = globalKeys.find(gk => gk.key === k);
    }
    
    if (existing && isMasked && existing.valid) {
      if (label && (!existing.label || existing.label !== label)) {
        existing.label = label;
      }
      testedKeys.push(existing);
    } else {
      let p = detectProvider(line, k);
      let res = await api('POST', '/llm/test', { key: k, provider: p, label: label });
      testedKeys.push({
        id: existing ? existing.id : 'k_' + (nextId++),
        key: existing ? existing.key : k,
        provider: res ? (res.provider || p || 'unknown') : (p || 'unknown'),
        valid: res && res.valid,
        info: res ? res.info : 'Error',
        caps: res && res.caps ? res.caps : [],
        label: label || (res && res.provider ? res.provider.toUpperCase() + '_API_KEY' : 'API_KEY')
      });
    }
  }
  
  let toSave = {};
  testedKeys.forEach(k => toSave[k.id] = k);
  await api('POST', '/llm/keys', toSave);
  
  globalKeys = testedKeys;
  renderKeyStatus(testedKeys);
  loadLLMConfig();
  } catch (err) {
    document.getElementById('llm-keys-status').innerHTML = '<span style="color:var(--red)">Fehler: ' + err.message + '</span>';
  }
}

function renderKeyStatus(keys) {
  let h = '';
  keys.forEach((k, idx) => {
    let mainColor = k.valid ? '#39ff14' : '#ff3333';
    let keyObscured = (k.key && !window.showKeysFull) ? maskKey(k.key) : (k.key || 'Unknown');
    
    let capsHtml = '';
    const capConfig = [
      { name: 'text', color: '#39ff14', label: 'TXT' },
      { name: 'vision', color: '#00e5ff', label: 'VIS' },
      { name: 'image', color: '#ff007f', label: 'IMG' },
      { name: 'audio', color: '#ffa500', label: 'AUD' },
      { name: 'web', color: '#00ffcc', label: 'WEB' },
      { name: 'tools', color: '#b026ff', label: 'TLS' }
    ];
    
    capConfig.forEach(c => {
      let hasCap = k.caps && k.caps.includes(c.name);
      if (hasCap) {
        capsHtml += `<span style="display:inline-flex; align-items:center; gap:2px; margin-left:4px; font-size:0.6rem; color:rgba(255,255,255,0.8); font-weight:bold; background:rgba(0,0,0,0.15); border:1px solid ${c.color}22; padding:0 3px; border-radius:2px;">
          <span style="width:4px; height:4px; border-radius:50%; background:${c.color}; box-shadow:0 0 2px ${c.color}; display:inline-block; flex-shrink:0;"></span>
          <span>${c.label}</span>
        </span>`;
      }
    });

    h += `
      <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px; font-size:0.72rem; background:rgba(255,255,255,0.02); padding:3px 6px; border-radius:4px; border:1px solid rgba(255,255,255,0.05);">
        <div style="width:8px; height:8px; border-radius:50%; background:${mainColor}; box-shadow:0 0 3px ${mainColor}; flex-shrink:0;" title="${k.valid ? 'Gültig' : 'Ungültig'}"></div>
        <div style="flex-grow:1; font-family:monospace; overflow:hidden; text-overflow:ellipsis;" title="${keyObscured}">${k.label ? k.label + ': ' : ''}${keyObscured} (${getProviderDisplayName(k.provider) || 'Unbekannt'})</div>
        <div style="display:flex; gap:2px; align-items:center; flex-shrink:0;">${capsHtml}</div>
      </div>
    `;
  });
  document.getElementById('llm-keys-status').innerHTML = h || '<div style="color:var(--text-muted)">Keine Keys hinterlegt.</div>';
}

window.runRoutingWithProgress = async function(agents, routeActionPromise) {
  const banner = document.getElementById('routing-progress-banner');
  const text = document.getElementById('routing-progress-text');
  const pct = document.getElementById('routing-progress-percentage');
  const spinner = document.getElementById('routing-banner-spinner');
  
  if (banner) {
    banner.style.display = 'flex';
    banner.style.background = 'rgba(0,229,255,0.08)';
    banner.style.borderColor = 'rgba(0,229,255,0.2)';
    if (text) {
      text.innerText = 'Auto-routing läuft: Mappe Agenten zu optimalen LLMs...';
      text.style.color = '#00e5ff';
    }
    if (pct) {
      pct.innerText = '0%';
      pct.style.color = 'rgba(0,229,255,0.7)';
    }
    if (spinner) {
      spinner.style.display = 'block';
      spinner.style.borderColor = 'rgba(0,229,255,0.3)';
      spinner.style.borderTopColor = '#00e5ff';
    }
  }
  
  try {
    await routeActionPromise;
    await loadLLMConfig();
    
    let completed = 0;
    const total = agents.length;
    if (total === 0) {
      if (pct) pct.innerText = '100%';
    }
    
    const testPromises = agents.map(async (a) => {
      const provSelect = document.getElementById(`prov-${a.name}`);
      const modSelect = document.getElementById(`mod-${a.name}`);
      const p = provSelect ? provSelect.value : 'auto';
      const m = modSelect ? modSelect.value : 'stage_3';
      
      const lamp = document.getElementById(`lamp-${a.name}`);
      if (lamp) {
        lamp.style.background = 'yellow';
        lamp.style.boxShadow = '0 0 8px yellow';
        lamp.title = 'Test läuft...';
      }
      
      try {
        let res = await api('POST', '/llm/test_agent', { agent: a.name, provider: p, model: m });
        window.testedAgentStatus = window.testedAgentStatus || {};
        const capsDiv = document.getElementById(`caps-agent-${a.name}`);
        if (lamp) {
          if (res && res.valid) {
            lamp.style.background = '#39ff14';
            lamp.style.boxShadow = '0 0 10px #39ff14';
            let detail = (res.resolved_provider && res.resolved_model) ? ` (${getProviderDisplayName(res.resolved_provider)} - ${res.resolved_model})` : '';
            lamp.title = `Test erfolgreich${detail}`;
            window.testedAgentStatus[a.name] = { 
              valid: true, 
              info: `Test erfolgreich${detail}`, 
              caps: res.caps || [],
              provider: p,
              model: m
            };
            if (capsDiv) capsDiv.innerHTML = getAgentCapsFromList(res.caps || []);
          } else {
            lamp.style.background = '#ff3333';
            lamp.style.boxShadow = '0 0 10px #ff3333';
            lamp.title = res ? (res.info || 'Test fehlgeschlagen') : 'Fehler';
            window.testedAgentStatus[a.name] = { 
              valid: false, 
              info: res ? (res.info || 'Test fehlgeschlagen') : 'Fehler', 
              caps: [],
              provider: p,
              model: m
            };
            if (capsDiv) capsDiv.innerHTML = '';
          }
        }
      } catch (e) {
        window.testedAgentStatus = window.testedAgentStatus || {};
        window.testedAgentStatus[a.name] = { 
          valid: false, 
          info: 'Verbindungsfehler', 
          caps: [],
          provider: p,
          model: m
        };
        if (lamp) {
          lamp.style.background = '#ff3333';
          lamp.style.boxShadow = '0 0 10px #ff3333';
          lamp.title = 'Verbindungsfehler';
        }
        const capsDiv = document.getElementById(`caps-agent-${a.name}`);
        if (capsDiv) capsDiv.innerHTML = '';
      }
      
      completed++;
      const percent = Math.round((completed / total) * 100);
      if (pct) pct.innerText = `${percent}%`;
    });
    
    await Promise.all(testPromises);
    if (window.testedAgentStatus) {
      localStorage.setItem('gnom_tested_agent_status', JSON.stringify(window.testedAgentStatus));
    }
    
    if (banner) {
      banner.style.background = 'rgba(57,255,20,0.08)';
      banner.style.borderColor = 'rgba(57,255,20,0.2)';
      if (text) {
        text.innerText = `Auto-routing abgeschlossen! ${total} Agenten erfolgreich verifiziert.`;
        text.style.color = '#39ff14';
      }
      if (pct) {
        pct.innerText = '100%';
        pct.style.color = 'rgba(57,255,20,0.7)';
      }
      if (spinner) spinner.style.display = 'none';
      await loadRoutingInsights();
      setTimeout(() => { banner.style.display = 'none'; }, 3000);
    }
  } catch (err) {
    console.error("Routing progress error", err);
    if (banner) {
      banner.style.background = 'rgba(255,51,51,0.08)';
      banner.style.borderColor = 'rgba(255,51,51,0.2)';
      if (text) {
        text.innerText = 'Fehler beim Auto-routing.';
        text.style.color = '#ff3333';
      }
      if (spinner) spinner.style.display = 'none';
      setTimeout(() => { banner.style.display = 'none'; }, 4000);
    }
  }
};

// Shared agent priority and model scoring for LLM assignment
const AGENT_PRIORITY = {
  'coderag': 1, 'researcherag': 2, 'writerag': 3, 'editorag': 4,
  'generalag': 5, 'securityag': 6, 'soulag': 7, 'watchdogag': 8
};

function modelScore(m) {
  const ml = m.toLowerCase();
  if (/405b/.test(ml)) return 900;
  if (/120b/.test(ml)) return 800;
  if (/80b/.test(ml)) return 750;
  if (/70b/.test(ml)) return 700;
  if (/31b|30b|26b/.test(ml)) return 600;
  if (/24b/.test(ml)) return 550;
  if (/20b/.test(ml)) return 500;
  if (/12b/.test(ml)) return 400;
  if (/9b/.test(ml)) return 350;
  if (/7b|8b/.test(ml)) return 300;
  if (/3b/.test(ml)) return 200;
  if (/1\.2b|1b/.test(ml)) return 100;
  return 350;
}

function sortAgentsByPriority(agents) {
  return [...agents].sort((a, b) => {
    const pa = AGENT_PRIORITY[a.name.toLowerCase()] || 99;
    const pb = AGENT_PRIORITY[b.name.toLowerCase()] || 99;
    return pa - pb;
  });
}

window.assignFreeModels = async function() {
  const agents = window.llmAgentsListGlobal || [];
  if (!agents.length) return;

  const availableModels = await api('GET', '/llm/available_models');
  const workingModels = (availableModels && availableModels.openrouter) || [];

  if (!workingModels.length) {
    alert('Keine Free-Modelle verfügbar.');
    return;
  }

  const sorted = [...workingModels].sort((a, b) => modelScore(b) - modelScore(a));
  const sortedAgents = sortAgentsByPriority(agents);

  let config = {};
  sortedAgents.forEach((a, i) => {
    const model = sorted[i % sorted.length];
    config[a.name.toLowerCase()] = { provider: 'openrouter', model: model };
  });
  await window.runRoutingWithProgress(agents, api('POST', '/llm/agents', config));
};

window.assignLocalModels = async function() {
  const agents = window.llmAgentsListGlobal || [];
  if (!agents.length) return;

  const workingLocalModels = ['mistral:latest', 'gemma2:2b', 'llama3:latest', 'qwen2:7b'];

  const sorted = [...workingLocalModels].sort((a, b) => modelScore(b) - modelScore(a));
  const sortedAgents = sortAgentsByPriority(agents);

  let config = {};
  sortedAgents.forEach((a, i) => {
    const model = sorted[i % sorted.length];
    config[a.name.toLowerCase()] = { provider: 'lokal', model: model };
  });
  await window.runRoutingWithProgress(agents, api('POST', '/llm/agents', config));
};

window.setAllAgentsToProvider = async function(provider, model) {
  const agents = window.llmAgentsListGlobal || [];
  let config = {};
  agents.forEach(a => {
    config[a.name.toLowerCase()] = { provider: provider, model: model };
  });
  await window.runRoutingWithProgress(agents, api('POST', '/llm/agents', config));
};

window.autoRouteAllAgents = async function() {
  const agents = window.llmAgentsListGlobal || [];
  await window.runRoutingWithProgress(agents, api('POST', '/llm/auto_assign'));
};

window.setAllToProvider = async function(providerKey) {
  const agents = window.llmAgentsListGlobal || [];
  await window.runRoutingWithProgress(agents, api('POST', '/llm/auto_assign?force_provider=' + providerKey));
};

window.loadRoutingInsights = async function() {
  const container = document.getElementById('routing-insights-panel');
  if (!container) return;
  
  try {
    const insights = await api('GET', '/llm/routing_insights');
    if (insights && Array.isArray(insights) && insights.length > 0) {
      container.style.display = 'block';
      let html = `<div style="display:flex; flex-direction:column; gap:6px;">`;
      
      insights.forEach(ins => {
        let badgeColor = '#888';
        let badgeBg = 'rgba(255,255,255,0.02)';
        let borderLeft = '3px solid rgba(255,255,255,0.2)';
        let badgeText = ins.status;
        let actionHtml = '';
        let iconSvg = '';
        
        if (ins.status === 'optimal') {
          badgeColor = '#39ff14';
          badgeBg = 'rgba(57,255,20,0.02)';
          borderLeft = '3px solid #39ff14';
          badgeText = 'Optimiert';
          iconSvg = `<svg style="width:12px; height:12px; fill:#39ff14; flex-shrink:0;" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>`;
        } else if (ins.status === 'upgrade_available') {
          badgeColor = '#00e5ff';
          badgeBg = 'rgba(0,229,255,0.04)';
          borderLeft = '3px solid #00e5ff';
          badgeText = 'Upgrade';
          iconSvg = `<svg style="width:12px; height:12px; fill:#00e5ff; flex-shrink:0; filter: drop-shadow(0 0 2px #00e5ff);" viewBox="0 0 24 24"><path d="M2 13h6v8h8v-8h6L12 3 2 13z"/></svg>`;
          actionHtml = `<button onclick="applyUpgrade('${ins.agent}', '${ins.optimal_provider}', '${ins.optimal_model}')" class="btn-primary" style="font-size:0.7rem; padding:2px 6px; margin-left:auto; background:#00e5ff; color:#000; border-radius:4px; font-weight:bold; border:none; cursor:pointer;">Anwenden</button>`;
        } else if (ins.status === 'manual_override') {
          badgeColor = '#ffa500';
          badgeBg = 'rgba(255,165,0,0.02)';
          borderLeft = '3px solid #ffa500';
          badgeText = 'Override';
          iconSvg = `<svg style="width:12px; height:12px; fill:#ffa500; flex-shrink:0;" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>`;
          actionHtml = `<button onclick="applyUpgrade('${ins.agent}', '${ins.optimal_provider}', '${ins.optimal_model}')" class="btn-primary" style="font-size:0.7rem; padding:2px 6px; margin-left:auto; background:transparent; border:1px solid rgba(255,255,255,0.2); color:rgba(255,255,255,0.8); border-radius:4px; cursor:pointer;">Reset</button>`;
        }
        
        html += `
          <div style="display:flex; align-items:center; gap:8px; padding:4px 8px; background:${badgeBg}; border:1px solid rgba(255,255,255,0.03); border-left:${borderLeft}; border-radius:4px; font-size:0.72rem; line-height:1.3; transition:all 0.2s ease; overflow:hidden;" onmouseover="this.style.background='rgba(255,255,255,0.04)';" onmouseout="this.style.background='${badgeBg}';">
            <div style="display:flex; align-items:center; gap:4px; width:80px; font-weight:bold; overflow:hidden; text-overflow:ellipsis; flex-shrink:0; color:#fff;">
              ${iconSvg}
              <span>${ins.agent}</span>
            </div>
            <div style="flex-grow:1; color:rgba(255,255,255,0.65); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${ins.explanation}">${ins.explanation}</div>
            <div style="display:flex; align-items:center; gap:6px; flex-shrink:0; margin-left:auto;">
              <span style="font-size:0.6rem; font-weight:bold; padding:1px 4px; border-radius:3px; border:1px solid ${badgeColor}33; color:rgba(255,255,255,0.85); font-family:monospace; background:rgba(0,0,0,0.2);">${badgeText.toUpperCase()}</span>
              ${actionHtml}
            </div>
          </div>
        `;
      });
      
      html += `</div>`;
      container.innerHTML = html;
    } else {
      container.style.display = 'none';
    }
  } catch (e) {
    console.error("Failed to load routing insights", e);
    container.style.display = 'none';
  }
};

window.applyUpgrade = async function(aName, pvd, mdl) {
  const pSelect = document.getElementById(`prov-${aName}`);
  if (pSelect) {
    pSelect.value = pvd;
    window.updateModels(aName);
    const mSelect = document.getElementById(`mod-${aName}`);
    if (mSelect) {
      mSelect.value = mdl;
      window.updateAgentCaps(aName);
    }
  }
  
  const lamp = document.getElementById(`lamp-${aName}`);
  if (lamp) {
    lamp.style.background = 'yellow';
    lamp.style.boxShadow = '0 0 8px yellow';
  }
  
  await saveAgentLLMs();
  await testAgentLLM(aName);
  await loadRoutingInsights();
};

async function saveAgentLLMs() {
  const btn = document.getElementById('save-agents-btn');
  const btnBottom = document.getElementById('save-agents-btn-bottom');
  const origText = btn ? btn.innerText : 'Save';
  const origTextBottom = btnBottom ? btnBottom.innerText : 'Routing Speichern';
  const origBg = btn ? btn.style.background : '';
  const origBgBottom = btnBottom ? btnBottom.style.background : '';
  
  const currentConfig = await api('GET', '/llm/agents') || {};
  const agentsRes = await api('GET', '/agents');
  let config = { ...currentConfig };
  let hasUpdated = false;
  if (agentsRes && Array.isArray(agentsRes)) {
    agentsRes.forEach(a => {
      let p = document.getElementById(`prov-${a.name}`);
      let m = document.getElementById(`mod-${a.name}`);
      if(p && m) {
        config[a.name.toLowerCase()] = {
          provider: p.value,
          model: m.value
        };
        hasUpdated = true;
      }
    });
  }
  if (!hasUpdated) {
    console.warn("saveAgentLLMs: No selects found in DOM, skipping save.");
    return {"status": "ok"};
  }
  const res = await api('POST', '/llm/agents', config);
  if (res) {
    if (btn) {
      btn.innerText = 'Saved! ✓';
      btn.style.background = '#39ff14';
      btn.style.color = '#000';
    }
    if (btnBottom) {
      btnBottom.innerText = 'Gespeichert! ✓';
      btnBottom.style.background = '#39ff14';
      btnBottom.style.borderColor = '#39ff14';
      btnBottom.style.color = '#000';
    }
    toast('Agent settings saved successfully!', 'success');
  } else {
    if (btn) {
      btn.innerText = 'Error';
      btn.style.background = '#ff3333';
    }
    if (btnBottom) {
      btnBottom.innerText = 'Fehler beim Speichern';
      btnBottom.style.background = '#ff3333';
      btnBottom.style.borderColor = '#ff3333';
    }
    toast('Failed to save agent settings.', 'error');
  }
  setTimeout(() => {
    if (btn) {
      btn.innerText = origText;
      btn.style.background = origBg;
      btn.style.color = '';
    }
    if (btnBottom) {
      btnBottom.innerText = origTextBottom;
      btnBottom.style.background = origBgBottom;
      btnBottom.style.borderColor = origBgBottom;
      btnBottom.style.color = '';
    }
  }, 1500);
}

async function testAgentLLM(aName) {
  const pEl = document.getElementById(`prov-${aName}`);
  const mEl = document.getElementById(`mod-${aName}`);
  const lamp = document.getElementById(`lamp-${aName}`);
  if (!pEl || !mEl || !lamp) return;
  const p = pEl.value;
  const m = mEl.value;
  
  lamp.style.background = 'yellow';
  lamp.style.boxShadow = '0 0 8px yellow';
  lamp.title = 'Test läuft...';
  
  let res = await api('POST', '/llm/test_agent', { agent: aName, provider: p, model: m });
  window.testedAgentStatus = window.testedAgentStatus || {};
  if (res && res.valid) {
    let detail = (res.resolved_provider && res.resolved_model) ? ` (${getProviderDisplayName(res.resolved_provider)} - ${res.resolved_model})` : '';
    window.testedAgentStatus[aName] = { 
      valid: true, 
      info: `Test erfolgreich${detail}`, 
      caps: res.caps || [],
      provider: (p === 'auto') ? res.resolved_provider : p,
      model: (p === 'auto') ? res.resolved_model : m
    };
    lamp.style.background = '#39ff14';
    lamp.style.boxShadow = '0 0 10px #39ff14';
    lamp.title = `Test erfolgreich${detail}`;
    
    if (p === 'auto' && res.resolved_provider && res.resolved_model) {
      const provSelect = document.getElementById(`prov-${aName}`);
      if (provSelect) {
        provSelect.value = res.resolved_provider;
        window.updateModels(aName);
        const modSelect = document.getElementById(`mod-${aName}`);
        if (modSelect) {
          modSelect.value = res.resolved_model;
          window.updateAgentCaps(aName);
        }
      }
    }
    const capsDiv = document.getElementById(`caps-agent-${aName}`);
    if (capsDiv) capsDiv.innerHTML = getAgentCapsFromList(res.caps || []);
  } else {
    let detail = (res && res.resolved_provider && res.resolved_model) ? ` (Tried ${getProviderDisplayName(res.resolved_provider)} - ${res.resolved_model})` : '';
    window.testedAgentStatus[aName] = { 
      valid: false, 
      info: (res && res.info) ? `Fehler: ${res.info}${detail}` : `Test fehlgeschlagen${detail}`, 
      caps: [],
      provider: (p === 'auto' && res) ? res.resolved_provider : p,
      model: (p === 'auto' && res) ? res.resolved_model : m
    };
    lamp.style.background = '#ff3333';
    const capsDiv = document.getElementById(`caps-agent-${aName}`);
    if (capsDiv) capsDiv.innerHTML = '';
    lamp.style.boxShadow = '0 0 10px #ff3333';
    lamp.title = (res && res.info) ? `Fehler: ${res.info}${detail}` : `Test fehlgeschlagen${detail}`;
    
    if (p === 'auto' && res && res.resolved_provider && res.resolved_model) {
      const provSelect = document.getElementById(`prov-${aName}`);
      if (provSelect) {
        provSelect.value = res.resolved_provider;
        window.updateModels(aName);
        const modSelect = document.getElementById(`mod-${aName}`);
        if (modSelect) {
          modSelect.value = res.resolved_model;
          window.updateAgentCaps(aName);
        }
      }
    }
  }
  localStorage.setItem('gnom_tested_agent_status', JSON.stringify(window.testedAgentStatus));
}

window.getAgentMeta = function(agentId) {
  const key = agentId ? agentId.toLowerCase().trim() : '';
  const roles = {
    'soulag':       { name: 'SoulAG',       desc: 'Swarm memory & semantic learning' },
    'generalag':    { name: 'GeneralAG',    desc: 'Coordinator' },
    'securityag':   { name: 'SecurityAG',   desc: 'Security auditing & scan' },
    'watchdogag':   { name: 'WatchdogAG',   desc: 'Rules & safety enforcement' },
    'coderag':      { name: 'CoderAG',      desc: 'Code implementation' },
    'researcherag': { name: 'ResearcherAG', desc: 'Information gathering & web research' },
    'writerag':     { name: 'WriterAG',     desc: 'Content creation & text drafting' },
    'editorag':     { name: 'EditorAG',     desc: 'Quality assurance & refactoring' }
  };
  return roles[key] || { name: agentId.charAt(0).toUpperCase() + agentId.slice(1), desc: 'Schwarm-Mitglied' };
};

window.getAgentAvatarUrl = function(agentId) {
  const known = ['soulag', 'generalag', 'coderag', 'researcherag', 'writerag', 'watchdogag', 'securityag', 'editorag'];
  const key = agentId ? agentId.toLowerCase().trim() : '';
  if (known.includes(key)) {
    return `/static/avatars/${key}.png`;
  }
  for (const k of known) {
    if (key.includes(k) || k.includes(key)) {
      return `/static/avatars/${k}.png`;
    }
  }
  return `/static/avatars/generalag.png`;
};

window.showAgentTuning = function(agentId) {
  if (typeof showWarRoom !== 'function') return;
  window.viewHistory.push('war-room');
  window.currentView = 'agent-tuning';
  if (window.updateBackButtonState) window.updateBackButtonState();
  const el = document.getElementById('content');
  if (!el) return;
  window._tuningAgentId = null;
  window._tuningTab = 'tuning';

  const allAgents = (window.agents || []);

  let html = '<div style="display:flex;flex-direction:column;gap:14px;height:100%;">';
  html += '<h2 style="color:var(--accent);margin:0;display:flex;align-items:center;gap:12px;">🎛️ Agent Tuning <span style="font-size:0.7rem;color:rgba(255,255,255,0.3);font-weight:400;">Prompt · Soul · Blockaden · Tools · Verhalten</span></h2>';

  html += '<div style="display:flex;gap:8px;flex-wrap:wrap;">';
  allAgents.forEach(a => {
    html += '<button class="btn-primary" id="atab-' + a.id + '" onclick="tuningSelect(\'' + a.id + '\')" style="background:rgba(255,255,255,0.03);border-color:rgba(255,255,255,0.1);color:rgba(255,255,255,0.6);padding:6px 14px;font-size:0.8rem;cursor:pointer;border-radius:6px;">' + a.name + '</button>';
  });
  html += '</div>';

  const tabs = [
    {id:'prompt', label:'📝 Prompt'},
    {id:'soul', label:'💡 Soul'},
    {id:'blockaden', label:'🛡️ Blockaden'},
    {id:'tools', label:'🔧 Tools'},
    {id:'tuning', label:'🎚️ Verhalten'},
    {id:'presets', label:'💾 Presets'},
    {id:'bake', label:'🏭 Bake'},
  ];
  html += '<div style="display:flex;gap:4px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:6px;">';
  tabs.forEach(t => {
    html += '<button class="ttab" id="ttab-' + t.id + '" onclick="tuningSwitchTab(\'' + t.id + '\')" style="padding:6px 14px;font-size:0.75rem;background:none;border:none;color:rgba(255,255,255,0.4);cursor:pointer;border-bottom:2px solid transparent;transition:all 0.2s;">' + t.label + '</button>';
  });
  html += '</div>';

  html += '<div id="tuning-content" style="flex:1;overflow-y:auto;padding-right:4px;"></div>';
  html += '</div>';
  el.innerHTML = html;

  var targetId = agentId || (allAgents.length > 0 ? allAgents[0].id : null);
  if (targetId) tuningSelect(targetId);
};

window.tuningSelect = function(agentId) {
  window._tuningAgentId = agentId;
  const allAgents = (window.agents || []);
  allAgents.forEach(a => {
    const btn = document.getElementById('atab-' + a.id);
    if (btn) { btn.style.background = a.id === agentId ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.03)'; btn.style.borderColor = a.id === agentId ? 'var(--agent-color, var(--accent))' : 'rgba(255,255,255,0.1)'; btn.style.color = a.id === agentId ? '#fff' : 'rgba(255,255,255,0.6)'; btn.style.setProperty('--agent-color', agentColor(a.name)); }
  });
  tuningSwitchTab(window._tuningTab || 'tuning');
};

window.tuningSwitchTab = function(tabId) {
  window._tuningTab = tabId;
  document.querySelectorAll('.ttab').forEach(b => { b.style.color='rgba(255,255,255,0.4)'; b.style.borderBottomColor='transparent'; });
  const t = document.getElementById('ttab-' + tabId);
  if (t) { t.style.color='var(--accent)'; t.style.borderBottomColor='var(--accent)'; }
  const fn = 'tuningRender_' + tabId;
  if (typeof window[fn] === 'function') window[fn](window._tuningAgentId);
};

// ── Tab: Prompt ──
window.tuningRender_prompt = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  const agent = (agents||[]).find(a => a.id === agentId); if (!agent) return;
  const key = agent.name.toLowerCase();
  let settings = {};
  try { const r = await api('GET', '/agents/' + agentId + '/settings'); if (r) settings = r; } catch(e){}
  el.innerHTML = '<div class="panel" style="display:flex;flex-direction:column;gap:12px;padding:16px;">'
    + '<div><label style="font-size:0.75rem;font-weight:600;margin-bottom:4px;display:block;">System-Prompt</label><textarea id="tsp-sys" style="width:100%;min-height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.12);color:#fff;border-radius:6px;padding:10px;font-family:monospace;font-size:0.75rem;resize:vertical;">' + escapeHtml((settings.sys_prompt||'')) + '</textarea></div>'
    + '<div><label style="font-size:0.75rem;font-weight:600;margin-bottom:4px;display:block;">Custom Suffix (wird angehängt)</label><textarea id="tsp-custom" style="width:100%;min-height:120px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.12);color:#fff;border-radius:6px;padding:10px;font-family:monospace;font-size:0.75rem;resize:vertical;">' + escapeHtml((settings.custom_prompt||'')) + '</textarea></div>'
    + '<button onclick="tuningSavePrompt(\'' + agentId + '\',\'' + key + '\')" style="padding:8px;font-size:0.8rem;font-weight:700;background:rgba(0,200,100,0.15);border:1px solid rgba(0,200,100,0.3);color:#0f0;border-radius:6px;cursor:pointer;">💾 Prompt speichern</button>'
    + '<div id="tmsg-prompt" style="font-size:0.65rem;color:rgba(255,255,255,0.3);text-align:center;"></div>'
    + '</div>';
};

window.tuningSavePrompt = async function(agentId, key) {
  const sysP = document.getElementById('tsp-sys')?.value || '';
  const custP = document.getElementById('tsp-custom')?.value || '';
  const r = await api('PUT', '/agents/' + agentId + '/settings', {sys_prompt: sysP, custom_prompt: custP});
  const msg = document.getElementById('tmsg-prompt');
  if (r !== null) { if (msg) { msg.textContent='✓ Gespeichert'; msg.style.color='#0f0'; setTimeout(()=>msg.textContent='',2000); } }
  else { if (msg) { msg.textContent='Fehler'; msg.style.color='#f00'; } }
};

// ── Tab: Soul ──
window.tuningRender_soul = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  const agent = (agents||[]).find(a => a.id === agentId); if (!agent) return;
  el.innerHTML = '<div style="color:rgba(255,255,255,0.3);padding:20px;text-align:center;">Lade Soul-Daten...</div>';
  let facts = [];
  try { const r = await api('GET', '/soul/all/' + agent.name); if (Array.isArray(r)) facts = r; } catch(e){}
  let html = '<div class="panel" style="padding:16px;display:flex;flex-direction:column;gap:12px;">';
  html += '<div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;">';
  html += '<div style="flex:1;min-width:150px;"><label style="font-size:0.7rem;display:block;margin-bottom:2px;">Filter</label><input id="tsoul-filter" placeholder="Suche..." oninput="tuningSoulFilter()" style="width:100%;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.12);color:#fff;border-radius:4px;padding:6px;font-size:0.75rem;"></div>';
  html += '<div><label style="font-size:0.7rem;display:block;margin-bottom:2px;">Priorität</label><select id="tsoul-prio" onchange="tuningSoulFilter()" style="background:rgba(0,0,0,0.3);color:#fff;border:1px solid rgba(255,255,255,0.12);border-radius:4px;padding:6px;font-size:0.75rem;"><option value="">Alle</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></div>';
  html += '<div><button onclick="tuningSoulAdd(\'' + agentId + '\',\'' + agent.name + '\')" style="padding:6px 12px;font-size:0.75rem;background:rgba(0,150,255,0.15);border:1px solid rgba(0,150,255,0.3);color:#0af;border-radius:6px;cursor:pointer;white-space:nowrap;">➕ Neu</button></div>';
  html += '</div>';
  html += '<div id="tsoul-cnt" style="font-size:0.7rem;color:rgba(255,255,255,0.4);">' + facts.length + ' Fakten</div>';
  html += '<div id="tsoul-list" style="max-height:500px;overflow-y:auto;display:flex;flex-direction:column;gap:4px;"></div>';
  html += '</div>';
  el.innerHTML = html;
  window._tuningSoulFacts = facts;
  window._tuningSoulAgent = agent;
  tuningSoulRenderList();
};

window.tuningSoulFilter = function() { tuningSoulRenderList(); };
window.tuningSoulRenderList = function() {
  const filter = (document.getElementById('tsoul-filter')?.value || '').toLowerCase();
  const prio = document.getElementById('tsoul-prio')?.value || '';
  let facts = window._tuningSoulFacts || [];
  if (filter) facts = facts.filter(f => (f.key||'').toLowerCase().includes(filter) || (f.value||'').toLowerCase().includes(filter));
  if (prio) facts = facts.filter(f => f.priority === prio);
  const el = document.getElementById('tsoul-list'); if (!el) return;
  document.getElementById('tsoul-cnt').textContent = facts.length + ' Fakten';
  if (!facts.length) { el.innerHTML = '<div style="color:rgba(255,255,255,0.2);padding:20px;text-align:center;">Keine Fakten gefunden</div>'; return; }
  el.innerHTML = facts.map(f => {
    const pc = f.priority==='high'?'#ff9900':f.priority==='low'?'#888':'#aaa';
    const k_enc = f.key.replace(/'/g,"&#39;").replace(/"/g,"&quot;");
    const v_enc = (f.value||'').substring(0,80).replace(/'/g,"&#39;").replace(/"/g,"&quot;");
    return '<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:8px 10px;display:flex;gap:8px;align-items:flex-start;"><div style="flex:1;min-width:0;"><div style="font-size:0.7rem;font-weight:600;color:'+pc+';margin-bottom:3px;word-break:break-word;">'+escapeHtml(f.key)+'</div><div style="font-size:0.65rem;color:rgba(255,255,255,0.5);word-break:break-word;">'+escapeHtml(f.value||'').substring(0,200)+'</div></div><div style="display:flex;gap:3px;flex-shrink:0;"><button data-soulkey="'+k_enc+'" data-soulval="'+v_enc+'" data-soulprio="'+f.priority+'" onclick="tuningSoulEditBtn(this)" style="background:none;border:none;color:#0af;cursor:pointer;font-size:0.7rem;padding:2px;" title="Bearbeiten">✏️</button><button data-soulkey="'+k_enc+'" onclick="tuningSoulDelBtn(this)" style="background:none;border:none;color:#f44;cursor:pointer;font-size:0.7rem;padding:2px;" title="Löschen">✕</button></div></div>';
  }).join('');
};

window.tuningSoulAdd = function(agentId, agentName) {
  const key = prompt('Key (z.B. "projekt_sprache"):');
  if (!key) return;
  const value = prompt('Wert:');
  if (!value) return;
  const priority = prompt('Priorität (high/medium/low):', 'medium') || 'medium';
  api('POST', '/soul/save', {key, value, priority}).then(r => {
    if (r && r.status === 'ok') { toast('Fakt gespeichert', 'success'); tuningRender_soul(agentId); }
    else { toast('Fehler', 'error'); }
  });
};

window.tuningSoulDelete = function(agentId, key) {
  if (!confirm('Fakt "' + key + '" wirklich löschen?')) return;
  api('POST', '/soul/delete', {key}).then(r => {
    if (r && r.status === 'ok') { toast('Gelöscht', 'info'); tuningRender_soul(agentId); }
    else { toast('Fehler', 'error'); }
  });
};

window.tuningSoulEditBtn = function(btn) {
  const key = btn.getAttribute('data-soulkey');
  const val = btn.getAttribute('data-soulval');
  const prio = btn.getAttribute('data-soulprio');
  const newVal = prompt('Wert bearbeiten:', val);
  if (newVal === null) return;
  const newPrio = prompt('Priorität (high/medium/low):', prio) || prio;
  api('POST', '/soul/save', {key, value: newVal, priority: newPrio}).then(r => {
    if (r && r.status === 'ok') { toast('Aktualisiert', 'success'); tuningRender_soul(window._tuningAgentId); }
    else { toast('Fehler', 'error'); }
  });
};

window.tuningSoulDelBtn = function(btn) {
  const key = btn.getAttribute('data-soulkey');
  if (!confirm('Fakt "' + key + '" löschen?')) return;
  api('POST', '/soul/delete', {key}).then(r => {
    if (r && r.status === 'ok') { toast('Gelöscht', 'info'); tuningRender_soul(window._tuningAgentId); }
    else { toast('Fehler', 'error'); }
  });
};

// ── Tab: Blockaden ──
window.tuningRender_blockaden = function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  const agent = (agents||[]).find(a => a.id === agentId); if (!agent) return;
  api('GET', '/api/state/enable_confirmations').then(r => {
    const enabled = r && r.value === true;
    el.innerHTML = '<div class="panel" style="padding:16px;display:flex;flex-direction:column;gap:14px;">'
      + '<h3 style="margin:0;font-size:0.95rem;">🛡️ Schutz-Status für ' + agent.name + '</h3>'
      + '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;">'
      + '<div class="bs-card" style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:12px;"><div style="font-weight:600;font-size:0.8rem;margin-bottom:6px;">📁 Systemdateien</div><div style="font-size:0.7rem;color:rgba(255,255,255,0.6);line-height:1.6;">Geschützte Pfade:</div><div style="font-size:0.65rem;color:#f44;font-family:monospace;margin-top:4px;">src/gnom_hub/<br>config/<br>.env<br>run.sh<br>index.html</div></div>'
      + '<div class="bs-card" style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:12px;"><div style="font-weight:600;font-size:0.8rem;margin-bottom:6px;">⚠️ Gefährliche Patterns</div><div style="font-size:0.65rem;color:#ffa500;font-family:monospace;">rm -rf<br>os.system()<br>subprocess.*<br>eval() / exec()</div></div>'
      + '<div class="bs-card" style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:12px;"><div style="font-weight:600;font-size:0.8rem;margin-bottom:6px;">🐚 Shell-Schutz</div><div style="font-size:0.65rem;color:rgba(255,255,255,0.6);">'
      + (agent.role === 'general' ? '<span style="color:#f44;">GeneralAG: KEINE Shell-Befehle</span>' : '<span style="color:#0f0;">Whitelist aktiv</span>')
      + '</div></div>'
      + '<div class="bs-card" style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:12px;"><div style="font-weight:600;font-size:0.8rem;margin-bottom:6px;">🔒 Workspace</div><div style="font-size:0.65rem;color:var(--accent);font-family:monospace;">gnom_workspace/default/</div></div>'
      + '</div>'
      + '<div class="panel" style="padding:12px;border:1px solid ' + (enabled ? '#f44' : '#0f0') + ';border-radius:8px;background:rgba(255,255,255,0.02);"><div style="display:flex;justify-content:space-between;align-items:center;"><div><div style="font-weight:600;font-size:0.85rem;margin-bottom:4px;">🛑 Bestätigungs-Modus</div><div style="font-size:0.7rem;color:rgba(255,255,255,0.5);">Legt fest ob gefährliche Aktionen manuell bestätigt werden müssen</div><div style="font-size:0.65rem;color:' + (enabled ? '#f44' : '#0f0') + ';margin-top:4px;">Status: <b>' + (enabled ? 'AKTIV — Aktionen müssen bestätigt werden' : 'DEAKTIVIERT — Auto-Approve') + '</b></div></div><button onclick="tuningToggleConfirmations(' + (enabled ? 'false' : 'true') + ')" style="padding:8px 16px;font-size:0.8rem;font-weight:700;background:' + (enabled ? 'rgba(0,200,100,0.15)' : 'rgba(255,50,50,0.15)') + ';border:1px solid ' + (enabled ? 'rgba(0,200,100,0.4)' : 'rgba(255,50,50,0.4)') + ';color:' + (enabled ? '#0f0' : '#f44') + ';border-radius:6px;cursor:pointer;">' + (enabled ? 'Deaktivieren' : 'Aktivieren') + '</button></div></div>'
      + '</div>';
  }).catch(() => { el.innerHTML = '<div class="panel" style="padding:16px;color:rgba(255,255,255,0.3);">Lade Blockaden...</div>'; });
};

window.tuningToggleConfirmations = function(enable) {
  api('POST', '/admin/config', {key: 'enable_confirmations', value: enable}).then(r => {
    if (r && r.status === 'ok') { toast(enable ? 'Bestätigungen AKTIVIERT' : 'Bestätigungen DEAKTIVIERT', enable ? 'warning' : 'success'); tuningRender_blockaden(window._tuningAgentId); }
    else { toast('Fehler', 'error'); }
  });
};

// ── Tab: Tools ──
window.tuningRender_tools = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  const agent = (agents||[]).find(a => a.id === agentId); if (!agent) return;
  el.innerHTML = '<div style="color:rgba(255,255,255,0.3);padding:20px;text-align:center;">Lade Tools...</div>';
  let profile = {};
  try { profile = await api('GET', '/agents/' + agentId + '/profile') || {}; } catch(e){}
  const tools = profile.tools || [];
  const allTools = [
    {key:'read_file', icon:'📄', label:'Read', desc:'Dateien lesen'},
    {key:'write_file', icon:'✏️', label:'Write', desc:'Dateien schreiben'},
    {key:'run_command', icon:'⚡', label:'Run', desc:'Shell-Befehle'},
    {key:'war_room_chat', icon:'💬', label:'@Job', desc:'Chat/Delegieren'},
    {key:'browser', icon:'🌐', label:'Browser', desc:'Playwright'},
    {key:'generate_image', icon:'🎨', label:'Image', desc:'Bilder erstellen'},
    {key:'crawl_url', icon:'🕷️', label:'Crawl', desc:'Web crawlen'},
    {key:'evolve', icon:'🧬', label:'Evolve', desc:'Selbst verbessern'},
    {key:'sys_cmd', icon:'🔧', label:'SysCmd', desc:'Systembefehle'},
    {key:'desktop_action', icon:'🖥️', label:'Desktop', desc:'Maus/Tastatur'},
    {key:'screenshot', icon:'📸', label:'Screen', desc:'Screenshots'},
    {key:'create_agent', icon:'🤖', label:'Agent+', desc:'Neue Agenten'},
  ];
  let html = '<div class="panel" style="padding:16px;"><h3 style="margin:0 0 10px 0;font-size:0.95rem;">🔧 Tools & Capabilities <span style="font-size:0.65rem;color:rgba(255,255,255,0.3);">— Klick zum Togglen</span></h3>';
  html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:6px;">';
  allTools.forEach(t => {
    const has = tools.includes(t.key);
    html += '<div onclick="tuningToggleTool(\'' + agentId + '\',\'' + t.key + '\')" style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:rgba(255,255,255,0.02);border:1px solid ' + (has ? 'rgba(57,255,20,0.3)' : 'rgba(255,255,255,0.06)') + ';border-radius:6px;cursor:pointer;transition:all 0.2s;" onmouseover="this.style.background=\'rgba(255,255,255,0.05)\'" onmouseout="this.style.background=\'rgba(255,255,255,0.02)\'" title="' + t.desc + '">';
    html += '<span style="font-size:1rem;">' + t.icon + '</span>';
    html += '<span style="font-size:0.75rem;color:' + (has ? '#39ff14' : 'rgba(255,255,255,0.35)') + ';">' + t.label + '</span>';
    html += '<span style="margin-left:auto;font-size:0.8rem;">' + (has ? '✅' : '⬜') + '</span>';
    html += '</div>';
  });
  html += '</div>';
  html += '<div style="font-size:0.6rem;color:rgba(255,255,255,0.25);margin-top:12px;">LLM: ' + (profile.llm_provider||'–') + ' / ' + (profile.llm_model||'–') + ' — Toggles nur temporär (Session)</div></div>';
  el.innerHTML = html;
};

window.tuningToggleTool = async function(agentId, toolKey) {
  const r = await api('POST', '/agents/' + agentId + '/tools/toggle', {tool: toolKey});
  if (r && r.status === 'ok') {
    toast(toolKey + (r.enabled ? ' ✅ aktiviert' : ' ❌ deaktiviert'), 'success');
    tuningRender_tools(agentId);
  } else { toast('Fehler beim Togglen', 'error'); }
};

// ── Tab: Verhalten (Sliders) ──
window.tuningRender_tuning = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  const agent = (agents||[]).find(a => a.id === agentId); if (!agent) return;
  let sliders = {};
  try { sliders = await api('GET', '/agents/' + agentId + '/sliders') || {}; } catch(e){}

  const isSystem = ['general','soul','watchdog','security'].includes(agent.role);
  const sliderDefs = [
    {id:'personality',    label:'Personality',    vals:{1:'Formal',2:'Semi-formal',3:'Balanced',4:'Casual',5:'Very Casual'}},
    {id:'creativity',     label:'Creativity',     vals:{1:'Conservative',2:'Focused',3:'Balanced',4:'Creative',5:'Wild'}},
    {id:'risk_tolerance', label:'Risk Tolerance', vals:{1:'Very Cautious',2:'Cautious',3:'Balanced',4:'Bold',5:'Very Bold'}},
    {id:'response_style', label:'Response Style', vals:{1:'Very Concise',2:'Concise',3:'Balanced',4:'Detailed',5:'Very Detailed'}},
    {id:'memory_strength',label:'Memory Strength',vals:{1:'Minimal',2:'Low',3:'Standard',4:'Strong',5:'Maximum'}},
  ];
  if (isSystem) {
    sliderDefs.push({id:'obedience', label:'Obedience', vals:{1:'Blindly Follows',2:'Strongly Follows',3:'Balanced',4:'Cautious',5:'Highly Autonomous'}});
  }

  let html = '<div class="panel" style="padding:16px;display:flex;flex-direction:column;gap:14px;">';
  html += '<h3 style="margin:0;font-size:0.95rem;">🎚️ Verhaltenseinstellungen <span style="font-size:0.65rem;font-weight:400;color:rgba(255,255,255,0.3);">— JSON-basiert (config/agents/' + agent.name + '.json)</span></h3>';
  sliderDefs.forEach(sl => {
    const sv = sliders[sl.id];
    const val = sv && sv.value ? sv.value : 3;
    html += '<div style="display:flex;flex-direction:column;gap:3px;">';
    html += '<div style="display:flex;justify-content:space-between;font-size:0.75rem;"><span>' + sl.label + '</span><span id="tlbl-' + sl.id + '" style="font-weight:600;">' + sl.vals[val] + '</span></div>';
    html += '<input type="range" id="tsl-' + sl.id + '" min="1" max="5" value="' + val + '" style="width:100%;" oninput="document.getElementById(\'tlbl-' + sl.id + '\').textContent={\'1\':\'' + sl.vals[1] + '\',\'2\':\'' + sl.vals[2] + '\',\'3\':\'' + sl.vals[3] + '\',\'4\':\'' + sl.vals[4] + '\',\'5\':\'' + sl.vals[5] + '\'}[this.value]">';
    html += '</div>';
  });
  html += '<button onclick="tuningSaveBehavior(\'' + agentId + '\')" style="padding:8px;font-size:0.8rem;font-weight:700;background:rgba(0,200,100,0.15);border:1px solid rgba(0,200,100,0.3);color:#0f0;border-radius:6px;cursor:pointer;">💾 Verhalten speichern</button>';
  html += '<div id="tmsg-behavior" style="font-size:0.65rem;color:rgba(255,255,255,0.3);text-align:center;"></div>';
  html += '</div>';
  el.innerHTML = html;
};

window.tuningSaveBehavior = async function(agentId) {
  const s = {
    personality: parseInt(document.getElementById('tsl-personality')?.value || 3),
    creativity: parseInt(document.getElementById('tsl-creativity')?.value || 3),
    risk_tolerance: parseInt(document.getElementById('tsl-risk_tolerance')?.value || 3),
    response_style: parseInt(document.getElementById('tsl-response_style')?.value || 3),
    memory_strength: parseInt(document.getElementById('tsl-memory_strength')?.value || 3),
  };
  const obed = document.getElementById('tsl-obedience');
  if (obed) s.obedience = parseInt(obed.value || 3);
  const r = await api('PUT', '/agents/' + agentId + '/sliders', s);
  const msg = document.getElementById('tmsg-behavior');
  if (r && r.status === 'ok') { if (msg) { msg.textContent='✓ Gespeichert (JSON)'; msg.style.color='#0f0'; setTimeout(()=>msg.textContent='',2000); } }
  else { if (msg) { msg.textContent='Fehler'; msg.style.color='#f00'; } }
};

// ── Tab: Presets ──
window.tuningRender_presets = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  el.innerHTML = '<div style="color:rgba(255,255,255,0.3);padding:20px;text-align:center;">Lade Presets...</div>';
  let settings = {}, llm = {}, presets = [];
  try { settings = await api('GET', '/agents/' + agentId + '/settings') || {}; } catch(e){}
  try { llm = await api('GET', '/llm/agents') || {}; } catch(e){}
  try { presets = await api('GET', '/presets') || []; } catch(e){}

  let html = '<div class="panel" style="padding:16px;display:flex;flex-direction:column;gap:14px;">';
  html += '<h3 style="margin:0;font-size:0.95rem;">💾 Presets <span style="font-size:0.65rem;color:rgba(255,255,255,0.3);">— Konfiguration speichern & laden</span></h3>';

  // Save current as preset
  html += '<div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:12px;">';
  html += '<div style="flex:1;min-width:150px;"><label style="font-size:0.7rem;display:block;margin-bottom:2px;">Preset-Name</label><input id="tpreset-name" placeholder="z.B. Web Development" style="width:100%;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.12);color:#fff;border-radius:4px;padding:6px;font-size:0.75rem;"></div>';
  html += '<div style="flex:2;min-width:200px;"><label style="font-size:0.7rem;display:block;margin-bottom:2px;">Beschreibung</label><input id="tpreset-desc" placeholder="Kurze Beschreibung..." style="width:100%;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.12);color:#fff;border-radius:4px;padding:6px;font-size:0.75rem;"></div>';
  html += '<div><button onclick="tuningSavePreset()" style="padding:6px 16px;font-size:0.75rem;font-weight:700;background:rgba(0,200,100,0.15);border:1px solid rgba(0,200,100,0.3);color:#0f0;border-radius:6px;cursor:pointer;white-space:nowrap;">💾 Speichern</button></div>';
  html += '</div>';

  // Preset list
  html += '<div style="display:flex;flex-direction:column;gap:6px;">';
  html += '<div style="font-size:0.7rem;color:rgba(255,255,255,0.5);">Gespeicherte Presets (' + presets.length + ')</div>';
  if (!presets.length) {
    html += '<div style="color:rgba(255,255,255,0.2);padding:20px;text-align:center;">Keine Presets vorhanden</div>';
  } else {
    presets.forEach(p => {
      html += '<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:6px;">';
      html += '<div style="flex:1;min-width:0;"><div style="font-size:0.8rem;font-weight:600;">' + escapeHtml(p.name) + '</div><div style="font-size:0.65rem;color:rgba(255,255,255,0.4);">' + escapeHtml(p.description||'').substring(0,100) + '</div></div>';
      html += '<button onclick="tuningLoadPreset(\'' + p.file + '\')" style="padding:5px 12px;font-size:0.7rem;font-weight:700;background:rgba(0,150,255,0.15);border:1px solid rgba(0,150,255,0.3);color:#0af;border-radius:4px;cursor:pointer;">📥 Laden</button>';
      html += '</div>';
    });
  }
  html += '</div></div>';
  el.innerHTML = html;
};

window.tuningSavePreset = async function() {
  const name = document.getElementById('tpreset-name')?.value?.trim();
  const desc = document.getElementById('tpreset-desc')?.value?.trim();
  if (!name || !desc) { toast('Name und Beschreibung erforderlich', 'warning'); return; }
  const r = await api('POST', '/presets/save', {name, description: desc});
  if (r && r.status === 'success') {
    toast('Preset "' + name + '" gespeichert', 'success');
    tuningRender_presets(window._tuningAgentId);
  } else { toast('Fehler beim Speichern', 'error'); }
};

window.tuningLoadPreset = async function(file) {
  if (!confirm('Preset laden? Überschreibt aktuelle Einstellungen aller Agenten.')) return;
  const r = await api('POST', '/presets/load', {file});
  if (r && r.status === 'ok') {
    toast('Preset geladen: ' + r.name, 'success');
    tuningRender_presets(window._tuningAgentId);
  }   else { toast('Fehler beim Laden', 'error'); }
};

// ── Tab: Bake ──
window.tuningRender_bake = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  el.innerHTML = '<div style="color:rgba(255,255,255,0.3);padding:20px;text-align:center;">Lade...</div>';
  let presets = [];
  try { presets = await api('GET', '/presets') || []; } catch(e){}
  let html = '<div class="panel" style="padding:16px;display:flex;flex-direction:column;gap:16px;">';
  html += '<h3 style="margin:0;font-size:0.95rem;">🏭 SuperGNOM backen <span style="font-size:0.65rem;color:rgba(255,255,255,0.3);">— Standalone exportieren</span></h3>';
  html += '<p style="font-size:0.7rem;color:rgba(255,255,255,0.5);margin:0;">Erzeugt ein lauffähiges, portables Gnom-Hub Paket mit allen 8 Agenten, API-Key, Workspace und Presets.</p>';

  // Name
  html += '<div><label style="font-size:0.7rem;display:block;margin-bottom:3px;">SuperGNOM-Name</label><input id="tbake-name" placeholder="z.B. meine_agenten" style="width:100%;max-width:400px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.12);color:#fff;border-radius:4px;padding:8px;font-size:0.8rem;"></div>';

  // Preset-Auswahl
  html += '<div><label style="font-size:0.7rem;display:block;margin-bottom:3px;">Preset (optional)</label><select id="tbake-preset" style="width:100%;max-width:400px;background:rgba(0,0,0,0.3);color:#fff;border:1px solid rgba(255,255,255,0.12);border-radius:4px;padding:8px;font-size:0.8rem;">';
  html += '<option value="">— Kein Preset (aktuellen Zustand backen) —</option>';
  presets.forEach(p => { html += '<option value="' + p.file + '">' + escapeHtml(p.name) + '</option>'; });
  html += '</select></div>';

  // Template
  html += '<div><label style="font-size:0.7rem;display:block;margin-bottom:3px;">Template</label><select id="tbake-tpl" style="width:100%;max-width:400px;background:rgba(0,0,0,0.3);color:#fff;border:1px solid rgba(255,255,255,0.12);border-radius:4px;padding:8px;font-size:0.8rem;">';
  html += '<option value="chat">Chat (Standard)</option><option value="minimal">Minimal (nur API)</option><option value="full">Full (Chat + Workspace)</option></select></div>';

  // Features
  html += '<div style="display:flex;flex-direction:column;gap:6px;">';
  html += '<label style="font-size:0.7rem;">Features</label>';
  html += '<div style="display:flex;gap:12px;flex-wrap:wrap;">';
  html += '<label style="font-size:0.7rem;display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="checkbox" id="tbake-api" checked> API-Key einbacken</label>';
  html += '<label style="font-size:0.7rem;display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="checkbox" id="tbake-run" checked> run.sh / run.bat</label>';
  html += '<label style="font-size:0.7rem;display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="checkbox" id="tbake-ws"> Workspace kopieren</label>';
  html += '</div></div>';

  // Bake Button
  html += '<button onclick="tuningDoBake()" style="padding:10px 20px;font-size:0.85rem;font-weight:700;background:rgba(255,150,0,0.2);border:1px solid rgba(255,150,0,0.5);color:#fa0;border-radius:8px;cursor:pointer;max-width:300px;transition:all 0.2s;" onmouseover="this.style.background=\'rgba(255,150,0,0.3)\'" onmouseout="this.style.background=\'rgba(255,150,0,0.2)\'">🔥 JETZT BACKEN</button>';
  html += '<div id="tbake-result" style="font-size:0.7rem;min-height:20px;"></div>';
  html += '</div>';
  el.innerHTML = html;
};

window.tuningDoBake = async function() {
  const name = document.getElementById('tbake-name')?.value?.trim();
  const preset = document.getElementById('tbake-preset')?.value;
  const tpl = document.getElementById('tbake-tpl')?.value || 'chat';
  const withKey = document.getElementById('tbake-api')?.checked;
  const resultEl = document.getElementById('tbake-result');
  if (!name) { toast('Bitte Namen eingeben', 'warning'); return; }
  resultEl.innerHTML = '<span style="color:#fa0;">⏳ Backe... das kann 10-30 Sekunden dauern.</span>';
  resultEl.style.color = '#fa0';
  try {
    const body = {name, template: tpl, embed_api_key: withKey};
    if (preset) body.preset_file = preset;
    const r = await api('POST', '/admin/bake', body);
    if (r && r.status === 'ok') {
      resultEl.innerHTML = '<span style="color:#0f0;">✅ Gebacken! Ordner: <b style="font-family:monospace;">' + r.path + '</b></span>';
      resultEl.style.color = '#0f0';
      toast('SuperGNOM gebacken!', 'success');
    } else {
      resultEl.innerHTML = '<span style="color:#f44;">❌ Fehler: ' + (r?.error || 'Unbekannt') + '</span>';
      resultEl.style.color = '#f44';
    }
  } catch(e) {
    resultEl.innerHTML = '<span style="color:#f44;">❌ Fehler: ' + e.message + '</span>';
    resultEl.style.color = '#f44';
  }
};

window.generateAutoPreset = async function() {
  const desc = document.getElementById('auto-preset-desc').value.trim();
  if (!desc) {
    toast('Bitte gib eine Beschreibung ein!', 'warning');
    return;
  }
  
  const clarifySec = document.getElementById('auto-preset-clarify-section');
  const previewSec = document.getElementById('auto-preset-preview-section');
  const saveBtn = document.getElementById('btn-save-generated-preset');
  const genBtn = document.getElementById('btn-generate-preset');
  const answerInput = document.getElementById('auto-preset-answer');
  
  let answer = null;
  if (clarifySec && clarifySec.style.display === 'flex') {
    answer = answerInput.value.trim();
  }
  
  genBtn.innerText = '⏳ Generiere...';
  genBtn.disabled = true;
  
  try {
    const res = await api('POST', '/admin/presets/generate', { description: desc, answer: answer || undefined });
    if (!res) {
      toast('Fehler bei der Preset-Generierung.', 'error');
      return;
    }
    
    if (res.status === 'clarify') {
      if (clarifySec) clarifySec.style.display = 'flex';
      document.getElementById('auto-preset-question-text').innerText = res.question;
      if (previewSec) previewSec.style.display = 'none';
      if (saveBtn) saveBtn.style.display = 'none';
      toast('Gegenfrage erhalten. Bitte beantworten!', 'info');
    } else if (res.status === 'success' && res.preset) {
      if (clarifySec) clarifySec.style.display = 'none';
      if (previewSec) previewSec.style.display = 'flex';
      if (saveBtn) saveBtn.style.display = 'block';
      
      const preset = res.preset;
      window.lastGeneratedPreset = preset;
      
      document.getElementById('auto-preset-preview-name').innerText = preset.name;
      document.getElementById('auto-preset-preview-desc').innerText = preset.description;
      
      let rolesTxt = '';
      for (const [agent, prompt] of Object.entries(preset.prompt_modifier || {})) {
        rolesTxt += `[${agent}]:\n${prompt}\n\n`;
      }
      document.getElementById('auto-preset-preview-details').innerText = rolesTxt;
      toast('Preset erfolgreich generiert!', 'success');
    } else {
      toast('Fehler: ' + (res.message || 'LLM konnte kein Preset erstellen.'), 'error');
    }
  } catch (e) {
    console.error("Preset generation failed", e);
    toast('Verbindungsfehler: ' + e.message, 'error');
  } finally {
    genBtn.innerText = '✨ Generieren';
    genBtn.disabled = false;
  }
};

window.saveGeneratedPreset = async function() {
  const preset = window.lastGeneratedPreset;
  if (!preset) return;
  
  const saveBtn = document.getElementById('btn-save-generated-preset');
  saveBtn.innerText = '⏳ Speichere...';
  saveBtn.disabled = true;
  
  try {
    const res = await api('POST', '/admin/presets/save_custom', preset);
    if (res && res.status === 'success') {
      toast('Preset erfolgreich gespeichert!', 'success');
      
      // Reset inputs & hide sections
      document.getElementById('auto-preset-desc').value = '';
      const ansInput = document.getElementById('auto-preset-answer');
      if (ansInput) ansInput.value = '';
      
      const clarifySec = document.getElementById('auto-preset-clarify-section');
      if (clarifySec) clarifySec.style.display = 'none';
      
      const previewSec = document.getElementById('auto-preset-preview-section');
      if (previewSec) previewSec.style.display = 'none';
      
      saveBtn.style.display = 'none';
      window.lastGeneratedPreset = null;
      
      // Reload presets dropdown (but do not switch to the new preset automatically)
      if (typeof loadActivePreset === 'function') {
        await loadActivePreset();
      }
    } else {
      toast('Fehler beim Speichern des Presets.', 'error');
    }
  } catch (e) {
    console.error("Failed to save preset", e);
    toast('Fehler beim Speichern: ' + e.message, 'error');
  } finally {
    saveBtn.innerText = '💾 Speichern';
    saveBtn.disabled = false;
  }
};

// ── Agent Behavior Modal Handlers ──

window.openAgentBehaviorModal = async function(agentId) {
  const modal = document.getElementById('agent-behavior-modal');
  if (!modal) return;
  modal.style.display = 'flex';
  
  const meta = window.getAgentMeta(agentId);
  const avatarUrl = window.getAgentAvatarUrl(agentId);
  document.getElementById('modal-agent-avatar').src = avatarUrl;
  document.getElementById('modal-agent-name').innerText = meta.name;
  document.getElementById('modal-agent-role').innerText = meta.desc;
  
  try {
    const settings = await api('GET', `/agents/${agentId}/settings`);
    if (settings) {
      document.getElementById('modal-opt-personality').value = settings.personality ?? 3;
      document.getElementById('modal-opt-response').value = settings.response_style ?? 3;
      document.getElementById('modal-opt-memory').value = settings.memory_strength ?? 3;
      document.getElementById('modal-opt-creativity').value = settings.creativity ?? 3;
      document.getElementById('modal-opt-risk').value = settings.risk_tolerance ?? 3;
      document.getElementById('modal-opt-custom-prompt').value = settings.custom_prompt ?? '';
      
      updateModalSliderLabel('personality', settings.personality ?? 3);
      updateModalSliderLabel('response', settings.response_style ?? 3);
      updateModalSliderLabel('memory', settings.memory_strength ?? 3);
      updateModalSliderLabel('creativity', settings.creativity ?? 3);
      updateModalSliderLabel('risk', settings.risk_tolerance ?? 3);
    }
  } catch (err) {
    console.error('Error loading settings in modal:', err);
  }
  
  const saveBtn = document.getElementById('modal-save-behavior-btn');
  if (saveBtn) {
    saveBtn.onclick = () => saveModalAgentBehavior(agentId);
  }
  
  const clearMemBtn = document.getElementById('modal-clear-memories-btn');
  if (clearMemBtn) {
    clearMemBtn.onclick = () => clearModalMemory(agentId);
  }
  
  const addMemBtn = document.getElementById('modal-add-mem-btn');
  if (addMemBtn) {
    addMemBtn.onclick = () => addModalMemory(agentId);
  }
  
  const searchInput = document.getElementById('modal-search-mem');
  if (searchInput) {
    searchInput.value = '';
    searchInput.oninput = (e) => searchModalMem(agentId, e.target.value);
  }
  
  loadModalAgentMemory(agentId);
};

window.closeAgentBehaviorModal = function() {
  const modal = document.getElementById('agent-behavior-modal');
  if (modal) modal.style.display = 'none';
};

window.updateModalSliderLabel = function(type, val) {
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
  const el = document.getElementById('modal-label-' + type);
  if (el) el.innerText = txt;
};

async function saveModalAgentBehavior(agentId) {
  const personality = parseInt(document.getElementById('modal-opt-personality').value);
  const response_style = parseInt(document.getElementById('modal-opt-response').value);
  const memory_strength = parseInt(document.getElementById('modal-opt-memory').value);
  const creativity = parseInt(document.getElementById('modal-opt-creativity').value);
  const risk_tolerance = parseInt(document.getElementById('modal-opt-risk').value);
  const custom_prompt = document.getElementById('modal-opt-custom-prompt').value;
  try {
    const res = await api('PUT', `/agents/${agentId}/settings`, { personality, response_style, memory_strength, creativity, risk_tolerance, custom_prompt });
    if (res !== null) {
      toast('Einstellungen erfolgreich gespeichert!', 'success');
      closeAgentBehaviorModal();
    } else {
      toast('Fehler beim Speichern der Einstellungen.', 'error');
    }
  } catch (err) {
    toast('Fehler beim Speichern: ' + err.message, 'error');
  }
}

async function loadModalAgentMemory(agentId) {
  const el = document.getElementById('modal-mem-list');
  if (!el) return;
  const mems = await api('GET', `/agents/${agentId}/memory`);
  renderModalMemories(el, mems, agentId);
}

async function searchModalMem(agentId, q) {
  const el = document.getElementById('modal-mem-list');
  if (!el) return;
  if (!q) return loadModalAgentMemory(agentId);
  const all = await api('GET', `/agents/${agentId}/memory`);
  const filtered = (all || []).filter(m => (m.content || '').toLowerCase().includes(q.toLowerCase()));
  renderModalMemories(el, filtered, agentId);
}

function renderModalMemories(el, mems, agentId) {
  if (!mems || !mems.length) { el.innerHTML = '<div class="empty">Keine Einträge im Gedächtnis.</div>'; return; }
  el.innerHTML = mems.map(m => {
    const d = m.timestamp ? new Date(m.timestamp).toLocaleString() : '';
    return `<div class="mem-item" id="modal-mem-${m.id}" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
      <div class="mem-head" style="display: flex; justify-content: space-between; font-size: 0.68rem; color: var(--text-dim); margin-bottom: 6px;">
        <span>${d}</span>
        <div style="display: flex; gap: 6px;">
          <button onclick="editModalMem('${m.id}', '${agentId}')" style="cursor: pointer; background: transparent; border: none; color: var(--cyan); padding: 0 4px;">✏</button>
          <button onclick="deleteModalMem('${m.id}', '${agentId}')" style="cursor: pointer; background: transparent; border: none; color: var(--red); padding: 0 4px;">✕</button>
        </div>
      </div>
      <div class="mem-content" id="modal-mc-${m.id}" style="font-size: 0.82rem; color: #fff; line-height: 1.4; white-space: pre-wrap; word-break: break-word;">${escapeHtml(m.content)}</div>
    </div>`;
  }).join('');
}

async function addModalMemory(agentId) {
  const ta = document.getElementById('modal-new-mem');
  const c = ta.value.trim();
  if (!c) return;
  await api('POST', '/memory', { agent_id: agentId, content: c });
  ta.value = '';
  loadModalAgentMemory(agentId);
  toast('Erinnerung hinzugefügt', 'success');
}

window.editModalMem = function(id, agentId) {
  const el = document.getElementById('modal-mc-' + id);
  const old = el.innerText;
  el.innerHTML = `<textarea id="modal-ed-${id}" style="width: 100%; min-height: 60px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.12); color: #fff; border-radius: 6px; padding: 6px; font-size: 0.8rem; outline: none; resize: vertical;">${old}</textarea>
    <div style="margin-top:6px;display:flex;gap:6px;justify-content:flex-end">
      <button onclick="loadModalAgentMemory('${agentId}')" style="padding: 3px 8px; font-size: 0.72rem; cursor: pointer;">Abbrechen</button>
      <button class="btn-primary" onclick="saveModalMem('${id}', '${agentId}')" style="padding: 3px 8px; font-size: 0.72rem; cursor: pointer;">Speichern</button>
    </div>`;
};

window.saveModalMem = async function(id, agentId) {
  const c = document.getElementById('modal-ed-' + id).value;
  await api('PUT', `/memory/${id}`, { content: c });
  loadModalAgentMemory(agentId);
  toast('Erinnerung aktualisiert', 'success');
};

window.deleteModalMem = async function(id, agentId) {
  if (!confirm('Erinnerung löschen?')) return;
  await api('DELETE', `/memory/${id}`);
  toast('Erinnerung gelöscht', 'info');
  loadModalAgentMemory(agentId);
};

async function clearModalMemory(agentId) {
  if (!confirm('Wirklich das gesamte Gedächtnis des Agenten löschen?')) return;
  await api('DELETE', `/agents/${agentId}/memory`);
  toast('Gedächtnis vollständig gelöscht', 'warning');
  loadModalAgentMemory(agentId);
}


/* ═══════════════════════════════════════════
   GNOM-HUB — Phase 6: DAG / Workflow Engine & Observability Visualizer
   ═══════════════════════════════════════════ */

var workflowPollInterval = null;
var activeWorkflowId = null;

function stopWorkflowPolling() {
  if (workflowPollInterval) {
    clearInterval(workflowPollInterval);
    workflowPollInterval = null;
  }
}

window.showWorkflowsView = async function() {
  if (typeof trackView === 'function') trackView('workflows');
  stopDashboardPolling();
  selectedId = null;

  document.getElementById('content').innerHTML = `
    <style>
      @keyframes pulse-border {
        from { box-shadow: 0 0 4px rgba(0, 229, 255, 0.2); border-color: rgba(0, 229, 255, 0.4); }
        to { box-shadow: 0 0 12px rgba(0, 229, 255, 0.6); border-color: rgba(0, 229, 255, 1); }
      }
      @keyframes dash {
        to {
          stroke-dashoffset: -20;
        }
      }
    </style>
    <div class="panel" id="workflows-panel" style="height:calc(100vh - 91px); box-sizing:border-box; display:flex; flex-direction:column; padding:15px 20px; background:rgba(10, 15, 30, 0.4); border:1px solid var(--glass-border); overflow:hidden;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px; flex-shrink:0;">
        <h2 style="margin:0; font-size:0.95rem; font-weight:600; border:none; letter-spacing:0.5px; display:flex; align-items:center; gap:8px;">
          <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--cyan); box-shadow:0 0 8px var(--cyan);"></span>
          Workflow Engine & Observability
        </h2>
      </div>

      <!-- Main Columns -->
      <div style="flex:1; display:grid; grid-template-columns:300px 1fr; gap:20px; overflow:hidden; min-height:0;">
        
        <!-- Left: Workflows List & Observability summary -->
        <div style="display:flex; flex-direction:column; gap:15px; height:100%; overflow:hidden;">
          <div style="flex:1; display:flex; flex-direction:column; background:rgba(0,0,0,0.15); border:1px solid rgba(255,255,255,0.04); border-radius:12px; padding:12px; overflow:hidden;">
            <h3 style="margin:0 0 10px 0; font-size:0.85rem; color:#fff; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Workflows</h3>
            <div id="workflows-list-container" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:8px; scrollbar-width:thin;">
              <div class="empty">Lade Workflows...</div>
            </div>
          </div>
          
          <!-- Observability Bento Stats (Summary) -->
          <div style="height:220px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:12px; padding:12px; display:flex; flex-direction:column; gap:8px; flex-shrink:0;">
            <h3 style="margin:0; font-size:0.85rem; color:#fff; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">System Latenz</h3>
            <div id="obs-summary-container" style="font-size:0.8rem; display:flex; flex-direction:column; gap:8px; color:var(--text-dim);">
              <div class="empty">Lade Telemetrie...</div>
            </div>
          </div>
        </div>

        <!-- Right: DAG Canvas & Detailed Metrics -->
        <div style="display:flex; flex-direction:column; gap:20px; height:100%; overflow:hidden;">
          <!-- SVG DAG Panel -->
          <div style="flex:1.5; background:rgba(0,0,0,0.25); border:1px solid rgba(255,255,255,0.05); border-radius:12px; padding:15px; display:flex; flex-direction:column; overflow:hidden; position:relative;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-shrink:0;">
              <h3 id="dag-workflow-title" style="margin:0; font-size:0.85rem; color:#fff; font-weight:600;">Wähle einen Workflow links</h3>
              <div id="dag-legend" style="display:flex; gap:8px; font-size:0.68rem;">
                <span style="color:#888;"><span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#555; margin-right:3px;"></span>Pending</span>
                <span style="color:#00e5ff;"><span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#00e5ff; margin-right:3px; animation:pulse-glow 1.5s infinite;"></span>Running</span>
                <span style="color:#10b981;"><span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#10b981; margin-right:3px;"></span>Completed</span>
                <span style="color:#ef4444;"><span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#ef4444; margin-right:3px;"></span>Failed</span>
              </div>
            </div>
            
            <div id="dag-canvas-container" style="flex:1; width:100%; overflow:auto; background:rgba(0,0,0,0.1); border-radius:8px; border:1px solid rgba(255,255,255,0.02); display:flex; align-items:center; justify-content:center;">
              <div style="color:var(--text-dim); font-style:italic;">Kein Workflow ausgewählt</div>
            </div>
          </div>

          <!-- Bottom detailed metrics -->
          <div style="flex:1; display:grid; grid-template-columns:1fr 1fr; gap:20px; overflow:hidden; min-height:0;">
            <!-- Agent latency breakdown -->
            <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:12px; padding:12px; display:flex; flex-direction:column; overflow:hidden;">
              <h3 style="margin:0 0 8px 0; font-size:0.8rem; color:#fff; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Agenten Latenzen</h3>
              <div id="obs-agent-breakdown" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:6px; scrollbar-width:thin;">
                <div class="empty">Keine Telemetrie</div>
              </div>
            </div>
            
            <!-- Capability metrics -->
            <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:12px; padding:12px; display:flex; flex-direction:column; overflow:hidden;">
              <h3 style="margin:0 0 8px 0; font-size:0.8rem; color:#fff; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Capability Latenzen</h3>
              <div id="obs-capability-breakdown" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:6px; scrollbar-width:thin;">
                <div class="empty">Keine Telemetrie</div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  `;

  await loadWorkflowsViewData();
  stopWorkflowPolling();
  workflowPollInterval = setInterval(refreshWorkflowsView, 3000);
};

async function loadWorkflowsViewData() {
  const workflows = await api('GET', '/workflows');
  const listContainer = document.getElementById('workflows-list-container');
  
  if (!listContainer) return;
  
  if (!workflows || workflows.length === 0) {
    listContainer.innerHTML = '<div class="empty">Keine Workflows registriert</div>';
    return;
  }
  
  // Render workflows list
  listContainer.innerHTML = workflows.map(w => {
    let badgeColor = '#555';
    if (w.status === 'running') badgeColor = '#00e5ff';
    else if (w.status === 'completed') badgeColor = '#10b981';
    else if (w.status === 'failed') badgeColor = '#ef4444';
    
    const isSelected = activeWorkflowId === w.id;
    const timeStr = new Date(w.created_at * 1000).toLocaleTimeString();
    
    return `
      <div onclick="selectWorkflow('${w.id}')" style="padding:10px; background:${isSelected ? 'rgba(0,229,255,0.08)' : 'rgba(255,255,255,0.02)'}; border:${isSelected ? '1px solid var(--accent)' : '1px solid rgba(255,255,255,0.05)'}; border-radius:8px; cursor:pointer; transition:var(--transition); display:flex; flex-direction:column; gap:4px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#fff; font-size:0.85rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:180px;">${escapeHtml(w.name)}</strong>
          <span style="font-size:0.65rem; font-weight:bold; color:${badgeColor}; border:1px solid ${badgeColor}33; border-radius:4px; padding:1px 4px; text-transform:uppercase;">${w.status}</span>
        </div>
        <div style="font-size:0.72rem; color:var(--text-muted); display:flex; justify-content:space-between;">
          <span>Start: ${timeStr}</span>
          ${w.completed_at ? `<span>Dauer: ${(w.completed_at - w.created_at).toFixed(1)}s</span>` : ''}
        </div>
      </div>
    `;
  }).join('');

  // Load telemetry metrics
  const obs = await api('GET', '/observability/metrics');
  const summaryContainer = document.getElementById('obs-summary-container');
  const agentBreakdown = document.getElementById('obs-agent-breakdown');
  const capBreakdown = document.getElementById('obs-capability-breakdown');

  if (obs) {
    if (summaryContainer) {
      const summary = obs.workflows_summary || { total_count: 0, completed_count: 0, failed_count: 0, avg_duration_s: 0 };
      summaryContainer.innerHTML = `
        <div style="display:flex; justify-content:space-between;"><span>Gesamt Workflows:</span><strong style="color:#fff;">${summary.total_count}</strong></div>
        <div style="display:flex; justify-content:space-between;"><span>Erfolgreich:</span><strong style="color:#10b981;">${summary.completed_count}</strong></div>
        <div style="display:flex; justify-content:space-between;"><span>Fehlgeschlagen:</span><strong style="color:#ef4444;">${summary.failed_count}</strong></div>
        <div style="display:flex; justify-content:space-between; border-top:1px solid rgba(255,255,255,0.05); padding-top:6px; margin-top:4px;"><span>Ø Workflow-Laufzeit:</span><strong style="color:var(--cyan);">${summary.avg_duration_s.toFixed(1)}s</strong></div>
      `;
    }

    if (agentBreakdown) {
      if (!obs.agents || obs.agents.length === 0) {
        agentBreakdown.innerHTML = '<div class="empty">Keine Metriken vorhanden</div>';
      } else {
        agentBreakdown.innerHTML = obs.agents.map(a => {
          const successPercent = (a.success_rate * 100).toFixed(0);
          return `
            <div style="padding:6px 10px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:6px; display:flex; justify-content:space-between; align-items:center; font-size:0.75rem;">
              <strong style="color:#fff; text-transform:capitalize;">${a.agent_name.replace('ag', 'AG')}</strong>
              <div style="display:flex; gap:12px; color:var(--text-dim);">
                <span>Queue: <strong style="color:#fff;">${a.avg_queue_wait_ms.toFixed(0)}ms</strong></span>
                <span>Exec: <strong style="color:#fff;">${a.avg_exec_time_ms.toFixed(0)}ms</strong></span>
                <span style="color:${a.success_rate >= 0.9 ? '#10b981' : '#f59e0b'};">Ok: ${successPercent}%</span>
              </div>
            </div>
          `;
        }).join('');
      }
    }

    if (capBreakdown) {
      if (!obs.capabilities || obs.capabilities.length === 0) {
        capBreakdown.innerHTML = '<div class="empty">Keine Metriken vorhanden</div>';
      } else {
        capBreakdown.innerHTML = obs.capabilities.map(c => {
          const successPercent = (c.success_rate * 100).toFixed(0);
          return `
            <div style="padding:6px 10px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:6px; display:flex; justify-content:space-between; align-items:center; font-size:0.75rem;">
              <strong style="color:#fff; text-transform:uppercase; letter-spacing:0.5px;">${c.capability}</strong>
              <div style="display:flex; gap:12px; color:var(--text-dim);">
                <span>Queue: <strong style="color:#fff;">${c.avg_queue_wait_ms.toFixed(0)}ms</strong></span>
                <span>Exec: <strong style="color:#fff;">${c.avg_exec_time_ms.toFixed(0)}ms</strong></span>
                <span style="color:${c.success_rate >= 0.9 ? '#10b981' : '#f59e0b'};">Ok: ${successPercent}%</span>
              </div>
            </div>
          `;
        }).join('');
      }
    }
  }

  // Draw current active workflow DAG
  if (activeWorkflowId) {
    drawWorkflowDAG(activeWorkflowId);
  }
}

window.selectWorkflow = function(id) {
  activeWorkflowId = id;
  loadWorkflowsViewData();
};

async function drawWorkflowDAG(workflowId) {
  const canvas = document.getElementById('dag-canvas-container');
  const title = document.getElementById('dag-workflow-title');
  if (!canvas) return;

  let wf;
  try {
    wf = await api('GET', `/workflows/${workflowId}`);
  } catch (e) {
    canvas.innerHTML = '<div class="empty" style="color:var(--error);">Fehler beim Laden des Workflows</div>';
    return;
  }

  if (!wf) {
    canvas.innerHTML = '<div class="empty">Workflow nicht gefunden</div>';
    return;
  }

  title.textContent = `Workflow: ${wf.name}`;

  const tasks = wf.tasks || [];
  if (tasks.length === 0) {
    canvas.innerHTML = '<div class="empty">Keine Tasks in diesem Workflow</div>';
    return;
  }

  // Topological sorting / levels calculation
  const levels = {};
  const tasksMap = {};
  tasks.forEach(t => {
    tasksMap[t.task_id] = t;
  });

  function getLevel(taskId) {
    if (levels[taskId] !== undefined) return levels[taskId];
    const t = tasksMap[taskId];
    if (!t || !t.depends_on || t.depends_on.length === 0) {
      levels[taskId] = 0;
      return 0;
    }
    let maxDep = 0;
    t.depends_on.forEach(dep => {
      maxDep = Math.max(maxDep, getLevel(dep));
    });
    levels[taskId] = maxDep + 1;
    return levels[taskId];
  }

  tasks.forEach(t => getLevel(t.task_id));

  // Layout levels
  const levelGroups = {};
  tasks.forEach(t => {
    const lvl = levels[t.task_id];
    if (!levelGroups[lvl]) levelGroups[lvl] = [];
    levelGroups[lvl].push(t.task_id);
  });

  const nodeWidth = 150;
  const nodeHeight = 70;
  const levelSpacing = 240;
  const rowSpacing = 110;

  const positions = {};
  const svgWidth = (Object.keys(levelGroups).length * levelSpacing) + 100;
  let maxRows = 0;
  
  Object.keys(levelGroups).forEach(lvl => {
    maxRows = Math.max(maxRows, levelGroups[lvl].length);
  });
  const svgHeight = (maxRows * rowSpacing) + 100;

  // Determine positions
  Object.keys(levelGroups).forEach(lvl => {
    const group = levelGroups[lvl];
    const x = 50 + lvl * levelSpacing;
    const levelHeight = group.length * rowSpacing;
    const startY = (svgHeight - levelHeight) / 2 + 20;

    group.forEach((taskId, index) => {
      positions[taskId] = {
        x: x,
        y: startY + index * rowSpacing
      };
    });
  });

  // Start SVG markup
  let svg = `<svg width="${Math.max(svgWidth, 600)}" height="${Math.max(svgHeight, 350)}" style="overflow:visible; font-family:'Inter', sans-serif;">`;
  
  // Define markers for arrows
  svg += `
    <defs>
      <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 2 L 10 5 L 0 8 z" fill="rgba(255,255,255,0.2)" />
      </marker>
      <marker id="arrow-active" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 2 L 10 5 L 0 8 z" fill="var(--cyan)" />
      </marker>
    </defs>
  `;

  // Draw connections (lines) first so they render behind nodes
  tasks.forEach(t => {
    const toPos = positions[t.task_id];
    if (t.depends_on && t.depends_on.length > 0) {
      t.depends_on.forEach(depId => {
        const fromPos = positions[depId];
        if (fromPos && toPos) {
          const x1 = fromPos.x + nodeWidth;
          const y1 = fromPos.y + nodeHeight / 2;
          const x2 = toPos.x;
          const y2 = toPos.y + nodeHeight / 2;

          const isActive = t.status === 'running' || t.status === 'completed';
          const stroke = isActive ? 'var(--cyan)' : 'rgba(255,255,255,0.12)';
          const marker = isActive ? 'url(#arrow-active)' : 'url(#arrow)';
          const dash = t.status === 'running' ? 'stroke-dasharray="5,5" animation="dash 1s linear infinite"' : '';

          svg += `
            <path d="M ${x1} ${y1} C ${(x1+x2)/2} ${y1}, ${(x1+x2)/2} ${y2}, ${x2} ${y2}" 
                  fill="none" 
                  stroke="${stroke}" 
                  stroke-width="${isActive ? 2 : 1.5}" 
                  marker-end="${marker}"
                  ${dash} />
          `;
        }
      });
    }
  });

  // Draw nodes
  tasks.forEach(t => {
    const pos = positions[t.task_id];
    if (!pos) return;

    let border = 'rgba(255,255,255,0.08)';
    let bg = 'rgba(255,255,255,0.02)';
    let textGlow = '';
    let statusClass = '';

    if (t.status === 'running') {
      border = 'var(--cyan)';
      bg = 'rgba(0,229,255,0.08)';
      textGlow = 'text-shadow:0 0 8px var(--cyan);';
      statusClass = 'animation: pulse-border 1.5s infinite alternate;';
    } else if (t.status === 'completed') {
      border = '#10b981';
      bg = 'rgba(16,185,129,0.06)';
    } else if (t.status === 'failed') {
      border = '#ef4444';
      bg = 'rgba(239,68,68,0.08)';
    }

    svg += `
      <g transform="translate(${pos.x}, ${pos.y})">
        <!-- Background glass card -->
        <rect width="${nodeWidth}" height="${nodeHeight}" rx="8" 
              fill="${bg}" stroke="${border}" stroke-width="1.5"
              style="backdrop-filter:blur(8px); ${statusClass}" />

        <!-- Task name -->
        <text x="12" y="24" fill="#fff" font-size="0.82rem" font-weight="700" style="${textGlow}">${escapeHtml(t.task_id)}</text>
        
        <!-- Capability badge -->
        <text x="12" y="42" fill="rgba(255,255,255,0.5)" font-size="0.68rem" font-weight="500" font-family="monospace">${escapeHtml(t.capability.toUpperCase())}</text>

        <!-- Status & Duration -->
        <text x="12" y="58" fill="rgba(255,255,255,0.4)" font-size="0.62rem">
          Status: <tspan fill="${t.status === 'completed' ? '#10b981' : t.status === 'failed' ? '#ef4444' : '#fff'}">${t.status.toUpperCase()}</tspan>
        </text>
      </g>
    `;
  });

  svg += `</svg>`;
  canvas.innerHTML = svg;
}

async function refreshWorkflowsView() {
  if (!document.getElementById('workflows-panel')) {
    stopWorkflowPolling();
    return;
  }
  await loadWorkflowsViewData();
}
