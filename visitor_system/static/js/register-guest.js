// Register Guest page initializer
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
    maskInput.addEventListener('blur', validate);

    const form = maskInput.closest('form');
    if (form) {
      form.addEventListener('submit', function (e) {
        if (!validate() && m.unmaskedValue.length > 0) {
          e.preventDefault();
          maskInput.focus();
        }
      });
    }

    if (m.unmaskedValue.length > 0) validate();
    return { mask: m, setFromHidden };
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
        if (!validate() && iinInput.value.trim().length > 0) {
          e.preventDefault();
          iinInput.focus();
        }
      });
    }
    if (iinInput.value.trim().length > 0) validate();
  }

  function initExpectedTimeToggle(container) {
    const radios = container.querySelectorAll('input[type="radio"][name="guest_reg_time"]');
    const wrapper = container.querySelector('#guest_expected_time_wrapper');
    if (!radios.length || !wrapper) return;
    function toggle() {
      const selected = container.querySelector('input[name="guest_reg_time"]:checked');
      const isLater = selected && selected.value === 'later';
      wrapper.style.display = isLater ? 'block' : 'none';
      wrapper.classList.toggle('active', isLater);
      const timeInput = wrapper.querySelector('input');
      if (timeInput) timeInput.required = isLater;
    }
    radios.forEach(r => r.addEventListener('change', toggle));
    toggle();
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

  function initPurposeOther(container, purposeId) {
    const select = purposeId ? container.querySelector(purposeId) : null;
    const wrapper = container.querySelector('#guest_purpose_other_wrapper');
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

  function initSelectsAndDirector(container, $jq, deptId, empId, phoneMasked, empHiddenPhoneId) {
    if (!$jq || !deptId || !empId) return;
    const $ = $jq;
    const dept = $(container.querySelector(deptId));
    const emp = $(container.querySelector(empId));
    const phoneMaskedEl = phoneMasked;
    const empHidden = empHiddenPhoneId ? $(container.querySelector(empHiddenPhoneId)) : null;
  const directorSpan = $(container.querySelector('#director_name_display'));
  const directorWrapper = $(container.querySelector('#director_info_wrapper'));
  const empEmailWrapper = $(container.querySelector('#employee_email_info'));
  const empEmailSpan = $(container.querySelector('#employee_email_display'));
    // endpoints from dataset (fallback to defaults)
    const empAutocompleteUrl = container.dataset.empAutocompleteUrl || '/visitors/ajax/employee-autocomplete/';
    const deptDetailsUrl = container.dataset.deptDetailsUrl || '/visitors/ajax/department-details/';
    const empDetailsUrlBase = container.dataset.empDetailsUrl || '/visitors/ajax/employee-details/0/';

    if (!dept.length || !emp.length) return;

    // init select2 on employee with retry if plugin not yet loaded
    (function setupSelect2WithRetry(attempts) {
      if (!$.fn || !$.fn.select2) {
        if (attempts > 0) return setTimeout(() => setupSelect2WithRetry(attempts - 1), 200);
        return; // give up silently
      }
      try {
        if (emp.hasClass('select2-hidden-accessible')) {
          try { emp.select2('destroy'); } catch (_) {}
        }
        emp.select2({
          ajax: {
            url: empAutocompleteUrl,
            dataType: 'json',
            delay: 250,
            data: function (params) {
              const dId = dept.val();
              const d = { 
                term: params.term, 
                page: params.page,
                department_id: dId || '' 
              };
              console.log('[register-guest] Autocomplete data being sent:', d);
              return d;
            },
            processResults: function (data, params) {
              return { results: data.results, pagination: { more: (params.page || 1) * 20 < data.count } };
            },
          },
          placeholder: 'Сначала выберите департамент...',
          minimumInputLength: 0,
          allowClear: true,
          width: '100%',
          dropdownParent: $(container),
          disabled: !dept.val(),
          templateSelection: function (data) {
            // Ensure selected text shows email part returned from backend
            return data.text || data.id || '';
          },
          templateResult: function (data) {
            return data.text || '';
          }
        });
      } catch (_) {}
    })(10); // retry up to ~2s

    // on department change: reset employee and phone, enable/disable, load director name via JSON
    dept.on('change', function () {
      const dId = $(this).val();
      console.log('[register-guest] Department changed to:', dId);
      emp.val(null).trigger('change');
      if (phoneMaskedEl) phoneMaskedEl.value = '';
      if (empHidden && empHidden.length) empHidden.val('');
      
      // Включаем/отключаем employee select и обновляем его состояние
      const hasValidDept = dId && dId !== '' && dId !== 'null' && dId !== 'undefined';
      emp.prop('disabled', !hasValidDept);
      
      // Обновляем Select2 с новыми параметрами для выбранного департамента
      if (emp.hasClass('select2-hidden-accessible')) {
        emp.select2('destroy');
      }
      
      emp.select2({
        ajax: {
          url: empAutocompleteUrl,
          dataType: 'json',
          delay: 250,
          data: function (params) {
            const d = { 
              term: params.term, 
              page: params.page,
              department_id: dId || '' 
            };
            console.log('[register-guest] Autocomplete data being sent:', d);
            return d;
          },
          processResults: function (data, params) {
            return { results: data.results, pagination: { more: (params.page || 1) * 20 < data.count } };
          },
        },
        placeholder: hasValidDept ? 'Начните вводить имя сотрудника...' : 'Сначала выберите департамент...',
        minimumInputLength: 0,
        allowClear: true,
        width: '100%',
        dropdownParent: $(container),
        disabled: !hasValidDept
      });
      
      if (empEmailWrapper.length) empEmailWrapper.hide();
      if (empEmailSpan.length) empEmailSpan.text('-');    if (dId && directorWrapper.length && directorSpan.length) {
        directorSpan.text('Загрузка...');
        directorWrapper.show();
        $.ajax({
      url: deptDetailsUrl,
          data: { department_id: dId },
          dataType: 'json',
          success: function (data) { directorSpan.text(data.director_name || 'Не назначен'); },
          error: function () { directorSpan.text('Ошибка загрузки'); },
        });
      } else {
        if (directorWrapper.length) directorWrapper.hide();
        if (directorSpan.length) directorSpan.text('-');
      }
    });

    // on employee select: fetch employee details and fill phone
    if (phoneMaskedEl) {
      emp.on('select2:select', function (e) {
        const data = e.params && e.params.data;
        const userId = data && data.id;
        if (!userId) {
          if (empHidden && empHidden.length) empHidden.val('');
          phoneMaskedEl.value = '';
          if (empEmailWrapper.length) empEmailWrapper.hide();
          if (empEmailSpan.length) empEmailSpan.text('-');
          return;
        }
        // Show email if present in the text: "Full Name (email)"
        try {
          const txt = (data && data.text) || '';
          const m = txt.match(/\(([^)]+)\)\s*$/);
          const email = m && m[1] ? m[1] : '';
          if (email) {
            if (empEmailSpan.length) empEmailSpan.text(email);
            if (empEmailWrapper.length) empEmailWrapper.show();
          } else {
            if (empEmailWrapper.length) empEmailWrapper.hide();
            if (empEmailSpan.length) empEmailSpan.text('-');
          }
        } catch (_) {}
        // replace trailing 0/ with userId/
        const url = empDetailsUrlBase.replace(/0\/$/, `${userId}/`);
        console.log('[register-guest] Fetching employee details from:', url);
        $.ajax({
          url, type: 'GET', dataType: 'json',
          success: function (resp) {
            console.log('[register-guest] Employee details response:', resp);
            const pn = resp.phone_number || '';
            // format into mask
            let digits = pn.replace(/\D/g, '');
            if (digits.startsWith('7')) digits = digits.substring(1);
            if (digits.length === 10) {
              phoneMaskedEl.value = `+7 (${digits.substring(0,3)}) ${digits.substring(3,6)} ${digits.substring(6,8)} ${digits.substring(8,10)}`;
            } else {
              phoneMaskedEl.value = pn;
            }
            if (empHidden && empHidden.length) empHidden.val(resp.phone_number || '');
          },
          error: function (xhr, status, error) {
            console.error('[register-guest] Employee details fetch failed:', status, error);
            if (empHidden && empHidden.length) empHidden.val('');
            phoneMaskedEl.value = '';
          }
        });
      });

      emp.on('select2:unselect', function () {
        phoneMaskedEl.value = '';
        if (empHidden && empHidden.length) empHidden.val('');
        if (empEmailWrapper.length) empEmailWrapper.hide();
        if (empEmailSpan.length) empEmailSpan.text('-');
      });
    }

  // initial disabled state
  emp.prop('disabled', !dept.val());
  }

  function initStyling(container) {
    const form = container.querySelector('form.needs-validation');
    if (!form) return;
    const controls = form.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]):not([type="submit"]):not([type="button"]):not([type="hidden"]), textarea, select');
    controls.forEach(function (c) {
      if (c.tagName === 'SELECT') c.classList.add('form-select');
      else if (!c.classList.contains('btn')) c.classList.add('form-control');
      const err = c.closest('.mb-3')?.querySelector('.invalid-feedback');
      if (err && err.innerText.trim() !== '') c.classList.add('is-invalid');
    });
  }

  function init(container) {
    if (!container) return;
    // dataset selectors
    const deptId = container.dataset.deptId;
    const empId = container.dataset.empId;
    const empHiddenPhoneId = container.dataset.empPhoneHiddenId;
    const guestHiddenPhoneId = container.dataset.guestPhoneHiddenId;
    const guestIinId = container.dataset.guestIinId;
    const purposeId = container.dataset.purposeId;

    // masks
    const guestPhoneMasked = container.querySelector('#guest_phone_masked');
    const guestPhoneHidden = guestHiddenPhoneId ? container.querySelector(guestHiddenPhoneId) : null;
    initPhoneMask(guestPhoneMasked, guestPhoneHidden);

    const employeePhoneMasked = container.querySelector('#employee_phone_masked');
    const employeePhoneHidden = empHiddenPhoneId ? container.querySelector(empHiddenPhoneId) : null;
    initPhoneMask(employeePhoneMasked, employeePhoneHidden);

    // iin
    const iinInput = guestIinId ? container.querySelector(guestIinId) : null;
    initIINValidation(iinInput);

    // full name, expected time, purpose other
    initGuestFullName(container);
    initExpectedTimeToggle(container);
    initPurposeOther(container, purposeId);

    // select2 + director
    const $jq = window.jQuery;
    initSelectsAndDirector(container, $jq, deptId, empId, employeePhoneMasked, empHiddenPhoneId);

    // styling
    initStyling(container);
  }

  function initNow() {
    const container = document.getElementById('guest-form-container');
    if (container) init(container);
  }

  document.addEventListener('DOMContentLoaded', initNow);
  document.addEventListener('htmx:afterSwap', function (evt) {
    const t = evt.detail && evt.detail.target;
    if (t && t.id === 'guest-form-container') init(t);
  });
})();
