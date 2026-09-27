#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
fi

if [ -n "${BOOTSTRAP_ADMIN_USERNAME:-}" ] && [ -n "${BOOTSTRAP_ADMIN_PASSWORD:-}" ]; then
    python manage.py bootstrap_api_admin
fi

# Una inicialización fallida no elimina el respaldo ni impide arrancar la API.
python manage.py refresh_rates || true

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout 30 \
    --access-logfile - \
    --error-logfile -
