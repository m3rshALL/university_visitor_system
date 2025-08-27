// Re-initialize Alpine.js for DOM inserted by HTMX swaps
// Safe to include on every page; no-ops if Alpine or htmx aren't present
(function () {
  function initAlpineIn(el) {
    try {
      if (window.Alpine && typeof window.Alpine.initTree === 'function' && el) {
        window.Alpine.initTree(el);
      }
    } catch (e) {
      // ignore
    }
  }

  document.addEventListener('htmx:afterSwap', function (evt) {
    // Initialize Alpine in the swapped content
    initAlpineIn(evt.detail && evt.detail.target);
  });

  // Also handle out-of-band swaps
  document.addEventListener('htmx:oobAfterSwap', function (evt) {
    initAlpineIn(evt.detail && evt.detail.target);
  });
})();
