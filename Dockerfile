# Этап 1: Установка зависимостей
FROM python:3.12-slim-bullseye

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Убедимся, что pip не создает кеш
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Копируем только файлы зависимостей для кеширования этого слоя
COPY pyproject.toml poetry.lock* /app/

# Установка Poetry
RUN pip install poetry==1.7.1 \
    && poetry config virtualenvs.create false

# Устанавливаем зависимости из poetry.lock
RUN poetry lock --no-interaction --no-ansi \
    && poetry install --only main --no-interaction --no-ansi

# Копируем весь код проекта
COPY . /app/

RUN python -m pip list | grep Django || echo "Django не найден в списке пакетов!"

# Используем проектный entrypoint (исполняет переданную команду)
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Открываем порт, на котором будет работать веб-приложение
EXPOSE 8000

# Используем entrypoint скрипт по умолчанию, но команду передаём из docker-compose
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]