const CACHE_NAME = 'visitor-system-cache-v3';
const DB_VERSION = 1;

// Ресурсы для кеширования - обновлены пути к существующим файлам
const OFFLINE_URL = '/offline.html';
const PAGES_TO_CACHE = [
    '/', '/visitors/history/',
];
const STATIC_ASSETS = [
    '/',
    OFFLINE_URL,
    // Используем только существующие файлы
    '/static/js/optimized-offline-handler.js',
    '/static/js/optimized-offline-sync.js',
    '/static/js/vendor/imask.6.4.3.min.js',
    '/static/css/style.css',
    // Иконки PWA
    '/static/img/icons/icon-72x72.png',
    '/static/img/icons/icon-96x96.png',
    '/static/img/icons/icon-128x128.png',
    '/static/img/icons/icon-144x144.png',
    '/static/img/icons/icon-152x152.png',
    '/static/img/icons/icon-192x192.png',
    '/static/img/icons/icon-384x384.png',
    '/static/img/icons/icon-512x512.png',
    '/static/img/icons/apple-touch-icon.png'
];

// Установка Service Worker и заполнение кеша
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Открытие кеша и добавление статических ресурсов');
                
                // Сначала кешируем offline страницу
                return cache.add(new Request(OFFLINE_URL, { cache: 'reload' }))
                    .then(() => {
                        // Затем пытаемся кешировать другие ресурсы
                        const cachePromises = [
                            ...STATIC_ASSETS,
                            ...PAGES_TO_CACHE
                        ].map(url => {
                            // Пропускаем offline URL, так как мы уже его кешировали
                            if (url === OFFLINE_URL) return Promise.resolve();
                            
                            return fetch(url, { 
                                credentials: 'same-origin',
                                cache: 'no-cache' // Всегда пытаемся получить свежую версию
                            })
                            .then(response => {
                                if (!response.ok) {
                                    console.log(`Пропускаем кеширование ${url}, статус: ${response.status}`);
                                    return;
                                }
                                return cache.put(url, response);
                            })
                            .catch(error => {
                                console.log(`Не удалось кешировать ${url}: ${error.message}`);
                                // Не прерываем установку, если один файл не может быть кеширован
                                return Promise.resolve();
                            });
                        });
                        
                        // Используем Promise.allSettled, чтобы установка прошла успешно, даже если некоторые ресурсы не удалось кешировать
                        return Promise.allSettled(cachePromises);
                    });
            })
            .then(() => {
                console.log('Service Worker успешно установлен');
                return self.skipWaiting();
            })
    );
});

// Активация Service Worker и очистка старых кешей
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.filter(cacheName => {
                    return cacheName !== CACHE_NAME;
                }).map(cacheName => {
                    console.log('Удаление старого кеша:', cacheName);
                    return caches.delete(cacheName);
                })
            );
        }).then(() => {
            console.log('PWA service worker активирован');
            return self.clients.claim();
        })
    );
});

// Обработка fetch запросов: сначала сеть, затем кеш, потом offline страница
self.addEventListener('fetch', event => {
    // Пропускаем не GET запросы
    if (event.request.method !== 'GET') return;
    
    // Пропускаем cross-origin запросы
    if (!event.request.url.startsWith(self.location.origin)) return;
    
    // Явно исключаем дашборд API из любой обработки SW
    if (event.request.url.includes('/dashboard/api/')) {
        return;
    }
    
    // Особая обработка для манифеста - всегда пробуем из сети
    if (event.request.url.includes('/manifest.json')) {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    console.log('Failed to fetch manifest.json from network');
                    return caches.match(event.request);
                })
        );
        return;
    }
    
    // Отдельная обработка API запросов
    if (event.request.url.includes('/api/')) {
        // Для API — выходим, не перехватываем
        return;
    }
    
    event.respondWith(
        fetch(event.request)
            .then(response => {
                // Если получили валидный ответ, клонируем его и обновляем кеш
                if (response && response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            })
            .catch(() => {
                // Если сеть недоступна, пробуем отдать из кеша
                return caches.match(event.request)
                    .then(cachedResponse => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        
                        // Если запрос для страницы (не ресурса), возвращаем offline страницу
                        if (event.request.mode === 'navigate') {
                            return caches.match(OFFLINE_URL);
                        }
                        
                        // Для других ресурсов просто возвращаем простой ответ
                        return new Response('Ресурс недоступен офлайн', {
                            status: 503,
                            statusText: 'Service Unavailable',
                            headers: new Headers({
                                'Content-Type': 'text/plain'
                            })
                        });
                    });
            })
    );
});

