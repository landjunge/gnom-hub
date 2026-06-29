/* ═══════════════════════════════════════════
   GNOM-HUB — Bento Dashboard & LLM Config
   ═══════════════════════════════════════════ */

// ── Custom SVG-Icons (line-art, agent-color) ────────────────────────────────
// Jeder Agent bekommt ein eigenes Icon (keine Emoji). Die SVGs sind 24×24
// line-art, mit currentColor färbbar — also passen sie sich der Frozen-
// Color des Agenten an (cyan für System, orange für Worker).
window.AgentIcons = {
  // System-Agenten (cyan)
  soulag:     `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.5c-3.6 0-6.5 2.9-6.5 6.5 0 2.3 1.2 4.3 3 5.5v3.5a1 1 0 0 0 1 1h5a1 1 0 0 0 1-1v-3.5c1.8-1.2 3-3.2 3-5.5 0-3.6-2.9-6.5-6.5-6.5z"/><path d="M9.5 19h5M10 21.5h4"/><circle cx="12" cy="9" r="1.2" fill="currentColor"/></svg>`,
  watchdogag: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M3 12h3M18 12h3M12 3v3M12 18v3"/></svg>`,
  generalag:  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 17l4-4 3 3 8-8M14 8l4 0 0 4"/><path d="M3 21h18"/></svg>`,
  securityag: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.5l8 3.5v6c0 4.5-3.4 8.6-8 10-4.6-1.4-8-5.5-8-10v-6l8-3.5z"/><path d="M9 12l2 2 4-4"/></svg>`,
  // Worker-Agenten (orange)
  writerag:   `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3l5 5-9 9H5v-5l9-9z"/><path d="M13 4l5 5"/></svg>`,
  coderag:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6l-5 6 5 6M16 6l5 6-5 6M14 4l-4 16"/></svg>`,
  researcherag:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/></svg>`,
  editorag:   `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12l4 4 14-14"/><path d="M14 5h5v5"/></svg>`,
};
// Fallback-Icon (für unbekannte Namen)
window.AgentIcons.default = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>`;
// Helper: gibt das passende Icon-SVG für einen Agentennamen zurück
window.agentIcon = function(name) {
  if (!name) return window.AgentIcons.default;
  const key = name.toLowerCase();
  return window.AgentIcons[key] || window.AgentIcons.default;
};

// ── i18n (Sprachumschaltung DE/EN) ────────────────────────────────────────────
// Single source of truth für UI-Strings und Help-Texte. Die aktive Sprache
// wird in window.appLang gehalten (Default: 'de'). Per t('key') greifen
// Funktionen und Renderer auf die Übersetzung zu.
window.I18N = {
  de: {
    // Header
    'header.back':        'Einen Schritt im Browserverlauf zurückgehen.',
    'header.workspace':   'Zeigt das Arbeitsverzeichnis des Schwarms mit allen generierten Dateien, Scripts und UI-Entwürfen.',
    'header.dashboard':   'Öffnet das Bento-Grid-Systemdashboard zur Überwachung von Agenten-Status, Token-Budgets und Antwortzeiten.',
    'header.workflows':   'Öffnet das Workflow-Dashboard mit der SVG-basierten Visualisierung des DAGs und Observability-Latenzen.',
    'header.llm':         'Öffnet die LLM-Einstellungen, um API-Keys einzutragen, Provider-Presets zu wählen und Agenten-Charaktere anzupassen.',
    'header.tuning':      'Öffnet den Agent Inspector mit Persönlichkeits-Reglern, Custom Prompts und Statistiken.',
    'header.help':        'Öffnet das Help Center mit der vollständigen Bedienungsanleitung und Erklärungen der Agenten.',
    'header.save':        'Sichert den aktuellen Hub-Zustand, Einstellungen und Verlauf global.',
    'header.clean':       'Löscht alle Daten: Chat, Workspace, Tokens, Soul-Memory, Workflows. Hub startet neu.',
    'header.lang':        'Wechselt die UI-Sprache. Hilfe-Texte und Mouseover-Erklärungen werden ebenfalls übersetzt.',
    // Tuning tabs
    'tab.prompt':         'System-Prompt und Custom-Suffix für diesen Agenten. Änderungen wirken sich auf alle zukünftigen Antworten aus.',
    'tab.soul':           'Langzeit-Fakten des Agenten aus dem SoulAG-Gedächtnis. Hier siehst du, was der Agent über dich, Projekte und Präferenzen "weiß".',
    'tab.blockaden':      'Übersicht aller Sicherheits-Blockaden für diesen Agenten. Zeigt Grund, Auslöser und Snippet — und ob eine Aktion explizit vom User autorisiert wurde.',
    'tab.tools':          '12 interne Tools, die dieser Agent nutzen darf (read_file, write_file, run_command, …). Klick auf eine Kachel togglet die Berechtigung.',
    'tab.modules':        'Erweiterbare Module: Webhooks (HTTP-Callbacks), Plugins (Custom Code) und Skills (gekaufte/eingespielte Fähigkeiten).',
    'tab.verhalten':      '5 Persönlichkeits-Slider: Kreativität, Präzision, Geschwindigkeit, kritisches Denken, Gehorsam. Steuert wie der Agent Antworten formuliert.',
    'tab.presets':        'Speichern/Laden kompletter Agent-Konfigurationen als JSON-Presets. Nützlich um Profile für verschiedene Aufgabentypen zu haben.',
    'tab.bake':           'Erstellt ein standalone "SuperGNOM"-Paket aus diesem Agenten inkl. API-Key, Prompt, Sliders und run.sh/run.bat. Portable & ohne Hub lauffähig.',
    // Sliders (Verhalten tab)
    'slider.creativity':  'Kreativität: Wie stark der Agent von Standardlösungen abweicht. Hoch = mehr ungewöhnliche Ideen.',
    'slider.precision':   'Präzision: Sorgfalt bei Fakten und Berechnungen. Hoch = weniger Halluzinationen.',
    'slider.speed':       'Geschwindigkeit: Wie schnell der Agent antwortet. Hoch = kürzere, direktere Antworten.',
    'slider.critical':    'Kritisches Denken: Hinterfragt Aufgaben und schlägt Verbesserungen vor. Hoch = mehr Eigeninitiative.',
    'slider.obedience':   'Gehorsam: Folgt Anweisungen genau. Hoch = minimale Eigeninterpretation, Niedrig = freier.',
    // Modules
    'mod.webhook.title':  '🔗 Webhooks',
    'mod.webhook.desc':   'HTTP-Callbacks die bei Agent-Events ausgelöst werden (z.B. POST an deinen Server wenn ein Task fertig ist). Konfiguriere URL, Methode und Event-Filter.',
    'mod.plugin.title':   '🧩 Plugins',
    'mod.plugin.desc':    'Eigener Code (Python), der die Agent-Fähigkeiten erweitert. Wird im Hub-Sandbox ausgeführt. Drop-in: .py in plugins/ ablegen, Hot-Reload.',
    'mod.skill.title':    '🎯 Skills',
    'mod.skill.desc':     'Gekaufte oder selbst-trainierte Skill-Pakete mit eigener Wissensbasis. Funktionieren wie zusätzliche Tools, aber mit großem Kontext.',
    // Lang switcher
    'lang.de':            'Deutsch',
    'lang.en':            'English',
    // Mouseover fallback
    'help.fallback':      'Interaktives Element. Details folgen.',
  },
  en: {
    'header.back':        'Go one step back in the browser history.',
    'header.workspace':   'Shows the swarm working directory with all generated files, scripts and UI drafts.',
    'header.dashboard':   'Opens the Bento grid system dashboard for monitoring agent status, token budgets and response times.',
    'header.workflows':   'Opens the workflow dashboard with the SVG-based DAG visualisation and observability latencies.',
    'header.llm':         'Opens LLM settings to paste API keys, pick provider presets and adjust agent characters.',
    'header.tuning':      'Opens the Agent Inspector with personality sliders, custom prompts and statistics.',
    'header.help':        'Opens the Help Center with the full user manual and agent explanations.',
    'header.save':        'Persists the current hub state, settings and history globally.',
    'header.clean':       'Deletes all data: chat, workspace, tokens, soul memory, workflows. Hub restarts.',
    'header.lang':        'Switches the UI language. Help texts and mouseover explanations are also translated.',
    'tab.prompt':         'System prompt and custom suffix for this agent. Changes affect all future answers.',
    'tab.soul':           'Long-term facts from the agent’s SoulAG memory. See what the agent "knows" about you, projects and preferences.',
    'tab.blockaden':      'Overview of all safety blockades for this agent. Shows reason, trigger and snippet — and whether an action was explicitly authorised by the user.',
    'tab.tools':          '12 internal tools this agent may use (read_file, write_file, run_command, …). Click a tile to toggle the permission.',
    'tab.modules':        'Extensible modules: webhooks (HTTP callbacks), plugins (custom code) and skills (bought or trained capabilities).',
    'tab.verhalten':      '5 personality sliders: creativity, precision, speed, critical thinking, obedience. Shapes how the agent answers.',
    'tab.presets':        'Save/load complete agent configurations as JSON presets. Useful for task-type profiles.',
    'tab.bake':           'Builds a standalone "SuperGNOM" package from this agent: API key, prompt, sliders and run.sh/run.bat. Portable, runs without the hub.',
    'slider.creativity':  'Creativity: how far the agent deviates from standard solutions. High = more unusual ideas.',
    'slider.precision':   'Precision: care with facts and calculations. High = fewer hallucinations.',
    'slider.speed':       'Speed: how fast the agent answers. High = shorter, more direct responses.',
    'slider.critical':    'Critical thinking: questions tasks and suggests improvements. High = more initiative.',
    'slider.obedience':   'Obedience: follows instructions literally. High = minimal interpretation, low = freer.',
    'mod.webhook.title':  '🔗 Webhooks',
    'mod.webhook.desc':   'HTTP callbacks fired on agent events (e.g. POST to your server when a task is done). Configure URL, method and event filter.',
    'mod.plugin.title':   '🧩 Plugins',
    'mod.plugin.desc':    'Custom code (Python) that extends agent capabilities. Runs in the hub sandbox. Drop-in: put .py into plugins/, hot-reload.',
    'mod.skill.title':    '🎯 Skills',
    'mod.skill.desc':     'Bought or self-trained skill packages with their own knowledge base. Work like extra tools but with rich context.',
    'lang.de':            'German',
    'lang.en':            'English',
    'help.fallback':      'Interactive element. Details to follow.',
  },
};

// Active UI language. Persisted in localStorage so it survives reloads.
window.appLang = (function () {
  try {
    const stored = localStorage.getItem('gnomhub.lang');
    if (stored === 'de' || stored === 'en') return stored;
  } catch (_) { /* localStorage may be blocked */ }
  return 'de';
})();
window.setAppLang = function (lang) {
  if (lang !== 'de' && lang !== 'en') return;
  window.appLang = lang;
  try { localStorage.setItem('gnomhub.lang', lang); } catch (_) {}
  // Trigger a custom event so other modules (showbox.js, dashboard.js) can refresh.
  document.dispatchEvent(new CustomEvent('appLangChanged', { detail: { lang } }));
  const btn = document.getElementById('btn-lang');
  if (btn) btn.textContent = lang === 'de' ? 'DE' : 'EN';
};

// Toggle-Helper für den Header-Sprach-Button.
window.toggleAppLang = function () {
  window.setAppLang(window.appLang === 'de' ? 'en' : 'de');
};

// Initial-Update des Sprach-Buttons beim Laden.
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('btn-lang');
  if (btn) btn.textContent = window.appLang === 'de' ? 'DE' : 'EN';
});
window.t = function (key, fallback) {
  const dict = window.I18N[window.appLang] || window.I18N.de;
  if (Object.prototype.hasOwnProperty.call(dict, key)) return dict[key];
  if (fallback !== undefined) return fallback;
  const de = window.I18N.de;
  if (Object.prototype.hasOwnProperty.call(de, key)) return de[key];
  return key;
};
// Resolve the right help text for an element depending on current language.
window.helpTextFor = function (el) {
  if (!el) return { title: '', body: '' };
  const en = el.getAttribute('data-help-en');
  const de = el.getAttribute('data-help');
  if (window.appLang === 'en' && en) return { title: el.getAttribute('data-help-title-en') || el.getAttribute('data-help-title') || '', body: en };
  return { title: el.getAttribute('data-help-title') || '', body: de || en || '' };
};
// Auto-decorate an element with data-help from a translation key.
window.decorateHelp = function (el, titleKey, bodyKey, fallbackTitle, fallbackBody) {
  if (!el) return;
  const title = titleKey ? window.t(titleKey, fallbackTitle) : (fallbackTitle || '');
  const body  = bodyKey  ? window.t(bodyKey,  fallbackBody)  : (fallbackBody  || '');
  el.setAttribute('data-help-title', title);
  el.setAttribute('data-help', body);
};

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
      <div class="slider-group" style="margin-top:12px; padding:10px 14px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); border-radius:var(--radius);">
        <label style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px; font-weight:500;">
          <span>🛡️ Blockade-Level</span>
          <span id="blockade-level-label" style="color:var(--accent); font-weight:bold;">Keine</span>
        </label>
        <input type="range" id="blockade-level-slider" min="0" max="4" value="0" oninput="updateBlockadeLabel(this.value)" style="cursor:pointer; width:100%;">
        <div style="display:flex; justify-content:space-between; font-size:0.65rem; color:var(--text-dim); margin-top:2px;">
          <span>0 — Keine</span>
          <span>1 — Leicht</span>
          <span>2 — Mittel</span>
          <span>3 — Streng</span>
          <span>4 — Max</span>
        </div>
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
  await loadBlockadeLevel();
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

window.updateBlockadeLabel = function(val) {
  const v = parseInt(val);
  const labels = ['Keine (0)', 'Leicht (1)', 'Mittel (2)', 'Streng (3)', 'Max (4)'];
  const el = document.getElementById('blockade-level-label');
  if (el) el.innerText = labels[v] || v;
  api('PUT', '/api/admin/blockade-level', { level: v });
};

async function loadBlockadeLevel() {
  const slider = document.getElementById('blockade-level-slider');
  if (!slider) return;
  const res = await api('GET', '/api/admin/blockade-level');
  if (res && typeof res.level === 'number') {
    slider.value = res.level;
    updateBlockadeLabel(res.level);
  }
}

async function loadDashboardData() {
  const metrics = await api('GET', '/api/metrics');
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

// ====================================================================
// showLLMConfig() — LLM Configuration Page
// Self-contained function. Replaces the old 5-slider modal design.
// ====================================================================

// ====================================================================
// showLLMConfig() — LLM Configuration Page
// Self-contained: everything inline. No external helpers.
// ====================================================================
async function showLLMConfig() {
  if (typeof trackView === 'function') trackView('llm');
  if (typeof selectedId !== 'undefined') selectedId = null;

  // Drop any per-row save leftovers from a previous mount, but keep global
  // pending changes — they're owned by other modules too.
  delete window.llmPendingChanges?.agents__ephemeral;

  // ── Provider mapping is now registry-driven (see loadProviderRegistry)
  //    at the bottom of this file. No more hardcoded switch chain. ──
  const pvdOf = (s) => detectProviderByRegistry(s);

  // Make sure the registry is loaded before we render the selects. If the
  // fetch fails we still render with an empty list so the UI is usable.
  const reg = await loadProviderRegistry();
  const allProviders = reg.providers || [];

  // Render an agent table inside a card
  const renderAgentTable = (group, agents) => {
    const rows = agents.map(a => `
      <tr data-agent="${a}" data-group="${group}" style="border-bottom:1px solid rgba(255,255,255,0.04);">
        <td style="padding:6px; color:#eef1f6; font-weight:500;">${a}</td>
        <td style="padding:6px;">
          <select data-agent="${a}" data-field="provider" data-group="${group}" data-llm-svc="agent" style="background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.12); color:#eef1f6; border-radius:4px; padding:2px 6px; font-size:0.78rem;">
            <option value="">—</option>
          </select>
        </td>
        <td style="padding:6px;">
          <select data-agent="${a}" data-field="model" data-group="${group}" data-llm-svc="agent" style="background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.12); color:#eef1f6; border-radius:4px; padding:2px 6px; font-size:0.78rem; width:100%;">
            <option value="">— Provider wählen —</option>
          </select>
        </td>
        <td data-agent-caps-col="${a}" style="padding:6px; color:var(--text-dim); font-size:0.75rem;">—</td>
        <td data-agent-status-cell="${a}" style="padding:6px;"><span class="llm-status-dot" data-agent-status-dot="${a}" style="display:inline-block; width:10px; height:10px; border-radius:2px; background:#6b7a90;"></span> <span data-agent-status-text="${a}" style="font-size:0.7rem; color:var(--text-dim); margin-left:4px;">—</span></td>
        <td style="padding:6px; color:var(--text-dim); font-size:0.7rem;" data-agent-cap="${a}">—</td>
      </tr>`).join('');
    return `
      <div data-group="${group}" style="background:rgba(16,20,32,0.7); border:1px solid rgba(91,156,246,0.15); border-radius:12px; padding:12px;">
        <h3 style="margin:0 0 8px 0; font-size:0.9rem; color:#eef1f6; font-weight:600;">${group === 'system' ? 'System Agents' : 'Worker Agents'}</h3>
        <div style="display:flex; gap:4px; flex-wrap:wrap; margin-bottom:8px;">
          ${['Only Free Models','Local First','Cost Optimized','Balanced','Performance']
            .map(m => `<button class="btn-primary llm-mode-btn" data-group="${group}" data-mode="${m}" style="padding:3px 8px; font-size:0.7rem;">${m}</button>`).join('')}
        </div>
        <table style="width:100%; border-collapse:collapse; font-size:0.78rem;">
          <thead><tr style="text-align:left; color:var(--text-dim); font-size:0.65rem; text-transform:uppercase; letter-spacing:0.5px;">
            <th style="padding:4px 6px; border-bottom:1px solid rgba(255,255,255,0.08);">Agent</th>
            <th style="padding:4px 6px; border-bottom:1px solid rgba(255,255,255,0.08);">Provider</th>
            <th style="padding:4px 6px; border-bottom:1px solid rgba(255,255,255,0.08);">Model</th>
            <th style="padding:4px 6px; border-bottom:1px solid rgba(255,255,255,0.08);">Capabilities</th>
            <th style="padding:4px 6px; border-bottom:1px solid rgba(255,255,255,0.08);">Status</th>
            <th style="padding:4px 6px; border-bottom:1px solid rgba(255,255,255,0.08);">Caps (DB)</th>
          </tr></thead>
          <tbody id="llm-tbody-${group}">${rows}</tbody>
        </table>
      </div>`;
  };

  // Render a service card (Web Search or TTS) — provider select + model
  // select + API-key input + status badge.
  const renderServiceCard = (label, svc, defaultsById, allList, keyInputId) => {
    const opts = allList.map(p => `<option value="${p.id}">${p.display_name}</option>`).join('');
    return `
      <div data-svc-card="${svc}" style="background:rgba(16,20,32,0.7); border:1px solid rgba(91,156,246,0.15); border-radius:12px; padding:12px;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
          <h3 style="margin:0; font-size:0.9rem; color:#eef1f6; font-weight:600;">${label}</h3>
          <span data-svc-badge="${svc}" data-svc-badge-state="unknown" style="font-size:0.72rem; padding:3px 8px; border-radius:6px; border:1px solid rgba(255,255,255,0.08); background:rgba(0,0,0,0.25); color:var(--text-muted);">— pending —</span>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
          <div>
            <label style="font-size:0.7rem; color:var(--text-dim); display:block; margin-bottom:3px;">Provider</label>
            <select data-llm-svc="${svc}" data-svc-field="provider" style="width:100%; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.12); color:#eef1f6; border-radius:6px; padding:5px 8px; font-size:0.78rem;">
              <option value="">—</option>
              ${opts}
            </select>
          </div>
          <div>
            <label style="font-size:0.7rem; color:var(--text-dim); display:block; margin-bottom:3px;">Model</label>
            <select data-llm-svc="${svc}" data-svc-field="model" style="width:100%; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.12); color:#eef1f6; border-radius:6px; padding:5px 8px; font-size:0.78rem;">
              <option value="">— select provider —</option>
            </select>
          </div>
        </div>
        <div style="margin-top:8px;">
          <label style="font-size:0.7rem; color:var(--text-dim); display:block; margin-bottom:3px;">API-Key <span style="opacity:0.6;">(leer lassen, wenn bereits oben in den Keys hinterlegt)</span></label>
          <div style="display:flex; gap:6px;">
            <input type="password" data-llm-svc="${svc}" data-svc-field="key" id="${keyInputId}" placeholder="Paste key here…"
              style="flex:1; min-width:0; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.12); color:#eef1f6; border-radius:6px; padding:5px 8px; font-size:0.78rem; font-family:'JetBrains Mono',monospace;" />
            <button class="btn-primary" data-svc-test="${svc}" style="white-space:nowrap; font-size:0.72rem;">Test</button>
          </div>
          <div data-svc-status-line="${svc}" style="margin-top:4px; font-size:0.7rem; color:var(--text-dim); min-height:14px;"></div>
        </div>
      </div>`;
  };

  // ── Web Search / TTS providers (filtered by category OR cap) ──
  // Generalisten wie MiniMax/OpenAI/Gemini haben audio/web caps ohne primary
  // category = tts/web_search. Damit sie in den Dropdowns erscheinen, filtern
  // wir zusätzlich auf caps.
  const wsProviders = (reg.providers || []).filter(p =>
    p.category === 'web_search' || (p.caps || []).includes('web'));
  const ttsProviders = (reg.providers || []).filter(p =>
    p.category === 'tts' || (p.caps || []).includes('audio'));
  const wsDefaults = reg.defaults?.web_search || {};
  const ttsDefaults = reg.defaults?.tts || {};

  document.getElementById('content').innerHTML = `
    <div style="height:calc(100vh - 91px); box-sizing:border-box; display:flex; flex-direction:column; padding:15px 20px; gap:14px; overflow-y:auto; background:rgba(5,5,10,0.4);">
      <div style="background:rgba(16,20,32,0.7); border:1px solid rgba(91,156,246,0.15); border-radius:12px; padding:10px 12px;">
        <div style="display:flex; align-items:center; gap:6px;">
          <input id="llm-keys-input" type="text" placeholder="Paste keys: PROVIDER=sk-… (one per line)" style="flex:1; min-width:0; background:rgba(0,0,0,0.35); border:1px solid rgba(255,255,255,0.12); color:#eef1f6; border-radius:6px; padding:6px 8px; font-family:'JetBrains Mono',monospace; font-size:0.78rem; outline:none;" />
          <button class="btn-primary" id="llm-import-file-btn" style="white-space:nowrap;">📁 File</button>
          <input id="llm-file-input" type="file" accept=".txt,.md,.env,.json" style="display:none;" />
        </div>
        <div id="llm-status" style="margin-top:6px; font-size:0.7rem; color:var(--text-dim); min-height:12px;"></div>
      </div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px;">
        ${renderAgentTable('system', ['SoulAG','WatchdogAG','GeneralAG','SecurityAG'])}
        ${renderAgentTable('worker', ['WriterAG','CoderAG','ResearcherAG','EditorAG'])}
      </div>
      <div data-svc-section style="display:grid; grid-template-columns:1fr 1fr; gap:14px;">
        ${renderServiceCard('Web Search', 'web_search', wsDefaults, wsProviders, 'llm-svc-key-web_search')}
        ${renderServiceCard('TTS', 'tts', ttsDefaults, ttsProviders, 'llm-svc-key-tts')}
      </div>
      <div style="background:rgba(16,20,32,0.4); border:1px dashed rgba(91,156,246,0.15); border-radius:12px; padding:8px 12px; font-size:0.72rem; color:var(--text-dim); text-align:center;">
        Änderungen werden erst nach Klick auf <b style="color:#eef1f6;">Save</b> (Header oben rechts) dauerhaft gespeichert.
      </div>
    </div>`;

  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const status = (msg, c) => { const e = $('#llm-status'); if (e) { e.textContent = msg; e.style.color = c || 'var(--text-dim)'; } };

  // ── Known model lists per provider (mirrors llm_agents.py:FREE_MODELS + PAID_MODELS) ──
  const FREE_MODELS = {
    'openrouter': [
      'meta-llama/llama-3.3-70b-instruct:free',
      'qwen/qwen3-coder:free',
      'nousresearch/hermes-3-llama-3.1-405b:free',
      'google/gemma-4-31b-it:free',
      'meta-llama/llama-3.2-3b-instruct:free',
      'liquid/lfm-2.5-1.2b-instruct:free',
      'openai/gpt-oss-120b:free',
    ],
    'deepseek':  ['deepseek-chat', 'deepseek-reasoner'],
    'gemini':    ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.5-pro', 'gemini-2.0-flash-exp:free'],
    'groq':      ['llama-3.1-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
    'mistral':   ['mistral-small-latest', 'open-mistral-7b', 'open-mixtral-8x7b'],
    'kimi':      ['moonshot-v1-8k', 'moonshot-v1-32k'],
    'github':    ['gpt-4o-mini'],
    'lokal':     ['llama3.2:3b', 'llama3.2:1b', 'mistral:latest', 'gemma2:2b'],
  };
  const PAID_MODELS = {
    'openai':    ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'o1-mini', 'o1-preview'],
    'anthropic': ['claude-3-5-haiku-20241022', 'claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'],
    'minimax':   ['MiniMax-M3'],
  };

  // ── Populate agent provider dropdowns ──
  // Source of truth: providers that have at least one valid key in DB. Falls
  // back to the full registry if no keys are present (so the user can still
  // browse and select; we'll require a key before saving).
  const populateAgentProviders = (kdb) => {
    const valid = new Set(Object.values(kdb || {}).filter(k => k.valid && k.provider).map(k => k.provider));
    const fallback = allProviders.filter(p => p.category === 'llm' || p.category === 'other');
    const list = valid.size > 0
      ? Array.from(valid)
      : fallback.map(p => p.id);
    $$('select[data-llm-svc="agent"][data-field="provider"]').forEach(sel => {
      const cur = sel.value;
      sel.innerHTML = '<option value="">—</option>' + list.map(p => {
        const meta = registryProviderById(p);
        const label = meta ? meta.display_name : p;
        return `<option value="${p}">${label}</option>`;
      }).join('');
      if (list.includes(cur)) sel.value = cur;
    });
  };

  // ── Populate model <select> based on selected provider (FIX 1: dropdown statt input) ──
  // Replaces the old updateAgentModelPlaceholder that expected an <input>.
  // Uses FREE_MODELS + PAID_MODELS as lists, falls back to registry default_model.
  // Always prepends an "Other..." option that allows free-text entry.
  const populateAgentModels = (modelSel, prov) => {
    if (!modelSel) return;
    const meta = registryProviderById(prov);
    const prev = modelSel.value;
    let html = '<option value="">—</option>';
    const free = (FREE_MODELS[prov] || []);
    const paid = (PAID_MODELS[prov] || []);
    if (free.length) {
      html += '<optgroup label="Free">' + free.map(m => `<option value="${m}">${m}</option>`).join('') + '</optgroup>';
    }
    if (paid.length) {
      html += '<optgroup label="Paid">' + paid.map(m => `<option value="${m}">${m}</option>`).join('') + '</optgroup>';
    }
    if (meta && meta.default_model && !free.includes(meta.default_model) && !paid.includes(meta.default_model)) {
      html += `<option value="${meta.default_model}">${meta.default_model} (default)</option>`;
    }
    // If a model was previously selected and isn't in any list, keep it
    if (prev && !free.includes(prev) && !paid.includes(prev) && prev !== meta?.default_model) {
      html += `<option value="${prev}">${prev} (custom)</option>`;
    }
    modelSel.innerHTML = html;
    // Restore selection
    if (prev && Array.from(modelSel.options).some(o => o.value === prev)) modelSel.value = prev;
  };

  // ── Update Capabilities-Spalte (FIX 3) — aus provider.caps ──
  const updateAgentCapsColumn = (agentName, prov) => {
    const cell = document.querySelector(`[data-agent-caps-col="${agentName}"]`);
    if (!cell) return;
    const meta = registryProviderById(prov);
    const caps = (meta && meta.caps) ? meta.caps : [];
    if (caps.length === 0) {
      cell.textContent = '—';
      cell.style.color = 'var(--text-dim)';
    } else {
      cell.textContent = caps.join(', ');
      cell.style.color = '#eef1f6';
    }
  };

  // ── Update Status-Lämpchen (FIX 2) — Quadrat wird grün/gelb/rot/grau ──
  const refreshAgentStatusDots = (kdb) => {
    const keys = Object.values(kdb || {}).filter(k => k && k.valid);
    const keyByProvider = new Map();
    keys.forEach(k => { if (k.provider) keyByProvider.set(k.provider, k); });
    const seenProvider = new Set();
    $$('select[data-llm-svc="agent"][data-field="provider"]').forEach(sel => {
      const name = sel.dataset.agent;
      const prov = sel.value;
      const dot = document.querySelector(`[data-agent-status-dot="${name}"]`);
      const txt = document.querySelector(`[data-agent-status-text="${name}"]`);
      if (!dot || !txt) return;
      seenProvider.add(prov || '');
      if (!prov) {
        dot.style.background = '#6b7a90';
        txt.textContent = '—';
        txt.style.color = 'var(--text-dim)';
      } else if (keyByProvider.has(prov)) {
        dot.style.background = '#39FF14';
        txt.textContent = 'key ✓';
        txt.style.color = '#39FF14';
      } else {
        dot.style.background = '#FF007F';
        txt.textContent = 'no key';
        txt.style.color = '#FF007F';
      }
    });
  };

  // ── Service card: rebuild model options + update badge when provider changes ──
  const refreshServiceCard = (svc, keyDb) => {
    const sel = document.querySelector(`select[data-llm-svc="${svc}"][data-svc-field="provider"]`);
    const modelSel = document.querySelector(`select[data-llm-svc="${svc}"][data-svc-field="model"]`);
    const badge = document.querySelector(`[data-svc-badge="${svc}"]`);
    const statusLine = document.querySelector(`[data-svc-status-line="${svc}"]`);
    if (!sel || !modelSel || !badge) return;
    const prov = sel.value;
    const defaults = svc === 'web_search' ? wsDefaults : ttsDefaults;
    const providers = svc === 'web_search' ? wsProviders : ttsProviders;
    const meta = providers.find(p => p.id === prov);

    // Build model options: registry default as primary; otherwise a free-text input
    // is offered via the placeholder.
    let modelOpts = '<option value="">—</option>';
    if (meta && meta.default_model) {
      modelOpts = `<option value="${meta.default_model}">${meta.default_model} (default)</option>`;
    }
    modelSel.innerHTML = modelOpts;
    // Restore previously persisted model
    const persisted = (window.llmPendingChanges[svc] && window.llmPendingChanges[svc].model)
      || (window.__llmServiceState && window.__llmServiceState[svc] && window.__llmServiceState[svc].model);
    if (persisted) {
      if (!Array.from(modelSel.options).some(o => o.value === persisted)) {
        const opt = document.createElement('option');
        opt.value = persisted; opt.textContent = persisted;
        modelSel.appendChild(opt);
      }
      modelSel.value = persisted;
    }

    // Status badge: green if a valid key for this provider is loaded; red if
    // user typed a key inline but didn't test yet; gray if no key at all.
    const hasKey = Object.values(keyDb || {}).some(k => k.valid && k.provider === prov);
    const inlineKey = document.querySelector(`input[data-llm-svc="${svc}"][data-svc-field="key"]`)?.value?.trim();
    if (hasKey) {
      badge.dataset.svcBadgeState = 'ok';
      badge.textContent = '✓ key loaded';
      badge.style.color = '#39FF14';
      badge.style.borderColor = 'rgba(57,255,20,0.35)';
      badge.style.background = 'rgba(57,255,20,0.08)';
      statusLine.textContent = `Key für ${meta?.display_name || prov} gefunden.`;
    } else if (inlineKey) {
      badge.dataset.svcBadgeState = 'pending';
      badge.textContent = '⏳ key not tested';
      badge.style.color = '#d29922';
      badge.style.borderColor = 'rgba(210,153,34,0.35)';
      badge.style.background = 'rgba(210,153,34,0.08)';
      statusLine.textContent = 'Inline-Key noch nicht getestet (klicke „Test").';
    } else if (!prov) {
      badge.dataset.svcBadgeState = 'unknown';
      badge.textContent = '— pending —';
      badge.style.color = 'var(--text-muted)';
      badge.style.borderColor = 'rgba(255,255,255,0.08)';
      badge.style.background = 'rgba(0,0,0,0.25)';
      statusLine.textContent = '';
    } else {
      badge.dataset.svcBadgeState = 'missing';
      badge.textContent = '✗ no key';
      badge.style.color = '#FF007F';
      badge.style.borderColor = 'rgba(255,0,127,0.35)';
      badge.style.background = 'rgba(255,0,127,0.06)';
      statusLine.textContent = `Kein Key für ${meta?.display_name || prov} hinterlegt. Bitte oben in die Keys-Box einfügen oder hier inline eintragen.`;
    }
  };

  // ── Inline parseKeyLines: supports .env, .txt, .md, .json ──
  const parseKeyLines = (text, source) => {
    const ext = (source.match(/\.([a-z0-9]+)$/i) || ['','txt'])[1].toLowerCase();
    const lines = text.split(/\r?\n/);
    const out = []; let inFence = false;
    for (let raw of lines) {
      const line = raw.trim();
      if (!line) continue;
      if (line.startsWith('```') || line.startsWith('~~~')) { inFence = !inFence; continue; }
      if (ext === 'md' && !inFence) {
        if (/^#/.test(line) || /^>/.test(line) || /^\|/.test(line)) continue;
        if (/^[-*:| ]+$/.test(line)) continue;
        if (/^[-*+] /.test(line) || /^\d+\. /.test(line)) continue;
        if (/`[^`]+`/.test(line)) continue;
      }
      if (line.startsWith('#') || line.startsWith('//')) continue;
      if (line.includes('=')) {
        const [lbl, ...rest] = line.split('=');
        const key = rest.join('=').trim();
        if (key) out.push({
          label: lbl.trim().toUpperCase().replace(/[^A-Z0-9_]/g, '_'),
          provider: pvdOf(lbl) || pvdOf(key) || lbl.trim().toLowerCase(),
          key
        });
      } else if (line.startsWith('sk-')) {
        out.push({ label: 'API_KEY', provider: pvdOf(line) || 'openai', key: line });
      }
    }
    return out;
  };

  // Test a key + save it
  const testAndSave = async (entry) => {
    try {
      const r = await fetch('/api/llm/test', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: entry.key, label: entry.label })
      });
      const d = r.ok ? await r.json() : { valid: false };
      if (!d.valid) return { ok: false, info: d.info || 'invalid' };
      const kid = `${entry.provider}_${Date.now()}_${Math.random().toString(36).slice(2,6)}`;
      await fetch('/api/llm/keys', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [kid]: { provider: d.provider || entry.provider, key: entry.key, label: entry.label, valid: true } })
      });
      return { ok: true, kid, provider: d.provider || entry.provider };
    } catch (e) { return { ok: false, info: e.message }; }
  };

  // Populate provider dropdowns from currently-known working keys
  const refreshProviders = () => {
    fetch('/api/llm/keys').then(r => r.ok ? r.json() : {}).then(kdb => {
      populateAgentProviders(kdb);
      // Rebuild model <select> options for the currently-selected provider
      $$('select[data-llm-svc="agent"][data-field="model"]').forEach(modelSel => {
        const provSel = modelSel.parentElement.previousElementSibling.querySelector('select');
        populateAgentModels(modelSel, provSel ? provSel.value : '');
      });
      // Status-Lämpchen (FIX 2) aktualisieren
      refreshAgentStatusDots(kdb);
      refreshServiceCard('web_search', kdb);
      refreshServiceCard('tts', kdb);
    });
  };

  // Load existing agent routings
  const loadAgents = () => {
    fetch('/api/llm/agents').then(r => r.ok ? r.json() : {}).then(ad => {
      const byName = {};
      if (ad && !Array.isArray(ad)) {
        Object.entries(ad).forEach(([k, v]) => { if (v && v.provider) byName[k.toUpperCase()] = v; });
      }
      $$('select[data-llm-svc="agent"][data-field="provider"]').forEach(sel => {
        const name = sel.dataset.agent;
        const cur = byName[name.toUpperCase()] || byName[name.toLowerCase()];
        if (cur && cur.provider) sel.value = cur.provider;
        // FIX 3: Capabilities-Spalte aus provider.caps befüllen
        updateAgentCapsColumn(name, sel.value);
      });
      // Model <select> + Caps (DB)-Spalte (FIX 4)
      $$('select[data-llm-svc="agent"][data-field="model"]').forEach(modelSel => {
        const name = modelSel.dataset.agent;
        const cur = byName[name.toUpperCase()] || byName[name.toLowerCase()];
        const provSel = modelSel.parentElement.previousElementSibling.querySelector('select');
        populateAgentModels(modelSel, provSel ? provSel.value : '');
        if (cur && cur.model) modelSel.value = cur.model;
        // FIX 4: Caps (DB) — was tatsächlich gespeichert ist
        const capCell = document.querySelector(`[data-agent-cap="${name}"]`);
        if (capCell) {
          if (cur && cur.provider) {
            const meta = registryProviderById(cur.provider);
            const caps = (meta && meta.caps) ? meta.caps.join(',') : '?';
            capCell.textContent = `${cur.provider} / ${cur.model || '?'} [${caps}]`;
            capCell.style.color = '#eef1f6';
          } else {
            capCell.textContent = '— (nicht gespeichert)';
            capCell.style.color = 'var(--text-dim)';
          }
        }
      });
    });
  };

  // Process pasted/imported text
  const processKeyText = async (text, source) => {
    const entries = parseKeyLines(text, source);
    if (!entries.length) { status(`No keys found in ${source}.`, '#d29922'); return; }
    status(`Importing ${entries.length} key(s) from ${source}…`, '#00e5ff');
    let ok = 0, bad = 0;
    for (const e of entries) {
      const r = await testAndSave(e);
      if (r.ok) ok++; else bad++;
    }
    status(`Imported ${ok} working key(s) from ${source}. Removed ${bad} non-working.`, bad ? '#d29922' : '#39FF14');
    document.getElementById('llm-keys-input').value = '';
    refreshProviders();
    loadAgents();
  };

  // ── Track pending changes in window.llmPendingChanges.agents ──
  const queueAgentChange = (name, provider, model) => {
    if (!window.llmPendingChanges) window.llmPendingChanges = { agents: {}, web_search: {}, tts: {} };
    const cur = window.llmPendingChanges.agents[name] || {};
    window.llmPendingChanges.agents[name] = {
      provider: provider !== undefined ? provider : cur.provider,
      model: model !== undefined ? model : cur.model,
    };
    if (window.updateSaveBadge) window.updateSaveBadge();
  };
  window.__llmQueueAgentChange = queueAgentChange;

  // ── Track pending service-card changes (Web Search + TTS) ──
  const queueServiceChange = (svc, patch) => {
    if (!window.llmPendingChanges) window.llmPendingChanges = { agents: {}, web_search: {}, tts: {} };
    window.llmPendingChanges[svc] = Object.assign(
      {}, window.llmPendingChanges[svc] || {}, patch
    );
    if (window.updateSaveBadge) window.updateSaveBadge();
  };
  window.__llmQueueServiceChange = queueServiceChange;

  // Auto-route a group — preview-only (dry_run), no DB write.
  // Global Save button (header) is the single source of truth for persisting
  // these queued changes.
  const autoRoute = async (group, mode) => {
    try {
      const r = await fetch('/api/llm/agents', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, group, dry_run: true })
      });
      const d = await r.json();
      if (r.ok && d.agents) {
        d.agents.forEach(a => {
          const sel = document.querySelector(`select[data-agent="${a.name}"][data-field="provider"]`);
          const modelSel = document.querySelector(`select[data-agent="${a.name}"][data-field="model"]`);
          if (sel) sel.value = a.provider || '';
          if (modelSel) {
            populateAgentModels(modelSel, a.provider || '');
            modelSel.value = a.model || '';
          }
          queueAgentChange(a.name, a.provider, a.model);
          updateAgentCapsColumn(a.name, a.provider || '');
        });
        fetch('/api/llm/keys').then(r => r.ok ? r.json() : {}).then(kdb => refreshAgentStatusDots(kdb));
        status(`Auto-routing (${mode}) VORSCHAU für ${group}: ${d.agents[0].provider}/${d.agents[0].model}. Klick „Save" (Header) zum Übernehmen.`, '#00e5ff');
      } else {
        status(`Auto-routing fehlgeschlagen: ${d.info || d.status || 'unknown'}`, '#FF007F');
      }
    } catch (e) { status(`Auto-routing-Fehler: ${e.message}`, '#FF007F'); }
  };

  // ── Wire up controls ──
  $('#llm-import-file-btn').addEventListener('click', () => $('#llm-file-input').click());
  $('#llm-file-input').addEventListener('change', async (e) => {
    const f = e.target.files[0]; if (!f) return;
    await processKeyText(await f.text(), 'file:' + f.name);
    e.target.value = '';
  });
  $('#llm-keys-input').addEventListener('paste', (e) => setTimeout(() => processKeyText(e.target.value, 'pasted'), 50));
  $('#llm-keys-input').addEventListener('change', (e) => { if (e.target.value.trim()) processKeyText(e.target.value, 'typed'); });

  // Agent provider change → refresh model <select> + caps + status-dot + queue
  document.addEventListener('change', (e) => {
    const sel = e.target.closest('select[data-llm-svc="agent"][data-field="provider"]');
    if (sel) {
      const modelSel = sel.parentElement.nextElementSibling.querySelector('select');
      // FIX 1: model <select> neu befüllen mit FREE_MODELS/PAID_MODELS
      populateAgentModels(modelSel, sel.value);
      // FIX 3: Capabilities-Spalte aktualisieren
      updateAgentCapsColumn(sel.dataset.agent, sel.value);
      // FIX 2: Status-Lämpchen neu färben
      fetch('/api/llm/keys').then(r => r.ok ? r.json() : {}).then(kdb => refreshAgentStatusDots(kdb));
      queueAgentChange(sel.dataset.agent, sel.value, modelSel?.value || '');
    }
    const mSel = e.target.closest('select[data-llm-svc="agent"][data-field="model"]');
    if (mSel) queueAgentChange(mSel.dataset.agent, undefined, mSel.value);
    // Service cards
    const svcSel = e.target.closest('select[data-svc-field]');
    if (svcSel) {
      const svc = svcSel.dataset.llmSvc;
      const field = svcSel.dataset.svcField;
      fetch('/api/llm/keys').then(r => r.ok ? r.json() : {}).then(kdb => {
        if (field === 'provider') queueServiceChange(svc, { provider: svcSel.value });
        refreshServiceCard(svc, kdb);
      });
    }
    const svcModel = e.target.closest('select[data-svc-field="model"]');
    if (svcModel) {
      queueServiceChange(svcModel.dataset.llmSvc, { model: svcModel.value });
    }
    const svcKey = e.target.closest('input[data-svc-field="key"]');
    if (svcKey) {
      queueServiceChange(svcKey.dataset.llmSvc, { inline_key: svcKey.value });
      // update badge inline without waiting for roundtrip
      fetch('/api/llm/keys').then(r => r.ok ? r.json() : {}).then(kdb => {
        refreshServiceCard(svcKey.dataset.llmSvc, kdb);
      });
    }
  });

  // Mode buttons + Service "Test" button
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.llm-mode-btn');
    if (btn) {
      $$('.llm-mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      autoRoute(btn.dataset.group, btn.dataset.mode);
    }
    const testBtn = e.target.closest('[data-svc-test]');
    if (testBtn) {
      const svc = testBtn.dataset.svcTest;
      const provSel = document.querySelector(`select[data-llm-svc="${svc}"][data-svc-field="provider"]`);
      const keyInp = document.querySelector(`input[data-llm-svc="${svc}"][data-svc-field="key"]`);
      const statusLine = document.querySelector(`[data-svc-status-line="${svc}"]`);
      if (!provSel?.value) { statusLine.textContent = 'Provider auswählen.'; return; }
      const key = keyInp?.value?.trim();
      if (!key) { statusLine.textContent = 'Bitte Key eintragen oder oben in die Keys-Box einfügen.'; return; }
      statusLine.textContent = 'Teste …';
      fetch('/api/llm/test', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, provider: provSel.value, label: svc.toUpperCase() + '_API_KEY' })
      }).then(r => r.json()).then(d => {
        if (d.valid) {
          statusLine.textContent = '✓ Key gültig — wird mit Save übernommen.';
          statusLine.style.color = '#39FF14';
        } else {
          statusLine.textContent = '✗ ' + (d.info || 'invalid');
          statusLine.style.color = '#FF007F';
        }
      }).catch(err => {
        statusLine.textContent = '✗ ' + err.message;
        statusLine.style.color = '#FF007F';
      });
    }
  });

  // Initial load (parallel)
  refreshProviders();
  loadAgents();
  // Fetch persisted Web Search + TTS config from backend
  fetch('/api/llm/service').then(r => r.ok ? r.json() : null).then(svc => {
    if (!svc) return;
    window.__llmServiceState = svc;
    ['web_search', 'tts'].forEach(s => {
      const cfg = svc[s] || {};
      const sel = document.querySelector(`select[data-llm-svc="${s}"][data-svc-field="provider"]`);
      const modelSel = document.querySelector(`select[data-llm-svc="${s}"][data-svc-field="model"]`);
      if (sel && cfg.provider) {
        sel.value = cfg.provider;
        fetch('/api/llm/keys').then(r => r.ok ? r.json() : {}).then(kdb => refreshServiceCard(s, kdb));
      }
      if (modelSel && cfg.model) {
        if (!Array.from(modelSel.options).some(o => o.value === cfg.model)) {
          const opt = document.createElement('option');
          opt.value = cfg.model; opt.textContent = cfg.model;
          modelSel.appendChild(opt);
        }
        modelSel.value = cfg.model;
      }
    });
  });

  if (typeof updateSaveBadge === 'function') updateSaveBadge();
  status('Ready. Paste keys or click 📁 File. Hit Save (header) when done.', 'var(--text-dim)');

  // Hook for globalSave(): refresh dropdowns/badges once the server has
  // persisted the pending changes.
  window.__llmRefreshAfterSave = () => {
    if (!document.getElementById('llm-keys-input')) return; // page no longer mounted
    refreshProviders();
    loadAgents();
    fetch('/api/llm/service').then(r => r.ok ? r.json() : null).then(svc => {
      if (!svc) return;
      window.__llmServiceState = svc;
      ['web_search', 'tts'].forEach(s => {
        const cfg = svc[s] || {};
        const sel = document.querySelector(`select[data-llm-svc="${s}"][data-svc-field="provider"]`);
        if (sel && cfg.provider) sel.value = cfg.provider;
        fetch('/api/llm/keys').then(r => r.ok ? r.json() : {}).then(kdb => refreshServiceCard(s, kdb));
      });
    });
  };
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
  // REMOVED 2026-06-15: Docker-Sandbox komplett entfernt.
  // Diese Funktion bleibt als No-Op, damit alte Bookmarks/UI nicht brechen.
  console.warn("toggleBrowserDocker ist deprecated — Docker-Sandbox wurde entfernt.");
}

