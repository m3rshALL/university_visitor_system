// Файл для тестирования PWA и оффлайн-режима
// Открывает в браузере панель управления для отключения/включения сети

const testOfflineMode = function() {
    // Создаем элемент панели управления
    const controlPanel = document.createElement('div');
    controlPanel.id = 'pwa-test-panel';
    controlPanel.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 10px;
        border-radius: 4px;
        z-index: 10000;
        font-size: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    `;
    
    controlPanel.innerHTML = `
        <div style="margin-bottom: 10px; font-weight: bold; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 5px;">
            Тестирование PWA
        </div>
        <div style="margin-bottom: 10px;">
            <button id="test-offline-button" style="width: 100%; padding: 5px; background: #f44336; border: none; color: white; border-radius: 4px; cursor: pointer;">
                Симулировать оффлайн
            </button>
        </div>
        <div style="margin-bottom: 10px;">
            <button id="test-online-button" style="width: 100%; padding: 5px; background: #4caf50; border: none; color: white; border-radius: 4px; cursor: pointer;">
                Симулировать онлайн
            </button>
        </div>
        <div style="margin-bottom: 10px;">
            <button id="clear-cache-button" style="width: 100%; padding: 5px; background: #2196f3; border: none; color: white; border-radius: 4px; cursor: pointer;">
                Очистить кеш
            </button>
        </div>
        <div style="margin-bottom: 5px;">
            <button id="close-test-panel" style="width: 100%; padding: 5px; background: #9e9e9e; border: none; color: white; border-radius: 4px; cursor: pointer;">
                Закрыть панель
            </button>
        </div>
    `;
    
    document.body.appendChild(controlPanel);
    
    // Добавляем обработчики
    document.getElementById('test-offline-button').addEventListener('click', function() {
        // Генерируем событие "offline"
        window.dispatchEvent(new Event('offline'));
        this.disabled = true;
        document.getElementById('test-online-button').disabled = false;
        
        // Уведомляем пользователя
        alert('Симуляция оффлайн-режима активирована. Некоторые функции будут недоступны.');
    });
    
    document.getElementById('test-online-button').addEventListener('click', function() {
        // Генерируем событие "online"
        window.dispatchEvent(new Event('online'));
        this.disabled = true;
        document.getElementById('test-offline-button').disabled = false;
        
        // Уведомляем пользователя
        alert('Симуляция онлайн-режима активирована. Функциональность восстановлена.');
    });
    
    document.getElementById('clear-cache-button').addEventListener('click', function() {
        if ('caches' in window) {
            caches.keys().then(function(names) {
                for (let name of names) {
                    caches.delete(name);
                }
                alert('Кеш PWA успешно очищен. Обновите страницу для повторной загрузки ресурсов.');
            });
        } else {
            alert('Ваш браузер не поддерживает Cache API.');
        }
    });
    
    document.getElementById('close-test-panel').addEventListener('click', function() {
        document.getElementById('pwa-test-panel').remove();
    });
};

// Запускаем панель управления только при наличии URL-параметра test_pwa=1
if (window.location.href.includes('test_pwa=1')) {
    document.addEventListener('DOMContentLoaded', testOfflineMode);
}
