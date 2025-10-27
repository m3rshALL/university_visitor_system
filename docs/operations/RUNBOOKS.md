# Runbooks

## HikCentral недоступен / TLS ошибка
1. Проверьте хелс `curl -vk https://<hikcentral-host>/artemis/api/common/v1/status`.
2. Если ошибка сертификата:
   - убедитесь, что `HIKCENTRAL_VERIFY_TLS=true`;
   - обновите `HIKCENTRAL_CA_BUNDLE` с актуальным корневым сертификатом;
   - перезапустите `web` и `worker`.
3. Снимите нагрузку (переключите очередь Celery на отложенную обработку, выставьте `HIKCENTRAL_FORCE_ORG=false`, если требуется).
4. Уведомите службу безопасности/оператора HikCentral.
5. После восстановления запустите повторный импорт из Celery (`celery -A visitor_system retry <task-id>` или повторное планирование).

## Celery queue растёт
1. `docker compose -f docker-compose.prod.yml exec worker celery -A visitor_system inspect active`.
2. Проверьте Redis (`redis-cli info | grep -E 'connected_clients|blocked_clients'`).
3. Если worker недоступен:
   - перезапустите `worker` контейнер;
   - увеличьте число воркеров (`deploy.replicas` в orchestrator).
4. Нарушение SLA — сформировать отчёт, зарегистрировать инцидент.

## Redis отказал
1. Проверьте состояние volume `redis_data`.
2. Включите резервный экземпляр (если кластер — переключите на реплику).
3. Очистите очередь Celery (только согласовав с владельцами функций): `celery -A visitor_system purge`.
4. После восстановления перезапустите `worker`, `beat`, `flower`.

## Postgres недоступен
1. Выполните `pg_isready` с каждого сервиса.
2. Проверить логи Postgres на отказ диска/кластера.
3. Поднимите резервную БД из бэкапа (`visitor_system/visitors/management/commands/backup_database.py`).
4. Переключите приложения на новый endpoint (обновите секреты/конфигурацию).
5. После восстановления прогоните smoke-тесты и убедитесь, что нет оторванных миграций.
