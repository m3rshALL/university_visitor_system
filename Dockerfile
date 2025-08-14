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
RUN poetry install --no-dev --no-interaction --no-ansi

# Копируем весь код проекта
COPY . /app/

RUN python -m pip list | grep Django || echo "Django не найден в списке пакетов!"

# Создаем улучшенный entrypoint скрипт с проверкой и созданием БД
RUN echo '#!/bin/bash\n\
echo "=== Структура директории проекта:"\n\
ls -la /app\n\
echo "=== Установленные пакеты Python:"\n\
pip list\n\
\n\
# Устанавливаем значения по умолчанию для переменных окружения, если они не заданы\n\
: ${DATABASE_HOST:="postgres"}\n\
: ${POSTGRES_PORT:="5432"}\n\
: ${POSTGRES_USER:="postgres"}\n\
: ${POSTGRES_PASSWORD:="postgres"}\n\
: ${POSTGRES_DB:="postgres"}\n\
\n\
echo "Настройки подключения к БД:"\n\
echo "DATABASE_HOST=$DATABASE_HOST"\n\
echo "POSTGRES_PORT=$POSTGRES_PORT"\n\
echo "POSTGRES_USER=$POSTGRES_USER"\n\
echo "POSTGRES_DB=$POSTGRES_DB"\n\
\n\
# Проверяем соединение с PostgreSQL\n\
echo "Ожидание запуска PostgreSQL..."\n\
until PGPASSWORD=$POSTGRES_PASSWORD pg_isready -h $DATABASE_HOST -p $POSTGRES_PORT -U $POSTGRES_USER; do\n\
  echo "PostgreSQL еще не доступен - ожидаем..."\n\
  sleep 2\n\
done\n\
echo "PostgreSQL запущен!"\n\
\n\
# Проверка существования базы данных и создание её при необходимости\n\
echo "Проверка существования базы данных $POSTGRES_DB..."\n\
if ! PGPASSWORD=$POSTGRES_PASSWORD psql -h $DATABASE_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -lqt | cut -d \| -f 1 | grep -qw $POSTGRES_DB; then\n\
  echo "База данных $POSTGRES_DB не существует. Создание..."\n\
  # Создаем базу данных\n\
  PGPASSWORD=$POSTGRES_PASSWORD psql -h $DATABASE_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -c "CREATE DATABASE $POSTGRES_DB;"\n\
  echo "База данных $POSTGRES_DB создана успешно!"\n\
else\n\
  echo "База данных $POSTGRES_DB уже существует."\n\
fi\n\
\n\
# Поиск файла manage.py\n\
MANAGE_PY_PATH=$(find /app -type f -name "manage.py" | head -1)\n\
\n\
if [ -z "$MANAGE_PY_PATH" ]; then\n\
  echo "ОШИБКА: Файл manage.py не найден в проекте."\n\
  exec bash\n\
else\n\
  echo "Найден файл manage.py: $MANAGE_PY_PATH"\n\
  echo "Применяем миграции к базе данных..."\n\
  cd $(dirname $MANAGE_PY_PATH) && python $(basename $MANAGE_PY_PATH) migrate --noinput\n\
  echo "Запуск Django-приложения:"\n\
  cd $(dirname $MANAGE_PY_PATH) && python $(basename $MANAGE_PY_PATH) runserver 0.0.0.0:8000\n\
fi' > /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh

# Открываем порт, на котором будет работать веб-приложение
EXPOSE 8000

# Используем entrypoint скрипт
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]