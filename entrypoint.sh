#!/bin/sh

# Ожидание доступности базы данных (опционально)
# echo "Waiting for postgres..."
# while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
#   sleep 0.1
# done
# echo "PostgreSQL started"

# Применение миграций базы данных
echo "Applying database migrations..."
poetry run python manage.py migrate --noinput

# Сбор статических файлов
# echo "Collecting static files..."
# poetry run python manage.py collectstatic --noinput --clear

# Запуск Gunicorn
echo "Starting Gunicorn..."
exec poetry run gunicorn --bind 0.0.0.0:8000 your_project_name.wsgi:application \
    --workers 3 \
    --log-level=info \
    --log-file=- \
    --access-logfile=-