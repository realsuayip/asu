FROM python:3.11-bullseye

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update && apt-get install -y --no-install-recommends netcat

WORKDIR /code

ADD ./deps/dev.txt /code/requirements.txt
RUN pip install -r requirements.txt --no-cache-dir --no-deps

COPY ../.. /code
ENTRYPOINT ["/code/docker/dev/entrypoint.sh"]
