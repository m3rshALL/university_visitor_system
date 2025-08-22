// Unified UI helpers: toast notifications and small utilities
(function(){
  function ensureToastRoot(){
    var root = document.getElementById('toast-root');
    if (!root){
      root = document.createElement('div');
      root.id = 'toast-root';
      root.className = 'toast-root';
      root.setAttribute('aria-live', 'polite');
      root.setAttribute('aria-atomic', 'true');
      root.setAttribute('role', 'region');
      document.body.appendChild(root);
    }
    return root;
  }

  function buildToastHtml(title, message, kind){
    var k = (kind || 'info').toLowerCase();
    var icon = {
      success: '✔',
      danger: '⚠',
      error: '⚠',
      warning: '⚠',
      info: 'ℹ'
    }[k] || 'ℹ';
    return '<div class="toast-item toast-'+k+'" role="alert" aria-live="polite" aria-atomic="true">'
      + '<div class="toast-icon" aria-hidden="true">'+icon+'</div>'
      + '<div class="toast-content">'
      +   (title ? '<div class="toast-title">'+escapeHtml(title)+'</div>' : '')
      +   (message ? '<div class="toast-message">'+escapeHtml(message)+'</div>' : '')
      + '</div>'
      + '<button class="toast-close" aria-label="Закрыть уведомление">×</button>'
      + '</div>';
  }

  function escapeHtml(str){
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function wireClose(btn, item){
    if (!btn || !item) return;
    btn.addEventListener('click', function(e){
      e.preventDefault();
      item.classList.add('toast-hide');
      setTimeout(function(){ item.remove(); }, 250);
    });
  }

  function toastCore(title, message, kind, ttl){
    var root = ensureToastRoot();
    var container = document.createElement('div');
    container.innerHTML = buildToastHtml(title, message, kind);
    var item = container.firstChild;
    root.appendChild(item);
    var closeBtn = item.querySelector('.toast-close');
    wireClose(closeBtn, item);
    var life = Math.max(1500, Math.min(10000, ttl || 3500));
    setTimeout(function(){
      if (!item.isConnected) return;
      item.classList.add('toast-hide');
      setTimeout(function(){ item.remove(); }, 250);
    }, life);
    return item;
  }

  // Public API
  window.toast = function(arg1, arg2, arg3, arg4){
    // Variants: (message, type), (title, message, type), ({title, message, type, ttl})
    if (typeof arg1 === 'object' && arg1){
      return toastCore(arg1.title || '', arg1.message || '', arg1.type || 'info', arg1.ttl || 3500);
    }
    if (typeof arg3 !== 'undefined'){
      return toastCore(arg1 || '', arg2 || '', arg3 || 'info', arg4 || 3500);
    }
    // (message, type)
    return toastCore('', arg1 || '', arg2 || 'info', 3500);
  };

  // Backward-compat helper used across templates
  window.showToast = function(arg1, arg2, arg3){
    // Dashboard uses (title, msg, kind), other pages use (message, kind)
    if (typeof arg3 !== 'undefined'){
      return window.toast(arg1, arg2, arg3);
    } else {
      return window.toast(arg1, arg2);
    }
  };
})();