async function toggleWorkspaceSandbox(val) {
  // REMOVED 2026-06-15: Sandbox-Toggle komplett entfernt.
  // Befehle laufen jetzt immer direkt im Host (cwd=workspace).
  console.warn("toggleWorkspaceSandbox ist deprecated — Sandbox wurde entfernt.");
}

async function loadWorkspaceSandboxState() {
  // REMOVED 2026-06-15: No-Op, alter UI-Code ruft diese Funktion evtl. noch auf.
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

        const sourceTag = ins.source === 'routing.txt'
          ? '<span style="color:#ffa500; font-size:0.6rem; margin-left:4px;" title="Wird von config/routing.txt überschrieben">⚠ routing.txt</span>'
          : '';

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
              <span style="font-size:0.6rem; font-weight:bold; padding:1px 4px; border-radius:3px; border:1px solid ${badgeColor}33; color:rgba(255,255,255,0.85); font-family:monospace; background:rgba(0,0,0,0.2);">${badgeText.toUpperCase()}${sourceTag}</span>
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

// ── Agent-Border (1px) ────────────────────────────────────────────────────────
// Setzt auf das Tuning-Panel (#content) und den Showbox-Container einen
// 1px-Rahmen in der Frozen-Color des angeklickten Agenten. Beim Verlassen
// des Tuning-Views wird der Rahmen wieder entfernt.
window.applyAgentBorder = function(agentName) {
  if (!agentName || typeof agentColor !== 'function') return;
  const c = agentColor(agentName);
  const targets = [
    document.getElementById('content'),
    document.getElementById('modular-showbox-container'),
  ].filter(Boolean);
  targets.forEach(el => {
    el.style.setProperty('--agent-border-color', c);
    el.classList.add('has-agent-border');
  });
};

window.clearAgentBorder = function() {
  ['content', 'modular-showbox-container'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('has-agent-border');
    el.style.removeProperty('--agent-border-color');
  });
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

  let html = '<div class="tuning-compact" style="display:flex;flex-direction:column;gap:8px;height:100%;">';
  html += '<div style="display:flex;align-items:center;gap:14px;margin-bottom:4px;">';
  html += '<span id="tuning-avatar" style="display:none;"></span>';
  html += '<div><h2 style="color:var(--accent);margin:0;font-size:1.1rem;">🎛️ Agent Tuning</h2><div id="tuning-agentname" style="font-size:0.8rem;font-weight:600;margin-top:2px;">Agent wählen</div></div>';
  html += '</div>';

  html += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px;align-items:center;font-size:0.75rem;color:rgba(255,255,255,0.45);">';
  html += '<span style="opacity:0.7;">Agent wählen im Header oder in der Sidebar →</span>';
  html += '</div>';

  const tabs = [
    {id:'prompt',    label:'Prompt'},
    {id:'soul',      label:'Soul'},
    {id:'blockaden', label:'Blockaden'},
    {id:'tools',     label:'Tools'},
    {id:'verhalten', label:'Verhalten'},
    {id:'presets',   label:'Presets'},
    {id:'bake',      label:'Bake'},
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
  const agent = allAgents.find(a => a.id === agentId);
  if (agent) {
    const avNameEl = document.getElementById('tuning-agentname');
    if (avNameEl) { avNameEl.textContent = agent.name; avNameEl.style.color = agentColor(agent.name); }
    if (window.applyAgentBorder) window.applyAgentBorder(agent.name);
  }
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
window.tuningRender_blockaden = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  const agent = (agents||[]).find(a => a.id === agentId); if (!agent) return;
  el.innerHTML = '<div style="color:var(--accent);padding:20px;text-align:center;">📋 Blockaden-Dashboard v2 lädt...</div>';

  const [data, overview] = await Promise.all([
    api('GET', '/agents/' + agentId + '/blockades').catch(() => ({count:0,blockades:[]})),
    api('GET', '/blockades/overview').catch(() => ({agents:[]}))
  ]);
  const blockades = data.blockades || [], count = data.count || 0;
  const sCol = s => s==='rejected'?'#f44':s==='timeout'?'#fa0':'#f60';

  let h = '<div style="display:flex;flex-direction:column;gap:8px;font-size:0.75rem;">';
  h += '<div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-weight:600;">🛡️ Blockaden: '+agent.name+'</span><span style="font-size:0.65rem;color:'+(count?'#f44':'#0f0')+';">'+count+' Einträge</span></div>';

  // Übersicht
  const ov = overview.agents || [];
  if (ov.length) {
    h += '<div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:4px;">';
    ov.forEach(o => {
      h += '<span style="font-size:0.55rem;padding:2px 6px;border-radius:3px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);">'+o.agent_name+': <b style="color:#f66;">'+o.cnt+'</b></span>';
    });
    h += '</div>';
  }

  // Aktionen
  h += '<div style="display:flex;gap:4px;margin-bottom:4px;">';
  h += '<button onclick="tuningClearBlockades(\''+agentId+'\')" style="font-size:0.6rem;padding:3px 8px;background:rgba(255,50,50,0.12);border:1px solid rgba(255,50,50,0.25);color:#f66;border-radius:4px;cursor:pointer;">🗑 Agent zurücksetzen</button>';
  h += '<button onclick="tuningClearAllBlockades()" style="font-size:0.6rem;padding:3px 8px;background:rgba(255,50,50,0.08);border:1px solid rgba(255,50,50,0.15);color:rgba(255,100,100,0.7);border-radius:4px;cursor:pointer;">🗑 Alle zurücksetzen</button>';
  h += '</div>';

  // Liste
  if (!blockades.length) {
    h += '<div style="padding:20px;text-align:center;color:rgba(255,255,255,0.2);font-size:0.7rem;">Keine Blockaden für '+agent.name+'</div>';
  } else {
    blockades.forEach(b => {
      const t = b.timestamp||'–';
      h += '<div style="display:flex;flex-direction:column;gap:2px;padding:6px 8px;border-bottom:1px solid rgba(255,255,255,0.03);background:rgba(255,255,255,0.01);">';
      // Zeile 1: Zeit + Status + Typ + Aktion
      h += '<div style="display:flex;align-items:center;gap:5px;">';
      h += '<span style="font-size:0.5rem;color:rgba(255,255,255,0.25);font-family:monospace;flex-shrink:0;">'+t.substring(11,19)+'</span>';
      h += '<span style="font-size:0.5rem;padding:0 4px;border-radius:2px;background:rgba(255,255,255,0.04);color:'+sCol(b.status)+';">'+b.status+'</span>';
      h += '<span style="font-size:0.55rem;color:rgba(0,200,255,0.6);flex-shrink:0;">'+escapeHtml(b.action_type||'')+'</span>';
      h += '<span style="font-size:0.6rem;font-family:monospace;color:#f88;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+escapeHtml(b.detail||'–')+'</span>';
      h += '<button onclick="tuningDeleteBlockade(\''+agentId+'\','+b.id+')" style="flex-shrink:0;background:none;border:none;color:rgba(255,50,50,0.4);cursor:pointer;font-size:0.55rem;padding:1px;">✕</button>';
      h += '</div>';
      // Zeile 2: Grund + Ausgelöst von
      h += '<div style="display:flex;align-items:center;gap:5px;padding-left:3px;">';
      h += '<span style="font-size:0.5rem;color:rgba(255,255,255,0.35);">🔒 '+escapeHtml(b.reason||'')+'</span>';
      h += '<span style="font-size:0.45rem;color:rgba(255,255,255,0.2);margin-left:auto;">via '+escapeHtml(b.blocked_by||'Gatekeeper')+'</span>';
      h += '</div>';
      // Zeile 3: Content-Snippet falls vorhanden
      if (b.content_snippet) {
        h += '<div style="font-size:0.45rem;color:rgba(255,255,255,0.2);padding-left:3px;font-family:monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%;">📝 '+escapeHtml(b.content_snippet.substring(0,100))+'</div>';
      }
      h += '</div>';
    });
  }
  h += '</div>';
  el.innerHTML = h;
};

window.tuningDeleteBlockade = async function(agentId, bid) {
  await api('DELETE', '/agents/' + agentId + '/blockades/' + bid);
  tuningRender_blockaden(agentId);
};
window.tuningClearBlockades = async function(agentId) {
  await api('DELETE', '/agents/' + agentId + '/blockades');
  tuningRender_blockaden(agentId);
};
window.tuningClearAllBlockades = async function() {
  await api('DELETE', '/blockades');
  tuningRender_blockaden(window._tuningAgentId);
};

// ════════════════════════════════════════════════════════════════════
// Blockaden Dashboard v2 — Standalone full-page view
// ════════════════════════════════════════════════════════════════════

var _bdPollInterval = null;

function stopBDPolling() {
  if (_bdPollInterval) {
    clearInterval(_bdPollInterval);
    _bdPollInterval = null;
  }
}

function runBDPolling() {
  if (!document.getElementById('blockaden-dashboard-panel')) {
    stopBDPolling();
    return;
  }
  loadBlockadenDashboardData();
}

async function showBlockadenDashboard() {
  if (typeof trackView === 'function') trackView('blockaden');
  selectedId = null;
  stopBDPolling();
  document.getElementById('content').innerHTML = `
    <div class="panel" id="blockaden-dashboard-panel" style="height:calc(100vh - 91px); box-sizing:border-box; display:flex; flex-direction:column; padding:15px 20px; background:rgba(10, 15, 30, 0.4); border:1px solid var(--glass-border); margin-bottom:0; overflow:hidden;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px; flex-shrink:0;">
        <h2 style="margin:0; font-size:0.95rem; font-weight:600; border:none; letter-spacing:0.5px; display:flex; align-items:center; gap:8px;">
          <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#f44; animation:pulse-glow 1.5s infinite;"></span>
          Blockaden-Dashboard v2
        </h2>
        <div style="display:flex; gap:6px; margin-left:auto;">
          <span id="bd-count-badge" style="font-size:0.65rem; padding:2px 8px; border-radius:4px; background:rgba(255,68,68,0.1); border:1px solid rgba(255,68,68,0.2); color:#f66;"></span>
          <button onclick="bdShowRules()" id="bd-rules-btn" style="font-size:0.6rem; padding:3px 8px; background:rgba(255,165,0,0.08); border:1px solid rgba(255,165,0,0.2); color:#ffa500; border-radius:4px; cursor:pointer;">📜 Regeln</button>
          <button onclick="showBlockadenDashboard()" style="font-size:0.6rem; padding:3px 8px; background:rgba(0,229,255,0.08); border:1px solid rgba(0,229,255,0.2); color:var(--accent); border-radius:4px; cursor:pointer;">⟳ Refresh</button>
          <button onclick="if(confirm('Wirklich ALLE Blockaden unwiderruflich löschen?')){tuningClearAllBlockades();setTimeout(showBlockadenDashboard,300)}" style="font-size:0.6rem; padding:3px 8px; background:rgba(255,50,50,0.08); border:1px solid rgba(255,50,50,0.15); color:#f66; border-radius:4px; cursor:pointer;">🗑 Alle löschen</button>
        </div>
      </div>
      <div id="bd-filter-bar" style="display:flex; gap:8px; margin-bottom:8px; flex-shrink:0; flex-wrap:wrap; align-items:center;">
        <input id="bd-filter-agent" placeholder="Agent filtern..." style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); color:#fff; border-radius:4px; padding:4px 8px; font-size:0.72rem; width:140px; outline:none;" oninput="bdApplyFilter()">
        <input id="bd-filter-reason" placeholder="Grund filtern..." style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); color:#fff; border-radius:4px; padding:4px 8px; font-size:0.72rem; width:140px; outline:none;" oninput="bdApplyFilter()">
        <select id="bd-filter-status" onchange="bdApplyFilter()" style="background:rgba(0,0,0,0.3); color:#fff; border:1px solid rgba(255,255,255,0.1); border-radius:4px; padding:4px 8px; font-size:0.72rem;">
          <option value="">Alle Status</option>
          <option value="blocked">blocked</option>
          <option value="warning">warning</option>
          <option value="rejected">rejected</option>
          <option value="timeout">timeout</option>
        </select>
        <div id="bd-agent-pills" style="display:flex; gap:4px; flex-wrap:wrap;"></div>
      </div>
      <div id="bd-list" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:3px; padding-right:4px; scrollbar-width:thin;">
        <div style="color:rgba(255,255,255,0.3); padding:40px; text-align:center;">Lade Blockaden...</div>
      </div>
    </div>
  `;
  await loadBlockadenDashboardData();
  _bdPollInterval = setInterval(runBDPolling, 4000);
}

window.bdApplyFilter = function() {
  const agentF = (document.getElementById('bd-filter-agent')?.value || '').toLowerCase();
  const reasonF = (document.getElementById('bd-filter-reason')?.value || '').toLowerCase();
  const statusF = document.getElementById('bd-filter-status')?.value || '';
  document.querySelectorAll('.bd-entry').forEach(el => {
    const agent = el.getAttribute('data-agent') || '';
    const reason = el.getAttribute('data-reason') || '';
    const status = el.getAttribute('data-status') || '';
    const matchAgent = !agentF || agent.includes(agentF);
    const matchReason = !reasonF || reason.includes(reasonF);
    const matchStatus = !statusF || status === statusF;
    el.style.display = (matchAgent && matchReason && matchStatus) ? '' : 'none';
  });
};

async function loadBlockadenDashboardData() {
  const container = document.getElementById('bd-list');
  if (!container) return;

  const data = await api('GET', '/blockades?limit=500').catch(() => null);
  if (!data) {
    container.innerHTML = '<div style="color:rgba(255,255,255,0.3); padding:40px; text-align:center;">Fehler beim Laden der Blockaden.</div>';
    return;
  }

  const blockades = data.blockades || [];
  const counts = data.counts || [];

  const badge = document.getElementById('bd-count-badge');
  if (badge) badge.textContent = blockades.length + ' Blockaden';

  // Agent pills
  const pillsEl = document.getElementById('bd-agent-pills');
  if (pillsEl) {
    const maxCnt = Math.max(...counts.map(c => c.cnt), 1);
    pillsEl.innerHTML = counts.map(c => {
      const pct = blockades.length ? Math.round((c.cnt / blockades.length) * 100) : 0;
      const barW = Math.round((c.cnt / maxCnt) * 60);
      const color = agentColor(c.agent_name);
      return `<span onclick="document.getElementById('bd-filter-agent').value='${c.agent_name}';bdApplyFilter()" style="position:relative; font-size:0.55rem; padding:3px 8px; border-radius:4px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); cursor:pointer; transition:all 0.2s; overflow:hidden;" onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'" title="${c.cnt} Blockaden (${pct}%)">
        <span style="position:absolute; left:0; top:0; height:100%; width:${barW}px; background:${color}18; pointer-events:none; border-radius:3px;"></span>
        <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:${color}; margin-right:4px; position:relative;"></span>
        <span style="position:relative; font-weight:500;">${c.agent_name.replace('ag','AG')}</span>
        <b style="color:#fff; background:${color}33; padding:0 5px; border-radius:3px; font-size:0.6rem; margin-left:4px; position:relative;">${c.cnt}</b>
      </span>`;
    }).join('');
  }

  if (!blockades.length) {
    container.innerHTML = '<div style="color:rgba(255,255,255,0.2); padding:40px; text-align:center;">🔒 Keine Blockaden vorhanden. Alle Agenten sind brav.</div>';
    return;
  }

  const sCol = s => s==='rejected'?'#f44':s==='timeout'?'#fa0':s==='warning'?'#ffa500':'#f60';

  container.innerHTML = blockades.map(b => {
    const ts = b.timestamp || '';
    const time = ts.substring(11, 19);
    const date = ts.substring(0, 10);
    const agentColorHex = agentColor(b.agent_name);

    const detail = b.detail || '–';
    const reason = b.reason || '–';
    const snippet = b.content_snippet || '';

    const agentName = b.agent_name || 'Unknown';
    const targetVal = encodeURIComponent(b.detail || '');
    const agentEnc = encodeURIComponent(agentName);
    const idEnc = b.id;

    return `
      <div class="bd-entry" data-agent="${agentName.toLowerCase()}" data-reason="${(b.reason||'').toLowerCase()}" data-status="${(b.status||'')}" style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-left:3px solid ${agentColorHex}; border-radius:4px; padding:5px 8px; display:flex; flex-direction:column; gap:2px; transition:all 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.04)'" onmouseout="this.style.background='rgba(255,255,255,0.02)'">
        <div style="display:flex; align-items:center; gap:4px; font-size:0.6rem;">
          <span style="color:${agentColorHex}; font-weight:600; text-transform:uppercase; flex-shrink:0;">${agentName.replace('ag','AG')}</span>
          <span style="font-size:0.45rem; color:rgba(255,255,255,0.25); font-family:monospace;">${date} ${time}</span>
          <span style="font-size:0.45rem; padding:0 3px; border-radius:2px; background:rgba(255,255,255,0.04); color:${sCol(b.status)}; font-weight:500;">${b.status}</span>
          <span style="font-size:0.5rem; color:rgba(0,200,255,0.6);">${b.action_type || ''}</span>
          <span style="font-size:0.5rem; color:rgba(255,255,255,0.3); margin-left:auto;">via ${b.blocked_by || 'Gatekeeper'}</span>
          <button onclick="bdDeleteBlockade(${b.id})" style="flex-shrink:0; background:none; border:none; color:rgba(255,50,50,0.3); cursor:pointer; font-size:0.5rem; padding:1px 3px;">✕</button>
        </div>
        <div style="display:flex; align-items:flex-start; gap:4px;">
          <span style="font-size:0.55rem; color:rgba(255,255,255,0.3); flex-shrink:0; width:44px;">🔒 Grund:</span>
          <span style="font-size:0.6rem; color:#f88; line-height:1.25; word-break:break-word; flex:1;">${escapeHtml(reason)}</span>
        </div>
        <div style="display:flex; align-items:flex-start; gap:4px;">
          <span style="font-size:0.55rem; color:rgba(255,255,255,0.3); flex-shrink:0; width:44px;">⚡ Auslöser:</span>
          <code style="font-size:0.55rem; color:#0af; line-height:1.2; word-break:break-word; font-family:monospace; background:rgba(0,0,0,0.2); padding:1px 4px; border-radius:2px; flex:1; overflow-x:auto; white-space:pre-wrap;">${escapeHtml(detail)}</code>
        </div>
        ${snippet ? `
        <div style="display:flex; align-items:flex-start; gap:4px;">
          <span style="font-size:0.55rem; color:rgba(255,255,255,0.3); flex-shrink:0; width:44px;">📝 Snippet:</span>
          <code style="font-size:0.5rem; color:rgba(255,255,255,0.5); line-height:1.2; word-break:break-word; font-family:monospace; background:rgba(0,0,0,0.15); padding:1px 4px; border-radius:2px; flex:1; overflow-x:auto; white-space:pre-wrap; max-height:2.4em; overflow:hidden;">${escapeHtml(snippet)}</code>
        </div>` : ''}
        <div style="display:flex; gap:3px; margin-top:2px; padding-top:3px; border-top:1px solid rgba(255,255,255,0.04);">
          <button onclick="bdAction(${idEnc},'allow_once','${targetVal}','')" style="font-size:0.45rem; padding:2px 5px; background:rgba(57,255,20,0.08); border:1px solid rgba(57,255,20,0.2); color:#39ff14; border-radius:3px; cursor:pointer; flex:1;">✅ Einmalig</button>
          <button onclick="bdAction(${idEnc},'whitelist','${targetVal}','')" style="font-size:0.45rem; padding:2px 5px; background:rgba(0,229,255,0.08); border:1px solid rgba(0,229,255,0.2); color:#00e5ff; border-radius:3px; cursor:pointer; flex:1;">➕ Whitelist</button>
          <button onclick="bdAction(${idEnc},'allow_agent','${targetVal}','${agentEnc}')" style="font-size:0.45rem; padding:2px 5px; background:rgba(176,38,255,0.08); border:1px solid rgba(176,38,255,0.2); color:#b026ff; border-radius:3px; cursor:pointer; flex:1;">👤 Agent</button>
          <button onclick="bdAction(${idEnc},'block_always','${targetVal}','')" style="font-size:0.45rem; padding:2px 5px; background:rgba(255,50,50,0.08); border:1px solid rgba(255,50,50,0.2); color:#f66; border-radius:3px; cursor:pointer; flex:1;">🚫 Block</button>
        </div>
      </div>
    `;
  }).join('');
}

window.bdDeleteBlockade = async function(bid) {
  await api('DELETE', '/blockades/' + bid).catch(() => {});
  loadBlockadenDashboardData();
};

window.bdShowRules = async function() {
  const res = await api('GET', '/blockades/rules').catch(() => ({rules: []}));
  const rules = res.rules || [];
  if (!rules.length) {
    toast('Keine aktiven Regeln.', 'info');
    return;
  }
  const labels = {'allow_once':'✅ Einmalig','whitelist':'➕ Whitelist','allow_agent':'👤 Agent','block_always':'🚫 Block'};
  let html = rules.map(r => `
    <div style="display:flex; align-items:center; gap:6px; padding:4px 8px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:4px; font-size:0.6rem;">
      <span style="padding:1px 4px; border-radius:2px; background:rgba(255,255,255,0.05);">${labels[r.type]||r.type}</span>
      <code style="flex:1; color:#0af; font-family:monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(r.target_value)}</code>
      <span style="color:rgba(255,255,255,0.3);">${r.agent ? escapeHtml(r.agent) : ''}</span>
      <button onclick="bdDeleteRule('${r.id}')" style="background:none; border:none; color:#f44; cursor:pointer; padding:1px 4px;">✕</button>
    </div>
  `).join('');
  document.getElementById('bd-list').innerHTML = `
    <div style="display:flex; flex-direction:column; gap:4px; padding:10px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="font-size:0.7rem; font-weight:600;">📜 Aktive Regeln (${rules.length})</span>
        <button onclick="loadBlockadenDashboardData()" style="font-size:0.55rem; padding:2px 6px; background:none; border:1px solid rgba(255,255,255,0.15); color:rgba(255,255,255,0.5); border-radius:3px; cursor:pointer;">← Zurück</button>
      </div>
      ${html}
    </div>
  `;
};

window.bdDeleteRule = async function(ruleId) {
  await api('DELETE', '/blockades/rules/' + ruleId).catch(() => {});
  bdShowRules();
};

window.bdAction = async function(bid, ruleType, targetVal, agent) {
  const labels = {
    'allow_once': '✅ Einmalig erlaubt',
    'whitelist': '➕ Auf Whitelist gesetzt',
    'allow_agent': '👤 Für Agenten erlaubt',
    'block_always': '🚫 Immer blockiert'
  };
  const target = decodeURIComponent(targetVal);
  const res = await api('POST', '/blockades/' + bid + '/action', {
    rule_type: ruleType,
    target_value: target,
    agent: decodeURIComponent(agent)
  });
  if (res && res.status === 'ok') {
    toast(res.message || labels[ruleType] || 'OK', 'success');
    loadBlockadenDashboardData();
  } else {
    toast('Fehler: ' + (res?.message || 'Unknown'), 'error');
  }
};

window.tuningRender_tools = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  const agent = (agents||[]).find(a => a.id === agentId); if (!agent) return;
  el.innerHTML = '<div style="color:rgba(255,255,255,0.3);padding:20px;text-align:center;">Lade Tools...</div>';
  let profile = {};
  try { profile = await api('GET', '/agents/' + agentId + '/profile') || {}; } catch(e){}
  const tools = profile.tools || [];
  const allTools = [
    {key:'read_file',     icon:'📄', label:'Read',   desc_de:'Dateien lesen (mit godmode auch außerhalb des Workspace).', desc_en:'Read files (with godmode also outside the workspace).'},
    {key:'write_file',    icon:'✏️', label:'Write',  desc_de:'Dateien schreiben — Hauptwerkzeug jedes Worker-Agenten.', desc_en:'Write files — main tool of every worker agent.'},
    {key:'run_command',   icon:'⚡', label:'Run',    desc_de:'Shell-Befehle ausführen (pip, brew, scripts). Sicherheitsgeprüft.', desc_en:'Execute shell commands (pip, brew, scripts). Safety-checked.'},
    {key:'war_room_chat', icon:'💬', label:'@Job',   desc_de:'Chat & Delegation. GeneralAG verteilt hier Aufgaben an Worker.', desc_en:'Chat & delegation. GeneralAG dispatches tasks to workers here.'},
    {key:'browser',       icon:'🌐', label:'Browser',desc_de:'Playwright-gesteuerter Chromium für Demos, Scraping, Formulare.', desc_en:'Playwright-controlled Chromium for demos, scraping, forms.'},
    {key:'generate_image',icon:'🎨', label:'Image',  desc_de:'Bilder erstellen (Matrix/MiniMax-Backend).', desc_en:'Generate images (matrix/MiniMax backend).'},
    {key:'crawl_url',     icon:'🕷️', label:'Crawl',  desc_de:'Webseite fetchen und Text extrahieren.', desc_en:'Fetch a web page and extract text.'},
    {key:'evolve',        icon:'🧬', label:'Evolve', desc_de:'Agent darf eigenen Code/Prompt iterativ verbessern.', desc_en:'Agent may iteratively improve its own code/prompt.'},
    {key:'sys_cmd',       icon:'🔧', label:'SysCmd', desc_de:'Programme installieren, System-Einstellungen ändern.', desc_en:'Install programs, change system settings.'},
    {key:'desktop_action',icon:'🖥️', label:'Desktop',desc_de:'Maus und Tastatur fernsteuern.', desc_en:'Remote-control mouse and keyboard.'},
    {key:'screenshot',    icon:'📸', label:'Screen', desc_de:'Screenshot vom Bildschirm oder Bereich.', desc_en:'Capture screen or region.'},
    {key:'create_agent',  icon:'🤖', label:'Agent+', desc_de:'Neue Sub-Agenten registrieren.', desc_en:'Register new sub-agents.'},
  ];
  // Modul-Karten (Webhooks / Plugins / Skills). UI-Stubs — Backend folgt.
  const modules = [
    { id:'webhook', title: window.t('mod.webhook.title'), body: window.t('mod.webhook.desc') },
    { id:'plugin',  title: window.t('mod.plugin.title'),  body: window.t('mod.plugin.desc') },
    { id:'skill',   title: window.t('mod.skill.title'),   body: window.t('mod.skill.desc') },
  ];

  let html = '<div class="panel" style="padding:16px;">';
  html += '<h3 style="margin:0 0 8px 0;font-size:0.85rem;">🔧 Tools <span style="font-size:0.62rem;color:rgba(255,255,255,0.3);">— Klick zum Togglen</span></h3>';
  html += '<div class="panel-grid">';
  allTools.forEach(t => {
    const has = tools.includes(t.key);
    html += '<div onclick="tuningToggleTool(\'' + agentId + '\',\'' + t.key + '\')" '
         +  'data-help-title="' + t.label + '" '
         +  'data-help="' + t.desc_de + '" '
         +  'data-help-en="' + t.desc_en + '" '
         +  'style="display:flex;align-items:center;gap:6px;padding:6px 8px;background:rgba(255,255,255,0.02);border:1px solid ' + (has ? 'rgba(57,255,20,0.3)' : 'rgba(255,255,255,0.06)') + ';border-radius:6px;cursor:pointer;transition:all 0.2s;" '
         +  'onmouseover="this.style.background=\'rgba(255,255,255,0.05)\'" '
         +  'onmouseout="this.style.background=\'rgba(255,255,255,0.02)\'">';
    html += '<span style="font-size:0.95rem;">' + t.icon + '</span>';
    html += '<span style="font-size:0.72rem;color:' + (has ? '#39ff14' : 'rgba(255,255,255,0.35)') + ';">' + t.label + '</span>';
    html += '<span style="margin-left:auto;font-size:0.78rem;">' + (has ? '✅' : '⬜') + '</span>';
    html += '</div>';
  });
  html += '</div>';
  html += '<div style="font-size:0.6rem;color:rgba(255,255,255,0.22);margin-top:6px;">LLM: ' + (profile.llm_provider||'–') + ' / ' + (profile.llm_model||'–') + ' · Toggles Session-scoped</div>';

  // ── Module-Sektion (Webhooks / Plugins / Skills) ──
  html += '<h3 style="margin:8px 0 6px 0;font-size:0.85rem;" data-help-title="' + window.t('tab.modules', 'Erweiterbare Module') + '" data-help="' + window.t('tab.modules', 'Erweiterbare Module.') + '">🧩 Module</h3>';
  html += '<div class="panel-grid">';
  modules.forEach(m => {
    html += '<div class="module-card" data-help-title="' + m.title + '" data-help="' + m.body + '" '
         +  'style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);">'
         +  '<h4>' + m.title + '</h4>'
         +  '<p>' + m.body + '</p>'
         +  '<div style="margin-top:6px;font-size:0.6rem;color:rgba(255,255,255,0.3);">Stub · Backend folgt</div>'
         +  '</div>';
  });
  html += '</div>';
  html += '</div>';
  el.innerHTML = html;
};

