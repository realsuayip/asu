#!/bin/bash

if [ "$DATABASE" = "postgres" ]; then
  echo "Checking for postgres..."

  while ! nc -z "$SQL_HOST" "$SQL_PORT"; do
    sleep 0.1
  done

  echo "PostgreSQL is up."
fi

python manage.py migrate

exec "$@"
