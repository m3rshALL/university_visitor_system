self.addEventListener('install', event => {
    self.skipWaiting();
});
self.addEventListener('activate', event => {
    console.log('PWA service worker activated');
});
self.addEventListener('fetch', event => {
    // можно добавить кеширование
});