window.tuningToggleTool = async function(agentId, toolKey) {
  const r = await api('POST', '/agents/' + agentId + '/tools/toggle', {tool: toolKey});
  if (r && r.status === 'ok') {
    toast(toolKey + (r.enabled ? ' ✅ aktiviert' : ' ❌ deaktiviert'), 'success');
    tuningRender_tools(agentId);
  } else { toast('Fehler beim Togglen', 'error'); }
};

// ── Tab: Verhalten (Claude 3-Level Sliders) ──
window.tuningRender_tuning = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  const agent = (agents||[]).find(a => a.id === agentId); if (!agent) return;
  let config = {};
  try { config = await api('GET', '/agents/' + agentId + '/sliders') || {}; } catch(e){}

  const sliders = config.sliders || {};
  const blocks = config.prompt_blocks || {};

  const sliderDefs = [
    {id:'creativity', label:'Creativity',
     vals:{0:'0 – rigid',1:'1 – proven',2:'2 – balanced',3:'3 – innovative',4:'4 – wild'},
     descs:{0:'No experimentation. Only standard patterns.',
            1:'Prefer proven patterns. Minimal variation.',
            2:'Balance standard with occasional creative.',
            3:'Propose novel solutions. Break conventions.',
            4:'Free innovation. Wild ideas welcome.'}},
    {id:'precision', label:'Precision',
     vals:{0:'0 – approx',1:'1 – low',2:'2 – balanced',3:'3 – high',4:'4 – flawless'},
     descs:{0:'Approximations fine. Speed over accuracy.',
            1:'Low precision. Verify only critical.',
            2:'Balanced accuracy. Verify main outputs.',
            3:'Detailed verification. Edge cases checked.',
            4:'Flawless. Double-check everything. No errors.'}},
    {id:'speed', label:'Speed',
     vals:{0:'0 – glacial',1:'1 – slow',2:'2 – steady',3:'3 – fast',4:'4 – instant'},
     descs:{0:'Maximum quality. Take all time needed.',
            1:'Slow pace. Thoroughness over velocity.',
            2:'Steady pace. Deliver when ready.',
            3:'Quick delivery. First version fast.',
            4:'Instant delivery. Speed over everything.'}},
    {id:'critical_thinking', label:'Critical Thinking',
     vals:{0:'0 – none',1:'1 – minimal',2:'2 – moderate',3:'3 – high',4:'4 – skeptic'},
     descs:{0:'Execute literally. No questioning.',
            1:'Flag only blocking issues.',
            2:'Think about task. Suggest improvements.',
            3:'Challenge assumptions. Propose changes.',
            4:'Question everything. Root cause analysis.'}},
    {id:'obedience', label:'Obedience',
     vals:{0:'0 – slave',1:'1 – follower',2:'2 – teammate',3:'3 – lead',4:'4 – sovereign'},
     descs:{0:'Follow literally. No interpretation.',
            1:'Close adherence. Minimal autonomy.',
            2:'Reasonable interpretation. Small adjustments.',
            3:'High autonomy. Guidelines over instructions.',
            4:'Full autonomy. Always choose best path.'}},
  ];

  let html = '<div class="panel" style="padding:16px;display:flex;flex-direction:column;gap:14px;">';
  html += '<h3 style="margin:0;font-size:0.95rem;">🎚️ Claude Slider <span style="font-size:0.65rem;font-weight:400;color:rgba(255,255,255,0.3);">— 5-Level (0–4)</span></h3>';
  sliderDefs.forEach(sl => {
    const val = sliders[sl.id] ?? 2;
    html += '<div style="display:flex;flex-direction:column;gap:3px;padding:6px 8px;background:rgba(255,255,255,0.02);border-radius:6px;">';
    html += '<div style="display:flex;justify-content:space-between;font-size:0.72rem;"><span><b>' + sl.label + '</b></span><span id="tlbl-' + sl.id + '" style="font-weight:600;color:var(--accent);">' + sl.vals[val] + '</span></div>';
    html += '<input type="range" id="tsl-' + sl.id + '" min="0" max="4" value="' + val + '" style="width:100%;margin:2px 0;" oninput="sliderUpdate(\'' + sl.id + '\',this.value)">';
    html += '<div id="tdesc-' + sl.id + '" style="font-size:0.6rem;color:rgba(255,255,255,0.45);line-height:1.3;">' + escapeHtml(sl.descs[val]) + '</div>';
    html += '</div>';
  });
  html += '<script>window._sliderDescs=' + JSON.stringify(sliderDefs) + ';</script>';
  html += '<button onclick="tuningSaveBehavior(\'' + agentId + '\')" style="padding:8px;font-size:0.8rem;font-weight:700;background:rgba(0,200,100,0.15);border:1px solid rgba(0,200,100,0.3);color:#0f0;border-radius:6px;cursor:pointer;">💾 Verhalten speichern</button>';
  html += '<div id="tmsg-behavior" style="font-size:0.65rem;color:rgba(255,255,255,0.3);text-align:center;"></div>';
  html += '</div>';
   el.innerHTML = html;
};

