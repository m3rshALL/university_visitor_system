/**
 * WebPush Notifications Manager
 * Управление подписками на push-уведомления
 */

class WebPushManager {
    constructor() {
        this.vapidPublicKey = null;
        this.isSupported = this.checkSupport();
        this.subscription = null;
        this.serviceWorkerRegistration = null;
        
        // Инициализация
        this.init();
    }

    /**
     * Проверка поддержки Push API
     */
    checkSupport() {
        if (!('serviceWorker' in navigator)) {
            console.warn('Service Workers не поддерживаются');
            return false;
        }

        if (!('PushManager' in window)) {
            console.warn('Push API не поддерживается');
            return false;
        }

        if (!('Notification' in window)) {
            console.warn('Notifications API не поддерживается');
            return false;
        }

        return true;
    }

    /**
     * Инициализация WebPush
     */
    async init() {
        if (!this.isSupported) {
            console.warn('WebPush не поддерживается в этом браузере');
            return;
        }

        try {
            // Получаем публичный VAPID ключ
            await this.getVapidPublicKey();
            
            // Регистрируем service worker
            await this.registerServiceWorker();
            
            // Проверяем существующую подписку
            await this.checkExistingSubscription();
            
            console.log('WebPush успешно инициализирован');
        } catch (error) {
            console.error('Ошибка инициализации WebPush:', error);
        }
    }

    /**
     * Получение публичного VAPID ключа с сервера
     */
    async getVapidPublicKey() {
        try {
            console.log('Запрашиваю VAPID ключ с /notifications/get-public-key/');
            const response = await fetch('/notifications/get-public-key/');
            console.log('Ответ получен, статус:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ошибка: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Данные от сервера:', data);
            
            this.vapidPublicKey = data.public_key;
            
            if (!this.vapidPublicKey) {
                console.error('VAPID ключ отсутствует в ответе сервера:', data);
                throw new Error('VAPID публичный ключ не найден');
            }
            
            console.log('VAPID ключ получен, длина:', this.vapidPublicKey.length);
            console.log('Первые 20 символов:', this.vapidPublicKey.substring(0, 20));
            
        } catch (error) {
            console.error('Ошибка получения VAPID ключа:', error);
            throw error;
        }
    }

    /**
     * Регистрация Service Worker
     */
    async registerServiceWorker() {
        try {
            this.serviceWorkerRegistration = await navigator.serviceWorker.register('/static/js/serviceworker.js');
            console.log('Service Worker зарегистрирован:', this.serviceWorkerRegistration);
        } catch (error) {
            console.error('Ошибка регистрации Service Worker:', error);
            throw error;
        }
    }

    /**
     * Проверка существующей подписки
     */
    async checkExistingSubscription() {
        try {
            this.subscription = await this.serviceWorkerRegistration.pushManager.getSubscription();
            
            if (this.subscription) {
                console.log('Найдена существующая подписка');
                this.updateUI(true);
            } else {
                console.log('Подписка не найдена');
                this.updateUI(false);
            }
        } catch (error) {
            console.error('Ошибка проверки подписки:', error);
        }
    }

    /**
     * Подписка на уведомления
     */
    async subscribe() {
        console.log('Начинаем процесс подписки на уведомления...');
        
        if (!this.isSupported) {
            this.showError('WebPush не поддерживается в вашем браузере');
            return false;
        }

        if (!this.serviceWorkerRegistration) {
            this.showError('Service Worker не зарегистрирован');
            return false;
        }

        if (!this.vapidPublicKey) {
            this.showError('VAPID ключ не получен с сервера');
            return false;
        }

        try {
            console.log('Запрашиваем разрешение на уведомления...');
            
            // Запрашиваем разрешение на уведомления
            const permission = await this.requestNotificationPermission();
            console.log('Получено разрешение:', permission);
            
            if (permission !== 'granted') {
                console.log('Разрешение не предоставлено, прерываем подписку');
                return false;
            }

            console.log('Создаем подписку через PushManager...');
            
            // Создаем подписку
            this.subscription = await this.serviceWorkerRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });

