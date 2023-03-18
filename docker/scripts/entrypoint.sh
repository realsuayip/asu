#!/bin/bash

while ! nc -z "$DATABASE_HOST" "$DATABASE_PORT"; do
  sleep 0.1
done

python manage.py migrate --no-input
exec "$@"
