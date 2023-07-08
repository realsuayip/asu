FROM python:3.11-alpine as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apk add --no-cache build-base libffi-dev python3-dev libpq-dev
RUN python -m pip install pip-tools==6.14.0

ADD deps/dev.txt /code/requirements.txt
RUN pip-sync /code/requirements.txt --pip-args "--user --no-warn-script-location --no-cache-dir --no-deps"

FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/django/.local/bin:$PATH

WORKDIR /code
COPY . /code

RUN apk add --no-cache netcat-openbsd libpq libmagic tini
RUN adduser django -S --disabled-password && chown -R django /code

COPY --from=builder /root/.local /home/django/.local

USER django
ENTRYPOINT ["/sbin/tini", "--", "/code/docker/prod/django/entrypoint.sh"]
