// HTMX event handlers and helpers
(function() {
    // Обработка HX-Trigger событий для тостов
    document.addEventListener('showToast', function(event) {
        const detail = event.detail;
        if (detail && detail.message) {
            window.toast(detail.message, detail.type || 'info', {
                duration: detail.duration || 4000
            });
        }
    });

    // Экспоненциальные интервалы для polling
    let pollCount = 0;
    const maxPolls = 10;
    const baseInterval = 1000; // 1 секунда

    function getNextPollInterval() {
        if (pollCount >= maxPolls) {
            return null; // Остановить polling
        }
        const interval = Math.min(baseInterval * Math.pow(2, pollCount), 30000); // Максимум 30 секунд
        pollCount++;
        return interval;
    }

    // Сброс счетчика polling при успешном ответе
    document.addEventListener('htmx:afterRequest', function(event) {
        if (event.detail.successful) {
            pollCount = 0;
        }
    });

    // Обработчик для динамических polling интервалов
    document.addEventListener('htmx:configRequest', function(event) {
        if (event.detail.elt.hasAttribute('hx-poll')) {
            const nextInterval = getNextPollInterval();
            if (nextInterval === null) {
                // Остановить polling
                event.detail.elt.removeAttribute('hx-poll');
                return;
            }
            // Обновить интервал
            event.detail.elt.setAttribute('hx-poll', `${nextInterval}ms`);
        }
    });

    // Глобальные обновления счетчиков через hx-swap-oob
    function updateGlobalCounters(data) {
        const counters = {
            'visit-counter': data.visitCount || data.active_visits_count,
            'guest-counter': data.guestCount || data.current_guests_count,
            'awaiting-counter': data.awaitingCount || data.awaiting_visits_count,
            'today-counter': data.todayCount || data.today_visits_count
        };
        
        Object.keys(counters).forEach(counterId => {
            const counter = document.getElementById(counterId);
            if (counter && counters[counterId] !== undefined) {
                // Добавляем анимацию обновления
                counter.style.transition = 'all 0.3s ease';
                counter.style.transform = 'scale(1.1)';
                counter.textContent = counters[counterId];
                
                setTimeout(() => {
                    counter.style.transform = 'scale(1)';
                }, 150);
            }
        });
    }

    // Обработка глобальных обновлений
    document.addEventListener('updateCounters', function(event) {
        const detail = event.detail;
        if (detail) {
            updateGlobalCounters(detail);
        }
    });

    // Обработка 304 Not Modified для кэширования
    document.addEventListener('htmx:responseError', function(event) {
        if (event.detail.xhr.status === 304) {
            // Контент не изменился, ничего не делаем
            event.preventDefault();
        }
    });

    // Обработка ошибок с тостами
    document.addEventListener('htmx:responseError', function(event) {
        const status = event.detail.xhr.status;
        if (status >= 400 && status < 500) {
            window.toast('Ошибка клиента: ' + status, 'error');
        } else if (status >= 500) {
            window.toast('Ошибка сервера: ' + status, 'error');
        }
    });

    // Показ индикатора загрузки
    document.addEventListener('htmx:beforeRequest', function(event) {
        const spinner = document.getElementById('global-spinner');
        if (spinner) {
            spinner.style.display = 'block';
        }
    });

    document.addEventListener('htmx:afterRequest', function(event) {
        const spinner = document.getElementById('global-spinner');
        if (spinner) {
            spinner.style.display = 'none';
        }
    });

    // Сохранение позиции скролла для hx-boost
    let scrollPositions = new Map();
    
    document.addEventListener('htmx:beforeRequest', function(event) {
        if (event.detail.boosted) {
            scrollPositions.set(window.location.href, window.scrollY);
        }
    });

    document.addEventListener('htmx:pushedIntoHistory', function(event) {
        if (event.detail.path) {
            const savedPosition = scrollPositions.get(event.detail.path);
            if (savedPosition !== undefined) {
                window.scrollTo(0, savedPosition);
            }
        }
    });

    // Автоматическая обработка форм с ошибками
    document.addEventListener('htmx:afterSwap', function(event) {
        const newContent = event.detail.target;
        
        // Фокус на первом поле с ошибкой
        const errorField = newContent.querySelector('.is-invalid, .error');
        if (errorField) {
            errorField.focus();
        }
        
        // Обновление счетчиков символов, если есть
        const charCounters = newContent.querySelectorAll('[data-char-counter]');
        charCounters.forEach(counter => {
            const target = document.getElementById(counter.dataset.charCounter);
            if (target) {
                target.textContent = counter.value.length;
            }
        });
    });

})();
