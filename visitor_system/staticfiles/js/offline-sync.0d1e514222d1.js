// Файл для синхронизации данных между оффлайн и онлайн режимами
// Будет использоваться для хранения данных в IndexedDB во время оффлайн-режима
// и синхронизации их с сервером при восстановлении соединения

class OfflineSync {
    constructor() {
        this.dbName = 'visitorSystemOfflineDB';
        this.dbVersion = 1;
        this.pendingChangesStore = 'pendingChanges';
        this.tempDataStore = 'tempData';
        this.db = null;
        
        // Инициализация базы данных
        this.initDB();
        
        // Проверка соединения при изменении статуса сети
        window.addEventListener('online', () => this.syncWithServer());
    }
    
    // Инициализация IndexedDB
    initDB() {
        const request = indexedDB.open(this.dbName, this.dbVersion);
        
        request.onerror = (event) => {
            console.error('Ошибка при открытии IndexedDB:', event.target.error);
        };
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            // Хранилище для отложенных изменений
            if (!db.objectStoreNames.contains(this.pendingChangesStore)) {
                const pendingStore = db.createObjectStore(this.pendingChangesStore, { keyPath: 'id', autoIncrement: true });
                pendingStore.createIndex('timestamp', 'timestamp', { unique: false });
                pendingStore.createIndex('endpoint', 'endpoint', { unique: false });
            }
            
            // Хранилище для временных данных
            if (!db.objectStoreNames.contains(this.tempDataStore)) {
                const tempStore = db.createObjectStore(this.tempDataStore, { keyPath: 'key' });
                tempStore.createIndex('timestamp', 'timestamp', { unique: false });
            }
        };
        