// Live Slider-Update
window.sliderUpdate = function(key, value) {
  value = parseInt(value);
  const defs = window._sliderDescs || [];
  const sl = defs.find(function(d) { return d.id === key; });
  if (!sl) return;
  const lbl = document.getElementById('tlbl-' + key);
  if (lbl) lbl.textContent = sl.vals[value];
  const desc = document.getElementById('tdesc-' + key);
  if (desc) desc.textContent = sl.descs[value];
};

window.tuningSaveBehavior = async function(agentId) {
  const s = {};
  ['creativity','precision','speed','critical_thinking','obedience'].forEach(k => {
    s[k] = parseInt(document.getElementById('tsl-' + k)?.value ?? 2);
  });
  const r = await api('PUT', '/agents/' + agentId + '/sliders', s);
  const msg = document.getElementById('tmsg-behavior');
  if (r && r.status === 'ok') { if (msg) { msg.textContent='✓ Gespeichert'; msg.style.color='#0f0'; setTimeout(()=>msg.textContent='',2000); } }
  else { if (msg) { msg.textContent='Fehler'; msg.style.color='#f00'; } }
};

// ── Tab: Presets (umbrella with 2 sub-tabs: Agent-Konfiguration + Snapshots) ──
window.tuningRender_presets = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  const sub = window._tuningPresetsSub || 'agent-config';
  window._tuningPresetsSub = sub;
  let html = '<div style="display:flex;flex-direction:column;gap:10px;padding:4px;">';
  html += '<div style="display:flex;gap:4px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:6px;">';
  html += '<button class="psubtab" id="psubtab-agent-config" onclick="tuningSwitchPresetsSub(\'agent-config\')" style="padding:6px 14px;font-size:0.75rem;background:none;border:none;color:rgba(255,255,255,0.4);cursor:pointer;border-bottom:2px solid transparent;transition:all 0.2s;">🎨 Agent-Konfiguration</button>';
  html += '<button class="psubtab" id="psubtab-snapshots" onclick="tuningSwitchPresetsSub(\'snapshots\')" style="padding:6px 14px;font-size:0.75rem;background:none;border:none;color:rgba(255,255,255,0.4);cursor:pointer;border-bottom:2px solid transparent;transition:all 0.2s;">💾 Snapshots</button>';
  html += '</div>';
  html += '<div id="presets-sub-content"></div>';
  html += '</div>';
  el.innerHTML = html;
  if (sub === 'snapshots') {
    await tuningRender_snapshots(agentId);
  } else {
    await tuningRender_agentConfig(agentId);
  }
};

