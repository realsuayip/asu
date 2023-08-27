#!/bin/sh

while ! nc -z "$DATABASE_HOST" "$DATABASE_PORT"; do
  sleep 0.1
done

if [ "${DJANGO_CONTEXT}" = "celery" ]; then
  while ! nc -z rabbitmq 5672; do
    sleep 0.1
  done
fi

if [ "${DJANGO_CONTEXT}" = "web" ]; then
  python manage.py migrate --no-input
fi

exec "$@"
