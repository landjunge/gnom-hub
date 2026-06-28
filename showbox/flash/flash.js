/* showbox/flash/flash.js
 * Blink-Trigger: MutationObserver auf document.body.
 * Matcht data-author, weist passende Animation zu.
 * Cleanup via animationend + 1400ms-Safety-Timeout.
 * Re-Flash-Schutz via dataset-Flag.
 */
(function () {
  'use strict';

  var FLASH_MAP = {
    general:    'flash-general',
    soul:       'flash-soul',
    coder:      'flash-coder',
    writer:     'flash-writer',
    editor:     'flash-editor',
    researcher: 'flash-researcher',
    security:   'flash-security',
    watchdog:   'flash-watchdog'
  };

  var FLASH_CLASS = 'showbox-flash-active';
  var FLASH_FLAG  = 'showboxFlashed';
  var DATA_AUTHOR = 'data-author';
  var SLIDE_SELECTORS = ['[data-author]', '.showbox-slide', '[data-showbox-slide]'];

  function getAnimationName(slide) {
    var author = slide.getAttribute(DATA_AUTHOR);
    if (!author) return null;
    var key = author.toLowerCase();
    return FLASH_MAP[key] || null;
  }

  function triggerFlash(slide) {
    if (!slide || slide.dataset[FLASH_FLAG] === 'true') return;

    var animName = getAnimationName(slide);
    if (!animName) return;

    slide.dataset[FLASH_FLAG] = 'true';
    slide.classList.add(FLASH_CLASS);
    slide.style.animationName = animName;

    var cleaned = false;
    function cleanup() {
      if (cleaned) return;
      cleaned = true;
      slide.classList.remove(FLASH_CLASS);
      slide.style.animationName = '';
      slide.removeEventListener('animationend', cleanup);
    }
    slide.addEventListener('animationend', cleanup);
    setTimeout(cleanup, 1400); // 600ms × 2 + Puffer
  }

  function scan(root) {
    if (!root || !root.querySelectorAll) return;
    SLIDE_SELECTORS.forEach(function (sel) {
      var nodes = root.querySelectorAll(sel);
      for (var i = 0; i < nodes.length; i++) triggerFlash(nodes[i]);
    });
  }

  function matchesAny(node) {
    if (!node.matches) return false;
    for (var i = 0; i < SLIDE_SELECTORS.length; i++) {
      if (node.matches(SLIDE_SELECTORS[i])) return true;
    }
    return false;
  }

  function init() {
    if (!document.body) return;

    var observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        mutation.addedNodes.forEach(function (node) {
          if (node.nodeType !== 1) return;
          if (matchesAny(node)) triggerFlash(node);
          scan(node);
        });
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
    scan(document.body);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.ShowboxFlash = {
    trigger: triggerFlash,
    scan: scan,
    map: FLASH_MAP
  };
})();