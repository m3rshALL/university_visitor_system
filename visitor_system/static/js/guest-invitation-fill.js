// Handles phone masking, basic validation UX, and submit spinner for guest invitation fill page
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('form');
    if (!form) return;

    // Phone mask: visible masked input + hidden numeric field used by Django form
    const phoneMasked = document.getElementById('guest_phone_masked');
    // Try to locate hidden phone field robustly by name ending, then by id
    let hiddenPhone = form.querySelector('input[type="hidden"][name$="guest_phone"]');
    if (!hiddenPhone) {
      // Fallback common id
      hiddenPhone = document.getElementById('id_guest_phone');
    }

    if (phoneMasked && hiddenPhone) {
      if (window.IMask) {
        const mask = IMask(phoneMasked, {
          mask: '+{7} (000) 000 00 00',
          definitions: { '0': /[0-9]/ },
        });

        // Populate UI from hidden value if present
        if (hiddenPhone.value) {
          try {
            mask.value = hiddenPhone.value;
          } catch (_) {}
        }

        mask.on('accept', function () {
          hiddenPhone.value = mask.unmaskedValue;
        });
      } else {
        // Lightweight fallback: keep digits only in hidden field
        const sync = () => {
          hiddenPhone.value = (phoneMasked.value || '').replace(/\D/g, '');
        };
        phoneMasked.addEventListener('input', sync);
        sync();
      }
    }

    // IIN mask (12 digits)
    const iinInput = form.querySelector('#guest_iin, input[name$="guest_iin"], input[name="guest_iin"]');
    if (iinInput && window.IMask) {
      IMask(iinInput, { mask: '000000000000', definitions: { '0': /[0-9]/ } });
    }

    // Submit UX: client-side required checks + spinner
    form.addEventListener('submit', function (e) {
      const submitBtn = form.querySelector('button[type="submit"]');
      const requiredFields = form.querySelectorAll('[required]');
      let isValid = true;
      let firstInvalid = null;

      requiredFields.forEach((field) => {
        const val = (field.value || '').trim();
        if (!val) {
          isValid = false;
          if (!firstInvalid) firstInvalid = field;
          field.classList.add('is-invalid');
        } else {
          field.classList.remove('is-invalid');
        }
      });

      if (!isValid) {
        e.preventDefault();
        if (firstInvalid) {
          firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
          setTimeout(() => firstInvalid.focus(), 300);
        }
        const existingAlert = document.querySelector('.validation-alert');
        if (existingAlert) existingAlert.remove();
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger validation-alert mt-3';
        alertDiv.innerHTML = `
          <div class="d-flex">
            <div class="flex-shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon alert-icon" width="20" height="20" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M12 9v2m0 4v.01" /><path d="M5 19h14a2 2 0 0 0 1.414 -3.414l-7 -7a2 2 0 0 0 -2.828 0l-7 7a2 2 0 0 0 1.414 3.414z" /></svg>
            </div>
            <div class="ms-2">
              <h4 class="alert-title">Заполните обязательные поля</h4>
              <div class="text-muted">Пожалуйста, заполните все обязательные поля формы</div>
            </div>
          </div>`;
        form.insertBefore(alertDiv, form.firstChild);
        setTimeout(() => alertDiv.remove(), 5000);
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span><span class="d-none d-sm-inline">Отправка...</span><span class="d-sm-none">...</span>';
        // Safety restore after 10s if still disabled
        setTimeout(() => {
          if (submitBtn.disabled) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-send me-1" width="18" height="18" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M10 14l11 -11" /><path d="M21 3l-6.5 18a.55 .55 0 0 1 -1 0l-3.5 -7l-7 -3.5a.55 .55 0 0 1 0 -1l18 -6.5" /></svg><span class="d-none d-sm-inline">Отправить данные</span><span class="d-sm-none">Отправить</span>';
          }
        }, 10000);
      }
    });

    // Realtime validation feedback
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach((el) => {
      el.addEventListener('blur', function () {
        if (this.hasAttribute('required') && !(this.value || '').trim()) {
          this.classList.add('is-invalid');
        } else {
          this.classList.remove('is-invalid');
        }
      });
      el.addEventListener('input', function () {
        if (this.classList.contains('is-invalid') && (this.value || '').trim()) {
          this.classList.remove('is-invalid');
        }
      });
    });
  });
})();
