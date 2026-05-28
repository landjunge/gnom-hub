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
  selectedId = null;
  document.getElementById('content').innerHTML = `
    <div class="panel" id="dashboard-panel">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px;">
        <button class="btn-primary" onclick="showWarRoom()" style="padding: 2px 6px; font-size:0.75rem;">◀ Zurück</button>
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
              <span style="color:var(--accent); font-weight:600;">${c.from}</span>
              <span style="color:rgba(255,255,255,0.6);">💬 fragt/antwortet</span>
              <span style="color:var(--accent); font-weight:600;">${c.to}</span>
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
            <div style="font-size: 0.9rem; color: #fff; line-height: 1.4;">${el.value}</div>
          </div>
        `;
      }).join('');
    }
  }
}

async function showLLMConfig() {
  selectedId = null;
  document.getElementById('content').innerHTML = `
    <div class="panel" id="llm-panel" style="padding:12px 15px;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px;">
        <button class="btn-primary" onclick="showWarRoom()">◀ Zurück</button>
        <h2 style="margin:0; font-size:0.95rem; font-weight:600; border:none; letter-spacing:0.5px;">LLM Configuration</h2>
      </div>
      <div style="display:flex; gap: 15px; flex-wrap: wrap;">
        <div style="flex:1; min-width: 250px; background:var(--bg-card); padding:12px; border-radius:var(--radius); border:1px solid rgba(255,255,255,0.1); display:flex; flex-direction:column; gap:10px;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <h3 style="margin:0; font-size:0.9rem;">API Keys</h3>
              <label style="display:flex; align-items:center; gap:5px; font-size:0.75rem; color:var(--text-muted); cursor:pointer;">
                <input type="checkbox" id="toggle-show-keys" onchange="toggleKeysVisibility(this.checked)" style="width:12px; height:12px; accent-color:var(--primary);">
                <span>Keys anzeigen</span>
              </label>
            </div>
            <p style="font-size:0.75rem; color:var(--text-muted); margin-bottom:4px;">Füge alle API-Keys ein (ein Key pro Zeile)</p>
            <textarea id="llm-keys-input" rows="1" style="width:100%; margin-bottom:6px; background:var(--bg); border:1px solid rgba(255,255,255,0.2); color:white; padding:4px 6px; border-radius:4px; font-size:0.8rem; height:28px; line-height:1.4; resize:none; overflow-y:hidden;" placeholder="Einfügen per Cmd+V"></textarea>
            <div style="display:flex; gap:6px; margin-bottom:6px;">
              <button class="btn-primary" id="save-keys-only-btn" onclick="saveKeysOnly()" style="flex:1;">Speichern</button>
              <button class="btn-primary" id="save-keys-btn" onclick="saveAndTestKeys()" style="flex:1;">Testen & Speichern</button>
            </div>
            <div id="llm-keys-status" style="margin-top:6px; font-size:0.8rem; max-height:65px; overflow-y:auto; display:flex; flex-direction:column; gap:3px;"></div>
          </div>
          
          <div style="display:flex; flex-direction:column; gap:8px; border-top:1px solid rgba(255,255,255,0.1); padding-top:8px;">
            <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:4px;">
              <h3 style="margin:0; font-size:0.9rem;">Agent Gang (Preset)</h3>
              <select id="preset-select" onchange="changePreset(this.value)" style="width:100%; background:rgba(0,0,0,0.3); color:var(--text); border:1px solid rgba(255,255,255,0.15); border-radius:6px; padding:6px 8px; font-size:0.8rem; outline:none; cursor:pointer;">
                <option value="Web Development">💻 Web Development</option>
                <option value="Graphic Design">🎨 Graphic Design</option>
                <option value="Audio Production">🎵 Audio Production</option>
                <option value="Video Production">🎬 Video Production</option>
                <option value="Content Creation">✍️ Content Creation</option>
                <option value="Research & Analysis">🔍 Research & Analysis</option>
              </select>
            </div>
            <div style="display:flex; flex-direction:column; gap:6px; border-top:1px dashed rgba(255,255,255,0.05); padding-top:6px;">
              <h3 style="margin:0; font-size:0.9rem;">Language</h3>
              <div style="display:flex; gap:6px;">
                <button class="btn-primary" id="lang-btn-de" onclick="setSystemLanguage('de')" style="flex:1;">DE</button>
                <button class="btn-primary" id="lang-btn-en" onclick="setSystemLanguage('en')" style="flex:1;">EN</button>
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:8px; margin-top:2px;">
              <input type="checkbox" id="auto-deploy-checkbox" onchange="toggleFtpAutoDeploy(this.checked)" style="width:14px; height:14px; cursor:pointer;">
              <label for="auto-deploy-checkbox" style="font-size:0.8rem; cursor:pointer;">Auto-Deploy Webseiten</label>
            </div>
          </div>
          <div id="system-info-panel" style="font-size:0.75rem; padding:8px 10px; border-radius:6px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); color:var(--text-muted);">
            Loading System Info...
          </div>
        </div>
        <div style="flex:2; min-width: 400px; background:var(--bg-card); padding:15px; border-radius:var(--radius); border:1px solid rgba(255,255,255,0.1);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; gap:8px; flex-wrap:wrap;">
            <h3 style="margin:0; font-size:0.9rem; flex-shrink:0;">Routing</h3>
            <div style="display:flex; gap:4px; align-items:center; flex-shrink:0; flex-wrap:wrap;">
              <button class="btn-primary" onclick="autoRouteAllAgents()" style="white-space:nowrap;">⚡ Auto-Route</button>
              <button id="save-agents-btn" class="btn-primary" onclick="saveAgentLLMs()" style="white-space:nowrap;">Speichern</button>
            </div>
          </div>
          
          <div id="routing-progress-banner" style="display:none; align-items:center; justify-content:space-between; margin-bottom:10px; padding:8px 12px; background:rgba(0,229,255,0.08); border:1px solid rgba(0,229,255,0.2); border-radius:8px; font-size:0.8rem; transition:all 0.3s ease;">
            <div style="display:flex; align-items:center; gap:8px;">
              <div id="routing-banner-spinner" style="width:14px; height:14px; border:2px solid rgba(0,229,255,0.3); border-top-color:#00e5ff; border-radius:50%; animation:spin 1s linear infinite;"></div>
              <span id="routing-progress-text" style="color:rgba(255,255,255,0.95); font-weight:500;">Auto-routing läuft: Mappe Agenten zu optimalen LLMs...</span>
            </div>
            <div id="routing-progress-percentage" style="color:rgba(255,255,255,0.7); font-family:monospace; font-weight:bold;">0%</div>
          </div>
          
          <div id="llm-agents-list" style="margin-bottom:0; max-height:250px; overflow-y:auto; padding-right:8px; scrollbar-width:thin;">Loading Agents...</div>

          <div style="margin-top: 10px; display: flex; justify-content: flex-end;">
            <button id="save-agents-btn-bottom" class="btn-primary" onclick="saveAgentLLMs()" style="width: 100%;">Routing Speichern</button>
          </div>
          
          <div id="routing-insights-panel" style="margin-top:15px; display:none;"></div>
        </div>
      </div>
    </div>
  `;
  loadLLMConfig();
}

