#!/bin/sh

# Ожидание доступности базы данных
echo "Waiting for postgres..."
# Устанавливаем netcat для проверки соединения
apt-get update && apt-get install -y netcat-openbsd
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 1
  echo "Waiting for PostgreSQL to be available..."
done
echo "PostgreSQL started"

# Применение миграций базы данных
echo "Applying database migrations..."
cd /app/visitor_system
poetry run python manage.py migrate --noinput

# Сбор статических файлов
echo "Collecting static files..."
poetry run python manage.py collectstatic --noinput --clear

# Запуск Gunicorn
echo "Starting Gunicorn..."
cd /app/visitor_system
exec poetry run gunicorn --bind 0.0.0.0:8000 visitor_system.wsgi:application \
    --workers 3 \
    --log-level=info \
    --log-file=- \
    --access-logfile=-