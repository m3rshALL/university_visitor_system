// d:\university_visitor_system\templates\sw.js
const CACHE_NAME = 'visitor-system-cache-v1';
const urlsToCache = [
  // Здесь можно указать URL-адреса для кэширования, например, главную страницу
  // "{% url 'home' %}",
  // "{% static 'css/tabler.min.css' %}", // Пример вашего CSS
  // "{% static 'js/tabler.min.js' %}"    // Пример вашего JS
  // Для начала можно оставить пустым или добавить только главную страницу
];

self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching app shell');
        // return cache.addAll(urlsToCache); // Раскомментируйте, если urlsToCache не пуст
        return Promise.resolve(); // Если urlsToCache пуст
      })
      .then(() => {
        console.log('Service Worker: Install completed');
        return self.skipWaiting(); // Активировать новый SW немедленно
      })
  );
});

self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  // Удаление старых кэшей
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('Service Worker: Clearing old cache:', cache);
            return caches.delete(cache);
          }
        })
      );
    }).then(() => {
        console.log('Service Worker: Activate completed');
        return self.clients.claim(); // Взять под контроль открытые клиенты немедленно
    })
  );
});

self.addEventListener('fetch', event => {
  // Простая стратегия "сначала сеть, потом кэш"
  event.respondWith(
    fetch(event.request).catch(() => {
      // Если сеть недоступна, пытаемся достать из кэша
      return caches.match(event.request).then(response => {
        if (response) {
          return response;
        }
        // Если и в кэше нет, можно вернуть страницу-заглушку "офлайн"
        // return caches.match("{% url 'offline_page_name' %}"); // Если у вас есть такая страница
      });
    })
  );
});
