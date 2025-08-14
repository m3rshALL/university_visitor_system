#!/bin/sh

# Выход при ошибке
set -e

# Ожидание доступности PostgreSQL (если используется)
# Поддерживаем обе схемы переменных: DATABASE_* или POSTGRES_*
DB_HOST=${DATABASE_HOST:-$POSTGRES_HOST}
DB_PORT=${DATABASE_PORT:-$POSTGRES_PORT}
DB_USER=${DATABASE_USER:-$POSTGRES_USER}

if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
  echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
  while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -q -U "$DB_USER"; do
    sleep 1
  done
  echo "PostgreSQL started"
fi

# Поиск файла manage.py
MANAGE_PY_PATH=$(find /app -type f -name "manage.py" | head -1)

if [ -z "$MANAGE_PY_PATH" ]; then
  echo "ERROR: manage.py not found in /app"
  exit 1
fi

MANAGE_DIR=$(dirname "$MANAGE_PY_PATH")
MANAGE_FILE=$(basename "$MANAGE_PY_PATH")

# Применение миграций (для Django)
echo "Applying database migrations..."
cd "$MANAGE_DIR" && python "$MANAGE_FILE" migrate --noinput

# Сбор статики (для Django)
echo "Collecting static files..."
cd "$MANAGE_DIR" && python "$MANAGE_FILE" collectstatic --noinput --clear

# Запуск основного процесса, переданного как аргументы этому скрипту
# Например, gunicorn, celery worker, etc.
exec "$@"