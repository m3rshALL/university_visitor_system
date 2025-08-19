// visitor_system/static/js/egov-integration.js
// Интеграция с egov.kz для проверки документов

document.addEventListener('DOMContentLoaded', function() {
    
    // Добавляем кнопки проверки к полям ИИН
    const iinFields = document.querySelectorAll('input[name*="iin"], input[id*="iin"]');
    iinFields.forEach(addVerificationButton);
    
    // Добавляем кнопки проверки к полям паспорта
    const passportFields = document.querySelectorAll('input[name*="passport"], input[id*="passport"]');
    passportFields.forEach(field => addVerificationButton(field, 'passport'));
    
});

function addVerificationButton(field, type = 'iin') {
    // Пропускаем, если кнопка уже добавлена
    if (field.parentNode.querySelector('.egov-verify-btn')) {
        return;
    }
    
    // Создаем контейнер для кнопки
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'egov-verification-container mt-2';
    
    // Создаем кнопку проверки
    const verifyButton = document.createElement('button');
    verifyButton.type = 'button';
    verifyButton.className = 'btn btn-outline-primary btn-sm egov-verify-btn';
    verifyButton.innerHTML = `
        <i class="fas fa-shield-alt me-1"></i>
        Проверить через egov.kz
    `;
    
    // Создаем контейнер для результата
    const resultContainer = document.createElement('div');
    resultContainer.className = 'egov-result-container mt-2';
    
    buttonContainer.appendChild(verifyButton);
    buttonContainer.appendChild(resultContainer);
    
    // Вставляем после поля ввода
    field.parentNode.insertBefore(buttonContainer, field.nextSibling);
    
    // Обработчик клика
    verifyButton.addEventListener('click', function() {
        const value = field.value.trim();
        
        if (!value) {
            showResult(resultContainer, {
                success: false,
                error: `${type === 'iin' ? 'ИИН' : 'Номер паспорта'} не указан`
            });
            return;
        }
        
        if (type === 'iin') {
            verifyIIN(value, verifyButton, resultContainer, field);
        } else {
            verifyPassport(value, verifyButton, resultContainer, field);
        }
    });
}

function verifyIIN(iin, button, resultContainer, field) {
    // Валидация ИИН
    if (iin.length !== 12 || !/^\d{12}$/.test(iin)) {
        showResult(resultContainer, {
            success: false,
            error: 'ИИН должен содержать ровно 12 цифр'
        });
        return;
    }
    
    setButtonLoading(button, true);
    
    fetch('/egov/ajax/verify-iin/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ iin: iin })
    })
    .then(response => response.json())
    .then(data => {
        setButtonLoading(button, false);
        showResult(resultContainer, data);
        
        // Если проверка успешна, автозаполняем другие поля
        if (data.success && data.data) {
            autoFillFields(data.data, field);
        }
    })
    .catch(error => {
        setButtonLoading(button, false);
        showResult(resultContainer, {
            success: false,
            error: 'Ошибка соединения с сервером'
        });
        console.error('Error:', error);
    });
}

function verifyPassport(passportNumber, button, resultContainer, field) {
    if (!passportNumber) {
        showResult(resultContainer, {
            success: false,
            error: 'Номер паспорта не указан'
        });
        return;
    }
    
    setButtonLoading(button, true);
    
    fetch('/egov/ajax/verify-passport/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ passport_number: passportNumber })
    })
    .then(response => response.json())
    .then(data => {
        setButtonLoading(button, false);
        showResult(resultContainer, data);
        
        // Автозаполнение полей
        if (data.success && data.data) {
            autoFillFields(data.data, field);
        }
    })
    .catch(error => {
        setButtonLoading(button, false);
        showResult(resultContainer, {
            success: false,
            error: 'Ошибка соединения с сервером'
        });
        console.error('Error:', error);
    });
}