window.tuningSwitchPresetsSub = async function(subId) {
  window._tuningPresetsSub = subId;
  document.querySelectorAll('.psubtab').forEach(b => {
    b.style.color = 'rgba(255,255,255,0.4)';
    b.style.borderBottomColor = 'transparent';
  });
  const t = document.getElementById('psubtab-' + subId);
  if (t) { t.style.color = 'var(--accent)'; t.style.borderBottomColor = 'var(--accent)'; }
  if (subId === 'snapshots') {
    await tuningRender_snapshots(window._tuningAgentId);
  } else {
    await tuningRender_agentConfig(window._tuningAgentId);
  }
};

window.tuningRender_snapshots = async function(agentId) {
  const el = document.getElementById('presets-sub-content'); if (!el) return;
  el.innerHTML = '<div style="color:rgba(255,255,255,0.3);padding:20px;text-align:center;">Lade Snapshots...</div>';
  let settings = {}, llm = {}, presets = [];
  try { settings = await api('GET', '/agents/' + agentId + '/settings') || {}; } catch(e){}
  try { llm = await api('GET', '/llm/agents') || {}; } catch(e){}
  try { presets = await api('GET', '/presets') || []; } catch(e){}

  let html = '<div class="panel" style="padding:16px;display:flex;flex-direction:column;gap:14px;">';
  html += '<h3 style="margin:0;font-size:0.95rem;">💾 Snapshots <span style="font-size:0.65rem;color:rgba(255,255,255,0.3);">— komplette Konfiguration speichern & laden</span></h3>';

  // Save current as preset
  html += '<div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:12px;">';
  html += '<div style="flex:1;min-width:150px;"><label style="font-size:0.7rem;display:block;margin-bottom:2px;">Snapshot-Name</label><input id="tpreset-name" placeholder="z.B. Web Development" style="width:100%;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.12);color:#fff;border-radius:4px;padding:6px;font-size:0.75rem;"></div>';
  html += '<div style="flex:2;min-width:200px;"><label style="font-size:0.7rem;display:block;margin-bottom:2px;">Beschreibung</label><input id="tpreset-desc" placeholder="Kurze Beschreibung..." style="width:100%;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.12);color:#fff;border-radius:4px;padding:6px;font-size:0.75rem;"></div>';
  html += '<div><button onclick="tuningSavePreset()" style="padding:6px 16px;font-size:0.75rem;font-weight:700;background:rgba(0,200,100,0.15);border:1px solid rgba(0,200,100,0.3);color:#0f0;border-radius:6px;cursor:pointer;white-space:nowrap;">💾 Speichern</button></div>';
  html += '</div>';

  // Preset list
  html += '<div style="display:flex;flex-direction:column;gap:6px;">';
  html += '<div style="font-size:0.7rem;color:rgba(255,255,255,0.5);">Gespeicherte Snapshots (' + presets.length + ')</div>';
  if (!presets.length) {
    html += '<div style="color:rgba(255,255,255,0.2);padding:20px;text-align:center;">Keine Snapshots vorhanden</div>';
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
    toast('Snapshot "' + name + '" gespeichert', 'success');
    tuningRender_snapshots(window._tuningAgentId);
  } else { toast('Fehler beim Speichern', 'error'); }
};

