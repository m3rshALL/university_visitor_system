# Этап 1: Сборка с Poetry
FROM python:3.13-slim-bullseye AS builder

# Установка системных зависимостей, необходимых для сборки некоторых Python пакетов
# Например, postgresql-client для psycopg2, build-essential для компиляции
RUN apt-get update && apt-get install -y --no-install-recommends curl\
    curl \
    build-essential \
    libpq-dev \
    # Другие системные зависимости, если нужны
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
ENV POETRY_VERSION=1.7.1 
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_IN_PROJECT=true 
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION} --yes

WORKDIR /app

# Копируем только файлы зависимостей для кеширования этого слоя
COPY pyproject.toml poetry.lock /app/

# Устанавливаем зависимости без dev-пакетов
# --no-root: не устанавливать сам проект как пакет (если он не библиотека)
# Используем --no-interaction --no-ansi для CI/CD
RUN poetry install --no-interaction --no-ansi --no-dev --no-root

# Этап 2: Финальный образ
FROM python:3.13-slim-bullseye AS final

# Установка системных зависимостей, необходимых для runtime
# Например, postgresql-client для pg_isready или других утилит
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    # libpq5 - уже должен быть если libpq-dev был на builder, но можно явно
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Копируем виртуальное окружение, созданное Poetry
COPY --from=builder /app/.venv ./.venv
# Активируем venv
ENV PATH="/app/.venv/bin:$PATH"

# Копируем весь код проекта
COPY . .

# Копируем и делаем исполняемым entrypoint скрипт (если используется)
COPY ./entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Открываем порт, на котором будет работать веб-приложение
EXPOSE 8000

# Пользователь (опционально, но рекомендуется для безопасности)
# RUN addgroup --system app && adduser --system --group app
# USER app

# Entrypoint (если используется)
# ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Команда по умолчанию (будет переопределена в docker-compose.yml для разных сервисов)
# CMD ["gunicorn", "project_config.wsgi:application", "--bind", "0.0.0.0:8000"]