            console.log('Подписка создана:', this.subscription);

            // Отправляем подписку на сервер
            console.log('Отправляем подписку на сервер...');
            const success = await this.sendSubscriptionToServer(this.subscription);
            
            if (success) {
                this.updateUI(true);
                this.showSuccess('Подписка на уведомления успешно оформлена!');
                console.log('Подписка успешно завершена');
                return true;
            } else {
                console.log('Ошибка при отправке подписки на сервер, отменяем подписку');
                await this.subscription.unsubscribe();
                this.subscription = null;
                this.updateUI(false);
                return false;
            }

        } catch (error) {
            console.error('Ошибка подписки:', error);
            this.showError('Ошибка при оформлении подписки: ' + error.message);
            return false;
        }
    }

    /**
     * Отписка от уведомлений
     */
    async unsubscribe() {
        if (!this.subscription) {
            console.log('Нет активной подписки');
            return false;
        }

        try {
            // Отправляем запрос на отписку на сервер
            await this.sendUnsubscribeToServer(this.subscription);

            // Отписываемся локально
            await this.subscription.unsubscribe();
            this.subscription = null;
            
            this.updateUI(false);
            this.showSuccess('Подписка на уведомления отменена');
            
            console.log('Подписка отменена');
            return true;

        } catch (error) {
            console.error('Ошибка отписки:', error);
            this.showError('Ошибка при отмене подписки: ' + error.message);
            return false;
        }
    }

    /**
     * Запрос разрешения на уведомления
     */
    async requestNotificationPermission() {
        console.log('Текущее разрешение на уведомления:', Notification.permission);
        
        if (Notification.permission === 'granted') {
            console.log('Разрешение уже предоставлено');
            return 'granted';
        }

        if (Notification.permission === 'denied') {
            console.log('Разрешение отклонено пользователем');
            this.showError('Уведомления заблокированы. Разрешите уведомления в настройках браузера и обновите страницу.');
            return 'denied';
        }

        try {
            // Показываем пользователю что сейчас будет запрос разрешения
            console.log('Запрашиваем разрешение на уведомления...');
            
            // Запрашиваем разрешение
            const permission = await Notification.requestPermission();
            console.log('Результат запроса разрешения:', permission);
            
            if (permission === 'granted') {
                this.showSuccess('Разрешение на уведомления получено!');
            } else if (permission === 'denied') {
                this.showError('Разрешение на уведомления отклонено. Разрешите уведомления в настройках браузера.');
            } else {
                this.showError('Не удалось получить разрешение на уведомления.');
            }
            
            return permission;
            
        } catch (error) {
            console.error('Ошибка при запросе разрешения:', error);
            this.showError('Ошибка при запросе разрешения на уведомления: ' + error.message);
            return 'denied';
        }
    }

    /**
     * Отправка подписки на сервер
     */
    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/notifications/subscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    endpoint: subscription.endpoint,
                    keys: {
                        p256dh: this.arrayBufferToBase64(subscription.getKey('p256dh')),
                        auth: this.arrayBufferToBase64(subscription.getKey('auth'))
                    }
                })
            });

            const data = await response.json();
            
            if (response.ok && data.success) {
                console.log('Подписка отправлена на сервер:', data);
                return true;
            } else {
                this.showError(data.error || 'Ошибка при отправке подписки на сервер');
                return false;
            }

        } catch (error) {
            console.error('Ошибка отправки подписки:', error);
            this.showError('Ошибка соединения с сервером');
            return false;
        }
    }

    /**
     * Отправка запроса на отписку на сервер
     */
    async sendUnsubscribeToServer(subscription) {
        try {
            const response = await fetch('/notifications/unsubscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    endpoint: subscription.endpoint
                })
            });

            const data = await response.json();
            
            if (!response.ok || !data.success) {
                console.warn('Ошибка отписки на сервере:', data.error);
                // Не прерываем процесс, так как локальная отписка может быть успешной
            }

        } catch (error) {
            console.error('Ошибка отправки отписки:', error);
            // Не прерываем процесс
        }
    }

    /**
     * Обновление UI
     */
    updateUI(isSubscribed) {
        const subscribeBtn = document.getElementById('webpush-subscribe-btn');
        const unsubscribeBtn = document.getElementById('webpush-unsubscribe-btn');
        const statusIndicator = document.getElementById('webpush-status');
        const supportMessage = document.getElementById('webpush-support-message');
        const permissionMessage = document.getElementById('webpush-permission-message');
        const blockedMessage = document.getElementById('webpush-blocked-message');

        // Скрываем все сообщения сначала
        if (supportMessage) supportMessage.style.display = 'none';
        if (permissionMessage) permissionMessage.style.display = 'none';
        if (blockedMessage) blockedMessage.style.display = 'none';

        if (!this.isSupported) {
            if (supportMessage) supportMessage.style.display = 'block';
            if (subscribeBtn) subscribeBtn.style.display = 'none';
            if (unsubscribeBtn) unsubscribeBtn.style.display = 'none';
            if (statusIndicator) {
                statusIndicator.textContent = 'Не поддерживается';
                statusIndicator.className = 'badge bg-danger';
            }
            return;
        }

        // Проверяем разрешения на уведомления
        if (Notification.permission === 'denied') {
            if (blockedMessage) blockedMessage.style.display = 'block';
        } else if (Notification.permission === 'default') {
            if (permissionMessage) permissionMessage.style.display = 'block';
        }

        if (subscribeBtn) {
            subscribeBtn.style.display = isSubscribed ? 'none' : 'inline-block';
            subscribeBtn.disabled = !this.isSupported;
        }

        if (unsubscribeBtn) {
            unsubscribeBtn.style.display = isSubscribed ? 'inline-block' : 'none';
        }

        if (statusIndicator) {
            if (isSubscribed) {
                statusIndicator.textContent = 'Push-уведомления включены';
                statusIndicator.className = 'badge bg-success';
            } else if (Notification.permission === 'denied') {
                statusIndicator.textContent = 'Уведомления заблокированы';
                statusIndicator.className = 'badge bg-danger';
            } else {
                statusIndicator.textContent = 'Push-уведомления отключены';
                statusIndicator.className = 'badge bg-secondary';
            }
        }

        // Обновляем иконку в навигации
        const navIcon = document.getElementById('webpush-nav-icon');
        if (navIcon) {
            navIcon.className = isSubscribed ? 
                'ti ti-bell text-success' : 
                'ti ti-bell-off text-muted';
        }
    }

    /**
     * Показ сообщения об успехе
     */
    showSuccess(message) {
        this.showToast(message, 'success');
    }

    /**
     * Показ сообщения об ошибке
     */
    showError(message) {
        this.showToast(message, 'error');
    }

    /**
     * Показ toast-уведомления
     */
    showToast(message, type = 'info') {
        // Если есть система тостов в проекте
        if (window.showToast) {
            window.showToast(message, type);
            return;
        }

        // Простое fallback уведомление
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible`;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
        `;
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Автоматически убираем через 5 секунд
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }

    /**
     * Получение CSRF токена
     */
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        
        return cookieValue || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    /**
     * Конвертация URL-safe base64 в Uint8Array
     */
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    /**
     * Конвертация ArrayBuffer в base64
     */
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    }
}

// Глобальный экземпляр WebPush менеджера
let webPushManager;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    webPushManager = new WebPushManager();
    
    // Привязываем обработчики к кнопкам
    const subscribeBtn = document.getElementById('webpush-subscribe-btn');
    const unsubscribeBtn = document.getElementById('webpush-unsubscribe-btn');
    
    if (subscribeBtn) {
        subscribeBtn.addEventListener('click', () => {
            webPushManager.subscribe();
        });
    }
    
    if (unsubscribeBtn) {
        unsubscribeBtn.addEventListener('click', () => {
            webPushManager.unsubscribe();
        });
    }
});

// Экспорт для глобального использования
window.WebPushManager = WebPushManager;
window.webPushManager = webPushManager;