// Функция для кеширования дополнительных страниц сайта
async function cacheAdditionalPages() {
    const cache = await caches.open(CACHE_NAME);
    
    // Кешируем основные страницы сайта
    for (const url of PAGES_TO_CACHE) {
        try {
            const response = await fetch(url, { credentials: 'same-origin' });
            if (response.ok) {
                await cache.put(url, response);
            }
        } catch (error) {
            console.warn(`Не удалось кешировать ${url}:`, error);
        }
    }
}

// Обработка запросов
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    
    // Пропускаем запросы к API и административной панели, а также внешние запросы
    if (
        url.pathname.includes('/api/') || 
        url.pathname.includes('/admin/') ||
        url.pathname.includes('/accounts/') ||
        (url.origin !== self.location.origin && !url.hostname.includes('googleapis.com')) ||
        event.request.method !== 'GET'
    ) {
        return;
    }

    // Для HTML-страниц используем стратегию "Network First, fallback to Cache"
    if (event.request.headers.get('Accept') && 
        event.request.headers.get('Accept').includes('text/html')) {
        
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    // Если успешный ответ, клонируем его и сохраняем в кеш
                    if (response.ok) {
                        const clonedResponse = response.clone();
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(event.request, clonedResponse);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    // Если сеть недоступна, пытаемся получить из кеша
                    return caches.match(event.request)
                        .then(cachedResponse => {
                            // Если страница есть в кеше, возвращаем её
                            if (cachedResponse) {
                                return cachedResponse;
                            }
                            // Иначе возвращаем страницу оффлайн
                            return caches.match(OFFLINE_URL);
                        });
                })
        );
    } else if (url.pathname.match(/\.(js|css|woff2?|ttf|eot|svg|png|jpe?g|gif|ico)$/i)) {
        // Для статических ресурсов используем стратегию "Cache First, fallback to Network"
        event.respondWith(
            caches.match(event.request)
                .then(cachedResponse => {
                    // Если ресурс найден в кеше, возвращаем его
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    
                    // Иначе делаем запрос к сети
                    return fetch(event.request)
                        .then(response => {
                            // Если получили успешный ответ, клонируем и кешируем его
                            if (response.ok && response.type === 'basic') {
                                const clonedResponse = response.clone();
                                caches.open(CACHE_NAME).then(cache => {
                                    cache.put(event.request, clonedResponse);
                                });
                            }
                            return response;
                        })
                        .catch(error => {
                            console.error('Ошибка при обработке запроса:', error);
                            // Для изображений возвращаем плейсхолдер
                            if (event.request.url.match(/\.(jpg|jpeg|png|gif|bmp|webp)$/i)) {
                                return caches.match('/static/img/placeholder.svg');
                            }
                            // Для других ресурсов возвращаем null
                            return Promise.resolve(null);
                        });
                })
        );
    } else {
        // Для остальных запросов используем стратегию "Network First, fallback to Cache"
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    // Если получили успешный ответ, возвращаем его
                    return response;
                })
                .catch(() => {
                    // Если сеть недоступна, пытаемся получить из кеша
                    return caches.match(event.request);
                })
        );
    }
});

// Функция для определения типа запроса
function isImage(url) {
    return url.match(/\.(jpg|jpeg|png|gif|bmp|webp|svg)$/i);
}

function isAsset(url) {
    return url.match(/\.(js|css|woff2?|ttf|eot)$/i);
}

