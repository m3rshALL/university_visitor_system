// Simple Tabler-style toast helper with aria-live support
(function () {
  const TYPES = {
    info: 'bg-blue-lt text-blue',
    success: 'bg-green-lt text-green',
    warning: 'bg-yellow-lt text-yellow',
    error: 'bg-red-lt text-red',
  };

  function ensureContainer() {
    let c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      c.setAttribute('aria-live', 'polite');
      c.setAttribute('aria-atomic', 'true');
      c.className = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  function toast(message, type = 'info', opts = {}) {
    const container = ensureContainer();
    const item = document.createElement('div');
    item.className = `toast-item ${TYPES[type] || TYPES.info}`;
    item.setAttribute('role', 'alert');
    item.setAttribute('aria-live', 'polite');
    item.setAttribute('aria-atomic', 'true');
    item.innerHTML = `
      <div class="d-flex align-items-center">
        <div class="me-2 toast-dot"></div>
        <div class="flex-fill">${message}</div>
        <button type="button" class="btn btn-link text-secondary ms-2 p-1 close-btn" aria-label="Закрыть">✕</button>
      </div>`;
    container.appendChild(item);

    const remove = () => {
      item.classList.add('hide');
      setTimeout(() => item.remove(), 250);
    };
    item.querySelector('.close-btn')?.addEventListener('click', remove);
    setTimeout(remove, opts.duration || 4000);
    return item;
  }

  window.toast = toast;
})();