window.tuningLoadPreset = async function(file) {
  if (!confirm('Snapshot laden? Überschreibt aktuelle Einstellungen aller Agenten.')) return;
  const r = await api('POST', '/presets/load', {file});
  if (r && r.status === 'ok') {
    toast('Snapshot geladen: ' + r.name, 'success');
    tuningRender_snapshots(window._tuningAgentId);
  }   else { toast('Fehler beim Laden', 'error'); }
};

// ── Sub-Tab: Agent-Konfiguration (per-Agent preset editor, moved from presets_management.js) ──
(function() {
  const AGENT_LABELS = {
    soulag: 'SoulAG — Identitäts-Anker',
    watchdogag: 'WatchdogAG — Sicherheits-Wächter',
    generalag: 'GeneralAG — Allround-Router',
    securityag: 'SecurityAG — Security-Auditor',
    coderag: 'CoderAG — Code-Worker',
    researcherag: 'ResearcherAG — Recherche-Worker',
    writerag: 'WriterAG — Text-Worker',
    editorag: 'EditorAG — QA-Worker'
  };

  const AGENT_FIELDS = [
    {key: 'prompt', label: 'System-Prompt', type: 'textarea', rows: 6},
    {key: 'focus', label: 'Fokus', type: 'text'},
    {key: 'target', label: 'Target (z.B. auto:stage_2 oder openrouter:modell)', type: 'text'},
    {key: 'creativity', label: 'Creativity (1-5)', type: 'number', min: 1, max: 5},
    {key: 'obedience', label: 'Obedience (1-5)', type: 'number', min: 1, max: 5},
    {key: 'model_override', label: 'Model-Override (oder leer)', type: 'text'},
    {key: 'enabled', label: 'Aktiv', type: 'checkbox'}
  ];

  let _presetsData = null;
  let _agentGroups = {system: ['soulag','watchdogag','generalag','securityag'], worker: ['coderag','researcherag','writerag','editorag']};

  async function loadPresetsData() {
    try {
      const [presetsRes, groupsRes] = await Promise.all([
        fetch('/api/presets/layer-a/list').then(r => r.json()),
        fetch('/api/presets/groups').then(r => r.json()).catch(() => null)
      ]);
      if (groupsRes) _agentGroups = groupsRes;
      _presetsData = {
        slugs: presetsRes || [],
        currentPreset: null,
        activeGroup: _presetsData ? _presetsData.activeGroup : 'system'
      };
      if (_presetsData.slugs.length > 0) {
        try {
          const r = await fetch('/api/presets/layer-a/' + encodeURIComponent(_presetsData.slugs[0].slug));
          _presetsData.currentPreset = await r.json();
        } catch (e) { /* ignore */ }
      }
    } catch (e) {
      console.error('loadPresetsData failed:', e);
    }
  }

  function renderPresetsList() {
    const sel = document.getElementById('presets-list-select');
    if (!sel) return;
    sel.innerHTML = '';
    if (!_presetsData || !_presetsData.slugs.length) {
      sel.innerHTML = '<option value="">— keine Presets —</option>';
      return;
    }
    _presetsData.slugs.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.slug;
      opt.textContent = p.name + ' (' + p.agent_count + ' Agents)';
      if (_presetsData.currentPreset && _presetsData.currentPreset.slug === p.slug) opt.selected = true;
      sel.appendChild(opt);
    });
  }

  function renderAgentsGrid() {
    const grid = document.getElementById('presets-agents-grid');
    if (!grid) return;
    if (!_presetsData) { grid.innerHTML = '<p style="color: var(--text-dim);">Lade Presets…</p>'; return; }
    const group = _presetsData.activeGroup || 'system';
    const agents = _agentGroups[group] || [];
    const preset = _presetsData.currentPreset;
    if (!preset) {
      grid.innerHTML = '<p style="color: var(--text-dim); padding: 20px; text-align: center;">Wähle ein Preset zum Bearbeiten</p>';
      return;
    }
    let html = '';
    agents.forEach(agentName => {
      const agentData = (preset.agents && preset.agents[agentName]) || {};
      const label = AGENT_LABELS[agentName] || agentName;
      html += '<div class="preset-agent-card" style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 12px;">';
      html += '<h3 style="margin: 0 0 8px 0; font-size: 0.9rem; color: var(--primary); display: flex; justify-content: space-between; align-items: center;">';
      html += '<span>' + label + '</span>';
      html += '<small style="color: var(--text-dim); font-size: 0.65rem;">' + agentName + '</small></h3>';
      AGENT_FIELDS.forEach(f => {
        const val = agentData[f.key];
        html += '<div data-agent="' + agentName + '" data-field="' + f.key + '" style="margin-bottom: 8px;">';
        html += '<label style="display: block; font-size: 0.7rem; color: var(--text-dim); margin-bottom: 2px;">' + f.label + ' <span class="save-status" style="margin-left: 6px; font-size: 0.65rem;"></span></label>';
        if (f.type === 'textarea') {
          html += '<textarea rows="' + (f.rows || 4) + '" onchange="tuningSaveAgentField(\'' + preset.slug + '\',\'' + agentName + '\',\'' + f.key + '\',this.value)" style="width: 100%; padding: 6px; background: var(--bg-input); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; color: var(--text); font-size: 0.75rem; font-family: inherit; resize: vertical;">' + (val || '') + '</textarea>';
        } else if (f.type === 'checkbox') {
          html += '<input type="checkbox" ' + (val ? 'checked' : '') + ' onchange="tuningSaveAgentField(\'' + preset.slug + '\',\'' + agentName + '\',\'' + f.key + '\',this.checked)" style="width: 18px; height: 18px;">';
        } else if (f.type === 'number') {
          html += '<input type="number" min="' + (f.min || 0) + '" max="' + (f.max || 100) + '" value="' + (val !== undefined && val !== null ? val : '') + '" onchange="tuningSaveAgentField(\'' + preset.slug + '\',\'' + agentName + '\',\'' + f.key + '\',this.value)" style="width: 100px; padding: 4px 8px; background: var(--bg-input); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; color: var(--text);">';
        } else {
          html += '<input type="text" value="' + (val || '').toString().replace(/"/g, '&quot;') + '" onchange="tuningSaveAgentField(\'' + preset.slug + '\',\'' + agentName + '\',\'' + f.key + '\',this.value)" style="width: 100%; padding: 4px 8px; background: var(--bg-input); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; color: var(--text); font-size: 0.75rem;">';
        }
        html += '</div>';
      });
      html += '</div>';
    });
    grid.innerHTML = html;
  }

  window.tuningRender_agentConfig = async function(agentId) {
    const el = document.getElementById('presets-sub-content'); if (!el) return;
    el.innerHTML = '<div style="color:rgba(255,255,255,0.3);padding:20px;text-align:center;">Lade Presets…</div>';
    await loadPresetsData();
    let html = '<div class="panel" style="padding:16px;display:flex;flex-direction:column;gap:14px;">';
    html += '<h3 style="margin:0;font-size:0.95rem;">🎨 Agent-Konfiguration <span style="font-size:0.65rem;color:rgba(255,255,255,0.3);">— System + Worker · per-Agent</span></h3>';

    html += '<div id="presets-group-tabs" style="display: flex; gap: 4px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px;">';
    html += '<button class="preset-group-tab" id="preset-group-system" data-group="system" onclick="tuningSwitchPresetsGroup(\'system\')" style="padding: 6px 14px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px 4px 0 0; color: var(--text-dim); cursor: pointer; font-weight: 500;">System-Agents</button>';
    html += '<button class="preset-group-tab" id="preset-group-worker" data-group="worker" onclick="tuningSwitchPresetsGroup(\'worker\')" style="padding: 6px 14px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px 4px 0 0; color: var(--text-dim); cursor: pointer; font-weight: 500;">Worker-Agents</button>';
    html += '</div>';

    html += '<div style="display: flex; gap: 8px; align-items: center;">';
    html += '<label style="font-size: 0.75rem; color: var(--text-dim);">Preset:</label>';
    html += '<select id="presets-list-select" onchange="tuningLoadPresetForEdit(this.value)" style="flex: 1; padding: 6px 10px; background: var(--bg-input); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; color: var(--text); font-size: 0.8rem;"><option value="">— lädt —</option></select>';
    html += '<button class="btn-primary" onclick="tuningCreateNewPreset()" style="padding: 4px 10px; font-size: 0.7rem;">+ Neu</button>';
    html += '<button onclick="tuningCloneCurrentPreset()" style="padding: 4px 10px; font-size: 0.7rem; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: var(--text); border-radius: 4px; cursor: pointer;">Clone</button>';
    html += '<button onclick="tuningDeleteCurrentPreset()" style="padding: 4px 10px; font-size: 0.7rem; background: rgba(255,80,80,0.15); border: 1px solid rgba(255,80,80,0.4); color: #ff8888; border-radius: 4px; cursor: pointer;">Löschen</button>';
    html += '</div>';

    html += '<div id="presets-agents-grid" style="display: grid; grid-template-columns: 1fr; gap: 10px;">';
    html += '<p style="color: var(--text-dim); padding: 20px; text-align: center;">Wähle ein Preset zum Bearbeiten</p>';
    html += '</div>';

    html += '</div>';
    el.innerHTML = html;
    renderPresetsList();
    renderAgentsGrid();
    _styleActiveGroupTab();
  };

  function _styleActiveGroupTab() {
    if (!_presetsData) return;
    const group = _presetsData.activeGroup || 'system';
    document.querySelectorAll('.preset-group-tab').forEach(b => {
      if (b.dataset.group === group) {
        b.style.background = 'rgba(0, 229, 255, 0.18)';
        b.style.color = 'var(--primary)';
        b.style.borderColor = 'var(--primary)';
      } else {
        b.style.background = 'rgba(255,255,255,0.04)';
        b.style.color = 'var(--text-dim)';
        b.style.borderColor = 'rgba(255,255,255,0.08)';
      }
    });
  }

  window.tuningSwitchPresetsGroup = function(group) {
    if (!_presetsData) _presetsData = {slugs: [], currentPreset: null, activeGroup: group};
    else _presetsData.activeGroup = group;
    _styleActiveGroupTab();
    renderAgentsGrid();
  };

  window.tuningLoadPresetForEdit = async function(slug) {
    if (!slug) {
      _presetsData.currentPreset = null;
      renderAgentsGrid();
      return;
    }
    const p = _presetsData.slugs.find(x => x.slug === slug);
    if (!p) return;
    try {
      const r = await fetch('/api/presets/layer-a/' + encodeURIComponent(slug));
      _presetsData.currentPreset = await r.json();
      renderAgentsGrid();
    } catch (e) { alert('Fehler: ' + e.message); }
  };

  window.tuningCreateNewPreset = async function() {
    const name = prompt('Name des neuen Presets:');
    if (!name) return;
    try {
      const r = await fetch('/api/presets/layer-a', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, description: ''})
      });
      if (!r.ok) throw new Error(await r.text());
      await loadPresetsData();
      renderPresetsList();
      const j = await r.json();
      tuningLoadPresetForEdit(j.slug);
    } catch (e) { alert('Fehler beim Anlegen: ' + e.message); }
  };

  window.tuningCloneCurrentPreset = async function() {
    if (!_presetsData.currentPreset) return alert('Bitte erst Preset wählen');
    const name = prompt('Name für den Klon:', _presetsData.currentPreset.name + ' (Kopie)');
    if (!name) return;
    try {
      const r = await fetch('/api/presets/layer-a/' + encodeURIComponent(_presetsData.currentPreset.slug) + '/clone', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
      });
      if (!r.ok) throw new Error(await r.text());
      await loadPresetsData();
      renderPresetsList();
    } catch (e) { alert('Fehler beim Klonen: ' + e.message); }
  };

  window.tuningDeleteCurrentPreset = async function() {
    if (!_presetsData.currentPreset) return alert('Bitte erst Preset wählen');
    if (_presetsData.currentPreset.slug === 'default') return alert('"default" Preset kann nicht gelöscht werden');
    if (!confirm('Preset "' + _presetsData.currentPreset.name + '" wirklich löschen?')) return;
    try {
      const r = await fetch('/api/presets/layer-a/' + encodeURIComponent(_presetsData.currentPreset.slug), {method: 'DELETE'});
      if (!r.ok) throw new Error(await r.text());
      _presetsData.currentPreset = null;
      await loadPresetsData();
      renderPresetsList();
      renderAgentsGrid();
    } catch (e) { alert('Fehler beim Löschen: ' + e.message); }
  };

  window.tuningSaveAgentField = async function(slug, agentName, fieldKey, value) {
    try {
      const r = await fetch('/api/presets/layer-a/' + encodeURIComponent(slug) + '/agents/' + encodeURIComponent(agentName), {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({[fieldKey]: value})
      });
      if (!r.ok) throw new Error(await r.text());
      if (_presetsData.currentPreset && _presetsData.currentPreset.agents[agentName]) {
        _presetsData.currentPreset.agents[agentName][fieldKey] = value;
      }
      const el = document.querySelector(`[data-agent="${agentName}"][data-field="${fieldKey}"] .save-status`);
      if (el) { el.textContent = '✓ gespeichert'; el.style.color = '#4ade80'; setTimeout(() => { el.textContent = ''; }, 2000); }
    } catch (e) {
      alert('Fehler beim Speichern: ' + e.message);
    }
  };
})();

