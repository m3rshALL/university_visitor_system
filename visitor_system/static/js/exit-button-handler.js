// Модуль для обработки кнопки "Выход" посетителя
document.addEventListener('DOMContentLoaded', function() {
    const exitButtons = document.querySelectorAll('.exit-button, button[data-action="exit"], form[action*="record_exit"] button[type="submit"]');
    
    // Если на странице есть кнопки выхода
    if (exitButtons && exitButtons.length > 0) {
        exitButtons.forEach(button => {
            button.addEventListener('click', handleExitClick);
        });
    }
    
    // Обработчик клика по кнопке выхода
    function handleExitClick(event) {
        // Добавляем индикатор загрузки
        const originalContent = this.innerHTML;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Обработка...';
        this.disabled = true;
        
        // Очищаем возможные закэшированные страницы перед отправкой формы
        try {
            // Выполняем префетч для обновления страницы без кэша
            if ('caches' in window) {
                caches.open('visitor-system-cache-v1')
                    .then(cache => {
                        // Очищаем ключи страниц истории визитов из кэша
                        cache.keys().then(requests => {
                            requests.forEach(request => {
                                const url = new URL(request.url);
                                if (url.pathname.includes('/visitors/history/') || 
                                    url.pathname === '/visitors/history' ||
                                    url.pathname.endsWith('/visitors/history/')) {
                                    cache.delete(request);
                                }
                            });
                        });
                    })
                    .catch(err => console.log('Ошибка при очистке кэша:', err));
            }
        } catch(e) {
            console.log('Ошибка при очистке кэша:', e);
        }
        
        // Продолжаем стандартную отправку формы
        const form = this.closest('form');
        if (form) {
            // Добавляем параметр для обхода кэша при редиректе
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = '_nocache';
            input.value = Date.now();
            form.appendChild(input);
            
            // Форма продолжит отправку нормально
            // setTimeout чтобы успел отобразиться спиннер
            setTimeout(() => {}, 10);
        } else {
            // Если это просто кнопка, а не форма
            console.log("Кнопка выхода не привязана к форме");
        }
    }
});
