#!/bin/bash
set -e # Немедленно выходить, если команда завершается с ненулевым статусом.

# Переменные для подключения к БД (могут быть переопределены переменными окружения)
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}" # pg_isready использует это для проверки

echo "Ожидание базы данных на $DB_HOST:$DB_PORT..."

# Цикл до тех пор, пока pg_isready не вернет 0 (успех)
# Таймаут после 30 попыток (например, 30 секунд, если задержка 1 секунда)
attempts=0
max_attempts=30
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; do
  attempts=$((attempts+1))
  if [ "$attempts" -gt "$max_attempts" ]; then
    echo "Таймаут подключения к базе данных после $max_attempts попыток."
    exit 1
  fi
  echo "База данных недоступна - ожидание 1 секунда"
  sleep 1
done

echo "База данных доступна - выполнение миграций."

# Выполнение миграций базы данных
poetry run python manage.py migrate --noinput

echo "Миграции завершены. Запуск Gunicorn."

# Выполнение команды, переданной как аргументы этому скрипту (команда Gunicorn)
exec "$@"
