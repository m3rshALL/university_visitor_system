#!/bin/sh

# Проверка переменных окружения
echo "Checking environment variables..."
echo "POSTGRES_HOST: $POSTGRES_HOST"
echo "POSTGRES_PORT: $POSTGRES_PORT"
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"

# Ожидание доступности базы данных
echo "Waiting for postgres..."
# Уже установили netcat-openbsd в Dockerfile
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 1
  echo "Waiting for PostgreSQL to be available..."
done
echo "PostgreSQL started"

# Применение миграций базы данных
echo "Applying database migrations..."
python manage.py migrate --noinput

# Сбор статических файлов
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Запуск Gunicorn
echo "Starting Gunicorn..."
exec gunicorn visitor_system.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --log-level=info \
    --log-file=- \
    --access-logfile=-