// ── Tab: Bake ──
window.tuningRender_bake = async function(agentId) {
  const el = document.getElementById('tuning-content'); if (!el) return;
  el.innerHTML = '<div style="color:rgba(255,255,255,0.3);padding:20px;text-align:center;">Lade...</div>';
  let presets = [];
  try { presets = await api('GET', '/presets') || []; } catch(e){}
  let preview = null;
  try { preview = await api('GET', '/admin/bake/preview'); } catch(e){}
  let html = '<div class="panel" style="padding:16px;display:flex;flex-direction:column;gap:16px;">';
  html += '<h3 style="margin:0;font-size:0.95rem;">🏭 SuperGNOM backen <span style="font-size:0.65rem;color:rgba(255,255,255,0.3);">— Standalone exportieren</span></h3>';
  html += '<p style="font-size:0.7rem;color:rgba(255,255,255,0.5);margin:0;">Erzeugt ein lauffähiges, portables Gnom-Hub Paket mit allen 8 Agenten, API-Key, Workspace und Presets.';

  // Name
  html += '<div><label style="font-size:0.7rem;display:block;margin-bottom:3px;">SuperGNOM-Name</label><input id="tbake-name" placeholder="z.B. meine_agenten" style="width:100%;max-width:400px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.12);color:#fff;border-radius:4px;padding:8px;font-size:0.8rem;"></div>';

  // Preset-Auswahl
  html += '<div><label style="font-size:0.7rem;display:block;margin-bottom:3px;">Preset (optional, alle Agents)</label><select id="tbake-preset" style="width:100%;max-width:400px;background:rgba(0,0,0,0.3);color:#fff;border:1px solid rgba(255,255,255,0.12);border-radius:4px;padding:8px;font-size:0.8rem;">';
  html += '<option value="">— Kein Preset (aktuellen Zustand backen) —</option>';
  presets.forEach(p => { html += '<option value="' + p.file + '">' + escapeHtml(p.name) + '</option>'; });
  html += '</select></div>';

  // Per-Agent Preset-Auswahl (v2 schema, sets preset per agent)
  const agents8 = [
    {key: 'soulag',      label: '🧠 SoulAG',      group: 'system'},
    {key: 'watchdogag',  label: '🐕 WatchdogAG',  group: 'system'},
    {key: 'generalag',   label: '🎩 GeneralAG',   group: 'system'},
    {key: 'securityag',  label: '🛡️ SecurityAG', group: 'system'},
    {key: 'writerag',    label: '✍️ WriterAG',    group: 'worker'},
    {key: 'coderag',     label: '💻 CoderAG',     group: 'worker'},
    {key: 'researcherag',label: '🔬 ResearcherAG',group: 'worker'},
    {key: 'editorag',    label: '📝 EditorAG',    group: 'worker'},
  ];
  html += '<div style="border:1px solid rgba(0,229,255,0.25);border-radius:6px;padding:10px;background:rgba(0,229,255,0.04);">';
  html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">';
  html += '<label style="font-size:0.75rem;font-weight:700;color:#0ef;">🎯 Preset pro Agent (v2-Schema)</label>';
  html += '<span style="font-size:0.6rem;color:rgba(255,255,255,0.4);">überschreibt das globale Preset für den jeweiligen Agenten</span>';
  html += '</div>';
  html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:6px;">';
  agents8.forEach(a => {
    html += '<div style="display:flex;align-items:center;gap:6px;">';
    html += '<label style="font-size:0.7rem;min-width:120px;">' + a.label + '</label>';
    html += '<select class="tbake-agent-preset" data-agent="' + a.key + '" style="flex:1;background:rgba(0,0,0,0.3);color:#fff;border:1px solid rgba(255,255,255,0.12);border-radius:4px;padding:5px;font-size:0.7rem;">';
    html += '<option value="">— Default —</option>';
    presets.forEach(p => { html += '<option value="' + p.file + '">' + escapeHtml(p.name) + '</option>'; });
    html += '</select></div>';
  });
  html += '</div></div>';

  // Template
  html += '<div><label style="font-size:0.7rem;display:block;margin-bottom:3px;">Template</label><select id="tbake-tpl" style="width:100%;max-width:400px;background:rgba(0,0,0,0.3);color:#fff;border:1px solid rgba(255,255,255,0.12);border-radius:4px;padding:8px;font-size:0.8rem;">';
  html += '<option value="chat">Chat (Standard)</option><option value="minimal">Minimal (nur API)</option><option value="full">Full (Chat + Workspace)</option></select></div>';

  // LLM-Modelle Auswahl
  html += '<div style="border:1px solid rgba(255,150,0,0.3);border-radius:6px;padding:12px;background:rgba(255,150,0,0.04);">';
  html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">';
  html += '<label style="font-size:0.75rem;font-weight:700;color:#fa0;">🤖 Lokale LLMs mitbacken</label>';
  html += '<span style="font-size:0.65rem;color:rgba(255,255,255,0.4);">Auto-Pull beim ersten Start</span>';
  html += '</div>';
  html += '<div style="font-size:0.68rem;color:rgba(255,255,255,0.55);margin-bottom:8px;line-height:1.4;">';
  html += 'Modelle werden beim Start auf dem Ziel-Mac per <code>ollama pull</code> geladen. Internet beim ersten Start erforderlich.';
  html += '</div>';
  if (preview && preview.intersection) {
    const inter = preview.intersection;
    html += '<div id="tbake-models-info" style="font-size:0.7rem;color:rgba(255,255,255,0.6);margin-bottom:8px;">';
    html += 'Ollama gesamt: <b>' + inter.total_ollama_size_gb + ' GB</b> installiert | ';
    html += 'Schnittmenge mit routing.txt: <b>' + inter.matches.length + '</b> Modelle';
    if (inter.routing_only.length) html += ' | Routing-only (nicht lokal): <b>' + inter.routing_only.length + '</b>';
    html += '</div>';
    if (inter.matches.length) {
      html += '<div style="display:flex;flex-direction:column;gap:4px;margin-bottom:6px;">';
      html += '<div style="font-size:0.7rem;color:#0f0;">✅ Schnittmenge (in Ollama + routing.txt) — vorausgewählt:</div>';
      inter.matches.forEach(m => {
        html += '<label style="font-size:0.7rem;display:flex;align-items:center;gap:6px;cursor:pointer;padding:4px 6px;background:rgba(0,255,0,0.05);border-radius:3px;">';
        html += '<input type="checkbox" class="tbake-model-cb" data-name="' + escapeHtml(m.name) + '" checked> ';
        html += '<span>' + escapeHtml(m.name) + '</span>';
        html += '<span style="margin-left:auto;color:rgba(255,255,255,0.4);">' + m.size_gb + ' GB</span>';
        html += '</label>';
      });
      html += '</div>';
    }
    if (inter.ollama_only.length) {
      html += '<div style="display:flex;flex-direction:column;gap:4px;margin-bottom:6px;">';
      html += '<div style="font-size:0.7rem;color:rgba(255,255,255,0.4);">ℹ️ Nur in Ollama (nicht in routing.txt):</div>';
      inter.ollama_only.forEach(m => {
        html += '<label style="font-size:0.7rem;display:flex;align-items:center;gap:6px;cursor:pointer;padding:4px 6px;opacity:0.7;">';
        html += '<input type="checkbox" class="tbake-model-cb" data-name="' + escapeHtml(m.name) + '"> ';
        html += '<span>' + escapeHtml(m.name) + '</span>';
        html += '<span style="margin-left:auto;color:rgba(255,255,255,0.4);">' + m.size_gb + ' GB</span>';
        html += '</label>';
      });
      html += '</div>';
    }
    if (inter.routing_only.length) {
      html += '<div style="font-size:0.7rem;color:#f80;margin-top:4px;">⚠️ In routing.txt aber NICHT lokal installiert: ';
      html += inter.routing_only.map(m => m.name).join(', ');
      html += ' (brauchen Internet-Provider)</div>';
    }
    html += '<div id="tbake-models-total" style="font-size:0.7rem;color:#fa0;margin-top:6px;font-weight:700;"></div>';
  } else {
    html += '<div style="font-size:0.7rem;color:#f80;">⚠️ Ollama nicht erreichbar. Bake läuft ohne lokale Modelle.</div>';
  }
  html += '</div>';

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
  // Live-Total updaten wenn Checkboxen ändern
  document.querySelectorAll('.tbake-model-cb').forEach(cb => {
    cb.addEventListener('change', updateBakeTotal);
  });
  updateBakeTotal();
};

function updateBakeTotal() {
  const totalEl = document.getElementById('tbake-models-total');
  if (!totalEl) return;
  const checked = Array.from(document.querySelectorAll('.tbake-model-cb:checked'));
  let total_gb = 0;
  checked.forEach(cb => {
    const label = cb.parentElement;
    const m = label.textContent.match(/(\d+\.\d+)\s*GB/);
    if (m) total_gb += parseFloat(m[1]);
  });
  if (checked.length === 0) {
    totalEl.innerHTML = 'Keine Modelle gewählt — Bake ohne lokale LLMs. Zielsystem braucht Internet-Provider (DeepSeek etc.).';
    totalEl.style.color = 'rgba(255,255,255,0.4)';
  } else {
    totalEl.innerHTML = checked.length + ' Modelle | ' + total_gb.toFixed(2) + ' GB Download | Modus: AUTO-PULL beim ersten Start';
    totalEl.style.color = '#fa0';
  }
}

window.tuningDoBake = async function() {
  const name = document.getElementById('tbake-name')?.value?.trim();
  const preset = document.getElementById('tbake-preset')?.value;
  const tpl = document.getElementById('tbake-tpl')?.value || 'chat';
  const withKey = document.getElementById('tbake-api')?.checked;
  const selectedModels = Array.from(document.querySelectorAll('.tbake-model-cb:checked'))
    .map(cb => cb.getAttribute('data-name'));
  const presetSelections = {};
  document.querySelectorAll('.tbake-agent-preset').forEach(sel => {
    const v = sel.value;
    if (v) presetSelections[sel.getAttribute('data-agent')] = v;
  });
  const resultEl = document.getElementById('tbake-result');
  if (!name) { toast('Bitte Namen eingeben', 'warning'); return; }
  resultEl.innerHTML = '<span style="color:#fa0;">⏳ Starte Bake-Job...</span>';
  try {
    const body = {name, template: tpl, embed_api_key: withKey, selected_models: selectedModels, preset_selections: presetSelections};
    if (preset) body.preset_file = preset;
    const start = await api('POST', '/admin/bake/start', body);
    if (!start || !start.job_id) { resultEl.innerHTML = '<span style="color:#f44;">❌ Fehler beim Starten</span>'; return; }
    resultEl.innerHTML = '<span style="color:#fa0;">⏳ Backe... Job ' + start.job_id + '</span>';
    // Poll until done
    for (let i = 1; i <= 60; i++) {
      await new Promise(r => setTimeout(r, 2000));
      const st = await api('GET', '/admin/bake/status/' + start.job_id);
      if (!st || st.status === 'not_found') { resultEl.innerHTML = '<span style="color:#f44;">❌ Job verloren</span>'; return; }
      if (st.status === 'finished') {
        resultEl.innerHTML = '<span style="color:#0f0;">✅ Gebacken: <b style="font-family:monospace;">' + st.path + '</b></span>';
        toast('SuperGNOM gebacken!', 'success');
        return;
      }
      if (st.status === 'error') {
        resultEl.innerHTML = '<span style="color:#f44;">❌ ' + (st.error || 'Fehler') + '</span>';
        return;
      }
      resultEl.innerHTML = '<span style="color:#fa0;">⏳ Backe... (' + (i*2) + 's)</span>';
    }
    resultEl.innerHTML = '<span style="color:#f44;">❌ Timeout nach 2 Min</span>';
  } catch(e) { resultEl.innerHTML = '<span style="color:#f44;">❌ ' + e.message + '</span>'; }
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
  // Inline edit: autosave on blur or Escape-to-cancel. No more per-row Save button.
  el.innerHTML = `<textarea id="modal-ed-${id}" data-mem-autosave="${id}" data-mem-agent="${agentId}" style="width: 100%; min-height: 60px; background: rgba(0,0,0,0.3); border: 1px solid rgba(91,156,246,0.4); color: #fff; border-radius: 6px; padding: 6px; font-size: 0.8rem; outline: none; resize: vertical;">${old}</textarea>
    <div style="margin-top:6px;display:flex;gap:6px;justify-content:flex-end; font-size:0.7rem; color:var(--text-dim);">
      <span>Speichert automatisch beim Verlassen des Feldes · <a href="#" onclick="loadModalAgentMemory('${agentId}'); return false;" style="color:var(--cyan);">Abbrechen</a></span>
    </div>`;
  const ta = document.getElementById('modal-ed-' + id);
  ta.focus();
  ta.setSelectionRange(ta.value.length, ta.value.length);
  const autosave = async () => {
    const c = ta.value;
    try {
      await api('PUT', `/memory/${id}`, { content: c });
      toast('Erinnerung aktualisiert', 'success');
      loadModalAgentMemory(agentId);
    } catch (e) {
      toast('Speichern fehlgeschlagen: ' + e.message, 'error');
    }
  };
  ta.addEventListener('blur', autosave, { once: true });
  ta.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape') { ev.preventDefault(); loadModalAgentMemory(agentId); }
    if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) { ev.preventDefault(); ta.blur(); }
  });
};

