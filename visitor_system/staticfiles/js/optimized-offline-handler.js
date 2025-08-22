// Файл для отслеживания статуса сети и управления оффлайн-режимом
document.addEventListener('DOMContentLoaded', function() {
    // Кэшируем DOM-запросы
    let cachedForms, cachedButtons;
    let cachedOfflinePages = null;
    let lastCacheCheck = 0;
    let networkStatusTimeout;

    // Создаем элемент уведомления о статусе сети только при необходимости
    let networkStatusElement = null;

    // Функция для создания уведомления о статусе сети (создаем только при необходимости)
    function createNetworkStatusElement() {
        if (networkStatusElement) return networkStatusElement;
        
        networkStatusElement = document.createElement('div');
        networkStatusElement.id = 'network-status';
        networkStatusElement.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 10px 15px;
            background-color: #f44336;
            color: white;
            border-radius: 4px;
            z-index: 9999;
            display: none;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-width: 250px;
            transition: all 0.3s ease;
            opacity: 0.95;
        `;
        networkStatusElement.innerHTML = `
            <div style="display: flex; align-items: center;">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 10px;">
                    <path d="M18.588 12.213a6.7 6.7 0 0 1-1.082 3.574m-5.055 2.126a6.67 6.67 0 0 1-6.01-6.011m9.907-4.633a10.88 10.88 0 0 1 2.264 3.576m-16.565 3.533a10.88 10.88 0 0 1 3.644-7.605L10.072 12l2.121 2.12" />
                </svg>
                <span>Нет подключения к интернету</span>
            </div>
            <button aria-label="Закрыть" style="background: transparent; border: none; color: white; cursor: pointer; margin-left: 10px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        `;
        
        // Обработчик для кнопки закрытия
        networkStatusElement.querySelector('button').addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            networkStatusElement.style.display = 'none';
        });
        
        document.body.appendChild(networkStatusElement);
        return networkStatusElement;
    }

    // Оптимизированная версия: кэширование запросов DOM
    const createCachedIndicator = () => {
        // Lazy инициализация кэшированных элементов
        if (!cachedForms || !cachedButtons) {
            cachedForms = Array.from(document.querySelectorAll('form:not(.cached-form-processed)'));
            cachedForms.forEach(form => form.classList.add('cached-form-processed'));
            
            cachedButtons = Array.from(document.querySelectorAll('button[type="submit"]:not(.cached-button-processed)'));
            cachedButtons.forEach(button => button.classList.add('cached-button-processed'));
        }
        
        const isOffline = !navigator.onLine;
        
        // Обработка форм только при изменении статуса сети
        cachedForms.forEach(form => {
            if (!form.classList.contains('offline-ready')) {
                if (isOffline && !form.classList.contains('offline-disabled')) {
                    // Сохраняем оригинальные значения только если еще не сохранены
                    if (!form.hasAttribute('data-original-action')) {
                        form.setAttribute('data-original-action', form.action || '');
                        form.setAttribute('data-original-onsubmit', form.onsubmit || '');
                        
                        // Предотвращаем отправку формы
                        form.onsubmit = (e) => {
                            e.preventDefault();
                            showOfflineMessage('Форма недоступна в офлайн-режиме');
                            return false;
                        };
                        
                        // Добавляем визуальный индикатор
                        form.classList.add('offline-disabled');
                    }
                } else if (!isOffline && form.classList.contains('offline-disabled')) {
                    // Восстанавливаем формы при возврате онлайн
                    const originalAction = form.getAttribute('data-original-action');
                    if (originalAction) form.action = originalAction;
                    form.onsubmit = null;
                    form.classList.remove('offline-disabled');
                }
            }
        });
        
        // Аналогично для кнопок
        cachedButtons.forEach(button => {
            if (!button.closest('.offline-ready')) {
                if (isOffline && !button.classList.contains('offline-disabled-btn')) {
                    button.setAttribute('data-original-disabled', button.disabled || false);
                    button.disabled = true;
                    button.setAttribute('data-original-title', button.title || '');
                    button.title = 'Недоступно в офлайн-режиме';
                    button.classList.add('offline-disabled-btn');
                } else if (!isOffline && button.classList.contains('offline-disabled-btn')) {
                    const originalDisabled = button.getAttribute('data-original-disabled');
                    const originalTitle = button.getAttribute('data-original-title');
                    
                    button.disabled = originalDisabled === 'true';
                    if (originalTitle) button.title = originalTitle;
                    
                    button.classList.remove('offline-disabled-btn');
                }
            }
        });
        
        // Обработка индикатора офлайн-режима
        if (isOffline && !document.getElementById('offline-mode-indicator')) {
            const offlineIndicator = document.createElement('div');
            offlineIndicator.id = 'offline-mode-indicator';
            offlineIndicator.style.cssText = `
                position: fixed;
                top: 10px;
                left: 10px;
                background: rgba(0,0,0,0.7);
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 12px;
                z-index: 9999;
            `;
            offlineIndicator.innerHTML = 'Офлайн-режим';
            document.body.appendChild(offlineIndicator);
        } else if (!isOffline) {
            const indicator = document.getElementById('offline-mode-indicator');
            if (indicator) {
                indicator.remove();
            }
        }
    };
    
    // Оптимизированная функция для показа сообщения офлайн-режима
    function showOfflineMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 15px 20px;
            border-radius: 4px;
            z-index: 10000;
            max-width: 80%;
            text-align: center;
        `;
        messageElement.textContent = message;
        document.body.appendChild(messageElement);
        
        setTimeout(() => {
            messageElement.style.opacity = '0';
            messageElement.style.transition = 'opacity 0.5s ease';
            setTimeout(() => messageElement.remove(), 500);
        }, 2000);
    }

    // Оптимизированная функция для проверки доступных офлайн-страниц
    function buildOfflineNavigation() {
        // Если браузер не поддерживает Cache API, выходим
        if (!('caches' in window) || navigator.onLine || document.getElementById('offline-nav')) return;
        
        const now = Date.now();
        // Используем кэшированные данные если они есть и прошло менее 5 минут
        if (cachedOfflinePages && (now - lastCacheCheck < 300000)) {
            createOfflineNavUI(cachedOfflinePages);
            return;
        }
        
        // Иначе запрашиваем данные из кэша
        caches.open('visitor-system-cache-v1').then(cache => {
            cache.keys().then(requests => {
                // Фильтруем только HTML-страницы
                const htmlPages = requests.filter(request => {
                    const url = new URL(request.url);
                    return !url.pathname.match(/\.(js|css|png|jpg|svg|json)$/i) && 
                           url.pathname !== '/offline.html';
                });
                
                // Кэшируем результат
                cachedOfflinePages = htmlPages;
                lastCacheCheck = now;
                
                if (htmlPages.length > 0) {
                    createOfflineNavUI(htmlPages);
                }
            }).catch(() => {
                // Игнорируем ошибки кэша
            });
        }).catch(() => {
            // Игнорируем ошибки кэша
        });
    }
    
    // Создание UI для офлайн-навигации
    function createOfflineNavUI(htmlPages) {
        // Создаем панель навигации офлайн
        const offlineNav = document.createElement('div');
        offlineNav.id = 'offline-nav';
        offlineNav.style.cssText = `
            position: fixed;
            bottom: 70px;
            right: 20px;
            background: white;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            padding: 10px;
            z-index: 9998;
            display: none;
            max-width: 300px;
            max-height: 400px;
            overflow-y: auto;
        `;
        
        // Русифицированные имена страниц
        const pageNameMap = {
            'employee_dashboard': 'Панель сотрудника',
            'current_guests': 'Текущие гости',
            'visit_history': 'История визитов',
            'visit_statistics': 'Статистика',
            'register_guest': 'Регистрация гостя'
        };
        
        let navHTML = `
            <div style="font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px;">
                Доступные страницы офлайн
            </div>
            <ul style="list-style: none; padding: 0; margin: 0;">
        `;
        
        htmlPages.forEach(request => {
            const url = new URL(request.url);
            let pageName = url.pathname === '/' ? 'Главная' : 
                          url.pathname.split('/').filter(Boolean).pop() || url.pathname;
            
            // Очищаем имя страницы от расширений и подчеркиваний
            pageName = pageName.replace(/\.html$/, '')
                               .replace(/_/g, ' ');
            
            navHTML += `<li style="margin-bottom: 5px;">
                <a href="${url.pathname}" style="color: #206bc4; text-decoration: none; display: block; padding: 5px;">
                    ${pageNameMap[pageName] || pageName}
                </a>
            </li>`;
        });
        
        navHTML += `</ul>`;
        offlineNav.innerHTML = navHTML;
        
        document.body.appendChild(offlineNav);
        
        // Добавляем кнопку для показа офлайн-навигации
        const navToggle = document.createElement('button');
        navToggle.id = 'offline-nav-toggle';
        navToggle.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 280px;
            background: #206bc4;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px;
            cursor: pointer;
            z-index: 9998;
            display: flex;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        `;
        navToggle.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 5px;">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                <polyline points="9 22 9 12 15 12 15 22"></polyline>
            </svg>
            Офлайн-страницы
        `;
        document.body.appendChild(navToggle);
        
        // Обработчик для показа/скрытия меню
        navToggle.addEventListener('click', () => {
            const nav = document.getElementById('offline-nav');
            if (nav.style.display === 'none') {
                nav.style.display = 'block';
            } else {
                nav.style.display = 'none';
            }
        });
    }

    // Функция дебаунсинга для предотвращения частых вызовов
    function debounceNetworkStatus(func, wait) {
        clearTimeout(networkStatusTimeout);
        networkStatusTimeout = setTimeout(func, wait);
    }

    // Оптимизированная обработка статуса сети
    function updateNetworkStatus() {
        // Запоминаем предыдущее состояние
        const wasOnlineBefore = localStorage.getItem('wasOnlineBefore') === 'true';
        const isOnlineNow = navigator.onLine;
        
        // Обновляем только при изменении состояния сети
        if (wasOnlineBefore !== isOnlineNow || localStorage.getItem('forceNetworkUpdate') === 'true') {
            localStorage.setItem('wasOnlineBefore', isOnlineNow.toString());
            localStorage.removeItem('forceNetworkUpdate');
            
            if (isOnlineNow) {
                // Ленивая инициализация элемента статуса сети
                if (networkStatusElement) {
                    networkStatusElement.style.display = 'none';
                }
                
                // Восстанавливаем функциональность страницы
                createCachedIndicator();
                
                // Удаляем навигацию офлайн, если она была
                document.getElementById('offline-nav')?.remove();
                document.getElementById('offline-nav-toggle')?.remove();
                
                // Если ранее были в офлайн-режиме
                if (localStorage.getItem('wasOffline') === 'true') {
                    localStorage.removeItem('wasOffline');
                    
                    const onlineNotification = document.createElement('div');
                    onlineNotification.style.cssText = `
                        position: fixed;
                        bottom: 20px;
                        right: 20px;
                        padding: 10px 15px;
                        background-color: #4caf50;
                        color: white;
                        border-radius: 4px;
                        z-index: 9999;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                        font-size: 14px;
                        display: flex;
                        align-items: center;
                    `;
                    onlineNotification.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 10px;">
                            <path d="M5 12l5 5l10 -10"></path>
                        </svg>
                        Соединение восстановлено
                    `;
                    document.body.appendChild(onlineNotification);
                    
                    setTimeout(() => {
                        onlineNotification.style.opacity = '0';
                        onlineNotification.style.transition = 'opacity 1s ease';
                        setTimeout(() => onlineNotification.remove(), 1000);
                    }, 3000);
                    
                    // Обновляем данные на странице, если необходимо
                    if (typeof updatePageContent === 'function') {
                        updatePageContent();
                    }
                }
            } else {
                // Создаем элемент статуса сети при необходимости
                networkStatusElement = createNetworkStatusElement();
                networkStatusElement.style.display = 'flex';
                localStorage.setItem('wasOffline', 'true');
                
                // Отключаем функции отправки форм
                createCachedIndicator();
                
                // Строим навигацию по офлайн-страницам
                buildOfflineNavigation();
            }
        }
    }

    // Функция для обновления контента страницы (переопределяется в конкретных страницах)
    window.updatePageContent = window.updatePageContent || function() {
        console.log('Функция обновления контента не определена для этой страницы');
    };
    
    // Добавляем стили для офлайн-элементов (один раз, не при каждом обновлении)
    if (!document.getElementById('offline-styles')) {
        const offlineStyle = document.createElement('style');
        offlineStyle.id = 'offline-styles';
        offlineStyle.textContent = `
            .offline-disabled {
                position: relative;
                pointer-events: none;
                opacity: 0.7;
            }
            
            .offline-disabled::after {
                content: 'Недоступно офлайн';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0,0,0,0.7);
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 12px;
                z-index: 1;
            }
            
            .offline-disabled-btn {
                opacity: 0.6;
                position: relative;
            }
        `;
        document.head.appendChild(offlineStyle);
    }

    // Слушаем изменения статуса сети с дебаунсингом
    window.addEventListener('online', () => debounceNetworkStatus(updateNetworkStatus, 300));
    window.addEventListener('offline', () => debounceNetworkStatus(updateNetworkStatus, 300));
    
    // Проверка статуса при видимости страницы
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            localStorage.setItem('forceNetworkUpdate', 'true');
            debounceNetworkStatus(updateNetworkStatus, 500);
        }
    });
    
    // Инициализация при загрузке страницы (с небольшой задержкой для улучшения производительности)
    setTimeout(updateNetworkStatus, 100);
    
    // Вместо setInterval используем более редкие проверки
    let periodicCheckId;
    function startPeriodicChecks() {
        periodicCheckId = setTimeout(() => {
            // Проверяем только если страница видима
            if (document.visibilityState === 'visible') {
                updateNetworkStatus();
            }
            startPeriodicChecks();
        }, 120000); // 2 минуты вместо 30 секунд
    }
    
    // Запускаем периодические проверки
    startPeriodicChecks();
    
    // Очистка при выгрузке страницы
    window.addEventListener('beforeunload', () => {
        clearTimeout(periodicCheckId);
        clearTimeout(networkStatusTimeout);
    });

    // Единая кнопка "Назад": обработчик для элементов с data-go-back
    document.addEventListener('click', function(e) {
        const backEl = e.target && e.target.closest && e.target.closest('[data-go-back]');
        if (!backEl) return;
        e.preventDefault();
        e.stopPropagation();
        try {
            // Не показывать прелоадер при возврате назад
            if (typeof window.navigationTriggered !== 'undefined') {
                window.navigationTriggered = false;
            }
            // Если есть история, используем history.back()
            if (window.history && window.history.length > 1) {
                window.history.back();
                return;
            }
            // Иначе уходим на запасной URL, если задан, либо на главную
            const fallbackUrl = backEl.getAttribute('data-back-url') || '/';
            // Навигация без показа прелоадера
            if (typeof window.navigationTriggered !== 'undefined') {
                window.navigationTriggered = false;
            }
            window.location.assign(fallbackUrl);
        } catch (_) {
            // На всякий случай, если что-то пошло не так
            try { window.history.back(); } catch {}
        }
    }, true);
});
