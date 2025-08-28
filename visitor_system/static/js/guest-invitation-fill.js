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
          mask: '+7 (000) 000 00 00', 
          lazy: false 
        });
        
        // Initialize from existing hidden value if present
        const setFromHidden = () => {
          const v = (hiddenPhone.value || '').replace(/\D/g, '');
          // If hidden starts with 7, remove it for the mask (since mask adds +7)
          const digits = v.startsWith('7') ? v.substring(1) : v;
          if (digits) mask.unmaskedValue = digits; else phoneMasked.value = '';
        };
        setFromHidden();
        
        // Validate phone number and provide visual feedback
        function validate() {
          const ok = mask.unmaskedValue && mask.unmaskedValue.length === 10;
          if (mask.unmaskedValue.length > 0) {
            phoneMasked.classList.toggle('is-valid', !!ok);
            phoneMasked.classList.toggle('is-invalid', !ok);
          } else {
            phoneMasked.classList.remove('is-valid', 'is-invalid');
          }
          return ok;
        }
        
        // Update hidden field with E.164 format on input
        mask.on('accept', function() {
          // Simply set the value to +7 followed by the unmasked digits
          hiddenPhone.value = '+7' + mask.unmaskedValue;
          validate();
        });
        
        // Also validate on blur
        phoneMasked.addEventListener('blur', function() {
          if (mask.unmaskedValue && mask.unmaskedValue.length > 0) validate();
        });
        
        // Form submission validation
        form.addEventListener('submit', function(e) {
          if (mask.unmaskedValue && mask.unmaskedValue.length > 0 && !validate()) {
            e.preventDefault();
            phoneMasked.focus();
          }
        });
        
        // Initial validation if value exists
        if (mask.unmaskedValue.length > 0) validate();
      } else {
        // Simple fallback when IMask isn't available
        function formatPhone(value) {
          const digits = (value || '').replace(/\D/g, '');
          if (!digits) return '';
          
          let formatted = '+7';
          if (digits.length > 0) formatted += ' ' + digits.substring(0, 3);
          if (digits.length > 3) formatted += ' ' + digits.substring(3, 6);
          if (digits.length > 6) formatted += ' ' + digits.substring(6, 8);
          if (digits.length > 8) formatted += ' ' + digits.substring(8, 10);
          return formatted;
        }
        
        // Initialize from existing value
        if (hiddenPhone.value) {
          const digits = hiddenPhone.value.replace(/\D/g, '');
          const cleanDigits = digits.startsWith('7') ? digits.substring(1) : digits;
          phoneMasked.value = formatPhone(cleanDigits);
        }
        
        function validate() {
          const digits = phoneMasked.value.replace(/\D/g, '');
          const ok = digits.length === 10 || (digits.length === 11 && digits.startsWith('7'));
          if (digits.length > 0) {
            phoneMasked.classList.toggle('is-valid', ok);
            phoneMasked.classList.toggle('is-invalid', !ok);
          } else {
            phoneMasked.classList.remove('is-valid', 'is-invalid');
          }
          return ok;
        }
        
        phoneMasked.addEventListener('input', function() {
          const digits = this.value.replace(/\D/g, '').substring(0, 10);
          hiddenPhone.value = '+7' + digits;
          this.value = formatPhone(digits);
          validate();
        });
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
