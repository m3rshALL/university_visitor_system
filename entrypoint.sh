#!/bin/sh
# Use /bin/sh for better compatibility with Alpine base images

set -e # Exit immediately if a command exits with error

# Default values, can be overridden by environment variables
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-visitor_system_user}" # Use same user as in settings_docker.py
DB_NAME="${POSTGRES_DB:-visitor_system_db}"
DB_PASSWORD="${POSTGRES_PASSWORD:-Sako2020}"

echo "Waiting for database availability on host $DB_HOST and port $DB_PORT..."

# Loop until pg_isready returns 0 (success)
# Timeout after specified number of attempts
attempts=0
max_attempts=60 # e.g. 60 attempts with 1 second delay = 1 minute
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; do
  attempts=$((attempts+1))
  if [ "$attempts" -gt "$max_attempts" ]; then
    echo "Database connection timeout after $max_attempts attempts."
    exit 1
  fi
  echo "Database unavailable - waiting 1 second (attempt $attempts/$max_attempts)"
  sleep 1
done

echo "Database is available."

# Make sure DJANGO_SETTINGS_MODULE is set
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-visitor_system.settings_docker}
echo "Using Django settings: $DJANGO_SETTINGS_MODULE"

echo "Running database migrations..."
poetry run python manage.py migrate --noinput

echo "Migrations completed."

# Run the main container command (e.g. Gunicorn)
echo "Running command: $@"
exec "$@"
