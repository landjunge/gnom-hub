/* showbox-module.js — Konsolidiertes Showbox-Modul (Render + State + Button-Grid)

   Vereinigt die ehemaligen Dateien:
     • showbox.js          (Render-Engine, State, Layers, Overlay, Help-Slides)
     • showbox-buttons.js  (8 dynamische Buttons im 2x4-Grid)

   Single source of truth. Kein window.ShowboxButtons mehr — die Render-Pipeline
   ruft die Button-Grid-Logik intern synchron auf, KEIN Race-Condition mehr
   durch Script-Load-Order. Public API: window.ShowboxModule (alte Aufrufer
   bekommen einen Backward-Compat-Shim auf window.ShowboxButtons).

   PARSE-LOGIK IDENTISCH ZU gnom_hub.frontend.showbox_button_parser (Python).
   Wenn du hier etwas änderst, MUSST du es im Python-Pendant nachziehen.

   Inline-Button-Extraktion unterstützt jetzt BEIDE Formate:
     Format A (Worker-HTML):
       <button action="approve_docs" label="Ja, Doku parallel">OK</button>
       <button action="run_python" label="Python-Playwright">  (ohne </button>!)
     Format B (DOM-Hooks für gerendertes HTML):
       <button data-sb-action="close" data-sb-label="Schließen" data-sb-color="red">
*/

