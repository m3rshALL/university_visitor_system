# CI/CD Pipeline Overview

## Структура workflow
Файл: `.github/workflows/ci.yml`

### Джобы
1. **lint-and-test**
   - Устанавливает Poetry.
   - Поднимает Postgres/Redis в сервисах.
   - Выполняет:
     - `poetry run flake8`
     - `poetry run python visitor_system/manage.py test --parallel`
   - Сохраняет артефакт отчёта тестов.
2. **security-scan**
   - Устанавливает `pip-audit` и `bandit`.
   - Запускает сканы зависимостей и исходников.
3. **docker-image**
   - Собирает образ `visitor-system/web`.
   - Прогоняет `docker compose -f docker-compose.prod.yml config` для валидации.
   - Публикует образ в реестр (Docker Hub, GHCR, ECR).

## Настройка секретов репозитория
- `REGISTRY_USERNAME` / `REGISTRY_PASSWORD`
- `DJANGO_SECRET_KEY`
- `MICROSOFT_CLIENT_ID/MICROSOFT_CLIENT_SECRET/MS_TENANT_ID`
- `HIKCENTRAL_*`
- `SENTRY_DSN`

## Проверки перед деплоем
- Workflow должен запускаться на `pull_request` и `push` в `main`.
- Для релиза используйте `workflow_dispatch` с параметрами `environment` и `image_tag`.
- После публикации образа запускайте отдельный deployment-пайплайн (ArgoCD/GitOps или ansible плейбук) с обновлённым тегом.
