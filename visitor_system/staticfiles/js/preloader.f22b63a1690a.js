// Управление прелоадером
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
    const target = event.target;
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
});
