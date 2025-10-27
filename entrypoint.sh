#!/bin/sh
set -e

APP_DIR=${APP_DIR:-/app}
MANAGE_CMD="python ${APP_DIR}/visitor_system/manage.py"

DB_HOST=${DATABASE_HOST:-${POSTGRES_HOST:-}}
DB_PORT=${DATABASE_PORT:-${POSTGRES_PORT:-}}
DB_USER=${DATABASE_USER:-${POSTGRES_USER:-postgres}}

if [ "${WAIT_FOR_DB:-true}" = "true" ] && [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
  echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
  until pg_isready -h "$DB_HOST" -p "$DB_PORT" -q -U "$DB_USER"; do
    sleep 1
  done
  echo "PostgreSQL is available"
fi

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Running Django migrations"
  ${MANAGE_CMD} migrate --noinput
fi

if [ "${COLLECT_STATIC:-false}" = "true" ]; then
  echo "Collecting static files"
  ${MANAGE_CMD} collectstatic --noinput --clear
fi

exec "$@"