async function showHelpPage() {
  selectedId = null;
  document.getElementById('content').innerHTML = `
    <div class="panel" id="help-panel" style="display:flex; flex-direction:column; gap:12px; height:100%; box-sizing:border-box; padding:12px 15px;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px;">
        <button class="btn-primary" onclick="showWarRoom()" style="padding: 2px 6px; font-size:0.75rem;">◀ Zurück</button>
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
        <div style="width:100px; font-weight:bold; overflow:hidden; text-overflow:ellipsis;">${a.name}</div>
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
  await loadLanguageState();
  await loadSystemInfoState();
  await loadFtpAutoDeployState();
  await loadActivePreset();

  const keysRes = await api('GET', '/llm/keys');
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

  const agentsRes = await api('GET', '/agents');
  const llmAgentsRes = await api('GET', '/llm/agents');
  
  const providers = ['deepseek', 'openrouter', 'openai', 'anthropic', 'gemini', 'mistral', 'lokal'];
  let models = {
    'deepseek': ['deepseek-chat', 'deepseek-reasoner'],
    'openrouter': ['deepseek/deepseek-v4-flash:free', 'qwen/qwen3-coder:free', 'meta-llama/llama-3.3-70b-instruct:free'],
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

window.updateAgentCaps = function(aName) {
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
  const btn = document.getElementById('save-keys-only-btn');
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
    const agentsList = window.llmAgentsListGlobal || [];
    let agentConfig = {};
    agentsList.forEach(a => {
      const p = document.getElementById(`prov-${a.name}`)?.value;
      const m = document.getElementById(`mod-${a.name}`)?.value;
      if (p && m) {
        agentConfig[a.name.toLowerCase()] = { provider: p, model: m };
      }
    });
    if (Object.keys(agentConfig).length > 0) {
      await api('POST', '/llm/agents', agentConfig);
    } else {
      await api('POST', '/llm/auto_assign');
    }

    globalKeys = testedKeys;
    renderKeyStatus(testedKeys);
    loadLLMConfig();
    
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
  
  const agentsList = window.llmAgentsListGlobal || [];
  let agentConfig = {};
  agentsList.forEach(a => {
    const p = document.getElementById(`prov-${a.name}`)?.value;
    const m = document.getElementById(`mod-${a.name}`)?.value;
    if (p && m) {
      agentConfig[a.name.toLowerCase()] = { provider: p, model: m };
    }
  });
  if (Object.keys(agentConfig).length > 0) {
    await api('POST', '/llm/agents', agentConfig);
  } else {
    await api('POST', '/llm/auto_assign');
  }
  
  globalKeys = testedKeys;
  renderKeyStatus(testedKeys);
  loadLLMConfig();
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

window.assignFreeModels = async function() {
  const agents = window.llmAgentsListGlobal || [];
  if (!agents.length) return;

  const availableModels = await api('GET', '/llm/available_models');
  const workingModels = (availableModels && availableModels.openrouter) || [];

  if (!workingModels.length) {
    alert('Keine Free-Modelle verfügbar.');
    return;
  }

  const agentPriority = {
    'coderag': 1,
    'researcherag': 2,
    'writerag': 3,
    'editorag': 4,
    'generalag': 5,
    'securityag': 6,
    'soulag': 7,
    'watchdogag': 8
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

  const sorted = [...workingModels].sort((a, b) => modelScore(b) - modelScore(a));
  const sortedAgents = [...agents].sort((a, b) => {
    const pa = agentPriority[a.name.toLowerCase()] || 99;
    const pb = agentPriority[b.name.toLowerCase()] || 99;
    return pa - pb;
  });

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

  const agentPriority = {
    'coderag': 1,
    'researcherag': 2,
    'writerag': 3,
    'editorag': 4,
    'generalag': 5,
    'securityag': 6,
    'soulag': 7,
    'watchdogag': 8
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

  const sorted = [...workingLocalModels].sort((a, b) => modelScore(b) - modelScore(a));
  const sortedAgents = [...agents].sort((a, b) => {
    const pa = agentPriority[a.name.toLowerCase()] || 99;
    const pb = agentPriority[b.name.toLowerCase()] || 99;
    return pa - pb;
  });

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
  const p = document.getElementById(`prov-${aName}`).value;
  const m = document.getElementById(`mod-${aName}`).value;
  const lamp = document.getElementById(`lamp-${aName}`);
  
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
