const CACHE_NAME = 'visitor-system-cache-v1';
const OFFLINE_URL = '/offline.html';
const DB_VERSION = 1;

// Ресурсы для кеширования
const STATIC_ASSETS = [
    '/',
    OFFLINE_URL,
    '/static/css/tabler.min.css',
    '/static/js/tabler.min.js',
    '/static/img/logo.png',
    '/static/js/chart.js',
    '/static/js/apexcharts.min.js',
    '/static/js/offline-handler.js',
    '/static/js/offline-sync.js',
    '/static/js/pwa-test.js',
    '/static/js/preloader.js',
    '/static/css/preloader.css',
    '/static/img/placeholder.svg',
    '/static/css/icons.css',
    '/static/tabler/css/tabler.min.css',
    '/static/tabler/js/tabler.min.js',
    // Дополнительные ресурсы
    '/static/tabler/css/tabler-flags.css',
    '/static/tabler/css/tabler-socials.css',
    '/static/tabler/css/tabler-payments.css',
    '/static/tabler/css/tabler-vendors.css',
    '/static/tabler/css/tabler-marketing.css',
    '/static/css/style.css',
    '/static/tabler/js/tabler-theme.js',
    // Шрифты и иконки
    '/static/fonts/tabler-icons.woff2',
    '/static/fonts/tabler-icons.woff',
    // Возможно другие ресурсы
];

// Какие страницы следует кешировать для оффлайн доступа
const PAGES_TO_CACHE = [
    '/',
    '/visitors/employee_dashboard/',
    '/visitors/current_guests/',
    '/visitors/visit_history/',
    '/visitors/visit_statistics/',
    '/offline.html'
];

// Установка Service Worker и заполнение кеша
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Открытие кеша и добавление статических ресурсов');
                const cachePromises = [
                    ...STATIC_ASSETS,
                    ...PAGES_TO_CACHE
                ].map(url => {
                    return fetch(url, { credentials: 'same-origin' })
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`Не удалось кешировать ${url}, статус: ${response.status}`);
                            }
                            return cache.put(url, response);
                        })
                        .catch(error => {
                            console.warn(`Не удалось кешировать ${url}:`, error);
                        });
                });
                
                return Promise.allSettled(cachePromises);
            })
            .then(() => {
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

// Периодический кеш дополнительных страниц (для навигации офлайн)
self.addEventListener('sync', event => {
    if (event.tag === 'cache-pages') {
        event.waitUntil(cacheAdditionalPages());
    }
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