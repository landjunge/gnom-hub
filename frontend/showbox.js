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

  // Initialize modular Showbox DOM structure
  function init() {
    const container = document.getElementById('modular-showbox-container');
    if (!container) {
      console.warn("Modular Showbox container (#modular-showbox-container) not found in DOM.");
      return;
    }

    // Build the markup
    container.innerHTML = `
      <div class="modular-showbox">
        <div class="showbox-layers-container" id="sb-layers-container">
          <!-- Layer 1: System-Agenten -->
          <div class="sb-layer active" id="sb-layer-1" data-layer="1">
            <span class="sb-layer-label">System-Agenten</span>
            <div class="sb-layer-body" id="sb-layer-body-1">STANDBY</div>
          </div>
          <!-- Layer 2: Worker -->
          <div class="sb-layer" id="sb-layer-2" data-layer="2">
            <span class="sb-layer-label">Worker</span>
            <div class="sb-layer-body" id="sb-layer-body-2">STANDBY</div>
          </div>
          <!-- Layer 3: User / Entscheidung -->
          <div class="sb-layer" id="sb-layer-3" data-layer="3">
            <span class="sb-layer-label">User / Entscheidung</span>
            <div class="sb-layer-body" id="sb-layer-body-3">STANDBY</div>
          </div>
        </div>
        <!-- 4 Buttons below -->
        <div class="showbox-controls">
          <button class="sb-btn" id="sb-btn-prev" title="Zurück">
            <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          </button>
          <button class="sb-btn" id="sb-btn-delete" title="Löschen">
            <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
          </button>
          <button class="sb-btn" id="sb-btn-switch" title="Layer wechseln">
            <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
          </button>
          <button class="sb-btn" id="sb-btn-next" title="Vor">
            <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
          </button>
        </div>
      </div>
    `;

    // Bind event listeners to buttons
    document.getElementById('sb-btn-prev').addEventListener('click', (e) => {
      e.stopPropagation();
      prevSlide();
    });
    document.getElementById('sb-btn-delete').addEventListener('click', (e) => {
      e.stopPropagation();
      clearActiveLayer();
    });
    document.getElementById('sb-btn-switch').addEventListener('click', (e) => {
      e.stopPropagation();
      cycleLayer();
    });
    document.getElementById('sb-btn-next').addEventListener('click', (e) => {
      e.stopPropagation();
      nextSlide();
    });

    // Make container clickable to open full detail modal
    document.getElementById('sb-layers-container').addEventListener('click', () => {
      if (typeof window.openShowboxOverlay === 'function') {
        window.openShowboxOverlay();
      }
    });

    // Sync button disabled states initially
    updateButtonStates();
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
  function switchLayer(layerIdx) {
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

    // Trigger frame flash/glow animation
    const container = document.getElementById('sb-layers-container');
    if (container) {
      container.classList.remove('flash-1', 'flash-2', 'flash-3');
      void container.offsetWidth; // Force CSS reflow
      container.classList.add(`flash-${layerIdx}`);
    }

    updateButtonStates();
  }

  // Cycle through the layers (1 -> 2 -> 3 -> 1)
  function cycleLayer() {
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

  // Render the current slide of the current history item in the given layer
  function renderLayerContent(layerIdx) {
    const layer = state.layers[layerIdx];
    const body = document.getElementById(`sb-layer-body-${layerIdx}`);
    if (!body) return;

    if (layer.currentHistoryIdx === -1 || layer.history.length === 0) {
      body.innerHTML = 'STANDBY';
      body.style.fontSize = '0.82rem';
      return;
    }

    const pres = layer.history[layer.currentHistoryIdx];
    const slide = pres.slides[pres.currentSlideIdx] || 'Kein Inhalt';
    body.innerHTML = slide;

    autoFitText(layerIdx);
  }

  // Navigate backward
  function prevSlide() {
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
    const btnPrev = document.getElementById('sb-btn-prev');
    const btnNext = document.getElementById('sb-btn-next');
    if (!btnPrev || !btnNext) return;

    const layer = state.layers[state.activeLayer];
    if (layer.currentHistoryIdx === -1 || layer.history.length === 0) {
      btnPrev.disabled = true;
      btnNext.disabled = true;
      btnPrev.style.opacity = 0.4;
      btnNext.style.opacity = 0.4;
      return;
    }

    const pres = layer.history[layer.currentHistoryIdx];
    
    // Can we go back?
    const hasPrev = pres.currentSlideIdx > 0 || layer.currentHistoryIdx > 0;
    btnPrev.disabled = !hasPrev;
    btnPrev.style.opacity = hasPrev ? 1 : 0.4;

    // Can we go forward?
    const hasNext = pres.currentSlideIdx < pres.slides.length - 1 || layer.currentHistoryIdx < layer.history.length - 1;
    btnNext.disabled = !hasNext;
    btnNext.style.opacity = hasNext ? 1 : 0.4;
  }

  // Expose triggers & helpers to window for Gnom-Hub sync and legacy code support

  // 1. window.triggerShowbox
  window.triggerShowbox = function (showboxIndex, sender) {
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
    window.activeShowboxIndex = -1;
    window.showboxActive = false;
    
    // Clear all layers to standby
    for (let i = 1; i <= 3; i++) {
      state.layers[i].currentHistoryIdx = -1;
      renderLayerContent(i);
    }
    updateButtonStates();
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
