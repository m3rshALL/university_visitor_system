// Register Student Visit page initializer
(function () {
  function initPhoneMask(maskInput, hiddenInput) {
    if (!window.IMask || !maskInput || !hiddenInput) return;
    const m = IMask(maskInput, { mask: '+7 (000) 000 00 00', lazy: false });
    const setFromHidden = () => {
      const v = (hiddenInput.value || '').replace(/\D/g, '');
      const digits = v.startsWith('7') ? v.substring(1) : v;
      if (digits) m.unmaskedValue = digits; else maskInput.value = '';
    };
    setFromHidden();
    function validate() {
      const ok = m.unmaskedValue && m.unmaskedValue.length === 10;
      if (m.unmaskedValue.length > 0) {
        maskInput.classList.toggle('is-valid', !!ok);
        maskInput.classList.toggle('is-invalid', !ok);
      } else {
        maskInput.classList.remove('is-valid', 'is-invalid');
      }
      return ok;
    }
    maskInput.addEventListener('input', function () {
      hiddenInput.value = '+7' + m.unmaskedValue;
      validate();
    });
    maskInput.addEventListener('blur', function(){
      if (m.unmaskedValue && m.unmaskedValue.length > 0) validate();
    });
    const form = maskInput.closest('form');
    if (form) {
      form.addEventListener('submit', function (e) {
        if (!m.unmaskedValue || m.unmaskedValue.length === 0) {
          maskInput.classList.add('is-invalid');
          e.preventDefault();
          maskInput.focus();
          return;
        }
        if (!validate()) {
          e.preventDefault();
          maskInput.focus();
        }
      });
    }
    if (m.unmaskedValue.length > 0) validate();
  }

  function initIINValidation(iinInput) {
    if (!iinInput) return;
    function validate() {
      const v = iinInput.value.trim();
      const ok = /^\d{12}$/.test(v);
      if (v.length > 0) {
        iinInput.classList.toggle('is-valid', ok);
        iinInput.classList.toggle('is-invalid', !ok);
      } else {
        iinInput.classList.remove('is-valid', 'is-invalid');
      }
      return ok;
    }
    iinInput.addEventListener('input', function () {
      const cur = this.selectionStart;
      const old = this.value;
      const neu = old.replace(/[^\d]/g, '');
      if (old !== neu) {
        this.value = neu;
        const delta = old.length - neu.length;
        this.setSelectionRange(cur - delta, cur - delta);
      }
      validate();
    });
    iinInput.addEventListener('blur', validate);
    const form = iinInput.closest('form');
    if (form) {
      form.addEventListener('submit', function (e) {
        if (iinInput.value.trim().length === 0) {
          iinInput.classList.add('is-invalid');
          e.preventDefault();
          iinInput.focus();
          return;
        }
        if (!validate()) {
          e.preventDefault();
          iinInput.focus();
        }
      });
    }
    if (iinInput.value.trim().length > 0) validate();
  }

  function initGuestFullName(container) {
    const s = container.querySelector('#guest_surname');
    const f = container.querySelector('#guest_firstname');
    const p = container.querySelector('#guest_patronymic');
    const hidden = container.querySelector('#guest_full_name_hidden');
    if (!hidden) return;
    function update() {
      const parts = [s?.value?.trim() || '', f?.value?.trim() || '', p?.value?.trim() || ''].filter(Boolean);
      hidden.value = parts.join(' ');
    }
    [s, f, p].forEach(el => el && el.addEventListener('input', update));
    update();
  }

  function initPurposeOther(container, purposeId, wrapperId) {
    const select = purposeId ? container.querySelector(purposeId) : null;
    const wrapper = container.querySelector(wrapperId || '#student_purpose_other_wrapper');
    if (!select || !wrapper) return;
    const input = wrapper.querySelector('input, textarea');
    function toggle() {
      if (select.value === 'Other') {
        wrapper.style.display = 'block';
      } else {
        wrapper.style.display = 'none';
        if (input) input.value = '';
      }
    }
    toggle();
    select.addEventListener('change', toggle);
  }

  function initRequiredChecks(container, formId, departmentId, purposeId) {
    const form = formId ? container.querySelector(formId) : null;
    const dept = departmentId ? container.querySelector(departmentId) : null;
    const purpose = purposeId ? container.querySelector(purposeId) : null;
    if (!form || !dept || !purpose) return;
    form.addEventListener('submit', function (e) {
      let hasError = false;
      if (!dept.value) {
        dept.classList.add('is-invalid');
        hasError = true;
      } else {
        dept.classList.remove('is-invalid');
      }
      if (!purpose.value) {
        purpose.classList.add('is-invalid');
        hasError = true;
      } else {
        purpose.classList.remove('is-invalid');
        if (purpose.value === 'Other') {
          const otherWrapper = container.querySelector('#student_purpose_other_wrapper');
          const otherInput = otherWrapper && otherWrapper.querySelector('input, textarea');
          if (otherInput && !otherInput.value.trim()) {
            otherInput.classList.add('is-invalid');
            hasError = true;
          } else if (otherInput) {
            otherInput.classList.remove('is-invalid');
          }
        }
      }
      if (hasError) e.preventDefault();
    });
  }

  function initStyling(container, formId) {
    const form = formId ? container.querySelector(formId) : null;
    const controls = form ? form.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]):not([type="submit"]):not([type="button"]):not([type="hidden"]), textarea, select') : [];
    controls.forEach(function (c) {
      if (c.tagName === 'SELECT') c.classList.add('form-select');
      else if (!c.classList.contains('btn')) c.classList.add('form-control');
      const err = c.closest('.mb-3')?.querySelector('.invalid-feedback');
      if (err && err.innerText.trim() !== '') c.classList.add('is-invalid');
      else c.classList.remove('is-invalid');
    });
  }

  function init(container) {
    // data attributes provide selectors
    const formId = container.dataset.formId || '#student-reg-form';
    const purposeId = container.dataset.purposeId;
    const deptId = container.dataset.deptId;
    const phoneHiddenId = container.dataset.guestPhoneHiddenId;
    const iinId = container.dataset.guestIinId;

    initPhoneMask(container.querySelector('#guest_phone_masked'), phoneHiddenId ? container.querySelector(phoneHiddenId) : null);
    initIINValidation(iinId ? container.querySelector(iinId) : null);
    initGuestFullName(container);
    initPurposeOther(container, purposeId, '#student_purpose_other_wrapper');
    initRequiredChecks(container, formId, deptId, purposeId);
    initStyling(container, formId);
  }

  function initNow() {
    const container = document.getElementById('student-form-container');
    if (container) init(container);
  }

  document.addEventListener('DOMContentLoaded', initNow);
  document.addEventListener('htmx:afterSwap', function (evt) {
    const t = evt.detail && evt.detail.target;
    if (t && t.id === 'student-form-container') init(t);
  });
})();
