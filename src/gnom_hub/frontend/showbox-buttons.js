/* showbox-buttons.js — Dynamic Showbox Button Controller
 * 8 dynamic slots in 2x4 grid. Buttons are configured by the worker/system agent
 * via ShowboxButtons.setButtons([...]) — typically called from showbox.js when
 * a new slide is rendered.
 *
 * Each button: { id, icon, label, color, onClick }
 *   - id:      string (e.g. "ok", "approve_decision_<uuid>")
 *   - icon:    string (HTML or emoji, e.g. "✓" or "<svg>...</svg>")
 *   - label:   string (optional text after icon)
 *   - color:   "red" | "green" | "orange" | "yellow" | "cyan" | "blue" | "purple" (optional)
 *   - onClick: function(e, btn) | string (action)
 *       - function: executed directly in the browser
 *       - string: parsed as an action:
 *           "approve_decision:<uuid>"  -> POSTs @@approve_decision <uuid>
 *           "reject_decision:<uuid>"   -> POSTs @@reject_decision <uuid>
 *           "close"                    -> closes the showbox
 *           "send:<text>"              -> sends <text> as user message
 *           anything else              -> sends as user message "[Button <id>] <action>"
 *
 * Empty slots render as invisible placeholders to keep the 2x4 grid aligned.
 */
(function () {
  const MAX_BUTTONS = 8;
  const buttons = new Array(MAX_BUTTONS).fill(null);

  const container = () => document.getElementById('showbox-control-buttons');

  function handleAction(btn) {
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

  function render() {
    const el = container();
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
            handleAction(btn);
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

  // ── Inline-Button-Extraktion ────────────────────────────────────────────
  // Scans ein Slide-Element nach Elementen mit `data-sb-action` oder der
  // Klasse `sb-promo`. Pro gefundenem Element wird ein Eintrag im
  // Button-Grid erzeugt (max MAX_BUTTONS). Die Inline-Elemente selbst
  // werden via CSS (Pointer-events: none + gestrichelter Rahmen) als
  // visueller Hinweis erhalten — der eigentliche Klick erfolgt unten.
  //
  // data-sb-action unterstützt:
  //   data-sb-action="close"            → schließt den Showbox
  //   data-sb-action="send:Hallo Welt"   → sendet Text als User-Message
  //   data-sb-action="next-slide"        → nächste Folie
  //   data-sb-action="prev-slide"        → vorherige Folie
  //   data-sb-action="toggle-lang"       → DE ↔ EN
  //   data-sb-action="open-overlay"      → Fullscreen-Overlay
  //   data-sb-action="<frei>"            → wird als User-Message gesendet
  //
  // data-sb-icon   Emoji/SVG für die Button-Grafik
  // data-sb-label  Beschriftung (Fallback: Element-TextContent)
  // data-sb-color  red/green/orange/yellow/cyan/blue/purple
  function extractInlineButtons(slideEl) {
    if (!slideEl) return [];
    const out = [];
    const seen = new Set();
    const selectors = '[data-sb-action], .sb-promo';
    const nodes = slideEl.querySelectorAll ? slideEl.querySelectorAll(selectors) : [];
    // Doppelte Elemente (z.B. data-sb-action + .sb-promo kombiniert) nur 1x.
    for (const node of nodes) {
      if (seen.has(node)) continue;
      seen.add(node);
      const action = node.getAttribute('data-sb-action') || node.textContent.trim();
      if (!action) continue;
      const label = node.getAttribute('data-sb-label') || node.textContent.trim().slice(0, 30) || action.slice(0, 30);
      const icon = node.getAttribute('data-sb-icon') || node.getAttribute('data-icon') || '';
      const color = node.getAttribute('data-sb-color') || '';
      const btn = { id: 'inline-' + (out.length + 1), icon, label, color, onClick: action };
      out.push(btn);
      if (out.length >= MAX_BUTTONS) break;
    }
    return out;
  }

  function setButtons(list) {
    buttons.fill(null);
    const arr = Array.isArray(list) ? list.slice(0, MAX_BUTTONS) : [];
    for (let i = 0; i < arr.length; i++) {
      buttons[i] = arr[i];
    }
    render();
  }

  function clearButtons() {
    buttons.fill(null);
    render();
  }

  window.ShowboxButtons = {
    setButtons,
    clearButtons,
    render,
    extractInlineButtons,
    MAX_BUTTONS
  };
})();
