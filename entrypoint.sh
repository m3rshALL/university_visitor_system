#!/bin/sh

# Выход при ошибке
set -e

# Ожидание доступности PostgreSQL (если используется)
if [ -n "$DATABASE_HOST" ] && [ -n "$DATABASE_PORT" ]; then
  echo "Waiting for PostgreSQL at $DATABASE_HOST:$DATABASE_PORT..."
  # nc -z -w1 "$DATABASE_HOST" "$DATABASE_PORT" # netcat может быть не установлен
  # Используем pg_isready, который требует postgresql-client
  while ! pg_isready -h "$DATABASE_HOST" -p "$DATABASE_PORT" -q -U "$DATABASE_USER"; do
    sleep 1
  done
  echo "PostgreSQL started"
fi

# Применение миграций (для Django)
echo "Applying database migrations..."
python manage.py migrate --noinput

# Сбор статики (для Django)
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Запуск основного процесса, переданного как аргументы этому скрипту
# Например, gunicorn, celery worker, etc.
exec "$@"