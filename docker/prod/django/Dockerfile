FROM python:3.12-alpine as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apk add --no-cache build-base libffi-dev python3-dev libpq-dev

COPY deps/prod.txt /code/requirements.txt
RUN pip install -r /code/requirements.txt --user --no-warn-script-location --no-cache-dir --no-deps

FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/django/.local/bin:$PATH

WORKDIR /code

RUN apk add --no-cache netcat-openbsd libpq libmagic tini
RUN addgroup -S django && adduser -S django -G django --disabled-password

COPY --chown=django:django . .
COPY --from=builder --chown=django:django /root/.local /home/django/.local

USER django
ENTRYPOINT ["/sbin/tini", "--", "/code/docker/prod/django/entrypoint.sh"]