        request.onsuccess = (event) => {
            this.db = event.target.result;
            console.log('IndexedDB успешно инициализирована');
            
            // При успешном подключении проверяем наличие отложенных изменений
            if (navigator.onLine) {
                this.syncWithServer();
            }
        };
    }
    
    // Сохранение данных формы, которые должны быть отправлены на сервер позже
    savePendingChange(endpoint, method, data) {
        return new Promise((resolve, reject) => {
            if (!this.db) {
                return reject(new Error('База данных не инициализирована'));
            }
            
            const transaction = this.db.transaction([this.pendingChangesStore], 'readwrite');
            const store = transaction.objectStore(this.pendingChangesStore);
            
            const record = {
                endpoint,
                method,
                data,
                timestamp: new Date().getTime(),
                attempts: 0
            };
            
            const request = store.add(record);
            
            request.onsuccess = () => {
                console.log('Изменение сохранено для последующей синхронизации');
                resolve(true);
                
                // Показываем уведомление пользователю
                this.showNotification(
                    'Данные сохранены локально', 
                    'Изменения будут отправлены на сервер, когда подключение к интернету будет восстановлено.'
                );
            };
            
            request.onerror = (event) => {
                console.error('Ошибка при сохранении изменения:', event.target.error);
                reject(event.target.error);
            };
        });
    }
    
    // Сохранение временных данных для использования в оффлайн-режиме
    saveTempData(key, data) {
        return new Promise((resolve, reject) => {
            if (!this.db) {
                return reject(new Error('База данных не инициализирована'));
            }
            
            const transaction = this.db.transaction([this.tempDataStore], 'readwrite');
            const store = transaction.objectStore(this.tempDataStore);
            
            const record = {
                key,
                data,
                timestamp: new Date().getTime()
            };
            
            const request = store.put(record);
            
            request.onsuccess = () => {
                console.log(`Временные данные сохранены (${key})`);
                resolve(true);
            };
            
            request.onerror = (event) => {
                console.error('Ошибка при сохранении временных данных:', event.target.error);
                reject(event.target.error);
            };
        });
    }
    
    // Получение временных данных
    getTempData(key) {
        return new Promise((resolve, reject) => {
            if (!this.db) {
                return reject(new Error('База данных не инициализирована'));
            }
            
            const transaction = this.db.transaction([this.tempDataStore], 'readonly');
            const store = transaction.objectStore(this.tempDataStore);
            
            const request = store.get(key);
            
            request.onsuccess = () => {
                resolve(request.result ? request.result.data : null);
            };
            
            request.onerror = (event) => {
                console.error('Ошибка при получении временных данных:', event.target.error);
                reject(event.target.error);
            };
        });
    }
    
    // Синхронизация отложенных изменений с сервером
    syncWithServer() {
        if (!navigator.onLine || !this.db) {
            return Promise.resolve(false);
        }
        
        return new Promise((resolve) => {
            const transaction = this.db.transaction([this.pendingChangesStore], 'readonly');
            const store = transaction.objectStore(this.pendingChangesStore);
            
            const request = store.openCursor();
            let pendingCount = 0;
            
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                
                if (cursor) {
                    pendingCount++;
                    cursor.continue();
                } else {
                    if (pendingCount > 0) {
                        this.processPendingChanges().then(result => {
                            if (result.success > 0) {
                                this.showNotification(
                                    'Данные синхронизированы', 
                                    `Успешно отправлено на сервер: ${result.success} изменений.` +
                                    (result.failed > 0 ? ` Ошибок: ${result.failed}.` : '')
                                );
                            }
                            resolve(true);
                        });
                    } else {
                        resolve(false);
                    }
                }
            };
            
            request.onerror = () => {
                resolve(false);
            };
        });
    }
    
    // Обработка отложенных изменений
    processPendingChanges() {
        return new Promise((resolve) => {
            const transaction = this.db.transaction([this.pendingChangesStore], 'readwrite');
            const store = transaction.objectStore(this.pendingChangesStore);
            
            const index = store.index('timestamp');
            const request = index.openCursor();
            
            let results = { success: 0, failed: 0 };
            
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                
                if (cursor) {
                    const record = cursor.value;
                    
                    // Отправляем запрос на сервер
                    this.sendToServer(record).then(success => {
                        if (success) {
                            // Если успешно, удаляем запись
                            store.delete(record.id);
                            results.success++;
                        } else {
                            // Увеличиваем счетчик попыток
                            record.attempts++;
                            
                            if (record.attempts >= 3) {
                                // После 3 неудачных попыток считаем запрос неуспешным
                                store.delete(record.id);
                                results.failed++;
                            } else {
                                // Обновляем запись
                                store.put(record);
                            }
                        }
                        cursor.continue();
                    }).catch(() => {
                        record.attempts++;
                        if (record.attempts >= 3) {
                            store.delete(record.id);
                            results.failed++;
                        } else {
                            store.put(record);
                        }
                        cursor.continue();
                    });
                } else {
                    resolve(results);
                }
            };
            
            request.onerror = () => {
                resolve(results);
            };
        });
    }
    
    // Отправка данных на сервер
    sendToServer(record) {
        return new Promise((resolve) => {
            // Добавляем CSRF-токен, если он есть
            const csrfToken = this.getCSRFToken();
            const headers = {
                'Content-Type': 'application/json',
            };
            
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }
            
            fetch(record.endpoint, {
                method: record.method,
                headers: headers,
                body: JSON.stringify(record.data),
                credentials: 'same-origin'
            }).then(response => {
                if (response.ok) {
                    resolve(true);
                } else {
                    console.warn('Ошибка при синхронизации с сервером:', response.status);
                    resolve(false);
                }
            }).catch(error => {
                console.error('Ошибка при отправке на сервер:', error);
                resolve(false);
            });
        });
    }
    
    // Получение CSRF-токена
    getCSRFToken() {
        const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (csrfInput) {
            return csrfInput.value;
        }
        
        const csrfCookie = document.cookie.match(/csrftoken=([^;]+)/);
        if (csrfCookie) {
            return csrfCookie[1];
        }
        
        return null;
    }
    
    // Отображение уведомления пользователю
    showNotification(title, message) {
        const notificationElement = document.createElement('div');
        notificationElement.style.cssText = `
            position: fixed;
            bottom: 80px;
            right: 20px;
            padding: 10px 15px;
            background-color: #4caf50;
            color: white;
            border-radius: 4px;
            z-index: 9999;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-size: 14px;
            max-width: 300px;
        `;
        
        notificationElement.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 5px;">${title}</div>
            <div>${message}</div>
        `;
        
        document.body.appendChild(notificationElement);
        
        setTimeout(() => {
            notificationElement.style.opacity = '0';
            notificationElement.style.transition = 'opacity 1s ease';
            setTimeout(() => {
                notificationElement.remove();
            }, 1000);
        }, 5000);
    }
    
    // Перехват отправки формы для возможности работы в оффлайн-режиме
    interceptForm(form, endpoint, method = 'POST', dataPreprocessor = null) {
        form.addEventListener('submit', (event) => {
            // Если нет подключения к сети
            if (!navigator.onLine) {
                event.preventDefault();
                
                // Собираем данные формы
                const formData = new FormData(form);
                const data = {};
                
                for (const [key, value] of formData.entries()) {
                    data[key] = value;
                }
                
                // Применяем предобработчик данных, если он указан
                const processedData = dataPreprocessor ? dataPreprocessor(data) : data;
                
                // Сохраняем данные для последующей синхронизации
                this.savePendingChange(endpoint, method, processedData);
                
                return false;
            }
        });
    }
}

// Создаем глобальный экземпляр, доступный всем скриптам
window.offlineSync = new OfflineSync();

// Функция для перехвата AJAX-запросов и сохранения их в IndexedDB в случае офлайн-режима
function setupAjaxInterception() {
    const originalFetch = window.fetch;
    
    window.fetch = function(input, init) {
        // Если сеть доступна, используем обычный fetch
        if (navigator.onLine) {
            return originalFetch.apply(this, arguments);
        }
        
        // В офлайн-режиме проверяем, является ли запрос возможным для отложенной обработки
        // Например, POST-запросы для сохранения данных
        
        const url = typeof input === 'string' ? input : input.url;
        const method = init && init.method ? init.method : 'GET';
        
        // Если это GET-запрос или запрос к стороннему домену, используем обычный fetch
        if (method === 'GET' || !/^(https?:\/\/[^/]*)?(\/|$)/.test(url)) {
            return originalFetch.apply(this, arguments);
        }
        
        // Для запросов изменения данных создаем запись в IndexedDB
        let data = null;
        
        if (init && init.body) {
            try {
                // Пытаемся разобрать JSON из тела запроса
                if (typeof init.body === 'string') {
                    data = JSON.parse(init.body);
                } else if (init.body instanceof FormData) {
                    // Преобразуем FormData в объект
                    data = {};
                    for (const [key, value] of init.body.entries()) {
                        data[key] = value;
                    }
                } else {
                    // Другие типы данных
                    data = init.body;
                }
            } catch (e) {
                console.error('Ошибка при разборе данных для офлайн-запроса:', e);
            }
        }
        
        // Сохраняем запрос для последующей отправки
        return window.offlineSync.savePendingChange(url, method, data)
            .then(() => {
                // Возвращаем фиктивный ответ
                return new Response(JSON.stringify({ 
                    success: true, 
                    offline: true, 
                    message: 'Данные сохранены для отправки после восстановления соединения' 
                }), {
                    status: 202,
                    headers: { 'Content-Type': 'application/json' }
                });
            })
            .catch(error => {
                console.error('Ошибка при сохранении офлайн-запроса:', error);
                throw new Error('Не удалось сохранить запрос для офлайн-режима');
            });
    };
}

// Настраиваем перехват запросов
document.addEventListener('DOMContentLoaded', setupAjaxInterception);
