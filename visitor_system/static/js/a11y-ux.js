// Global UX helpers: HTMX indicators, aria-busy, sticky submit on mobile, focus styles
(function () {
  // HTMX indicators: toggle aria-busy and disabled on submit buttons; mark busy containers
  document.addEventListener('htmx:beforeRequest', function (e) {
    const tgt = e.target;
    if (!tgt) return;
    const indicatorSel = tgt.getAttribute('hx-indicator');
    const indicator = indicatorSel ? document.querySelector(indicatorSel) : null;
    if (indicator) indicator.classList.add('is-loading');

    // Determine the submit button to disable/spin (works when tgt is a form)
    let btn = null;
    if (tgt.matches('button,[type="submit"]')) {
      btn = tgt;
  } else if (tgt.closest && tgt.closest('button,[type="submit"]')) {
      // Fallback for events triggered from descendants
      btn = tgt.closest('button,[type="submit"]');
    } else if (tgt.tagName === 'FORM') {
      // Prefer focused submit inside the form, else the first enabled submit
      const active = document.activeElement;
      if (active && tgt.contains(active) && active.matches('button,[type="submit"]')) {
        btn = active;
      } else {
        btn = tgt.querySelector('button[type="submit"]:not([disabled])');
      }
    }
    if (btn) {
      btn.dataset._prevText = btn.innerHTML;
      btn.disabled = true;
      btn.setAttribute('aria-busy', 'true');
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span><span>Загрузка...</span>';
    }

    const container = (tgt.closest ? tgt.closest('[data-busy-container]') : null) || (indicator ? indicator.closest('[data-busy-container]') : null);
    if (container) container.setAttribute('aria-busy', 'true');
  });

  function endLoading(e) {
    const tgt = e.target;
    if (!tgt) return;
    const indicatorSel = tgt.getAttribute('hx-indicator');
    const indicator = indicatorSel ? document.querySelector(indicatorSel) : null;
    if (indicator) indicator.classList.remove('is-loading');
    const btn = (tgt.matches('button,[type="submit"]') ? tgt : tgt.closest('button,[type="submit"]'));
    if (btn && btn.dataset._prevText != null) {
      btn.disabled = false;
      btn.removeAttribute('aria-busy');
      btn.innerHTML = btn.dataset._prevText;
      delete btn.dataset._prevText;
    }
    const container = tgt.closest('[data-busy-container]');
    if (container) container.removeAttribute('aria-busy');
  }
  document.addEventListener('htmx:afterOnLoad', endLoading);
  document.addEventListener('htmx:responseError', endLoading);

  // Sticky submit on mobile: any form with [data-sticky-submit]
  function setupSticky() {
    document.querySelectorAll('form[data-sticky-submit] .sticky-submit').forEach((bar) => {
      bar.classList.add('sticky-submit-ready');
    });
  }
  document.addEventListener('DOMContentLoaded', setupSticky);
  document.addEventListener('htmx:afterSwap', setupSticky);

  // Error summary helper: builds a clickable list of invalid fields
  window.buildErrorSummary = function (form, title) {
    const invalids = form.querySelectorAll('.is-invalid, [aria-invalid="true"]');
    if (!invalids.length) return null;
    let box = form.querySelector('.error-summary');
    if (!box) {
      box = document.createElement('div');
      box.className = 'error-summary alert alert-danger';
      box.setAttribute('role', 'alert');
      box.setAttribute('tabindex', '-1');
      form.prepend(box);
    }
    const list = Array.from(invalids).map((el) => {
      const id = el.id || (el.name ? el.name.replace(/[^a-z0-9_\-]/gi, '_') : Math.random().toString(36).slice(2));
      if (!el.id) el.id = id;
      const label = form.querySelector(`label[for="${el.id}"]`)?.textContent?.trim() || el.placeholder || el.name || 'Поле';
      return `<li><a href="#${id}">${label}</a></li>`;
    }).join('');
    box.innerHTML = `<strong>${title || 'Проверьте форму:'}</strong><ul class="mt-2 mb-0">${list}</ul>`;
    box.querySelectorAll('a').forEach((a) => {
      a.addEventListener('click', (ev) => {
        ev.preventDefault();
        const target = form.querySelector(a.getAttribute('href'));
        target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => target?.focus(), 250);
      });
    });
    box.focus();
    return box;
  };

  // Global client-side validation for .needs-validation forms
  function markInvalid(el) {
    if (!el) return;
    if (typeof el.checkValidity === 'function' && !el.checkValidity()) {
      el.classList.add('is-invalid');
    }
  }

  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (!form.classList.contains('needs-validation')) return;
    // Use native validation; if fails, prevent submit and build summary
    if (!form.checkValidity()) {
      e.preventDefault();
      e.stopPropagation();
      // Mark all invalid fields and focus first
      const invalids = form.querySelectorAll(':invalid');
      invalids.forEach((el) => el.classList.add('is-invalid'));
      const first = invalids[0];
      if (first) {
        first.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => first.focus(), 250);
      }
      buildErrorSummary(form, 'Проверьте форму:');
    }
  }, true);

  // Keep is-invalid in sync as user fixes fields
  document.addEventListener('input', function (e) {
    const el = e.target;
    const form = el && el.closest && el.closest('form.needs-validation');
    if (!form) return;
    if (typeof el.checkValidity === 'function' && el.classList.contains('is-invalid') && el.checkValidity()) {
      el.classList.remove('is-invalid');
    }
  });

  // When the browser fires invalid, add class for consistent styling
  document.addEventListener('invalid', function (e) {
    const el = e.target;
    if (el && el.classList) el.classList.add('is-invalid');
  }, true);

  // Link help texts to inputs for aria-describedby when missing
  function wireHelpTextDescribedBy(root) {
    (root || document).querySelectorAll('.form-text, .form-hint').forEach((hint) => {
      if (!hint.id) hint.id = 'hint_' + Math.random().toString(36).slice(2);
      // Try to find a control before or parent container
      let control = hint.previousElementSibling;
      if (!(control && (/(INPUT|SELECT|TEXTAREA)/).test(control.tagName))) {
        control = hint.closest('.mb-3,.form-group,.col,.row')?.querySelector('input,select,textarea');
      }
      if (control && !control.getAttribute('aria-describedby')) {
        control.setAttribute('aria-describedby', hint.id);
      }
    });
  }
  document.addEventListener('DOMContentLoaded', function(){ wireHelpTextDescribedBy(); });
  document.addEventListener('htmx:afterSwap', function(e){ wireHelpTextDescribedBy(e.target); });

  // After HTMX swap, move focus to first heading or form control in target region
  document.addEventListener('htmx:afterSwap', function (e) {
    try {
      var t = e.target;
      if (!t) return;
      var focusable = t.querySelector('h1, h2, h3, [role="heading"], input, select, textarea, button, a[href]');
      if (focusable) {
        if (!focusable.hasAttribute('tabindex')) focusable.setAttribute('tabindex', '-1');
        focusable.focus({ preventScroll: false });
      }
    } catch (_) {}
  });
})();
