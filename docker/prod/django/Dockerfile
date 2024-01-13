FROM python:3.12-alpine as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apk add --no-cache build-base libffi-dev python3-dev libpq-dev

COPY deps/prod.txt requirements.txt
RUN pip wheel -r requirements.txt --no-cache-dir --no-deps --wheel-dir /wheels

FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/django/.local/bin:$PATH

WORKDIR /code

RUN apk add --no-cache netcat-openbsd libpq libmagic tini
RUN addgroup -S django && adduser -S django -G django --disabled-password

COPY --chown=django:django . .
COPY --from=builder /wheels /wheels
RUN pip install /wheels/* && rm -rf /wheels

USER django
ENTRYPOINT ["/sbin/tini", "--", "/code/docker/prod/django/entrypoint.sh"]
