// Управление прелоадером
let navigationTriggered = false;

// Отмечаем навигацию только при явных действиях пользователя (внутренние ссылки/формы)
document.addEventListener('click', function(e) {
    const link = e.target && e.target.closest && e.target.closest('a[href]');
    if (link) {
        try {
            const url = new URL(link.href, window.location.href);
            if (url.origin === window.location.origin) {
                navigationTriggered = true;
            }
        } catch(_) {}
    }
});
document.addEventListener('submit', function() {
    navigationTriggered = true;
}, true);

document.addEventListener('DOMContentLoaded', function() {
    // Измерение времени загрузки
    const startTime = window.performance.timing.navigationStart;
    const endTime = new Date().getTime();
    const loadTime = endTime - startTime;
    
    // Гарантируем минимальное время отображения прелоадера (минимум 700мс)
    // чтобы он выглядел более естественно и не мигал при быстрой загрузке
    const minPreloaderTime = 700; 
    const timeToWait = loadTime < minPreloaderTime ? minPreloaderTime - loadTime : 0;
    
    // Показываем контент
    const contentWrapper = document.querySelector('.content-wrapper');
    if (contentWrapper) {
        setTimeout(() => {
            contentWrapper.classList.add('loaded');
        }, timeToWait);
    }
    
    // Скрываем прелоадер
    const preloader = document.getElementById('preloader');
    if (preloader) {
        setTimeout(() => {
            preloader.classList.add('hidden');
            
            // Полностью удаляем прелоадер после завершения анимации
            setTimeout(() => {
                preloader.remove();
            }, 500);
        }, timeToWait);
    }
});

// Показываем прелоадер при переходе на другую страницу
window.addEventListener('beforeunload', function(event) {
    // Не показываем прелоадер для внешних ссылок, только для навигации внутри сайта
    // И не показываем при кнопке Назад/Вперед (navigationTriggered=false)
    const target = event.target;
    if (!navigationTriggered) {
        return;
    }
    if (target && target.activeElement && target.activeElement.href) {
        const href = target.activeElement.href;
        if (href.indexOf(window.location.origin) !== 0) {
            return; // Это внешняя ссылка, не показываем прелоадер
        }
    }
    
    // При переходе на другую страницу показываем прелоадер снова
    const existingPreloader = document.getElementById('preloader');
      if (!existingPreloader) {
        const preloader = document.createElement('div');        
        preloader.id = 'preloader';
        preloader.className = 'preloader';
        preloader.innerHTML = `
            <div class="spinner"></div>
            <div class="preloader-text">Загрузка системы пропусков...</div>
        `;
        document.body.appendChild(preloader);
    } else {
        existingPreloader.classList.remove('hidden');
    }
    // Сбрасываем флаг
    navigationTriggered = false;
});

// При возврате по кнопке Назад/Вперед (bfcache) гарантируем скрытие прелоадера
window.addEventListener('pageshow', function(event) {
    try {
        const navEntries = performance.getEntriesByType && performance.getEntriesByType('navigation');
        const navType = navEntries && navEntries[0] && navEntries[0].type;
        if (event.persisted === true || navType === 'back_forward') {
            const preloader = document.getElementById('preloader');
            if (preloader) {
                preloader.classList.add('hidden');
                setTimeout(() => preloader.remove(), 300);
            }
            const contentWrapper = document.querySelector('.content-wrapper');
            if (contentWrapper) {
                contentWrapper.classList.add('loaded');
            }
        }
    } catch(_) {}
});
