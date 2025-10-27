# HikCentral TLS Validation

## Подготовка сертификатов
1. Получите корневой и промежуточные сертификаты HikCentral.
2. Сложите их в PEM-файл и смонтируйте в контейнер (например, `/etc/ssl/certs/hikcentral.pem`).
3. Установите переменную `HIKCENTRAL_CA_BUNDLE` в путь к PEM.

## Проверка
```bash
curl --cacert /etc/ssl/certs/hikcentral.pem https://hikcentral.example.com/artemis/api/common/v1/status
```
Должен вернуться JSON `{"code":"0", ...}`.

## Smoke-тесты
- `poetry run python visitor_system/manage.py test_hikcentral_connection`
- `poetry run python visitor_system/manage.py test_photo_upload --person <id> --image <path>`
- Создайте гостя через UI и убедитесь, что Celery назначил доступ.

## Алертинг
- В `settings` при `DEBUG=False` и `HIKCENTRAL_VERIFY_TLS=false` приложение не стартует — это защита от отключения TLS.
- В логах HikCentralSession пишет предупреждение, если в dev отключена проверка сертификата. Настройте Prometheus лог-алерт на `HikCentralSession ... TLS verification disabled`.
