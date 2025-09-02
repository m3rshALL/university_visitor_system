// Простой и быстрый прелоадер без сложной логики
(function() {
    'use strict';
    
    // Защита от повторной инициализации
    if (window.simplePreloaderInit) return;
    window.simplePreloaderInit = true;

    function showContent() {
        // Ищем правильный content wrapper
        const contentWrapper = document.querySelector('.content-wrapper') || 
                              document.querySelector('.page.content-wrapper') ||
                              document.querySelector('.page');
        if (contentWrapper) {
            contentWrapper.classList.add('loaded');
            contentWrapper.style.opacity = '1';
            contentWrapper.style.visibility = 'visible';
        }
        
        // Также показываем весь body
        document.body.style.opacity = '1';
        document.body.style.visibility = 'visible';
    }

    function hidePreloader() {
        const preloader = document.getElementById('preloader');
        if (preloader) {
            preloader.style.opacity = '0';
            preloader.style.visibility = 'hidden';
            preloader.classList.add('hidden');
            
            // Удаляем через короткое время
            setTimeout(() => {
                if (preloader && preloader.parentNode) {
                    preloader.remove();
                }
            }, 300);
        }
    }

    // Основная логика - показываем контент быстро
    function initPage() {
        console.log('Preloader: инициализация страницы');
        
        // Немедленно показываем контент
        showContent();
        
        // Быстро скрываем прелоадер
        setTimeout(() => {
            hidePreloader();
            console.log('Preloader: скрыт');
        }, 100);
    }

    // Обработка HTMX событий
    document.addEventListener('htmx:beforeSwap', function() {
        console.log('Preloader: HTMX before swap - показываем контент');
        showContent();
    });
    
    document.addEventListener('htmx:afterSwap', function() {
        console.log('Preloader: HTMX after swap - финализация');
        showContent();
        hidePreloader();
    });

    // Инициализация при готовности DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPage);
    } else {
        // Если DOM уже готов
        console.log('Preloader: DOM уже готов');
        initPage();
    }

    // Защита - принудительно показываем контент через короткое время
    setTimeout(() => {
        console.log('Preloader: принудительное показывание контента');
        showContent();
        hidePreloader();
    }, 500);

})();