function setButtonLoading(button, loading) {
    if (loading) {
        button.disabled = true;
        button.innerHTML = `
            <span class="spinner-border spinner-border-sm me-1" role="status"></span>
            Проверяем...
        `;
    } else {
        button.disabled = false;
        button.innerHTML = `
            <i class="fas fa-shield-alt me-1"></i>
            Проверить через egov.kz
        `;
    }
}

function showResult(container, data) {
    let html = '';
    
    if (data.success) {
        html = `
            <div class="alert alert-success alert-dismissible">
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                <div class="d-flex">
                    <div>
                        <i class="fas fa-check-circle me-2"></i>
                    </div>
                    <div>
                        <h4 class="alert-title">Документ проверен</h4>
                        ${data.data ? formatVerificationData(data.data) : ''}
                        <div class="text-muted small mt-2">
                            Проверено через egov.kz
                            ${data.verified_at ? ` в ${new Date(data.verified_at).toLocaleString()}` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else {
        html = `
            <div class="alert alert-danger alert-dismissible">
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                <div class="d-flex">
                    <div>
                        <i class="fas fa-exclamation-triangle me-2"></i>
                    </div>
                    <div>
                        <h4 class="alert-title">Ошибка проверки</h4>
                        <div class="text-muted">${data.error || 'Неизвестная ошибка'}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
    
    // Автоматически скрываем через 10 секунд
    setTimeout(() => {
        const alert = container.querySelector('.alert');
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 10000);
}

function formatVerificationData(data) {
    let html = '<div class="verification-data">';
    
    if (data.full_name) {
        html += `<div><strong>ФИО:</strong> ${data.full_name}</div>`;
    }
    
    if (data.birth_date) {
        html += `<div><strong>Дата рождения:</strong> ${data.birth_date}</div>`;
    }
    
    if (data.gender) {
        const genderText = data.gender === 'M' ? 'Мужской' : data.gender === 'F' ? 'Женский' : data.gender;
        html += `<div><strong>Пол:</strong> ${genderText}</div>`;
    }
    
    if (data.issue_date) {
        html += `<div><strong>Дата выдачи:</strong> ${data.issue_date}</div>`;
    }
    
    if (data.expiry_date) {
        html += `<div><strong>Срок действия:</strong> ${data.expiry_date}</div>`;
    }
    
    if (data.issuer) {
        html += `<div><strong>Орган выдачи:</strong> ${data.issuer}</div>`;
    }
    
    html += '</div>';
    return html;
}

function autoFillFields(data, currentField) {
    const form = currentField.closest('form');
    if (!form) return;
    
    // Автозаполнение ФИО
    if (data.full_name) {
        const nameFields = form.querySelectorAll('input[name*="name"], input[name*="full_name"], input[id*="name"]');
        nameFields.forEach(field => {
            if (field !== currentField && !field.value.trim()) {
                field.value = data.full_name;
                // Подсвечиваем автозаполненное поле
                highlightAutoFilled(field);
            }
        });
    }
    
    // Можно добавить автозаполнение других полей...
}

function highlightAutoFilled(field) {
    field.classList.add('border-success');
    field.style.backgroundColor = '#f8fff9';
    
    // Создаем подсказку
    const tooltip = document.createElement('div');
    tooltip.className = 'small text-success mt-1';
    tooltip.innerHTML = '<i class="fas fa-check me-1"></i>Автозаполнено из egov.kz';
    
    field.parentNode.insertBefore(tooltip, field.nextSibling);
    
    // Убираем подсветку через 5 секунд
    setTimeout(() => {
        field.classList.remove('border-success');
        field.style.backgroundColor = '';
        if (tooltip.parentNode) {
            tooltip.remove();
        }
    }, 5000);
}

function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    
    // Альтернативный способ - из meta тега
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        return csrfMeta.getAttribute('content');
    }
    
    // Из hidden input
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (csrfInput) {
        return csrfInput.value;
    }
    
    return '';
}

// Глобальные функции для использования в других скриптах
window.EgovIntegration = {
    verifyIIN: verifyIIN,
    verifyPassport: verifyPassport,
    showResult: showResult
};