// Обработка push-уведомлений
self.addEventListener('push', event => {
    console.log('Push-уведомление получено:', event);
    
    if (!event.data) {
        console.log('Push-уведомление без данных');
        return;
    }
    
    try {
        // Получаем данные уведомления
        const data = event.data.json();
        console.log('Данные push-уведомления:', data);
        
        // Параметры уведомления
        const title = data.title || 'Система пропусков AITU';
        const options = {
            body: data.body || 'Новое уведомление',
            icon: data.icon || '/static/img/icons/icon-192x192.png',
            badge: data.badge || '/static/img/icons/icon-72x72.png',
            tag: data.tag || 'default',
            timestamp: data.timestamp || Date.now(),
            requireInteraction: data.requireInteraction || false,
            silent: data.silent || false,
            data: data.data || {},
            actions: data.actions || []
        };

        // Добавляем действия для определенных типов уведомлений
        if (data.data && data.data.type) {
            switch (data.data.type) {
                case 'visit_approved':
                case 'guest_arrived':
                    options.actions = [
                        {
                            action: 'view',
                            title: 'Посмотреть',
                            icon: '/static/img/icons/icon-72x72.png'
                        },
                        {
                            action: 'dismiss',
                            title: 'Закрыть'
                        }
                    ];
                    break;
                case 'booking_confirmed':
                    options.actions = [
                        {
                            action: 'view_booking',
                            title: 'Мои бронирования',
                            icon: '/static/img/icons/icon-72x72.png'
                        }
                    ];
                    break;
            }
        }
        
        // Показываем уведомление
        event.waitUntil(
            self.registration.showNotification(title, options)
        );
        
    } catch (error) {
        console.error('Ошибка обработки push-уведомления:', error);
        
        // Показываем базовое уведомление в случае ошибки
        event.waitUntil(
            self.registration.showNotification('Система пропусков AITU', {
                body: 'Новое уведомление',
                icon: '/static/img/icons/icon-192x192.png',
                badge: '/static/img/icons/icon-72x72.png'
            })
        );
    }
});

// Обработка клика по уведомлению
self.addEventListener('notificationclick', event => {
    console.log('Клик по уведомлению:', event);
    
    event.notification.close();
    
    // Получаем данные уведомления
    const data = event.notification.data || {};
    const action = event.action;
    
    // Определяем URL для открытия
    let targetUrl = '/';
    
    if (action === 'dismiss') {
        // Просто закрываем уведомление
        return;
    }
    
    // Обработка действий
    switch (action) {
        case 'view':
            targetUrl = data.url || '/visitors/history/';
            break;
        case 'view_booking':
            targetUrl = '/classroom/my-bookings/';
            break;
        default:
            // Обработка по типу уведомления
            if (data.type) {
                switch (data.type) {
                    case 'visit_approved':
                    case 'visit_denied':
                    case 'guest_arrived':
                        targetUrl = data.url || '/visitors/history/';
                        break;
                    case 'booking_confirmed':
                    case 'booking_cancelled':
                        targetUrl = '/classroom/my-bookings/';
                        break;
                    case 'system':
                        targetUrl = data.url || '/';
                        break;
                    default:
                        targetUrl = data.url || '/';
                }
            } else {
                targetUrl = data.url || '/';
            }
    }
    
    console.log('Открываем URL:', targetUrl);
    
    // Открываем нужную страницу при клике на уведомление
    event.waitUntil(
        clients.matchAll({ 
            type: 'window',
            includeUncontrolled: true 
        }).then(windowClients => {
            // Проверяем, есть ли открытые окна с нужным URL
            for (let client of windowClients) {
                if (client.url === targetUrl && 'focus' in client) {
                    return client.focus();
                }
            }
            
            // Проверяем, есть ли открытые окна с тем же origin
            for (let client of windowClients) {
                if (client.url.startsWith(self.location.origin) && 'navigate' in client) {
                    return client.navigate(targetUrl).then(() => client.focus());
                }
            }
            
            // Если нет подходящих окон, открываем новое
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        }).catch(error => {
            console.error('Ошибка при открытии страницы:', error);
            // Fallback: пробуем просто открыть новое окно
            return clients.openWindow(targetUrl);
        })
    );
});

// Обработка закрытия уведомления
self.addEventListener('notificationclose', event => {
    console.log('Уведомление закрыто:', event);
    
    // Можно отправить аналитику о закрытии уведомления
    const data = event.notification.data || {};
    if (data.notification_id) {
        // Отправляем информацию о закрытии уведомления на сервер (опционально)
        fetch('/notifications/track-close/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                notification_id: data.notification_id,
                action: 'close'
            })
        }).catch(error => {
            console.log('Не удалось отправить аналитику закрытия:', error);
        });
    }
});