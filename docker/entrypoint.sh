#!/bin/sh
set -e

if [ "${DB_ENGINE}" = "postgresql" ]; then
  echo "Waiting for PostgreSQL..."
  ATTEMPTS=0
  until python manage.py showmigrations >/dev/null 2>&1; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ "$ATTEMPTS" -ge 30 ]; then
      echo "PostgreSQL is still unavailable after multiple attempts."
      exit 1
    fi
    sleep 2
  done
fi

echo "Applying migrations..."
python manage.py migrate --noinput

exec "$@"
