// Guest invitation public page: countdown timer, input masks, validation, and submit UX
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    let submitted = false;
    const form = document.getElementById('visitor-form');
    const timerWarning = document.getElementById('timer-warning');
    const timeLeftSpan = document.getElementById('time-left');
    const mainTimerSpan = document.getElementById('main-timer');
    let totalTime = 300; // 5 minutes
    let timerInterval;

    function updateTimer() {
      if (totalTime <= 0) {
        clearInterval(timerInterval);
        try { alert('Время заполнения формы истекло. Страница будет закрыта.'); } catch (_) {}
        window.close();
        return;
      }
      totalTime--;
      const minutes = Math.floor(totalTime / 60);
      const seconds = totalTime % 60;
      const formatted = `${minutes}:${seconds.toString().padStart(2, '0')}`;
      if (mainTimerSpan) mainTimerSpan.textContent = formatted;
      if (totalTime <= 30 && timerWarning && timeLeftSpan) {
        timeLeftSpan.textContent = totalTime;
        timerWarning.style.display = 'block';
      }
    }
    timerInterval = setInterval(updateTimer, 1000);

    // Phone mask
    const phoneMasked = document.getElementById('guest_phone_masked');
    const hiddenPhone = document.getElementById('guest_phone');
    if (phoneMasked && hiddenPhone) {
      if (window.IMask) {
        const mask = IMask(phoneMasked, { mask: '+{7} (000) 000 00 00', definitions: { '0': /[0-9]/ } });
        mask.on('accept', function () { hiddenPhone.value = mask.unmaskedValue; });
      } else {
        phoneMasked.addEventListener('input', function () {
          hiddenPhone.value = (phoneMasked.value || '').replace(/\D/g, '');
        });
      }
    }

    // IIN mask
    const iin = document.getElementById('guest_iin');
    if (iin && window.IMask) {
      IMask(iin, { mask: '000000000000', definitions: { '0': /[0-9]/ } });
    }

    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        const required = form.querySelectorAll('[required]');
        let isValid = true;
        let firstInvalid = null;
        required.forEach((f) => {
          const ok = (f.value || '').trim().length > 0;
          if (!ok) {
            isValid = false;
            if (!firstInvalid) firstInvalid = f;
            f.classList.add('is-invalid');
          } else {
            f.classList.remove('is-invalid');
          }
        });
        if (!isValid) {
          if (firstInvalid) {
            firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            setTimeout(() => firstInvalid.focus(), 300);
          }
          const existing = document.querySelector('.validation-alert');
          if (existing) existing.remove();
          const alertDiv = document.createElement('div');
          alertDiv.className = 'alert alert-danger validation-alert mt-3';
          alertDiv.innerHTML = '<div class="d-flex"><div class="flex-shrink-0"><svg xmlns="http://www.w3.org/2000/svg" class="icon alert-icon" width="20" height="20" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M12 9v2m0 4v.01" /><path d="M5 19h14a2 2 0 0 0 1.414 -3.414l-7 -7a2 2 0 0 0 -2.828 0l-7 7a2 2 0 0 0 1.414 3.414z" /></svg></div><div class="ms-2"><h4 class="alert-title">Заполните обязательные поля</h4><div class="text-muted">Пожалуйста, заполните все обязательные поля формы</div></div></div>';
          form.insertBefore(alertDiv, form.firstChild);
          setTimeout(() => alertDiv.remove(), 5000);
          return;
        }
        submitted = true;
        clearInterval(timerInterval);
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span><span class="d-none d-sm-inline">Отправка...</span><span class="d-sm-none">...</span>';
        }
        // Defer to server submit: trigger real submission
        form.submit();
      });

      // Realtime validation feedback
      form.querySelectorAll('input, select, textarea').forEach((el) => {
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

      // Inactivity resets the timer back to 5 minutes when the user interacts
      function resetInactivityTimer() {
        if (!submitted) {
          clearInterval(timerInterval);
          totalTime = 300;
          if (timerWarning) timerWarning.style.display = 'none';
          timerInterval = setInterval(updateTimer, 1000);
        }
      }
      document.addEventListener('click', resetInactivityTimer);
      document.addEventListener('keypress', resetInactivityTimer);
      document.addEventListener('scroll', resetInactivityTimer);
      form.addEventListener('input', resetInactivityTimer);

      window.addEventListener('beforeunload', function (e) {
        const nameField = form.querySelector('input[name="guest_full_name"], #guest_full_name');
        if (!submitted && nameField && (nameField.value || '').trim()) {
          const message = 'Вы уверены, что хотите покинуть страницу? Введенные данные будут потеряны.';
          e.returnValue = message;
          return message;
        }
      });
    }
  });
})();
