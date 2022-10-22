#!/bin/bash

if [ "$DATABASE" = "postgres" ]; then
  while ! nc -z "$SQL_HOST" "$SQL_PORT"; do
    sleep 0.1
  done
fi

exec "$@"
