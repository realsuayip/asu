#!/bin/bash

while ! nc -z "$DATABASE_HOST" "$DATABASE_PORT"; do
  sleep 0.1
done

while ! nc -z rabbitmq 5672; do
  sleep 0.1
done

exec "$@"
