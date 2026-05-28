/* showbox.js — Modular Showbox Script */

(function () {
  // 3 Layers configuration
  const LAYERS = {
    SYSTEM: 1, // System-Agenten (GeneralAG, SoulAG, SecurityAG, WatchdogAG, System)
    WORKER: 2, // Worker (CoderAG, WriterAG, ResearcherAG, EditorAG)
    USER: 3    // User / Entscheidungen
  };

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
    if (window.ShowboxButtons) {
      window.ShowboxButtons.configure('ok', { disabled: true });
      window.ShowboxButtons.configure('cancel', { disabled: true });
    }
    if (typeof window.api === 'function') {
      await window.api('POST', '/chat', { content: `@@approve_decision ${activeDecisionId}` });
      if (typeof window.loadChat === 'function') window.loadChat();
    }
  }

  async function handleCancelAction() {
    if (!activeDecisionId) return;
    toast('Entscheidung gesendet: Ablehnen', 'warning');
    if (window.ShowboxButtons) {
      window.ShowboxButtons.configure('ok', { disabled: true });
      window.ShowboxButtons.configure('cancel', { disabled: true });
    }
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
      <div class="showbox-controls">
        <button class="sb-btn" id="sb-btn-prev" title="Zurück"></button>
        <button class="sb-btn" id="sb-btn-delete" title="Löschen"></button>
        <button class="sb-btn" id="sb-btn-switch" title="Layer wechseln"></button>
        <button class="sb-btn" id="sb-btn-next" title="Vor"></button>
      </div>
      <div class="showbox-extra-controls">
        <button class="sb-btn sb-btn-long" id="sb-btn-cancel"></button>
        <button class="sb-btn sb-btn-long" id="sb-btn-ok"></button>
      </div>
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

  function initButtons() {
    if (window.ShowboxButtons) {
      window.ShowboxButtons.configure('prev', {
        icon: `<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>`,
        onClick: () => prevSlide()
      });
      window.ShowboxButtons.configure('delete', {
        icon: `<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>`,
        onClick: () => clearActiveLayer()
      });
      window.ShowboxButtons.configure('switch', {
        icon: `<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>`,
        onClick: () => cycleLayer()
      });
      window.ShowboxButtons.configure('next', {
        icon: `<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>`,
        onClick: () => nextSlide()
      });
      window.ShowboxButtons.configure('cancel', {
        text: 'Abbrechen',
        color: 'red',
        onClick: () => handleCancelAction()
      });
      window.ShowboxButtons.configure('ok', {
        text: 'Okay',
        color: 'green',
        onClick: () => handleOkAction()
      });
      window.ShowboxButtons.init();
    }
    updateButtonStates();
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
    initButtons();
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

    updateButtonStates();
  }

  // Cycle through the layers (1 -> 2 -> 3 -> 1)
  function cycleLayer() {
    cancelToastRevert();
    let next = state.activeLayer + 1;
    if (next > 3) next = 1;
    switchLayer(next);
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
    if (window.ShowboxButtons) {
      const disabled = !decisionId;
      window.ShowboxButtons.configure('ok', { disabled });
      window.ShowboxButtons.configure('cancel', { disabled });
    }
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
      return;
    }

    const pres = layer.history[layer.currentHistoryIdx];
    const slide = pres.slides[pres.currentSlideIdx] || 'Kein Inhalt';
    body.innerHTML = slide;

    if (layerIdx === LAYERS.USER) {
      const match = slide.match(/@@approve_decision\s+([a-f0-9\-]+)/);
      updateDecisionButtons(match ? match[1] : null);
    }

    autoFitText(layerIdx);
  }

  // Navigate backward
  function prevSlide() {
    cancelToastRevert();
    const layer = state.layers[state.activeLayer];
    if (layer.currentHistoryIdx === -1) return;

    const pres = layer.history[layer.currentHistoryIdx];
    if (pres.currentSlideIdx > 0) {
      // Go to previous slide in same presentation
      pres.currentSlideIdx--;
    } else if (layer.currentHistoryIdx > 0) {
      // Go to previous presentation in history
      layer.currentHistoryIdx--;
      const newPres = layer.history[layer.currentHistoryIdx];
      newPres.currentSlideIdx = newPres.slides.length - 1; // Start at last slide of previous presentation
    } else {
      return; // At the very beginning
    }

    renderLayerContent(state.activeLayer);
    updateButtonStates();
  }

  // Navigate forward
  function nextSlide() {
    cancelToastRevert();
    const layer = state.layers[state.activeLayer];
    if (layer.currentHistoryIdx === -1) return;

    const pres = layer.history[layer.currentHistoryIdx];
    if (pres.currentSlideIdx < pres.slides.length - 1) {
      // Go to next slide in same presentation
      pres.currentSlideIdx++;
    } else if (layer.currentHistoryIdx < layer.history.length - 1) {
      // Go to next presentation in history
      layer.currentHistoryIdx++;
      const newPres = layer.history[layer.currentHistoryIdx];
      newPres.currentSlideIdx = 0; // Start at first slide
    } else {
      return; // At the very end
    }

    renderLayerContent(state.activeLayer);
    updateButtonStates();
  }

  // Clear history of the active layer and reset to standby
  function clearActiveLayer() {
    cancelToastRevert();
    const layer = state.layers[state.activeLayer];
    layer.history = [];
    layer.currentHistoryIdx = -1;
    
    renderLayerContent(state.activeLayer);
    updateButtonStates();
    
    // Clear global active presentation if we just deleted it
    if (state.activeLayer === LAYERS.SYSTEM || state.activeLayer === LAYERS.USER) {
      if (typeof window.api === 'function') {
        window.api('POST', '/showbox/active', { name: "" });
      }
    }
  }

  // Update enable/disabled visual states of buttons
  function updateButtonStates() {
    if (!window.ShowboxButtons) return;
    const layer = state.layers[state.activeLayer];
    if (layer.currentHistoryIdx === -1 || layer.history.length === 0) {
      window.ShowboxButtons.configure('prev', { disabled: true });
      window.ShowboxButtons.configure('next', { disabled: true });
      return;
    }
    const pres = layer.history[layer.currentHistoryIdx];
    const hasPrev = pres.currentSlideIdx > 0 || layer.currentHistoryIdx > 0;
    const hasNext = pres.currentSlideIdx < pres.slides.length - 1 || layer.currentHistoryIdx < layer.history.length - 1;
    window.ShowboxButtons.configure('prev', { disabled: !hasPrev });
    window.ShowboxButtons.configure('next', { disabled: !hasNext });
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
      layer.currentHistoryIdx = existingIdx;
    } else {
      // Push new presentation to history
      layer.history.push({
        name: pres.name,
        slides: slides,
        sender: senderName,
        currentSlideIdx: 0
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
    updateButtonStates();
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
    updateButtonStates();

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
        updateButtonStates();
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

  // 4. window.navigateShowboxHistory (bridge for overlay modal)
  window.navigateShowboxHistory = function (direction) {
    if (direction < 0) {
      prevSlide();
    } else {
      nextSlide();
    }
  };

  // Initialize component on document ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
