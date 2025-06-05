const CACHE_NAME = 'visitor-system-cache-v2';
const DB_VERSION = 1;

// Ресурсы для кеширования - обновлены пути к существующим файлам
const STATIC_ASSETS = [
    '/',
    OFFLINE_URL,
    // Используем только имеющиеся файлы
    '/static/js/offline-handler.js',
    '/static/js/offline-sync.js',
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
        // Для API всегда сначала пробуем сеть
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

// Обработка push-уведомлений (если поддерживается)
self.addEventListener('push', event => {
    if (!event.data) return;
    
    // Получаем данные уведомления
    const data = event.data.json();
    
    // Показываем уведомление
    const title = data.title || 'Система пропусков';
    const options = {
        body: data.body || 'Новое уведомление',
        icon: data.icon || '/static/img/icons/icon-72x72.png',
        badge: data.badge || '/static/img/icons/badge-72x72.png',
        data: data.data || {}
    };
    
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// Обработка клика по уведомлению
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    // Получаем данные, привязанные к уведомлению
    const data = event.notification.data;
    const url = data.url || '/';
    
    // Открываем нужную страницу при клике на уведомление
    event.waitUntil(
        clients.matchAll({ type: 'window' })
            .then(windowClients => {
                // Проверяем, есть ли открытые окна
                for (let client of windowClients) {
                    if (client.url === url && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Если нет открытых окон, открываем новое
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});