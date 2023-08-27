FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apk add --no-cache build-base libffi-dev python3-dev libpq-dev netcat-openbsd

WORKDIR /code

ADD ./deps/dev.txt /code/requirements.txt
RUN pip install -r requirements.txt --no-cache-dir --no-deps

COPY ../.. /code
ENTRYPOINT ["/code/docker/dev/entrypoint.sh"]
