FROM python:3.11-alpine as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apk add --no-cache build-base libffi-dev python3-dev libpq-dev

ADD deps/prod.txt /code/requirements.txt
RUN pip install -r /code/requirements.txt --user --no-warn-script-location --no-cache-dir --no-deps

FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/django/.local/bin:$PATH

WORKDIR /code
COPY . /code

RUN apk add --no-cache netcat-openbsd libpq libmagic tini
COPY --from=builder /root/.local /home/django/.local

RUN adduser django -S --disabled-password && chown -R django /code
USER django

ENTRYPOINT ["/sbin/tini", "--", "/code/docker/prod/django/entrypoint.sh"]
