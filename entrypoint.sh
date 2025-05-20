#!/bin/sh
# Используйте /bin/sh для большей совместимости с базовыми образами Alpine

set -e # Выходить немедленно, если команда завершается с ошибкой

# Значения по умолчанию, могут быть переопределены переменными окружения
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-visitor_system_user}" # Используем того же пользователя, что и в settings_docker.py
DB_NAME="${POSTGRES_DB:-visitor_system_db}"
DB_PASSWORD="${POSTGRES_PASSWORD:-Sako2020}"

echo "Ожидание доступности базы данных на хосте $DB_HOST и порту $DB_PORT..."

# Цикл до тех пор, пока pg_isready не вернет 0 (успех)
# Таймаут после определенного количества попыток
attempts=0
max_attempts=60 # Например, 60 попыток с задержкой 1 секунда = 1 минута
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" -q || [ "$attempts" -eq 10 ]; do
  attempts=$((attempts+1))
  if [ "$attempts" -gt "$max_attempts" ]; then
    echo "Таймаут подключения к базе данных после $max_attempts попыток."
    exit 1
  fi
  echo "База данных недоступна - ожидание 1 секунда (попытка $attempts/$max_attempts)"
  sleep 1
done

echo "База данных доступна."

# Убедимся, что DJANGO_SETTINGS_MODULE установлен (хотя лучше это делать в docker-compose.yml)
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-visitor_system.settings_docker}
echo "Используются настройки Django: $DJANGO_SETTINGS_MODULE"

echo "Выполнение миграций базы данных..."
poetry run python manage.py migrate --noinput

echo "Миграции завершены."

# Запуск основной команды контейнера (например, Gunicorn), переданной через CMD
echo "Запуск команды: $@"
exec "$@"
