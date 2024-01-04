FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

RUN apk add --no-cache build-base libffi-dev python3-dev libpq-dev netcat-openbsd gettext

COPY ./deps/dev.txt ./requirements.txt
RUN pip install -r requirements.txt --no-cache-dir --no-deps

COPY . .
ENTRYPOINT ["/code/docker/dev/entrypoint.sh"]
