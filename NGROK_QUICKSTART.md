# 🚀 Быстрый запуск с ngrok

## Проблема: ERR_NGROK_3200 или 403 Forbidden

### ✅ Решение в 2 шага:

#### 1️⃣ Запустите ngrok с флагом --host-header:
```powershell
# Используйте готовый скрипт (РЕКОМЕНДУЕТСЯ):
.\start_ngrok.bat

# Или вручную:
ngrok http 8000 --host-header=localhost:8000
```

#### 2️⃣ Запустите Django с URL от ngrok:
```powershell
# Скопируйте URL из ngrok (например: https://a006f6aa4edc.ngrok-free.app)
.\start_with_ngrok.bat https://a006f6aa4edc.ngrok-free.app
```

## ⚠️ ВАЖНО!

- **ВСЕГДА** используйте флаг `--host-header=localhost:8000` при запуске ngrok
- **БЕЗ** этого флага ngrok не сможет проксировать запросы к Django
- Используйте HTTPS URL от ngrok (не HTTP)
- При первом посещении нажмите "Visit Site" на странице ngrok

## 📝 Полная документация

См. [NGROK_SETUP.md](./NGROK_SETUP.md) для подробных инструкций и решения других проблем.

## 🔧 Быстрая диагностика

Если что-то не работает:

1. **Остановите ngrok** (Ctrl+C)
2. **Перезапустите с правильным флагом:**
   ```powershell
   ngrok http 8000 --host-header=localhost:8000
   ```
3. **Очистите куки браузера** или откройте в режиме инкогнито
4. **Убедитесь, что Django запущен** с правильным URL

## 📞 Проверка статуса

```powershell
# Проверить, что сервисы запущены
.\check_services_status.bat

# Остановить все
.\stop_all.bat
```

---

**Причина ошибки:** ngrok на бесплатном плане требует явного указания заголовка Host для проксирования запросов к localhost. Без флага `--host-header` ngrok не знает, куда перенаправлять запросы, и показывает свою страницу с ошибкой ERR_NGROK_3200.
