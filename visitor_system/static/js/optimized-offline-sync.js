// Оптимизированная версия offline-sync.js
document.addEventListener('DOMContentLoaded', function() {
    // Проверка поддержки IndexedDB
    if (!window.indexedDB) {
        console.log('Этот браузер не поддерживает IndexedDB, офлайн-синхронизация недоступна');
        return;
    }
    
    // Кеш для хранения состояния запросов
    let pendingRequests = [];
    let isProcessing = false;
    let db = null;
    
    // Инициализируем IndexedDB для хранения отложенных запросов
    function initDatabase() {
        const request = indexedDB.open('offlineRequestsDB', 1);
        
        request.onupgradeneeded = function(event) {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('pendingRequests')) {
                db.createObjectStore('pendingRequests', { keyPath: 'id', autoIncrement: true });
            }
        };
        
        request.onsuccess = function(event) {
            db = event.target.result;
            loadPendingRequests();
        };
        
        request.onerror = function(event) {
            console.error('Ошибка открытия IndexedDB:', event.target.errorCode);
        };
    }
    
    // Загрузка сохраненных запросов из IndexedDB
    function loadPendingRequests() {
        if (!db) return;
        
        const transaction = db.transaction(['pendingRequests'], 'readonly');
        const store = transaction.objectStore('pendingRequests');
        const getAll = store.getAll();
        
        getAll.onsuccess = function(event) {
            pendingRequests = event.target.result || [];
            
            // Если есть отложенные запросы и мы онлайн, пытаемся их отправить
            if (pendingRequests.length > 0 && navigator.onLine) {
                processPendingRequests();
            }
        };
    }
    
    // Добавление запроса в очередь и сохранение в IndexedDB
    function addRequestToQueue(request) {
        if (!db) return;
        
        const transaction = db.transaction(['pendingRequests'], 'readwrite');
        const store = transaction.objectStore('pendingRequests');
        const addRequest = store.add(request);
        
        addRequest.onsuccess = function() {
            pendingRequests.push(request);
            
            // Если мы онлайн, пытаемся отправить запрос сразу
            if (navigator.onLine) {
                processPendingRequests();
            }
        };
    }
    
    // Удаление запроса из IndexedDB после успешной отправки
    function removeRequestFromQueue(id) {
        if (!db) return;
        
        const transaction = db.transaction(['pendingRequests'], 'readwrite');
        const store = transaction.objectStore('pendingRequests');
        store.delete(id);
        
        // Также удаляем из локального массива
        pendingRequests = pendingRequests.filter(req => req.id !== id);
    }
    
    // Обработка отложенных запросов
    function processPendingRequests() {
        if (isProcessing || pendingRequests.length === 0 || !navigator.onLine) return;
        
        isProcessing = true;
        
        // Берем первый запрос из очереди
        const request = pendingRequests[0];
        
        fetch(request.url, {
            method: request.method || 'POST',
            headers: request.headers || {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: request.body
        })
        .then(response => {
            if (response.ok) {
                // Если запрос успешен, удаляем его из очереди
                removeRequestFromQueue(request.id);
                
                // Показываем уведомление об успешной синхронизации (только для первого запроса)
                if (pendingRequests.length === 0) {
                    showSyncNotification('Данные успешно синхронизированы');
                }
            } else {
                console.error('Ошибка при отправке отложенного запроса:', response.statusText);
            }
        })
        .catch(error => {
            console.error('Ошибка при отправке отложенного запроса:', error);
        })
        .finally(() => {
            isProcessing = false;
            
            // Если еще остались запросы, продолжаем обработку
            if (pendingRequests.length > 0) {
                setTimeout(processPendingRequests, 1000); // Задержка между запросами
            }
        });
    }
    
    // Получение CSRF-токена из cookie
    function getCsrfToken() {
        const name = 'csrftoken';
        const cookieValue = document.cookie.split(';')
            .map(cookie => cookie.trim())
            .find(cookie => cookie.startsWith(name + '='));
            
        return cookieValue ? cookieValue.split('=')[1] : '';
    }
    
    // Показ уведомления о синхронизации
    function showSyncNotification(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 20px;
            padding: 10px 15px;
            background-color: #4caf50;
            color: white;
            border-radius: 4px;
            z-index: 9999;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-size: 14px;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 1s ease';
            setTimeout(() => notification.remove(), 1000);
        }, 3000);
    }
    
    // Экспортируем функцию для добавления запросов в очередь
    window.queueRequestForSync = function(url, method, body, headers) {
        const request = {
            url,
            method: method || 'POST',
            body: typeof body === 'string' ? body : JSON.stringify(body),
            headers,
            timestamp: Date.now()
        };
        
        addRequestToQueue(request);
        return true;
    };
    
    // Инициализируем БД при загрузке
    initDatabase();
    
    // Слушаем изменение статуса сети для возобновления отправки запросов
    window.addEventListener('online', processPendingRequests);
});