(function () {
  // 3 Layers configuration
  const LAYERS = {
    SYSTEM: 1, // System-Agenten (GeneralAG, SoulAG, SecurityAG, WatchdogAG, System)
    WORKER: 2, // Worker (CoderAG, WriterAG, ResearcherAG, EditorAG)
    USER: 3    // User / Entscheidungen
  };

  // ── Button-Grid-Konstanten (2x4 = max 8 Slots) ────────────────────────
  const MAX_BUTTONS = 8;
  const DEFAULT_BUTTON_ICON = "▶";

  // Button-State (Ersatz für showbox-buttons.js:24)
  const buttons = new Array(MAX_BUTTONS).fill(null);

  // State management per layer
  const state = {
    activeLayer: LAYERS.SYSTEM,
    layers: {
      [LAYERS.SYSTEM]: {
        name: "System-Agenten",
        history: [], // Array of presentations: { name, slides: [], sender, currentSlideIdx }
        currentHistoryIdx: -1
      },
      [LAYERS.WORKER]: {
        name: "Worker",
        history: [],
        currentHistoryIdx: -1
      },
      [LAYERS.USER]: {
        name: "User / Entscheidung",
        history: [],
        currentHistoryIdx: -1
      }
    }
  };

  // Global references
  window.showboxPresentations = [];
  window.showboxes = [];
  window.activeShowboxIndex = -1;
  window.showboxActive = false;
  window.showboxManualNavigation = false;

  let toastRevertTimeout = null;
  let activeDecisionId = null;

  function cancelToastRevert() {
    if (toastRevertTimeout) {
      clearTimeout(toastRevertTimeout);
      toastRevertTimeout = null;
    }
  }

  async function handleOkAction() {
    if (!activeDecisionId) return;
    toast('Entscheidung gesendet: Erlauben', 'success');
    if (typeof window.api === 'function') {
      await window.api('POST', '/chat', { content: `@@approve_decision ${activeDecisionId}` });
      if (typeof window.loadChat === 'function') window.loadChat();
    }
  }

  async function handleCancelAction() {
    if (!activeDecisionId) return;
    toast('Entscheidung gesendet: Ablehnen', 'warning');
    if (typeof window.api === 'function') {
      await window.api('POST', '/chat', { content: `@@reject_decision ${activeDecisionId}` });
      if (typeof window.loadChat === 'function') window.loadChat();
    }
  }

  function initHTML(container) {
    container.classList.add('modular-showbox');
    container.innerHTML = `
      <div class="showbox-layers-container" id="sb-layers-container">
        <div class="sb-layer active" id="sb-layer-1" data-layer="1">
          <span class="sb-layer-label"><span class="sb-layer-id">#1001</span>System-Agenten</span>
          <span class="sb-layer-description">Aktivität & System-Status</span>
          <div class="sb-layer-body" id="sb-layer-body-1">STANDBY</div>
        </div>
        <div class="sb-layer" id="sb-layer-2" data-layer="2">
          <span class="sb-layer-label"><span class="sb-layer-id">#1002</span>Worker</span>
          <span class="sb-layer-description">Arbeitsberichte & Entwürfe</span>
          <div class="sb-layer-body" id="sb-layer-body-2">STANDBY</div>
        </div>
        <div class="sb-layer" id="sb-layer-3" data-layer="3">
          <span class="sb-layer-label"><span class="sb-layer-id">#1003</span>User / Entscheidung</span>
          <span class="sb-layer-description">Freigaben & Blockaden</span>
          <div class="sb-layer-body" id="sb-layer-body-3">STANDBY</div>
        </div>
      </div>
      <div class="showbox-controls" id="showbox-control-buttons"></div>
    `;
  }

  function initLayers() {
    const container = document.getElementById('sb-layers-container');
    if (container) {
      container.addEventListener('dblclick', () => {
        if (typeof window.openShowboxOverlay === 'function') {
          window.openShowboxOverlay();
        }
      });
    }
    for (let i = 1; i <= 3; i++) {
      const layerEl = document.getElementById(`sb-layer-${i}`);
      if (layerEl) {
        layerEl.addEventListener('click', (e) => {
          if (e.target.closest('button') || e.target.closest('a') || e.target.closest('.showbox-controls') || e.target.closest('.showbox-extra-controls')) return;
          cancelToastRevert();
          switchLayer(i);
        });
      }
    }
  }

  // Initialize modular Showbox DOM structure
  function init() {
    const container = document.getElementById('modular-showbox-container');
    if (!container) {
      console.warn("Modular Showbox container (#modular-showbox-container) not found in DOM.");
      return;
    }
    initHTML(container);
    initLayers();
    switchLayer(state.activeLayer, true);
  }

  // Determine which of the 3 layers a presentation belongs to
  function resolveTargetLayer(sender, name, slides) {
    const s = (sender || '').toLowerCase().trim();
    const n = (name || '').toLowerCase().trim();
    const slideStr = JSON.stringify(slides).toLowerCase();

    // 1. Critical decision blockades, ja/nein questions, or explicit user senders go to Layer 3 (User)
    if (s === 'user' || s === 'you' || n.startsWith('blockade:') || slideStr.includes('@@approve_decision') || slideStr.includes('@@reject_decision') || slideStr.includes('ja, aktion erlauben')) {
      return LAYERS.USER;
    }

    // 2. System orchestrators go to Layer 1 (System-Agenten)
    const systemAgents = ['generalag', 'soulag', 'securityag', 'watchdogag', 'system', ''];
    if (systemAgents.includes(s)) {
      return LAYERS.SYSTEM;
    }

    // 3. All other worker agents (CoderAG, WriterAG, etc.) go to Layer 2 (Worker)
    return LAYERS.WORKER;
  }

  // Switch the active layer in the DOM and trigger the frame flash animation
  function switchLayer(layerIdx, skipFlash = false) {
    if (![1, 2, 3].includes(layerIdx)) return;

    originalShowboxContent = null;
    originalActiveLayer = null;

    state.activeLayer = layerIdx;

    // Toggle active class on DOM layer elements
    for (let i = 1; i <= 3; i++) {
      const el = document.getElementById(`sb-layer-${i}`);
      if (el) {
        if (i === layerIdx) {
          el.classList.add('active');
        } else {
          el.classList.remove('active');
        }
      }
    }

    // Toggle body active layer classes
    document.body.classList.remove('sb-active-layer-1', 'sb-active-layer-2', 'sb-active-layer-3');
    document.body.classList.add(`sb-active-layer-${layerIdx}`);

    // Trigger frame flash/glow animation
    const container = document.getElementById('sb-layers-container');
    if (container && !skipFlash) {
      container.classList.remove('flash-1', 'flash-2', 'flash-3');
      void container.offsetWidth; // Force CSS reflow
      container.classList.add(`flash-${layerIdx}`);
    }

    // Add flash classes on borders based on the new active layer
    const agentList = document.getElementById('agent-list');
    const statusLamps = document.getElementById('status-lamps');
    
    if (agentList) {
      agentList.classList.remove('flash-active');
    }
    if (statusLamps) {
      statusLamps.classList.remove('flash-active');
    }

    if (!skipFlash) {
      // Force CSS reflow to restart the animation if it was already running
      if (agentList) void agentList.offsetWidth;
      if (statusLamps) void statusLamps.offsetWidth;
      
      if (layerIdx === 1 && statusLamps) {
        statusLamps.classList.add('flash-active');
      } else if (layerIdx === 2 && agentList) {
        agentList.classList.add('flash-active');
      }
    }

  }

  // Scale font sizes dynamically so slide content fits the viewport
  function autoFitText(layerIdx) {
    const body = document.getElementById(`sb-layer-body-${layerIdx}`);
    const layerEl = document.getElementById(`sb-layer-${layerIdx}`);
    if (!body || !layerEl) return;

    let size = 40;
    body.style.fontSize = size + 'px';

    // Iteratively decrease font size until height & width fit container bounds
    while ((body.scrollHeight > layerEl.clientHeight - 36 || body.scrollWidth > layerEl.clientWidth - 16) && size > 11) {
      size -= 2;
      body.style.fontSize = size + 'px';
    }
  }

  function updateDecisionButtons(decisionId) {
    activeDecisionId = decisionId;
  }

  // ── Inline-Button-Extraktion (BEIDE Formate) ─────────────────────────────
  // PARSE-LOGIK IDENTISCH ZU gnom_hub.frontend.showbox_button_parser.py.
  //
  // Format A: <button action="X" label="Y">...</button>  (Worker-HTML, häufig ohne </button>)
  // Format B: <button data-sb-action="X" data-sb-label="Y" data-sb-icon="..." data-sb-color="...">
  //
  // Robust gegen:
  //   • fehlende </button> close-tags (häufig in LLM-Outputs!)
  //   • Single ODER Double Quotes
  //   • beliebige Reihenfolge der Attribute
  //   • optionale label/data-sb-label Attribute
  function extractInlineButtons(domBody, rawSlide) {
    const out = [];
    const seen = new Set();
    const sources = [];

    // 1. Raw-Slide-String (Format A) — vor sanitizeHTML, weil sanitizeHTML
    //    zwar action/label behält, aber `body.innerHTML = sanitizeHTML(slide)`
    //    kann theoretisch Tags normalisieren. Raw ist die Original-Quelle.
    if (typeof rawSlide === 'string' && rawSlide.length) {
      sources.push(rawSlide);
    }

    // 2. DOM-Body (Format A als gerendertes HTML + Format B als data-sb-action)
    if (domBody) {
      // DOM outerHTML ist sicherer als innerHTML für Regex (kein </body>-Tag-Konflikt)
      sources.push(domBody.outerHTML || domBody.innerHTML || '');
    }

    // Regex: action ODER data-sb-action, label ODER data-sb-label,
    // close-tag OPTIONAL (typisch für Worker-Output).
    const btnRe = /<button\b[^>]*?(?:action|data-sb-action)\s*=\s*["']([^"']+)["'][^>]*?(?:label|data-sb-label)\s*=\s*["']([^"']*)["'][^>]*?>(?:[^<]*<\/button>|[^<]*)/gi;
    // Fallback-Pattern FÜR Buttons OHNE label/data-sb-label-Attribut (nur action)
    const btnReNoLabel = /<button\b[^>]*?\baction\s*=\s*["']([^"']+)["'][^>]*?>(?:[^<]*<\/button>|[^<]*)/gi;

    for (const html of sources) {
      // Pattern 1: action + label
      let m;
      btnRe.lastIndex = 0;
      while ((m = btnRe.exec(html)) !== null) {
        if (out.length >= MAX_BUTTONS) break;
        const action = (m[1] || '').trim();
        if (!action || seen.has(action)) continue;
        // javascript:/data: rausfiltern (Sicherheit)
        if (/^(javascript|data|vbscript):/i.test(action)) continue;
        seen.add(action);
        const label = (m[2] || '').trim() || (action.includes(':') ? action.split(':')[1].slice(0, 50) : action.slice(0, 50)) || 'OK';
        // data-sb-icon/data-sb-color aus dem Original-Tag extrahieren
        const tagText = m[0];
        const iconM = tagText.match(/data-sb-icon\s*=\s*["']([^"']+)["']/i);
        const colorM = tagText.match(/data-sb-color\s*=\s*["']([^"']+)["']/i);
        out.push({
          id: `inline-${out.length + 1}`,
          icon: iconM ? iconM[1].trim() : DEFAULT_BUTTON_ICON,
          label: label.slice(0, 50),
          color: colorM ? colorM[1].trim() : '',
          onClick: action
        });
      }
      // Pattern 2: nur action (kein label) — Worker lassen label oft weg
      btnReNoLabel.lastIndex = 0;
      while ((m = btnReNoLabel.exec(html)) !== null) {
        if (out.length >= MAX_BUTTONS) break;
        const action = (m[1] || '').trim();
        if (!action || seen.has(action)) continue;
        if (/^(javascript|data|vbscript):/i.test(action)) continue;
        seen.add(action);
        const label = action.includes(':') ? action.split(':')[1].slice(0, 50) : action.slice(0, 50) || 'OK';
        out.push({
          id: `inline-${out.length + 1}`,
          icon: DEFAULT_BUTTON_ICON,
          label: label,
          color: '',
          onClick: action
        });
      }
      if (out.length >= MAX_BUTTONS) break;
    }

    return out;
  }

  // ── Button-Action-Handler ────────────────────────────────────────────────
  function handleButtonAction(btn) {
    if (typeof btn.onClick === 'function') {
      try { btn.onClick({ target: null }, btn); } catch (e) { console.error('Button onClick error:', e); }
      return;
    }
    if (typeof btn.onClick !== 'string') return;
    const action = btn.onClick;
    const send = (text) => {
      if (typeof window.api === 'function') {
        window.api('POST', '/chat', { content: text })
          .then(() => { if (typeof window.loadChat === 'function') window.loadChat(); });
      }
    };
    if (action.startsWith('approve_decision:')) {
      const id = action.slice('approve_decision:'.length).trim();
      send(`@@approve_decision ${id}`);
    } else if (action.startsWith('reject_decision:')) {
      const id = action.slice('reject_decision:'.length).trim();
      send(`@@reject_decision ${id}`);
    } else if (action === 'close') {
      if (typeof window.closeShowbox === 'function') window.closeShowbox();
    } else if (action === 'next-slide') {
      if (typeof window.showboxNextSlide === 'function') window.showboxNextSlide();
      else if (typeof window.nextOverlaySlide === 'function') window.nextOverlaySlide();
    } else if (action === 'prev-slide') {
      if (typeof window.showboxPrevSlide === 'function') window.showboxPrevSlide();
      else if (typeof window.prevOverlaySlide === 'function') window.prevOverlaySlide();
    } else if (action === 'toggle-lang') {
      if (typeof window.toggleAppLang === 'function') window.toggleAppLang();
    } else if (action === 'open-overlay') {
      if (typeof window.openShowboxOverlay === 'function') window.openShowboxOverlay();
    } else if (action.startsWith('send:')) {
      send(action.slice('send:'.length));
    } else {
      send(`[Button ${btn.id}] ${action}`);
    }
  }

  // ── Button-Grid-Rendering (2x4) ─────────────────────────────────────────
  function renderButtonGrid() {
    const el = document.getElementById('showbox-control-buttons');
    if (!el) return;
    el.innerHTML = '';
    for (let i = 0; i < MAX_BUTTONS; i++) {
      const btn = buttons[i];
      const slot = document.createElement('button');
      slot.className = 'sb-btn';
      slot.id = `control-btn-${i}`;
      slot.setAttribute('data-help', btn ? `Button: ${btn.label || btn.id}` : 'Leerer Slot');
      if (btn) {
        slot.disabled = !!btn.disabled;
        slot.style.opacity = btn.disabled ? '0.4' : '1';
        slot.style.pointerEvents = btn.disabled ? 'none' : 'auto';
        if (btn.color) slot.classList.add(`sb-btn-${btn.color}`);
        let html = '';
        if (btn.icon) html += btn.icon;
        if (btn.label) {
          if (html) html += ' ';
          html += `<span>${btn.label}</span>`;
        }
        slot.innerHTML = html || '&nbsp;';
        if (!btn.disabled) {
          slot.addEventListener('click', (e) => {
            e.stopPropagation();
            handleButtonAction(btn);
          });
        }
      } else {
        slot.style.visibility = 'hidden';
        slot.innerHTML = '&nbsp;';
        slot.disabled = true;
      }
      el.appendChild(slot);
    }
  }

  // ── Button-Setter (intern + Public-API) ─────────────────────────────────
  function setButtons(list) {
    buttons.fill(null);
    const arr = Array.isArray(list) ? list.slice(0, MAX_BUTTONS) : [];
    for (let i = 0; i < arr.length; i++) {
      buttons[i] = arr[i];
    }
    renderButtonGrid();
  }

  function clearButtons() {
    buttons.fill(null);
    renderButtonGrid();
  }

  // Render the current slide of the current history item in the given layer
  function renderLayerContent(layerIdx) {
    const layer = state.layers[layerIdx];
    const body = document.getElementById(`sb-layer-body-${layerIdx}`);
    if (!body) return;

    if (layer.currentHistoryIdx === -1 || layer.history.length === 0) {
      body.innerHTML = 'STANDBY';
      body.style.fontSize = '0.82rem';
      if (layerIdx === LAYERS.USER) updateDecisionButtons(null);
      clearButtons();
      return;
    }

    const pres = layer.history[layer.currentHistoryIdx];
    const slide = pres.slides[pres.currentSlideIdx] || 'Kein Inhalt';
    body.innerHTML = (typeof sanitizeHTML === 'function') ? sanitizeHTML(slide) : slide;

    if (layerIdx === LAYERS.USER) {
      const match = slide.match(/@@approve_decision\s+([a-f0-9\-]+)/);
      updateDecisionButtons(match ? match[1] : null);
    }

    // Dynamic buttons for this slide — konsolidiertes Grid (Format A + Format B).
    // Reihenfolge: (1) pres.buttons aus DB/JSON, (2) Inline-Extraktion aus
    // RAW-Slide (Format A — vor sanitizeHTML, weil close-tags oft fehlen),
    // (3) DOM-basierte Extraktion (Format B + Format A als gerendertes HTML).
    // Deduplizierung passiert in extractInlineButtons.
    const presBtns = Array.isArray(pres.buttons) ? pres.buttons.slice() : [];
    const inlineBtns = extractInlineButtons(body, slide);
    const merged = presBtns.concat(inlineBtns).slice(0, MAX_BUTTONS);
    setButtons(merged);

    autoFitText(layerIdx);
  }

  // Expose triggers & helpers to window for Gnom-Hub sync and legacy code support

  // 1. window.triggerShowbox
  window.triggerShowbox = function (showboxIndex, sender) {
    cancelToastRevert();
    if (!window.showboxPresentations || showboxIndex < 0 || showboxIndex >= window.showboxPresentations.length) {
      return;
    }

    const pres = window.showboxPresentations[showboxIndex];
    if (!pres) return;

    window.activeShowboxIndex = showboxIndex;
    window.showboxActive = true;

    // Standardize slides to array of strings
    let slides = pres.slides;
    if (typeof slides === 'string') {
      try {
        slides = JSON.parse(slides);
      } catch (e) {
        slides = [slides];
      }
    }
    if (!Array.isArray(slides)) {
      slides = [slides];
    }

    // Resolve target layer
    const senderName = sender || pres.sender || 'System';
    const targetLayer = resolveTargetLayer(senderName, pres.name, slides);

    const layer = state.layers[targetLayer];

    // Check if this presentation is already in history (by name)
    let existingIdx = layer.history.findIndex(h => h.name === pres.name);

    if (existingIdx !== -1) {
      // Update the slides of existing entry and jump to it
      layer.history[existingIdx].slides = slides;
      layer.history[existingIdx].currentSlideIdx = 0;
      if (pres.buttons !== undefined) layer.history[existingIdx].buttons = pres.buttons;
      layer.currentHistoryIdx = existingIdx;
    } else {
      // Push new presentation to history
      layer.history.push({
        name: pres.name,
        slides: slides,
        sender: senderName,
        currentSlideIdx: 0,
        buttons: pres.buttons || []
      });
      // Limit history to 30 items to keep DOM performant
      if (layer.history.length > 30) {
        layer.history.shift();
      }
      layer.currentHistoryIdx = layer.history.length - 1;
    }

    // Switch view to the target layer and render
    switchLayer(targetLayer);
    renderLayerContent(targetLayer);

    // ── Agent-Color Flash auf Showbox-Container ──
    // User-Mandat 2026-06-28 07:53: Showbox blinkt kurz in der Farbe des Agenten.
    const _AGENT_COLORS = {
      soulag:'soulag', watchdogag:'watchdogag', generalag:'generalag', securityag:'securityag',
      writerag:'writerag', coderag:'coderag', researcherag:'researcherag', editorag:'editorag',
      user:'soulag', system:'system'
    };
    const _glowClass = 'sb-glow-' + (_AGENT_COLORS[senderName.toLowerCase()] || 'system');
    const _container = document.getElementById('sb-layers-container');
    if (_container) {
      _container.classList.remove('sb-glow','sb-glow-soulag','sb-glow-watchdogag','sb-glow-generalag',
        'sb-glow-securityag','sb-glow-writerag','sb-glow-coderag','sb-glow-researcherag',
        'sb-glow-editorag','sb-glow-system');
      void _container.offsetWidth;
      _container.classList.add('sb-glow', _glowClass);
      setTimeout(() => _container.classList.remove(_glowClass), 1200);
    }

    // SuperGNOM Mode overrides
    if (document.body.classList.contains('supergnom-mode')) {
      const drawerBody = document.getElementById('supergnom-drawer-body');
      const drawerTitle = document.getElementById('supergnom-drawer-title');
      const drawerBtn = document.getElementById('supergnom-drawer-btn');
      const tribunalOverlay = document.getElementById('supergnom-tribunal-overlay');
      const tribunalCard = document.getElementById('supergnom-tribunal-card');
      
      const slideContent = slides[0] || 'Kein Inhalt';
      
      if (targetLayer === LAYERS.USER) {
        if (tribunalCard && tribunalOverlay) {
          const match = slideContent.match(/@@approve_decision\s+([a-f0-9\-]+)/);
          activeDecisionId = match ? match[1] : null;
          
          tribunalCard.innerHTML = (typeof sanitizeHTML === 'function') ? sanitizeHTML(slideContent) : slideContent;
          tribunalOverlay.classList.add('show');
        }
      } else {
        if (drawerBody && drawerTitle && drawerBtn) {
          drawerTitle.textContent = pres.name || "Ausgabe / Entwurf";
          drawerBody.innerHTML = slideContent;
          drawerBtn.style.display = 'flex';
          
          const drawer = document.getElementById('supergnom-drawer');
          if (drawer && !drawer.classList.contains('open')) {
            drawerBtn.classList.add('has-unread');
          }
        }
      }
    }
  };

  // 2. window.closeShowbox
  window.closeShowbox = function () {
    cancelToastRevert();
    window.activeShowboxIndex = -1;
    window.showboxActive = false;
    
    // Clear all layers to standby
    for (let i = 1; i <= 3; i++) {
      state.layers[i].currentHistoryIdx = -1;
      renderLayerContent(i);
    }

    // SuperGNOM Mode overrides
    if (document.body.classList.contains('supergnom-mode')) {
      const tribunalOverlay = document.getElementById('supergnom-tribunal-overlay');
      if (tribunalOverlay) {
        tribunalOverlay.classList.remove('show');
      }
      activeDecisionId = null;
      
      const drawerBtn = document.getElementById('supergnom-drawer-btn');
      const drawer = document.getElementById('supergnom-drawer');
      if (drawerBtn) {
        drawerBtn.style.display = 'none';
        drawerBtn.classList.remove('has-unread');
      }
      if (drawer) {
        drawer.classList.remove('open');
      }
    }
  };

  // ── Help-Slides (User-Layer Präsentation) ──────────────────────────────────
  // Mehrsprachige Slideshow (DE default, EN wenn appLang==='en') mit allem
  // was man über den Hub wissen muss: Swarm, Befehle, UI, MiniMax, Module,
  // Mouseover-Hilfe. Wird per showHelpSlides() in den User-Layer geschaltet.
  window.buildHelpSlides = function () {
    const lang = (window.appLang === 'en') ? 'en' : 'de';
    const T = (de, en) => lang === 'en' ? en : de;
    const cy = '#00e5ff', og = '#ffa500', gn = '#39ff14';
    const card = (inner, color, title) => `
      <div style="display:flex;flex-direction:column;gap:14px;padding:24px;height:100%;box-sizing:border-box;justify-content:center;">
        ${title ? `<h1 style="margin:0;font-size:1.6rem;color:${color};font-weight:700;letter-spacing:0.5px;">${title}</h1>` : ''}
        ${inner}
      </div>`;
    const pill = (label, color) => `<span style="display:inline-block;padding:3px 10px;border-radius:999px;border:1px solid ${color};color:${color};font-size:0.7rem;font-weight:600;margin:2px;">${label}</span>`;
    const row = (k, v) => `<div style="display:flex;gap:12px;font-size:0.8rem;line-height:1.4;"><span style="color:rgba(255,255,255,0.5);min-width:130px;">${k}</span><span style="color:#fff;">${v}</span></div>`;
    const stat = (label, value, color) => `
      <div style="flex:1;padding:14px;background:rgba(255,255,255,0.03);border:1px solid ${color}33;border-radius:8px;text-align:center;">
        <div style="font-size:1.4rem;font-weight:700;color:${color};">${value}</div>
        <div style="font-size:0.62rem;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.5px;margin-top:4px;">${label}</div>
      </div>`;

    // Slide 1 — Welcome
    const s1 = card(`
      <div style="text-align:center;">
        <div style="font-size:3rem;margin-bottom:8px;">🧠</div>
        <p style="font-size:1rem;color:rgba(255,255,255,0.75);margin:6px 0;line-height:1.4;">${T(
          '8 Agenten, ein MiniMax-Key, ein kontinuierlicher Loop.',
          '8 agents, one MiniMax key, one continuous loop.')}</p>
        <div style="display:flex;gap:10px;justify-content:center;margin-top:18px;">
          ${stat(T('Aktiv', 'Active'), '8', cy)}
          ${stat(T('Port', 'Port'), '3002', og)}
          ${stat(T('Modell', 'Model'), 'M3', gn)}
        </div>
        <p style="font-size:0.7rem;color:rgba(255,255,255,0.3);margin-top:18px;">
          ${T('Folie 1 / 6 · Benutze die Buttons unten zum Navigieren.',
              'Slide 1 / 6 · Use the buttons below to navigate.')}
        </p>
      </div>`);

    // Slide 2 — Die 8 Gnome
    const s2 = card(`
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
        <div>
          <h2 style="margin:0 0 6px 0;font-size:0.95rem;color:${cy};">${T('System-Agenten', 'System agents')}</h2>
          ${pill('SoulAG', cy)} ${pill('WatchdogAG', cy)} ${pill('GeneralAG', cy)} ${pill('SecurityAG', cy)}
          <p style="font-size:0.72rem;color:rgba(255,255,255,0.55);margin-top:8px;line-height:1.4;">
            ${T('Koordination, Gedächtnis, Sicherheit, Patrouille.',
                'Coordination, memory, safety, patrol.')}</p>
        </div>
        <div>
          <h2 style="margin:0 0 6px 0;font-size:0.95rem;color:${og};">${T('Worker-Agenten', 'Worker agents')}</h2>
          ${pill('WriterAG', og)} ${pill('CoderAG', og)} ${pill('ResearcherAG', og)} ${pill('EditorAG', og)}
          <p style="font-size:0.72rem;color:rgba(255,255,255,0.55);margin-top:8px;line-height:1.4;">
            ${T('Texte, Code, Recherche, Review — die Ausführenden.',
                'Text, code, research, review — the executors.')}</p>
        </div>
      </div>
      <div style="margin-top:14px;padding:10px 14px;background:rgba(57,255,20,0.05);border:1px solid rgba(57,255,20,0.25);border-radius:8px;font-size:0.78rem;color:${gn};">
        ${T('Alle 8 laufen über minimax | MiniMax-M3 — ein einziger sk-cp-…-Key reicht.',
            'All 8 run via minimax | MiniMax-M3 — a single sk-cp-… key is enough.')}
      </div>`,
      '', T('Die 8 Gnome', 'The 8 gnomes'));

    // Slide 3 — Befehle
    const s3 = card(`
      <div style="font-size:0.78rem;line-height:1.7;">
        ${row(T('Delegieren', 'Delegate'), `<code style="color:${cy};">@job &lt;aufgabe&gt;</code> — ${T('verteilt an Worker', 'dispatches to workers')}`)}
        ${row(T('Brainstorm', 'Brainstorm'), `<code style="color:${cy};">@bs &lt;thema&gt;</code> — ${T('mehrere Agenten parallel', 'multiple agents in parallel')}`)}
        ${row(T('Recherche', 'Research'), `<code style="color:${cy};">@research &lt;thema&gt;</code>`)}
        ${row(T('Status', 'Status'), `<code style="color:${cy};">@@status</code>`)}
        ${row(T('Hilfe', 'Help'), `<code style="color:${cy};">@@help</code> · <code style="color:${cy};">@@slides</code>`)}
        ${row(T('Aufräumen', 'Clean up'), `<code style="color:${cy};">@@clear chat|db|all</code>`)}
        ${row(T('Merken', 'Remember'), `<code style="color:${cy};">@merken &lt;fakt&gt;</code>`)}
      </div>`,
      '', T('Chat-Befehle', 'Chat commands'));

    // Slide 4 — UI-Header
    const s4 = card(`
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;font-size:0.74rem;">
        ${['Back', 'Workspace', 'Dashboard', 'Workflows', 'LLM', 'Tuning', 'Help', 'DE/EN', 'Save', 'Clean'].map(b => `
          <div style="padding:8px 12px;background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.2);border-radius:6px;">
            <b style="color:${cy};">${b}</b>
            <div style="font-size:0.65rem;color:rgba(255,255,255,0.4);margin-top:2px;">${T('Mouseover → Showbox', 'Mouseover → Showbox')}</div>
          </div>`).join('')}
      </div>
      <p style="font-size:0.7rem;color:rgba(255,255,255,0.4);margin-top:14px;text-align:center;">
        ${T('Jeder Button erklärt sich im Showbox bei Mouseover — bilingual via DE/EN-Schalter.',
            'Every button explains itself in the Showbox on mouseover — bilingual via DE/EN switch.')}
      </p>`,
      '', T('UI-Buttons', 'UI buttons'));

    // Slide 5 — MiniMax + Setup
    const s5 = card(`
      <div style="font-size:0.78rem;line-height:1.55;">
        <p style="margin:0 0 10px 0;color:rgba(255,255,255,0.7);">
          ${T('Ein einziger', 'One single')}
          <code style="color:${gn};background:rgba(57,255,20,0.08);padding:2px 6px;border-radius:4px;">sk-cp-…</code>
          ${T('Key deckt alle Features ab:', 'key covers all features:')}
        </p>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 14px 0;">
          ${pill('💬 Text', gn)} ${pill('👁 Vision', cy)} ${pill('🎨 Image', '#ff007f')}
          ${pill('🔊 Audio/TTS', og)} ${pill('🎬 Video', '#cc33ff')} ${pill('🎵 Music', gn)}
          ${pill('🛠 Tools', '#a855f7')}
        </div>
        <p style="margin:10px 0;font-size:0.72rem;color:rgba(255,255,255,0.55);">
          ${T('Setup-Skript:', 'Setup script:')}
          <code style="background:rgba(0,0,0,0.4);padding:2px 6px;border-radius:4px;">bash scripts/agent-setup-minimal.sh</code>
        </p>
        <div style="padding:10px 12px;background:rgba(57,255,20,0.05);border:1px solid rgba(57,255,20,0.2);border-radius:8px;font-size:0.72rem;">
          <b style="color:${gn};">${T('Blockade-Setup:', 'Blockade setup:')}</b><br>
          ${T('blockade_level=0, security_blockade_level=0, enable_confirmations=false',
              'blockade_level=0, security_blockade_level=0, enable_confirmations=false')}
        </div>
      </div>`,
      '', T('MiniMax-Routing & Setup', 'MiniMax routing & setup'));

    // Slide 6 — Module + Mouseover
    const s6 = card(`
      <div style="font-size:0.78rem;line-height:1.5;">
        <h3 style="margin:0 0 8px 0;font-size:0.85rem;color:${og};">🧩 ${T('Module im Tools-Tab', 'Modules in the Tools tab')}</h3>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;">
          ${pill('🔗 Webhooks', cy)} ${pill('🧩 Plugins', og)} ${pill('🎯 Skills', gn)}
        </div>
        <h3 style="margin:14px 0 8px 0;font-size:0.85rem;color:${cy};">💡 ${T('Mouseover-Hilfe', 'Mouseover help')}</h3>
        <p style="margin:0;color:rgba(255,255,255,0.7);">
          ${T('Bewege die Maus über jeden Button, Slider oder jedes Modul — die Erklärung erscheint sofort in dieser Showbox.',
              'Move the mouse over any button, slider or module — the explanation appears immediately in this Showbox.')}
        </p>
        <p style="margin:8px 0 0 0;font-size:0.7rem;color:rgba(255,255,255,0.4);">
          ${T('Sprache umschaltbar mit dem DE/EN-Button im Header.',
              'Switchable via DE/EN button in the header.')}
        </p>
      </div>`,
      '', T('Module & Mouseover-Hilfe', 'Modules & mouseover help'));

    return [s1, s2, s3, s4, s5, s6];
  };

  // Trigger für die User-Layer-Hilfe-Slides. Schaltet auf Layer 3 und ruft
  // die Help-Präsentation (Index 2) auf. Kann via Button oder Chat-Command
  // aufgerufen werden.
  window.showHelpSlides = function () {
    if (typeof switchLayer === 'function') switchLayer(LAYERS.USER);
    if (typeof window.triggerShowbox === 'function') window.triggerShowbox(2, 'user');
    if (typeof window.openShowboxOverlay === 'function') {
      // Fullscreen-Overlay öffnen damit alle Slides sichtbar sind
      setTimeout(() => window.openShowboxOverlay(), 250);
    }
  };

  // ── Agent-Art-Show (1950er Sci-Fi Prompt-Slideshow) ──────────────────────
  // 9 Slides: 1 Intro + 8 Agenten-Prompts. Sprache via appLang (DE/EN).
  // Jede Folie enthält den fertigen 1950er-Sci-Fi-Prompt zum Kopieren
  // in eine Bild-KI. Agent-SVG-Icon + Frozen-Color + Rolle + Prompt.
  window.buildAgentArtShow = function () {
    const lang = (window.appLang === 'en') ? 'en' : 'de';
    const T = (de, en) => lang === 'en' ? en : de;

    // Frozen-Color-Lookup (sync mit core/agent_names.py)
    const COLORS = {
      soulag: '#00e5ff', watchdogag: '#00e5ff', generalag: '#00e5ff', securityag: '#00e5ff',
      writerag: '#ffa500', coderag: '#ffa500', researcherag: '#ffa500', editorag: '#ffa500'
    };
    const ROLES_DE = {
      soulag: 'Gedächtnis & User-Interface', watchdogag: 'Regel-Patrolle & Sicherheit',
      generalag: 'Koordination & Orchestrierung', securityag: 'System-Schutz',
      writerag: 'Texte & Dokumentation', coderag: 'Code & Debugging',
      researcherag: 'Web-Recherche & Fakten', editorag: 'QA & Refactoring'
    };
    const ROLES_EN = {
      soulag: 'Memory & user interface', watchdogag: 'Rule patrol & safety',
      generalag: 'Coordination & orchestration', securityag: 'System protection',
      writerag: 'Texts & documentation', coderag: 'Code & debugging',
      researcherag: 'Web research & facts', editorag: 'QA & refactoring'
    };

    // 1950er Sci-Fi Prompt (DE) — bilingual
    const PROMPTS_DE = {
      soulag: 'Retro-futuristisches 1950er Sci-Fi Interior, ein leuchtendes kühlschrankgroßes Gedächtnisarchiv aus poliertem Chrom und Bakelit mit pulsierenden Vakuumröhren im Inneren, unzählige bläulich-cyan #00e5ff leuchtende Kristallspulen die sachte vor sich hinsummen, im Hintergrund dezent ein chromblonder Androide mit Glaskuppelkopf der konzentriert in einem dicken Logbuch blättert, klarer Mid-Century-Look, sauberer Cinematic-Stil, atmosphärisch, hochwertig, kein billiger Plastik-Look, 16:9 Komposition, Kino-Look.',
      watchdogag: 'Retro-futuristisches 1950er Sci-Fi Kontrollzentrum, eine ringförmige Patrouille-Konsole mit phosphor-grünen Radarschirmen und rotierenden Drehknöpfen in einer Kuppelstation, in der Mitte ein wachsamer chromfarbener Wachroboter mit einem einzelnen kreisrunden Teleskop-Auge, ständig alles im Blick behaltend, im Hintergrund abstrakte Cyan #00e5ff Funkensignale auf einer gekrümmten Weltkarte, klassischer 50er Sci-Fi Look, atmosphärisch, kein Plastik, saubere Komposition, 16:9, Kino-Stil.',
      generalag: 'Retro-futuristisches 1950er Sci-Fi Orchestersaal, ein dirigentenhafter Androide mit schlanker Chromfigur und gläserner Kuppel auf einem erhöhten Podest, vor ihm eine halbkreisförmige Anordnung von Arbeitstischen mit leuchtenden Vakuumröhren und Notenblatt-Haltern, dezente Cyan #00e5ff Akzentbeleuchtung von unten, an den Wänden analoge Wanduhren mit römischen Ziffern, klassische 50er-Weltraum-Ästhetik, kein Plastik, sauberer Mid-Century-Stil, 16:9, atmosphärisch, cinematisch.',
      securityag: 'Retro-futuristisches 1950er Sci-Fi Tresorraum, ein massiver gepanzerter Schutz-Androide mit Chrom-Helm und Schulterpanzerung steht Wache vor einer stählernen Safe-Tür mit analogen Zahlenrädern, dahinter deckenhohe Schränke mit roten und grünen Statuslämpchen in Reih und Glied, alles sauber in Bakelit und gebürstetem Stahl, Akzentfarbe Cyan #00e5ff auf den Sicherheits-Kontrollleuchten, dramatische seitliche Beleuchtung, 50er Sci-Fi ohne Plastik-Look, klar und atmosphärisch, 16:9, Kino-Komposition.',
      writerag: 'Retro-futuristisches 1950er Sci-Fi Redaktionsraum, ein eleganter Schreib-Androide mit chromfarbenem Torso und langen Greifarmen sitzt an einer futuristischen Schreibmaschine aus gebürstetem Aluminium, umgeben von aufgeschlagenen Notizbüchern, halbvollen Kaffeetassen und einem rotierenden Telex-Gerät mit orangefarbenem #ffa500 Papierstreifen, an der Wand gerahmte Schlagzeilen, eine altmodische Stehlampe mit orangem Schirm, klassische 50er Newsroom-Ästhetik, kein Plastik, kein Neon, saubere Komposition, 16:9, cinematisch, atmosphärisch.',
      coderag: 'Retro-futuristisches 1950er Sci-Fi Werkstatt, ein konzentriert arbeitender Schmied-Androide mit Lederschürze und chromfarbenen Greifarmen hämmert auf einer Lochkarten-Stanzmaschine aus Gusseisen, überall verstreute Pappkarten mit geheimnisvollen Lochmustern, im Hintergrund meterhohe Aktenschränke mit orangenen #ffa500 Beschriftungsschildern, hängende Industrielampen mit Metallschirm, ein oszilloskop zeigt eine ruhige Sinuskurve, klassischer 50er Maschinenraum-Look, kein Plastik, kein Cyberpunk, 16:9, Kino-Stil, atmosphärisch, sauber.',
      researcherag: 'Retro-futuristisches 1950er Sci-Fi Observatorium, ein neugieriger Forschungs-Androide mit Brille und Notizblock steht vor einem gewaltigen Spiegelteleskop aus poliertem Messing, eine projizierte Sternkarte leuchtet orange #ffa500 an der Kuppelwand, ringsum Bücherstapel und ein Globus mit eingezeichneten Erkundungsrouten, sanftes Sternenlicht fällt durch die Beobachtungsöffnung, klassische 50er Astronomie-Ästhetik, kein Plastik, kein Neon, sauberer Mid-Century-Stil, 16:9, cinematisch, atmosphärisch.',
      editorag: 'Retro-futuristisches 1950er Sci-Fi Prüflabor, ein pedantischer Inspektions-Androide mit chromglänzender Monokel-Lupe und rotem Prüfstift beugt sich über ein beleuchtetes Glaspanel auf dem ein Bauplan liegt, ein kleines orange #ffa500 Lämpchen leuchtet als Freigabe-Signal, im Hintergrund Registrierkassen-artige Messgeräte mit Skalen, ein Notizbuch mit roten Anmerkungen, alles aufgeräumt und symmetrisch wie in einem Schweizer Qualitätslabor, 50er Inspektions-Ästhetik, kein Plastik, kein Cyberpunk, 16:9, cinematisch, atmosphärisch.'
    };
    const PROMPTS_EN = {
      soulag: 'Retro-futuristic 1950s sci-fi interior, a luminous refrigerator-sized memory archive made of polished chrome and Bakelite with pulsing vacuum tubes inside, countless cyan #00e5ff crystal coils humming softly, in the background a discreet chrome-blond android with a glass dome head concentrating on a thick leather-bound logbook, clean mid-century look, no cheap plastic, atmospheric, cinematic, 16:9.',
      watchdogag: 'Retro-futuristic 1950s sci-fi control room, a circular patrol console with phosphor-green radar screens and rotating knobs in a domed station, in the middle a vigilant chrome sentry robot with a single circular telescope eye watching everything, abstract cyan #00e5ff signal sparks on a curved world map in the background, classic 50s sci-fi atmosphere, no plastic, clean composition, 16:9, cinematic.',
      generalag: 'Retro-futuristic 1950s sci-fi orchestra hall, a conductor-like android with a slender chrome figure and glass dome on an elevated podium, in front of him a semi-circular arrangement of workstations with glowing vacuum tubes and music-stand holders, discreet cyan #00e5ff uplighting, on the walls analogue wall clocks with Roman numerals, classic 50s space-age aesthetic, no plastic, clean mid-century style, 16:9, cinematic.',
      securityag: 'Retro-futuristic 1950s sci-fi vault, a massive armoured guardian android with chrome helmet and shoulder plating stands watch before a steel safe door with analogue number wheels, behind it ceiling-high cabinets with red and green status lamps in perfect rows, polished steel and Bakelite, cyan #00e5ff accent on the security lamps, dramatic side lighting, 50s sci-fi without plastic, clean and atmospheric, 16:9, cinematic composition.',
      writerag: 'Retro-futuristic 1950s sci-fi editorial room, an elegant chrome writing-android sits at a futuristic typewriter made of brushed aluminium, surrounded by open notebooks, half-full coffee cups and a rotating telex machine with an orange #ffa500 paper strip, framed headlines on the wall, an old-fashioned floor lamp with orange shade, classic 50s newsroom aesthetic, no plastic, no neon, clean composition, 16:9, cinematic, atmospheric.',
      coderag: 'Retro-futuristic 1950s sci-fi workshop, a focused smith-android in a leather apron and chrome arms hammers at a cast-iron punch-card machine, perforated cards scattered everywhere, towering filing cabinets with orange #ffa500 labels in the background, hanging industrial lamps with metal shades, an oscilloscope shows a calm sine wave, classic 50s machine-room look, no plastic, no cyberpunk, 16:9, cinematic, atmospheric, clean.',
      researcherag: 'Retro-futuristic 1950s sci-fi observatory, a curious research-android with spectacles and notepad stands before a giant brass reflecting telescope, a projected star chart glows orange #ffa500 on the dome wall, books piled around and a globe with annotated exploration routes, soft starlight falling through the observation slit, classic 50s astronomy aesthetic, no plastic, no neon, clean mid-century, 16:9, cinematic, atmospheric.',
      editorag: 'Retro-futuristic 1950s sci-fi inspection laboratory, a pedantic inspector-android with a gleaming chrome monocle-magnifier and red proofreading pen leans over an illuminated glass panel with a blueprint, a small orange #ffa500 lamp glows as an approval signal, in the background cash-register-like meters with scales, a notebook with red annotations, all tidy and symmetrical like a Swiss quality lab, 50s inspection aesthetic, no plastic, no cyberpunk, 16:9, cinematic, atmospheric.'
    };

    const AGENTS = [
      ['soulag','SoulAG'],['watchdogag','WatchdogAG'],['generalag','GeneralAG'],['securityag','SecurityAG'],
      ['writerag','WriterAG'],['coderag','CoderAG'],['researcherag','ResearcherAG'],['editorag','EditorAG']
    ];

    const slides = [];

    // Slide 0 — Intro
    slides.push(`
      <div style="display:flex;flex-direction:column;gap:14px;padding:24px;height:100%;box-sizing:border-box;justify-content:center;text-align:center;">
        <div style="font-size:2.6rem;">🎬</div>
        <h1 style="margin:0;font-size:1.5rem;color:#fff;font-weight:700;letter-spacing:0.5px;">
          ${T('Agent Art Show', 'Agent Art Show')}
        </h1>
        <p style="font-size:0.9rem;color:rgba(255,255,255,0.7);margin:6px 0;line-height:1.4;">
          ${T('8 Retro-Futurismus-1950-Prompts für die 8 Agenten.',
              '8 retro-futurism 1950s prompts for the 8 agents.')}
        </p>
        <p style="font-size:0.74rem;color:rgba(255,255,255,0.4);margin:0;">
          ${T('Mouseover auf einen Agenten öffnet die passende Folie.',
              'Mouseover on an agent card opens the matching slide.')}
        </p>
        <div style="display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin-top:8px;">
          ${AGENTS.map(([k]) => `<span style="display:inline-flex;width:18px;height:18px;align-items:center;justify-content:center;color:${COLORS[k]};">${window.agentIcon ? window.agentIcon(k) : ''}</span>`).join('')}
        </div>
      </div>`);

    // Slides 1-8 — ein Agent pro Folie
    AGENTS.forEach(([key, name], idx) => {
      const color = COLORS[key];
      const role = (lang === 'en' ? ROLES_EN : ROLES_DE)[key] || '';
      const prompt = (lang === 'en' ? PROMPTS_EN : PROMPTS_DE)[key] || '';
      const icon = window.agentIcon ? window.agentIcon(key) : '';
      slides.push(`
        <div style="display:flex;flex-direction:column;gap:10px;padding:18px 20px;height:100%;box-sizing:border-box;overflow:hidden;">
          <div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">
            <span style="display:inline-flex;width:34px;height:34px;align-items:center;justify-content:center;color:${color};border:1px solid ${color};border-radius:8px;flex-shrink:0;">${icon}</span>
            <div style="flex:1;min-width:0;">
              <div style="font-size:1.05rem;font-weight:700;color:${color};">${name}</div>
              <div style="font-size:0.7rem;color:rgba(255,255,255,0.55);">${role}</div>
            </div>
            <div style="font-size:0.62rem;color:rgba(255,255,255,0.35);text-align:right;flex-shrink:0;">
              ${idx + 1} / 8<br><span style="color:${color};">${color}</span>
            </div>
          </div>
          <div style="flex:1;min-height:0;background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.08);border-radius:6px;padding:10px 12px;overflow-y:auto;font-size:0.72rem;line-height:1.45;color:rgba(255,255,255,0.85);">
            ${prompt}
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0;">
            <button data-sb-action="send:@merken 1950er-prompt für ${name}" data-sb-icon="💾" data-sb-label="${T('Merken', 'Save')}" data-sb-color="green" style="flex:1;padding:6px 8px;background:rgba(57,255,20,0.1);border:1px solid rgba(57,255,20,0.3);color:#39ff14;border-radius:5px;font-size:0.72rem;cursor:pointer;font-family:inherit;">
              ${T('💾 Prompt merken', '💾 Save prompt')}
            </button>
            <button data-sb-action="close" data-sb-icon="✕" data-sb-label="${T('Schließen', 'Close')}" data-sb-color="red" style="flex:1;padding:6px 8px;background:rgba(255,85,119,0.1);border:1px solid rgba(255,85,119,0.3);color:#ff5577;border-radius:5px;font-size:0.72rem;cursor:pointer;font-family:inherit;">
              ${T('✕ Schließen', '✕ Close')}
            </button>
          </div>
        </div>`);
    });

    return slides;
  };

  // Trigger: beim Mouseover auf eine Agent-Card springt die Showbox auf
  // die passende Folie der Art-Show. Bei erneutem Trigger derselben Folie
  // passiert nichts (idempotent).
  window.triggerAgentArtShow = function (agentName) {
    if (!agentName || typeof window.buildAgentArtShow !== 'function') return;
    if (typeof window.__agentArtShowIndex !== 'number') return;
    const KEY = (agentName || '').toLowerCase();
    const order = ['soulag','watchdogag','generalag','securityag','writerag','coderag','researcherag','editorag'];
    const idx = order.indexOf(KEY);
    if (idx < 0) return;
    // Folie ist idx+1 (0 = Intro), Index 1..8
    const slideIdx = idx + 1;
    if (typeof switchLayer === 'function') switchLayer(LAYERS.USER);
    if (typeof window.triggerShowbox === 'function') {
      window.triggerShowbox(window.__agentArtShowIndex, 'user');
      // Auf richtige Slide springen
      setTimeout(() => {
        const pres = window.showboxPresentations && window.showboxPresentations[window.__agentArtShowIndex];
        if (pres) {
          pres.currentSlideIdx = slideIdx;
          if (typeof window.renderLayerContent === 'function') window.renderLayerContent(LAYERS.USER);
        }
      }, 80);
    }
  };

  window.toggleSuperGnomDrawer = function () {
    const drawer = document.getElementById('supergnom-drawer');
    const btn = document.getElementById('supergnom-drawer-btn');
    if (!drawer) return;
    drawer.classList.toggle('open');
    if (drawer.classList.contains('open')) {
      if (btn) btn.classList.remove('has-unread');
    }
  };

  // 3. window.showboxToast
  window.showboxToast = function (msg, type = 'info') {
    const targetLayer = LAYERS.SYSTEM;
    const layer = state.layers[targetLayer];

    // Clear any existing toast revert timer
    cancelToastRevert();

    // Save previous state to revert to it later
    const prevHistoryIdx = layer.currentHistoryIdx;
    const prevSlideIdx = (prevHistoryIdx !== -1 && layer.history[prevHistoryIdx]) 
      ? layer.history[prevHistoryIdx].currentSlideIdx 
      : 0;
    const prevActiveLayer = state.activeLayer;

    // Define colors and icons based on message type
    let color = '#00e5ff'; // info (cyan)
    let icon = 'ℹ️';
    let rgb = '0, 229, 255';
    if (type === 'success') {
      color = 'var(--green)';
      icon = '✅';
      rgb = '57, 255, 20';
    } else if (type === 'error') {
      color = 'var(--red)';
      icon = '❌';
      rgb = '255, 0, 127';
    } else if (type === 'warning') {
      color = '#ffa500'; // orange
      icon = '⚠️';
      rgb = '255, 165, 0';
    }

    // Build styled card HTML for the Showbox
    const htmlContent = `
      <div class="sb-toast sb-toast-${type}" style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 8px; width: 100%; height: 100%; box-sizing: border-box; padding: 12px;">
        <div style="font-size: 2.2rem; filter: drop-shadow(0 0 8px rgba(${rgb}, 0.6));">${icon}</div>
        <div style="color: ${color}; font-weight: 700; font-size: 0.95rem; text-shadow: 0 0 10px rgba(${rgb}, 0.5); line-height: 1.4; word-break: break-word;">
          ${msg}
        </div>
      </div>
    `;

    const presName = "System Status";
    let existingIdx = layer.history.findIndex(h => h.name === presName);

    if (existingIdx !== -1) {
      layer.history[existingIdx].slides = [htmlContent];
      layer.history[existingIdx].currentSlideIdx = 0;
      layer.currentHistoryIdx = existingIdx;
    } else {
      layer.history.push({
        name: presName,
        slides: [htmlContent],
        sender: "System",
        currentSlideIdx: 0
      });
      if (layer.history.length > 30) {
        layer.history.shift();
      }
      layer.currentHistoryIdx = layer.history.length - 1;
    }

    // Switch view to System layer and render content
    switchLayer(targetLayer);
    renderLayerContent(targetLayer);

    // Auto-revert timer to return to previous presentation and active layer after 6 seconds
    toastRevertTimeout = setTimeout(() => {
      // Revert only if we are still displaying the "System Status" presentation
      const currentPres = layer.history[layer.currentHistoryIdx];
      if (currentPres && currentPres.name === presName) {
        layer.currentHistoryIdx = prevHistoryIdx;
        if (prevHistoryIdx !== -1 && layer.history[prevHistoryIdx]) {
          layer.history[prevHistoryIdx].currentSlideIdx = prevSlideIdx;
        }
        renderLayerContent(targetLayer);
        switchLayer(prevActiveLayer, true); // skip flash/glow on revert
      }
    }, 6000);
  };

  // 3. window.loadShowboxList (replaces index.html polling parser)
  window.loadShowboxList = async function () {
    if (typeof window.api !== 'function') return;

    try {
      const res = await window.api('GET', '/showbox/presentations');
      if (res && Array.isArray(res)) {
        window.showboxPresentations = res;
        window.showboxes = res.map(p => p.slides);
      }
      // Ensure at least 3 slots for the 3-layer system (system=0, worker=1, user=2)
      while (window.showboxPresentations.length < 3) {
        var idx = window.showboxPresentations.length;
        var names = ['System-Layer', 'Worker-Layer', 'User-Layer'];
        window.showboxPresentations.push({
          name: names[idx] || 'Layer ' + (idx + 1),
          slides: ['<div style="padding:40px;text-align:center;color:rgba(255,255,255,0.15);font-size:0.8rem;">🔇 Keine aktive Präsentation in diesem Layer.</div>'],
          sender: 'System'
        });
        window.showboxes.push(window.showboxPresentations[idx].slides);
      }

      // ── Inject Help-Slides-Präsentation in den User-Layer (Index 2) ──
      // Statische, mehrsprachige Slideshow die das System + MiniMax-Setup
      // + Mouseover-Hilfe erklärt. Wird genau einmal pro Session injiziert
      // und ersetzt den User-Layer-Slot durch eine reichhaltige Hilfe.
      if (!window.__helpSlidesInjected) {
        window.__helpSlidesInjected = true;
        const slides = window.buildHelpSlides ? window.buildHelpSlides() : [];
        if (slides.length) {
          const userIdx = 2; // 0=system, 1=worker, 2=user
          window.showboxPresentations[userIdx] = {
            id: 'help-slides',
            name: 'Gnom-Hub Hilfe (User-Layer)',
            slides: slides,
            sender: 'user',
            buttons: [
              { id: 'next', label: '▶ Nächste', action: 'next-slide' },
              { id: 'prev', label: '◀ Vorherige', action: 'prev-slide' },
              { id: 'lang', label: 'DE / EN', action: 'toggle-lang' },
              { id: 'overlay', label: '⛶ Groß', action: 'open-overlay' }
            ]
          };
          window.showboxes[userIdx] = slides;
        }

        // ── Inject Agent-Art-Show Präsentation (Index 3+) ──
        // 1950er Sci-Fi-Bild-Prompts für jeden Agenten, fertig zum
        // Kopieren in die Bild-KI. Wird per mouseover auf Agent-Cards
        // oder via @@artshow-Command getriggert.
        const artSlides = window.buildAgentArtShow ? window.buildAgentArtShow() : [];
        if (artSlides.length) {
          window.showboxPresentations.push({
            id: 'agent-art-show',
            name: 'Agent Art Show — 1950er Sci-Fi',
            slides: artSlides,
            sender: 'user',
            buttons: [
              { id: 'next', label: '▶', action: 'next-slide' },
              { id: 'prev', label: '◀', action: 'prev-slide' },
              { id: 'lang', label: 'DE/EN', action: 'toggle-lang' },
              { id: 'overlay', label: '⛶', action: 'open-overlay' }
            ]
          });
          window.showboxes.push(artSlides);
          window.__agentArtShowIndex = window.showboxPresentations.length - 1;
        }
      }

      // Sync active state from DB
      const activeRes = await window.api('GET', '/showbox/active');
      if (activeRes && activeRes.active) {
        const idx = window.showboxPresentations.findIndex(p => p.name === activeRes.active);
        if (idx >= 0) {
          const targetPres = window.showboxPresentations[idx];
          const isImportant = targetPres && targetPres.name && (targetPres.name.startsWith("Blockade:") || targetPres.name.startsWith("Important"));
          
          if (isImportant) {
            if (window.activeShowboxIndex !== idx || !window.showboxActive) {
              window.showboxManualNavigation = false;
              window.triggerShowbox(idx);
            }
          } else if (!window.showboxManualNavigation) {
            if (window.activeShowboxIndex !== idx || !window.showboxActive) {
              window.triggerShowbox(idx);
            }
          }
        }
      } else if (!window.showboxManualNavigation) {
        // Only close if not actively navigating manually
        const activeLayerHasHistory = state.layers[state.activeLayer].currentHistoryIdx !== -1;
        if (window.showboxActive && !activeLayerHasHistory) {
          window.closeShowbox();
        }
      }
    } catch (e) {
      console.error("Failed to sync modular Showbox list:", e);
    }
  };

  // 4. window.navigateShowboxHistory — REMOVED (no navigation)

  // ── Global Interactive Help Event Listeners ──
  let originalShowboxContent = null;
  let originalActiveLayer = null;

  window.showShowboxHelp = function(title, text) {
    const activeLayer = state.activeLayer;
    const bodyEl = document.getElementById(`sb-layer-body-${activeLayer}`);
    if (!bodyEl) return;
    
    if (originalShowboxContent === null) {
      originalShowboxContent = bodyEl.innerHTML;
      originalActiveLayer = activeLayer;
    }
    
    bodyEl.innerHTML = `
      <div class="interactive-help-box" style="padding: 24px 20px; background: rgba(0, 229, 255, 0.08); border: 2px solid rgba(0, 229, 255, 0.25); border-radius: 12px; animation: fadeIn 0.2s ease; width: 90%; height: 90%; display: flex; flex-direction: column; justify-content: center; box-sizing: border-box; box-shadow: 0 0 20px rgba(0, 229, 255, 0.15); margin: auto;">
        <h4 style="margin: 0 0 14px 0; font-size: 1.3rem; color: var(--cyan); display: flex; align-items: center; gap: 8px; font-weight: 700; text-shadow: 0 0 10px rgba(0, 229, 255, 0.4); text-transform: none; letter-spacing: 0.5px;">
          💡 ${title}
        </h4>
        <div style="margin: 0; font-size: 1.05rem; line-height: 1.55; color: #ffffff; font-weight: normal; white-space: normal; text-transform: none; word-break: break-word; text-align: left; overflow-y: auto; flex: 1; padding-right: 6px;">
          ${text}
        </div>
      </div>
    `;
  };

  window.hideShowboxHelp = function() {
    if (originalShowboxContent !== null && originalActiveLayer !== null) {
      const bodyEl = document.getElementById(`sb-layer-body-${originalActiveLayer}`);
      if (bodyEl) {
        bodyEl.innerHTML = originalShowboxContent;
      }
      originalShowboxContent = null;
      originalActiveLayer = null;
    }
  };

  // Listen to global mouse events
  document.addEventListener('mouseover', (e) => {
    const el = e.target.closest('[data-help], [data-help-en]');
    if (el) {
      const help = (typeof window.helpTextFor === 'function')
        ? window.helpTextFor(el)
        : { title: el.getAttribute('data-help-title') || 'Erklärung',
            body: el.getAttribute('data-help') || '' };
      window.showShowboxHelp(help.title || 'Erklärung', help.body);
    }
  });

  document.addEventListener('mouseout', (e) => {
    const el = e.target.closest('[data-help], [data-help-en]');
    if (el) {
      window.hideShowboxHelp();
    }
  });

  // Initialize component on document ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ── Public API: window.ShowboxModule ───────────────────────────────────────
  // Single source of truth für alles was vorher über getrennte Globals lief.
  // Backward-Compat: alte window.ShowboxButtons-Aufrufer (User-Mandat: nichts
  // hart abreißen) bekommen einen Shim der auf die neuen Methoden delegiert.
  const ShowboxModule = {
    // Render-Pipeline
    render: renderLayerContent,
    init,
    switchLayer: (idx, skipFlash) => switchLayer(idx, skipFlash),

    // Showbox-Trigger
    trigger: window.triggerShowbox,
    close: window.closeShowbox,
    toast: window.showboxToast,
    loadList: window.loadShowboxList,

    // Help & Art
    buildHelpSlides: window.buildHelpSlides,
    showHelp: window.showHelpSlides,
    buildAgentArtShow: window.buildAgentArtShow,
    triggerAgentArtShow: window.triggerAgentArtShow,

    // Button-Grid (intern)
    setButtons,
    clearButtons,
    extractInlineButtons,
    MAX_BUTTONS,

    // Meta
    LAYERS,
    VERSION: '2.0.0-consolidated'
  };
  window.ShowboxModule = ShowboxModule;

  // Backward-Compat-Shim für window.ShowboxButtons (alte showbox-buttons.js API).
  // Wer noch window.ShowboxButtons.setButtons(...) ruft → landet hier.
  window.ShowboxButtons = {
    setButtons,
    clearButtons,
    render: renderButtonGrid,
    extractInlineButtons: (domBody) => extractInlineButtons(domBody, null),
    MAX_BUTTONS
  };
})();