// saveModalMem is intentionally removed — edits autosave on blur now.
// Kept as a stub so old onclick handlers (e.g. cache) don't break; just
// performs an immediate PUT like before.
window.saveModalMem = async function(id, agentId) {
  const ta = document.getElementById('modal-ed-' + id);
  if (!ta) return;
  const c = ta.value;
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
  const listContainer = document.getElementById('workflows-list-container');
  if (!listContainer) return;

  // 1) Workflow-Liste laden — bei Fehlern explizit eine Empty-State-UI zeigen,
  //    damit der View nicht im 'Lade Workflows...'-State hängenbleibt.
  let workflows = [];
  try {
    const res = await api('GET', '/workflows', null, { silent: true, timeout: 8000 });
    workflows = Array.isArray(res) ? res : [];
  } catch (e) {
    if (e && e.timeout) {
      listContainer.innerHTML = `<div class="empty" style="color:#f59e0b;">⏱ Backend antwortet nicht (Timeout). <a href="javascript:void(0)" onclick="loadWorkflowsViewData()" style="color:var(--cyan); text-decoration:underline;">Retry</a></div>`;
    } else if (e && e.status) {
      listContainer.innerHTML = `<div class="empty" style="color:#ef4444;">✗ Backend Fehler ${e.status}: ${escapeHtml(String(e.message).slice(0, 200))}. <a href="javascript:void(0)" onclick="loadWorkflowsViewData()" style="color:var(--cyan); text-decoration:underline;">Retry</a></div>`;
    } else {
      listContainer.innerHTML = `<div class="empty" style="color:#ef4444;">✗ Netzwerkfehler. <a href="javascript:void(0)" onclick="loadWorkflowsViewData()" style="color:var(--cyan); text-decoration:underline;">Retry</a></div>`;
    }
    return;
  }

  if (workflows.length === 0) {
    listContainer.innerHTML = '<div class="empty">Keine Workflows registriert</div>';
  } else {
    // Render workflows list — robust gegen fehlende Felder
    listContainer.innerHTML = workflows.map(w => {
      let badgeColor = '#555';
      const st = (w.status || 'pending').toLowerCase();
      if (st === 'running') badgeColor = '#00e5ff';
      else if (st === 'completed') badgeColor = '#10b981';
      else if (st === 'failed') badgeColor = '#ef4444';

      const isSelected = activeWorkflowId === w.id;
      // created_at kann Unix-ts (float) ODER ISO-String sein — beides abfangen
      let timeStr = '—';
      const ca = w.created_at;
      if (typeof ca === 'number') {
        timeStr = new Date(ca * 1000).toLocaleTimeString();
      } else if (typeof ca === 'string') {
        const d = new Date(ca);
        if (!isNaN(d.getTime())) timeStr = d.toLocaleTimeString();
      }

      const durationSec = (w.completed_at && typeof w.completed_at === 'number'
                           && typeof w.created_at === 'number')
                          ? (w.completed_at - w.created_at).toFixed(1) : null;

      return `
        <div onclick="selectWorkflow('${w.id}')" style="padding:10px; background:${isSelected ? 'rgba(0,229,255,0.08)' : 'rgba(255,255,255,0.02)'}; border:${isSelected ? '1px solid var(--accent)' : '1px solid rgba(255,255,255,0.05)'}; border-radius:8px; cursor:pointer; transition:var(--transition); display:flex; flex-direction:column; gap:4px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:#fff; font-size:0.85rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:180px;">${escapeHtml(w.name)}</strong>
            <span style="font-size:0.65rem; font-weight:bold; color:${badgeColor}; border:1px solid ${badgeColor}33; border-radius:4px; padding:1px 4px; text-transform:uppercase;">${escapeHtml(st)}</span>
          </div>
          <div style="font-size:0.72rem; color:var(--text-muted); display:flex; justify-content:space-between;">
            <span>Start: ${timeStr}</span>
            ${durationSec !== null ? `<span>Dauer: ${durationSec}s</span>` : ''}
          </div>
        </div>
      `;
    }).join('');
  }

  // 2) Observability-Metriken — non-blocking; Fehler werden ignoriert mit Empty-State
  let obs = null;
  try {
    obs = await api('GET', '/observability/metrics', null, { silent: true, timeout: 6000 });
  } catch (e) {
    obs = null;
  }
  const summaryContainer = document.getElementById('obs-summary-container');
  const agentBreakdown = document.getElementById('obs-agent-breakdown');
  const capBreakdown = document.getElementById('obs-capability-breakdown');

  if (!obs) {
    if (summaryContainer) summaryContainer.innerHTML = '<div class="empty">Telemetrie nicht erreichbar</div>';
    if (agentBreakdown) agentBreakdown.innerHTML = '<div class="empty">Telemetrie nicht erreichbar</div>';
    if (capBreakdown) capBreakdown.innerHTML = '<div class="empty">Telemetrie nicht erreichbar</div>';
  } else {
    if (summaryContainer) {
      const summary = obs.workflows_summary || { total_count: 0, completed_count: 0, failed_count: 0, avg_duration_s: 0 };
      const avgDur = Number(summary.avg_duration_s || 0).toFixed(1);
      summaryContainer.innerHTML = `
        <div style="display:flex; justify-content:space-between;"><span>Gesamt Workflows:</span><strong style="color:#fff;">${summary.total_count || 0}</strong></div>
        <div style="display:flex; justify-content:space-between;"><span>Erfolgreich:</span><strong style="color:#10b981;">${summary.completed_count || 0}</strong></div>
        <div style="display:flex; justify-content:space-between;"><span>Fehlgeschlagen:</span><strong style="color:#ef4444;">${summary.failed_count || 0}</strong></div>
        <div style="display:flex; justify-content:space-between; border-top:1px solid rgba(255,255,255,0.05); padding-top:6px; margin-top:4px;"><span>Ø Workflow-Laufzeit:</span><strong style="color:var(--cyan);">${avgDur}s</strong></div>
      `;
    }

    if (agentBreakdown) {
      if (!obs.agents || obs.agents.length === 0) {
        agentBreakdown.innerHTML = '<div class="empty">Keine Metriken vorhanden</div>';
      } else {
        agentBreakdown.innerHTML = obs.agents.map(a => {
          const successPercent = ((a.success_rate || 0) * 100).toFixed(0);
          return `
            <div style="padding:6px 10px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:6px; display:flex; justify-content:space-between; align-items:center; font-size:0.75rem;">
              <strong style="color:#fff; text-transform:capitalize;">${escapeHtml((a.agent_name || '?').replace('ag', 'AG'))}</strong>
              <div style="display:flex; gap:12px; color:var(--text-dim);">
                <span>Queue: <strong style="color:#fff;">${(a.avg_queue_wait_ms || 0).toFixed(0)}ms</strong></span>
                <span>Exec: <strong style="color:#fff;">${(a.avg_exec_time_ms || 0).toFixed(0)}ms</strong></span>
                <span style="color:${(a.success_rate || 0) >= 0.9 ? '#10b981' : '#f59e0b'};">Ok: ${successPercent}%</span>
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
          const successPercent = ((c.success_rate || 0) * 100).toFixed(0);
          return `
            <div style="padding:6px 10px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:6px; display:flex; justify-content:space-between; align-items:center; font-size:0.75rem;">
              <strong style="color:#fff; text-transform:uppercase; letter-spacing:0.5px;">${escapeHtml(c.capability || '?')}</strong>
              <div style="display:flex; gap:12px; color:var(--text-dim);">
                <span>Queue: <strong style="color:#fff;">${(c.avg_queue_wait_ms || 0).toFixed(0)}ms</strong></span>
                <span>Exec: <strong style="color:#fff;">${(c.avg_exec_time_ms || 0).toFixed(0)}ms</strong></span>
                <span style="color:${(c.success_rate || 0) >= 0.9 ? '#10b981' : '#f59e0b'};">Ok: ${successPercent}%</span>
              </div>
            </div>
          `;
        }).join('');
      }
    }
  }

  // Draw current active workflow DAG (nur wenn aktiv — vermeidet unnötige Calls)
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
    wf = await api('GET', `/workflows/${workflowId}`, null, { silent: true, timeout: 8000 });
  } catch (e) {
    canvas.innerHTML = `<div class="empty" style="color:#ef4444;">Fehler beim Laden: ${escapeHtml(String(e.message).slice(0, 200))}</div>`;
    return;
  }

  if (!wf) {
    canvas.innerHTML = '<div class="empty">Workflow nicht gefunden</div>';
    return;
  }

  title.textContent = `Workflow: ${wf.name || '(unnamed)'}`;

  const tasks = Array.isArray(wf.tasks) ? wf.tasks : [];
  if (tasks.length === 0) {
    canvas.innerHTML = '<div class="empty">Keine Tasks in diesem Workflow</div>';
    return;
  }

  // Topological sorting / levels calculation (iterativ + cycle-safe)
  const levels = {};
  const tasksMap = {};
  tasks.forEach(t => {
    tasksMap[t.task_id] = t;
  });

  // Iterative Berechnung statt Rekursion: vermeidet Stack-Overflow bei
  // zyklischen depends_on (A → B → A). MAX_LEVELS als Cycle-Stop.
  const MAX_LEVELS = tasks.length + 1;
  for (let iter = 0; iter < MAX_LEVELS; iter++) {
    let progress = false;
    for (const t of tasks) {
      if (levels[t.task_id] !== undefined) continue;
      const deps = (Array.isArray(t.depends_on) ? t.depends_on : []).filter(d => tasksMap[d]);
      if (deps.length === 0) {
        levels[t.task_id] = 0;
        progress = true;
      } else {
        const depLevels = deps.map(d => levels[d]).filter(l => typeof l === 'number');
        if (depLevels.length === deps.length) {
          levels[t.task_id] = Math.max(...depLevels) + 1;
          progress = true;
        }
      }
    }
    if (!progress) break;
  }
  // Tasks, die nach MAX_LEVELS noch keine Level haben → Cycle: gib ihnen Level 0 + Warning
  let hasCycle = false;
  for (const t of tasks) {
    if (levels[t.task_id] === undefined) {
      levels[t.task_id] = 0;
      hasCycle = true;
    }
  }
  if (hasCycle) {
    console.warn(`[drawWorkflowDAG] Cycle detected in workflow ${workflowId}; rendering with best-effort layout`);
  }

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
        <text x="12" y="24" fill="#fff" font-size="0.82rem" font-weight="700" style="${textGlow}">${escapeHtml(t.task_id || '(unnamed)')}</text>

        <!-- Capability badge (null-safe) -->
        <text x="12" y="42" fill="rgba(255,255,255,0.5)" font-size="0.68rem" font-weight="500" font-family="monospace">${escapeHtml((t.capability || 'unknown').toUpperCase())}</text>

        <!-- Status & Duration -->
        <text x="12" y="58" fill="rgba(255,255,255,0.4)" font-size="0.62rem">
          Status: <tspan fill="${t.status === 'completed' ? '#10b981' : t.status === 'failed' ? '#ef4444' : '#fff'}">${escapeHtml((t.status || 'pending').toUpperCase())}</tspan>
        </text>
      </g>
    `;

    // Optional: error_summary als kleines Tooltip-Element unter der Karte
    if (t.status === 'failed' && t.error_summary) {
      const errY = pos.y + nodeHeight + 14;
      const errText = String(t.error_summary).slice(0, 60);
      svg += `
        <g transform="translate(${pos.x}, ${errY})">
          <rect x="0" y="0" width="${nodeWidth}" height="14" rx="3"
                fill="rgba(239,68,68,0.18)" stroke="rgba(239,68,68,0.4)" stroke-width="1" />
          <text x="6" y="10" fill="#ef4444" font-size="0.6rem" font-family="monospace">✗ ${escapeHtml(errText)}</text>
        </g>
      `;
    }
  });

  svg += `</svg>`;
  // Falls Cycle: Warning-Banner über dem Canvas einblenden
  if (hasCycle) {
    const banner = `
      <div style="position:absolute; top:6px; left:6px; padding:6px 10px; background:rgba(245,158,11,0.15); border:1px solid #f59e0b; border-radius:6px; color:#f59e0b; font-size:0.72rem; z-index:10;">
        ⚠️ Zyklus in depends_on erkannt — DAG wird unvollständig dargestellt
      </div>`;
    canvas.innerHTML = banner + svg;
  } else {
    canvas.innerHTML = svg;
  }
}

async function refreshWorkflowsView() {
  if (!document.getElementById('workflows-panel')) {
    stopWorkflowPolling();
    return;
  }
  await loadWorkflowsViewData();
}

// ====================================================================
// Provider Registry — single source of truth, fetched from the backend.
// Replaces the hardcoded pvdOf() switch chain. The backend exposes
// /api/llm/providers which returns id, display_name, caps, category,
// key_prefixes, label_patterns and a sensible default_model per provider.
// ====================================================================

window.__llmProviderRegistry = null;
window.__llmProviderRegistryPromise = null;

async function loadProviderRegistry(force = false) {
  if (!force && window.__llmProviderRegistry) return window.__llmProviderRegistry;
  if (!force && window.__llmProviderRegistryPromise) return window.__llmProviderRegistryPromise;
  window.__llmProviderRegistryPromise = (async () => {
    try {
      const r = await fetch('/api/llm/providers');
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const data = await r.json();
      window.__llmProviderRegistry = data;
      return data;
    } catch (e) {
      console.warn('[llm] provider registry fetch failed, using empty stub:', e);
      window.__llmProviderRegistry = { providers: [], categories: [], defaults: { web_search: {}, tts: {} } };
      return window.__llmProviderRegistry;
    }
  })();
  return window.__llmProviderRegistryPromise;
}

function registryProviderById(id) {
  const reg = window.__llmProviderRegistry;
  if (!reg) return null;
  return reg.providers.find(p => p.id === id) || null;
}

function registryProvidersByCategory(category) {
  const reg = window.__llmProviderRegistry;
  if (!reg) return [];
  return reg.providers.filter(p => p.category === category);
}

// Generic detect-from-string: walks the registry's key_prefixes + label_patterns
// + display_name substring instead of relying on a hardcoded switch chain.
// Falls back to the first matching provider if multiple matches.
//
// Prefix matching is sorted by prefix length DESC so that `sk-cp-` beats the
// generic `sk-` prefix that several providers share.
function detectProviderByRegistry(s) {
  const reg = window.__llmProviderRegistry;
  if (!reg || !s) return null;
  const lower = String(s).toLowerCase();

  // 1. Prefix match — collect (provider, prefix) pairs, sort by length DESC.
  const prefixMatches = [];
  for (const p of reg.providers) {
    for (const prefix of (p.key_prefixes || [])) {
      if (prefix && lower.startsWith(String(prefix).toLowerCase())) {
        prefixMatches.push({ id: p.id, len: String(prefix).length });
      }
    }
  }
  if (prefixMatches.length > 0) {
    prefixMatches.sort((a, b) => b.len - a.len);
    return prefixMatches[0].id;
  }
  // 2. Label substring match (label_patterns OR display_name substring)
  for (const p of reg.providers) {
    for (const pat of (p.label_patterns || [])) {
      if (pat && lower.includes(String(pat).toLowerCase())) return p.id;
    }
    if (p.display_name && lower.includes(String(p.display_name).toLowerCase())) return p.id;
  }
  return null;
}

// Keep the legacy export name so existing callers (parseKeyLines) still work.
function pvdOf(s) { return detectProviderByRegistry(s); }

window.loadProviderRegistry = loadProviderRegistry;
window.detectProviderByRegistry = detectProviderByRegistry;
window.registryProvidersByCategory = registryProvidersByCategory;
window.registryProviderById = registryProviderById;

// ====================================================================
// Pending changes tracker — surfaces unsaved state to the global Save
// button (header) and the beforeunload guard. Each module (LLM page,
// worker sidebar, agent-tuning modal, ...) can register / clear / flush
// its own change-set via window.llmPendingChanges.
// ====================================================================

window.llmPendingChanges = {
  agents:   {},   // agent_name → { provider, model }
  web_search: {}, // { provider, model, key_id? }
  tts:       {},  // { provider, model, key_id? }
  hasAny() {
    return Object.keys(this.agents).length > 0
        || Object.keys(this.web_search).length > 0
        || Object.keys(this.tts).length > 0;
  },
  clear() { this.agents = {}; this.web_search = {}; this.tts = {}; },
  summary() {
    const parts = [];
    if (Object.keys(this.agents).length)   parts.push(`${Object.keys(this.agents).length} agent(s)`);
    if (Object.keys(this.web_search).length) parts.push('Web Search');
    if (Object.keys(this.tts).length)        parts.push('TTS');
    return parts.join(', ');
  },
};

// ── Visual badge on the global Save button ──
function updateSaveBadge() {
  const btn = document.getElementById('btn-save');
  if (!btn) return;
  const has = window.llmPendingChanges.hasAny();
  btn.classList.toggle('pending', has);
  const orig = btn.getAttribute('data-orig-text') || btn.textContent;
  if (!btn.getAttribute('data-orig-text')) btn.setAttribute('data-orig-text', orig);
  btn.textContent = has ? `Save · ${window.llmPendingChanges.summary()}` : orig;
  btn.title = has ? 'Ungespeicherte Änderungen: ' + window.llmPendingChanges.summary() : 'Global speichern';
}
window.updateSaveBadge = updateSaveBadge;
