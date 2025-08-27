// Dynamic guest formset builder for group invitations with basic IIN/phone helpers
(function () {
  function showToast(message, type) {
    if (window.toast) return window.toast(message, type);
    if (window.showToast && window.showToast !== showToast) return window.showToast(message, type);
    try { alert(message); } catch (_) {}
  }

  function formatPhone(input) {
    let phone = (input.value || '').replace(/\D/g, '');
    if (phone.startsWith('8')) phone = '7' + phone.substring(1);
    if (phone.length > 0 && !phone.startsWith('7')) phone = '7' + phone;
    if (phone.length > 11) phone = phone.substring(0, 11);
    let formatted = '';
    if (phone.length > 0) {
      formatted = '+7';
      if (phone.length > 1) {
        formatted += ' (' + phone.substring(1, 4);
        if (phone.length > 4) {
          formatted += ') ' + phone.substring(4, 7);
          if (phone.length > 7) {
            formatted += '-' + phone.substring(7, 9);
            if (phone.length > 9) formatted += '-' + phone.substring(9, 11);
          }
        }
      }
    }
    input.value = formatted;
    input.classList.remove('is-valid', 'is-invalid');
    if (phone.length === 11 && phone.startsWith('7')) input.classList.add('is-valid');
  }

  function validateIIN(input) {
    const iin = (input.value || '').replace(/\D/g, '');
    input.value = iin.substring(0, 12);
    input.classList.remove('is-valid');
    if (iin.length === 12) input.classList.add('is-valid');
  }

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('group-form');
    const totalFormsInput = document.getElementById('id_form-TOTAL_FORMS');
    const addBtn = document.getElementById('add-guest-btn');
    const formsetDiv = document.getElementById('guests-formset');
    const counterBadge = document.getElementById('guest-counter');
    const maxGuests = 10;

    if (!form || !totalFormsInput || !addBtn || !formsetDiv) return;

    function currentCount() { return formsetDiv.querySelectorAll('.guest-form-row').length; }

    function updateGuestCounter() {
      const count = currentCount();
      if (counterBadge) counterBadge.textContent = `Гостей: ${count}`;
      formsetDiv.querySelectorAll('.guest-form-row').forEach((row, idx) => {
        const title = row.querySelector('.card-title');
        if (title) title.textContent = `Гость #${idx + 1}`;
      });
      addBtn.style.display = count >= maxGuests ? 'none' : 'inline-flex';
    }

    function updateRemoveButtons() {
      const removeButtons = formsetDiv.querySelectorAll('.remove-guest-btn');
      const count = currentCount();
      removeButtons.forEach((btn) => {
        btn.style.display = count <= 1 ? 'none' : 'inline-flex';
        btn.onclick = function () {
          const row = btn.closest('.guest-form-row');
          if (currentCount() <= 1) {
            showToast('Должен остаться хотя бы один гость', 'warning');
            return;
          }
          row.style.transition = 'opacity 0.3s ease';
          row.style.opacity = '0';
          setTimeout(() => {
            row.remove();
            totalFormsInput.value = String(parseInt(totalFormsInput.value || '1', 10) - 1);
            updateGuestCounter();
            updateRemoveButtons();
            showToast('Гость удален', 'info');
          }, 300);
        };
      });
    }

    function addNewGuest() {
      const count = currentCount();
      if (count >= maxGuests) return;
      const idx = count;
      const colors = ['blue', 'green', 'purple', 'orange', 'yellow', 'red', 'pink', 'indigo', 'teal', 'cyan'];
      const color = colors[idx % colors.length];
      const html = `
      <div class="card border mb-3 guest-form-row">
        <div class="card-status-start bg-${color}"></div>
        <div class="card-header">
          <h4 class="card-title">Гость #${idx + 1}</h4>
          <div class="card-actions">
            <button type="button" class="btn btn-outline-danger btn-sm remove-guest-btn" title="Удалить гостя">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M4 7l16 0"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"/><path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"/></svg>
              Удалить
            </button>
          </div>
        </div>
        <div class="card-body">
          <div class="row g-3 mb-3">
            <div class="col-md-6">
              <label class="form-label required">ФИО</label>
              <input type="text" name="form-${idx}-full_name" class="form-control" maxlength="255" required />
              <small class="form-hint">Полное имя гостя</small>
            </div>
            <div class="col-md-6">
              <label class="form-label required">Email</label>
              <input type="email" name="form-${idx}-email" class="form-control" maxlength="255" required />
              <small class="form-hint">Электронная почта для уведомлений</small>
            </div>
          </div>
          <div class="row g-3 mb-3">
            <div class="col-md-6">
              <label class="form-label">Телефон</label>
              <input type="text" name="form-${idx}-phone_number" class="form-control" maxlength="20" placeholder="+7 (___) ___-__-__" />
              <small class="form-hint">Контактный номер телефона</small>
            </div>
            <div class="col-md-6">
              <label class="form-label required">ИИН</label>
              <input type="text" name="form-${idx}-iin" class="form-control" maxlength="12" placeholder="000000000000" required />
              <small class="form-hint">12-значный ИИН</small>
            </div>
          </div>
          <div class="row g-3">
            <div class="col-md-12">
              <label class="form-label">Фото гостя</label>
              <input type="file" name="form-${idx}-photo" class="form-control" accept="image/*" />
              <small class="form-hint">Загрузите фотографию 3x4 для пропуска (JPG, PNG)</small>
            </div>
          </div>
        </div>
      </div>`;
      formsetDiv.insertAdjacentHTML('beforeend', html);
      totalFormsInput.value = String(parseInt(totalFormsInput.value || '0', 10) + 1);
      updateGuestCounter();
      updateRemoveButtons();
      showToast(`Добавлен гость #${idx + 1}`, 'success');
      formsetDiv.lastElementChild.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    addBtn.addEventListener('click', addNewGuest);
    updateGuestCounter();
    updateRemoveButtons();

    // Delegated input validation
    document.addEventListener('input', function (e) {
      const t = e.target;
      if (!t || !t.name) return;
      if (t.name.includes('-iin')) validateIIN(t);
      if (t.name.includes('-phone_number')) formatPhone(t);
    });

    form.addEventListener('submit', function (e) {
      const rows = formsetDiv.querySelectorAll('.guest-form-row');
      let hasErrors = false;
      rows.forEach((row, idx) => {
        const fullName = row.querySelector(`[name="form-${idx}-full_name"]`);
        const email = row.querySelector(`[name="form-${idx}-email"]`);
        const iin = row.querySelector(`[name="form-${idx}-iin"]`);
        const phone = row.querySelector(`[name="form-${idx}-phone_number"]`);
        [fullName, email, iin].forEach((f) => {
          if (f && !(f.value || '').trim()) { f.classList.add('is-invalid'); hasErrors = true; }
          else if (f) { f.classList.remove('is-invalid'); }
        });
        if (iin) {
          const digits = (iin.value || '').replace(/\D/g, '');
          if (digits && digits.length !== 12) { iin.classList.add('is-invalid'); hasErrors = true; }
        }
        if (phone && (phone.value || '').trim()) {
          const d = (phone.value || '').replace(/\D/g, '');
          if (!(d.length === 11 && d.startsWith('7'))) { phone.classList.add('is-invalid'); hasErrors = true; }
          else { phone.classList.remove('is-invalid'); }
        }
      });
      if (hasErrors) {
        e.preventDefault();
        showToast('Пожалуйста, заполните все обязательные поля корректно', 'error');
        const first = form.querySelector('.is-invalid');
        if (first) {
          first.scrollIntoView({ behavior: 'smooth', block: 'center' });
          first.focus();
        }
      }
    });
  });
})();
