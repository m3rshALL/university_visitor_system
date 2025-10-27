# Управление секретами и ротация ключей

## Перенос секретов
- Создайте централизованное хранилище (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault или GitHub Actions Encrypted Secrets).
- Внесите туда:
  - `DJANGO_SECRET_KEY`
  - креденшелы Azure AD (`MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MS_TENANT_ID`)
  - HikCentral (`HIKCENTRAL_INTEGRATION_KEY`, `HIKCENTRAL_INTEGRATION_SECRET`, `HIKCENTRAL_USERNAME`, `HIKCENTRAL_PASSWORD`)
  - ключи веб-пушей (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`)
  - Sentry (`SENTRY_DSN`, `SENTRY_RELEASE`)
  - любые дополнительные технические токены (SMTP, API внешних сервисов).
- Запретите локальные `.env` в репозитории. Для разработчиков оставьте `.env.example` с пустыми значениями.

## Ротация (каждые 90 дней или при инциденте)
1. Снимите бэкап текущих значений.
2. Сгенерируйте новые ключи:
   - Django: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
   - HikCentral/AD — через соответствующие консоли.
   - VAPID: `npx web-push generate-vapid-keys`.
3. Обновите значения в сторе, затем в Kubernetes/Compose перезапустите поды с `redeploy`.
4. Протестируйте логин, отправку уведомлений, интеграцию HikCentral.
5. Задокументируйте дату ротации в журнале `docs/operations/SECRET_ROTATION_LOG.md` (создайте при необходимости).

## Контроль доступа
- Ограничьте доступ к секретам списком доверенных операторов.
- Включите аудит чтения/изменения (CloudTrail, Vault audit devices).
- Настройте уведомления на изменение ключей (Slack/Email).

## Автоматизация
- Подготовьте GitHub Action/Job, который синхронизирует секреты из стора в окружение при деплое.
- Добавьте unit-тест `manage.py check --deploy` в пайплайн, чтобы убедиться, что секреты настроены.
